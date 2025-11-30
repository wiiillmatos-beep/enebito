import requests
from bs4 import BeautifulSoup
import time
import schedule
import os
import io
import json
import random 
import asyncio
from flask import Flask
from threading import Thread
from waitress import serve

# Importações do Python Telegram Bot (PTB)
from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackContext, filters

# --- ⚙️ CONFIGURAÇÕES (LENDO VARIÁVEIS DE AMBIENTE) ---

BOT_TOKEN = os.getenv("BOT_TOKEN") 
CHAT_ID = os.getenv("CHAT_ID")

# LEITURA ROBUSTA DO ADMIN_USER_ID
admin_user_id_str = os.getenv("ADMIN_USER_ID")
if admin_user_id_str and admin_user_id_str.isdigit():
    ADMIN_USER_ID = int(admin_user_id_str)
else:
    print("⚠️ ERRO: ADMIN_USER_ID não definido ou não é um número. Comandos de admin serão desativados.")
    ADMIN_USER_ID = 0
    
# ** LINK DE SCRAPING ESPECÍFICO **
SCRAPING_URL = "https://www.eneba.com/br/store/xbox-games?drms[]=xbox&page=1&regions[]=egypt&regions[]=latam&regions[]=saudi_arabia&regions[]=argentina&types[]=game" 

PRECO_MAXIMO_FILTRO_BRL = 150.00 
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
RASTREAMENTO_FILE = 'sent_offers_ids.txt' 

telegram_bot = Bot(token=BOT_TOKEN or "placeholder") 

# --- 💵 FUNÇÃO PARA BUSCAR A COTAÇÃO DE CÂMBIO (EUR/BRL) ---

def get_exchange_rate():
    """Busca a taxa de câmbio EUR/BRL atualizada."""
    API_URL = "https://api.exchangerate-api.com/v4/latest/EUR"
    try:
        response = requests.get(API_URL, timeout=10) 
        response.raise_for_status() 
        return response.json()['rates']['BRL']
    except requests.exceptions.RequestException:
        print("⚠️ Erro ao obter câmbio EUR/BRL. Usando taxa fallback (5.50).")
        return 5.50

# --- 💾 RASTREAMENTO E ENVIO ---

def load_sent_ids():
    """Carrega IDs de ofertas já enviadas."""
    if not os.path.exists(RASTREAMENTO_FILE):
        return set()
    with open(RASTREAMENTO_FILE, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def save_sent_ids(ids_para_adicionar):
    """Salva novos IDs de ofertas enviadas."""
    with open(RASTREAMENTO_FILE, 'a') as f:
        for product_id in ids_para_adicionar:
            f.write(f"{product_id}\n")

async def enviar_mensagem(chat_id_destino, texto):
    """Envia a mensagem ao Telegram."""
    if not telegram_bot.token or not chat_id_destino:
        return False
        
    try:
        await telegram_bot.send_message(
            chat_id=chat_id_destino,
            text=texto,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False
        )
        return True
    except Exception as e:
        print(f"Erro ao enviar mensagem para {chat_id_destino}: {e}")
        return False

def formatar_oferta(oferta, exchange_rate):
    """Formata os dados extraídos em uma mensagem."""
    produto = oferta.get('name', 'Produto Desconhecido')
    preco_eur = oferta.get('price_usd', 0.0)
    link = oferta.get('url', '#')
    
    try:
        preco_eur = float(preco_eur)
        preco_brl = preco_eur * exchange_rate
    except (ValueError, TypeError):
        preco_brl = 0.0
        
    preco_brl_formatado = f"{preco_brl:.2f}".replace('.', ',')
    
    mensagem = (
        f"🔥 **NOVA OFERTA!** 🔥\n\n"
        f"🏷️ Jogo: **{produto}**\n"
        f"💸 Preço Estimado: **R$ {preco_brl_formatado}**\n"
        f"_Preço em EUR: €{preco_eur:.2f} | Câmbio: {exchange_rate:.4f}_\n\n"
        f"[🛒 COMPRE AQUI! 🛒]({link})\n\n"
        f"---"
    )
    return mensagem

# --- 🕷️ FUNÇÃO DE WEB SCRAPING ---

def perform_scraping(url):
    """Extrai nome, preço e link dos produtos da Eneba usando BeautifulSoup."""
    headers = {'User-Agent': USER_AGENT}
    ofertas = []
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Seletor para os cards de produto
        product_cards = soup.find_all('div', class_=lambda c: c and 'product-list-item' in c)
        
        if not product_cards:
            print("⚠️ Scraping: Não encontrou cards de produto. O seletor pode estar desatualizado.")
            return ofertas

        for card in product_cards:
            link_tag = card.find('a', href=True)
            link = "https://www.eneba.com" + link_tag['href'] if link_tag else None
            product_id = link.split('/')[-1] if link else None
            
            name_tag = card.find('span', class_=lambda c: c and 'product-title' in c)
            name = name_tag.text.strip() if name_tag else None
            
            price_tag = card.find('div', class_=lambda c: c and 'product-price' in c)
            price_eur = None
            if price_tag:
                price_text = price_tag.text.replace('$', '').replace('€', '').replace('R', '').replace(',', '.').strip()
                try:
                    price_eur = float(price_text)
                except ValueError:
                    price_eur = 0.0
            
            if name and link and price_eur:
                 ofertas.append({
                    'id': product_id,
                    'name': name,
                    'price_usd': price_eur,
                    'url': link
                })

        print(f"Scraping concluído: Encontradas {len(ofertas)} ofertas.")
        return ofertas

    except requests.exceptions.RequestException as e:
        print(f"ERRO DE CONEXÃO/SCRAPING: {e}")
        return []

# --- 🚀 LÓGICA DE BUSCA DE OFERTAS AGENDADAS (COM SCRAPING) ---

def buscar_e_enviar_ofertas(numero_de_ofertas):
    """Faz o scraping, filtra e envia ofertas novas."""
    print(f"Iniciando Scraping e buscando {numero_de_ofertas} novas ofertas...")
    
    if not BOT_TOKEN or not CHAT_ID: return

    current_exchange_rate = get_exchange_rate()
    sent_ids = load_sent_ids()
    ids_enviados_nesta_execucao = []
    
    ofertas_extraidas = perform_scraping(SCRAPING_URL)
    
    if not ofertas_extraidas:
        print("Scraping falhou ou não retornou dados. Nenhuma oferta para processar.")
        return

    ofertas_para_enviar = []
    
    for oferta in ofertas_extraidas:
        product_id = oferta.get('id')
        price_eur = oferta.get('price_usd', 0.0) 
        
        if product_id not in sent_ids:
            try:
                price_brl = price_eur * current_exchange_rate
                if price_brl <= PRECO_MAXIMO_FILTRO_BRL:
                    ofertas_para_enviar.append(oferta)
            except (TypeError, ValueError):
                continue

    ofertas_para_enviar = ofertas_para_enviar[:numero_de_ofertas]

    if not ofertas_para_enviar:
        print("Nenhuma nova oferta que atenda aos filtros foi encontrada após o scraping.")
        return
    
    print(f"Enviando {len(ofertas_para_enviar)} ofertas...")
    
    for oferta in ofertas_para_enviar:
        mensagem_formatada = formatar_oferta(oferta, current_exchange_rate)
        
        asyncio.run(enviar_mensagem(CHAT_ID, mensagem_formatada))
        
        product_id = oferta.get('id')
        ids_enviados_nesta_execucao.append(product_id)
        print(f"  -> Oferta '{oferta.get('name', 'N/A')}' enviada.")

    if ids_enviados_nesta_execucao:
        save_sent_ids(ids_enviados_nesta_execucao)
        print(f"Rastreamento atualizado com {len(ids_enviados_nesta_execucao)} novos IDs.")

# --- 📅 FUNÇÕES DE AGENDAMENTO ---

def enviar_mensagem_personalizada(mensagem):
    """Envia uma mensagem de texto simples e depois busca 4 ofertas."""
    import asyncio
    asyncio.run(enviar_mensagem(CHAT_ID, mensagem))
    buscar_e_enviar_ofertas(4) 

def agendar_0930():
    mensagem = "☀️ **BOM DIA, CHAT! É HORA DE ECONOMIZAR!** 🚀\n\nAcompanhe as ofertas fresquinhas para começar o dia no game!"
    enviar_mensagem_personalizada(mensagem)

def agendar_1100():
    mensagem = "⚡️ **ALERTA DE OFERTAS DE MEIO DE MANHÃ!** ☕️\n\nNovos preços acabaram de chegar. Não perca tempo!"
    enviar_mensagem_personalizada(mensagem)

def agendar_1225():
    mensagem = "⏳ **ALERTA DE OFERTAS PÓS-ALMOÇO!** 🎮\n\nEstá na hora perfeita para caçar aquele jogo que ficou na lista. Veja 4 ofertas que acabaram de cair!"
    enviar_mensagem_personalizada(mensagem)

def agendar_1300():
    mensagem = "🍕 **PAUSA PARA O ALMOÇO, OFERTAS NA MESA!** 🍽️\n\nQue tal um jogo novo para animar o resto do seu dia? Confira 4 ofertas!"
    enviar_mensagem_personalizada(mensagem)

def agendar_1700():
    mensagem = "⏰ **ÚLTIMA CHAMADA ANTES DO PICO DA NOITE!** 🥳\n\nAs melhores ofertas costumam ir rápido. Garanta a sua agora!"
    enviar_mensagem_personalizada(mensagem)

def agendar_2000():
    mensagem = "🌙 **BOA NOITE E BOAS OFERTAS!** ✨\n\nRelaxe e explore 4 jogos incríveis a preços imperdíveis para fechar o dia."
    enviar_mensagem_personalizada(mensagem)

# --- ⏰ AGENDAMENTO DAS FUNÇÕES ---
def configurar_agendamento():
    schedule.every().day.at("09:30").do(agendar_0930) 
    schedule.every().day.at("11:00").do(agendar_1100) 
    schedule.every().day.at("12:25").do(agendar_1225)
    schedule.every().day.at("13:00").do(agendar_1300) 
    schedule.every().day.at("17:00").do(agendar_1700) 
    schedule.every().day.at("20:00").do(agendar_2000) 
    print("Agendamento diário configurado para 09:30, 11:00, 12:25, 13:00, 17:00 e 20:00.")

# --- 🔑 FUNÇÕES PARA COMANDOS MANUAIS (COM SCRAPING) ---

async def check_admin(update: Update) -> bool:
    """Verifica se o comando foi enviado no chat privado e pelo Admin."""
    user = update.effective_user
    
    if ADMIN_USER_ID == 0:
        await update.message.reply_text("🚫 Configuração: O ADMIN_USER_ID não está configurado corretamente. Comandos de admin desativados.")
        return False

    if update.effective_chat.type != "private":
        await update.message.reply_text("Este comando só pode ser usado no chat privado com o bot.")
        return False
        
    if user.id != ADMIN_USER_ID:
        await update.message.reply_text("🚫 Acesso negado. Você não é o administrador deste bot.")
        return False
    
    return True

async def start_command(update: Update, context: CallbackContext) -> None:
    """Comando /start: Busca ofertas via scraping e envia uma aleatória (Admin Only)."""
    if not await check_admin(update):
        return

    await update.message.reply_text("Iniciando Scraping e buscando uma oferta aleatória para envio...")
    
    current_exchange_rate = get_exchange_rate()
    sent_ids = load_sent_ids()
    
    try:
        ofertas_extraidas = perform_scraping(SCRAPING_URL)
        
        ofertas_filtradas = []
        for oferta in ofertas_extraidas:
            product_id = oferta.get('id')
            price_eur = oferta.get('price_usd', 0.0)
            
            if product_id not in sent_ids:
                try:
                    price_brl = price_eur * current_exchange_rate
                    if price_brl <= PRECO_MAXIMO_FILTRO_BRL:
                        ofertas_filtradas.append(oferta)
                except (TypeError, ValueError):
                    continue
        
        if not ofertas_filtradas:
            await update.message.reply_text("Scraping efetuado, mas nenhuma oferta nova e filtrada foi encontrada!")
            return

        oferta = random.choice(ofertas_filtradas)
        mensagem_formatada = formatar_oferta(oferta, current_exchange_rate)
        
        if await enviar_mensagem(CHAT_ID, mensagem_formatada):
            await update.message.reply_text(f"✅ Oferta aleatória ({oferta.get('name', 'N/A')}) enviada com sucesso para o canal!")
            save_sent_ids([oferta.get('id')])
        else:
            await update.message.reply_text("❌ Falha ao enviar a oferta para o canal.")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao buscar/enviar oferta: Scraping falhou.")
        print(f"ERRO NO COMANDO /START (SCRAPING): {e}")


async def promo_command(update: Update, context: CallbackContext) -> None:
    """Comando /promo [link]: Envia uma oferta específica (Web Scraping Simples)."""
    if not await check_admin(update):
        return

    if not context.args or not context.args[0].startswith("http"):
        await update.message.reply_text("❌ Formato incorreto. Use: `/promo https://completa.com.br/`")
        return

    url_do_produto = context.args[0]
    await update.message.reply_text(f"Iniciando Scraping para obter detalhes da URL: `{url_do_produto}`")
    
    current_exchange_rate = get_exchange_rate()
    headers = {'User-Agent': USER_AGENT}
    
    try:
        response = requests.get(url_do_produto, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        name_tag = soup.find('h1', class_=lambda c: c and 'pdp-title' in c) 
        name = name_tag.text.strip() if name_tag else "Produto Promovido"

        price_tag = soup.find('div', class_=lambda c: c and 'pdp-price' in c) 
        price_eur = 0.0
        if price_tag:
             price_text = price_tag.text.replace('$', '').replace('€', '').replace('R', '').replace(',', '.').strip()
             try:
                price_eur = float(price_text)
             except ValueError:
                price_eur = 0.0

        oferta = {
            'id': url_do_produto.split('/')[-1],
            'name': name,
            'price_usd': price_eur, 
            'url': url_do_produto
        }

        mensagem_formatada = formatar_oferta(oferta, current_exchange_rate)
        
        if await enviar_mensagem(CHAT_ID, mensagem_formatada):
            await update.message.reply_text(f"✅ Oferta específica ({oferta['name']}) enviada com sucesso para o canal!")
        else:
            await update.message.reply_text("❌ Falha ao enviar a oferta para o canal.")

    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao processar o link (Scraping falhou): {e}")
        print(f"ERRO NO COMANDO /PROMO (SCRAPING): {e}")

# --- 🌐 FUNÇÕES DE SERVIÇO ---

app = Flask(__name__)
PORT = int(os.environ.get("PORT", 5000))

@app.route('/')
def home():
    """Endpoint para o Render e serviços de Keep-Alive/Monitoramento."""
    return "Bot de Ofertas está online e verificando o feed...", 200

# Função separada para rodar o bot do Telegram de forma não bloqueante
def run_telegram_bot(app_instance):
    """Inicia o Telegram Bot em sua própria thread."""
    try:
        print("Bot do Telegram (Comandos) iniciado em modo 'run_non_blocking' (Thread separada).")
        app_instance.run_
