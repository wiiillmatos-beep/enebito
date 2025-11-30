import pandas as pd
import requests
import time
import schedule
import os
import io
import json
import random 
from flask import Flask
from threading import Thread

# Importações do Python Telegram Bot (PTB)
from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackContext, filters

# --- ⚙️ CONFIGURAÇÕES (LENDO VARIÁVEIS DE AMBIENTE) ---

# IDs essenciais lidos do ambiente do Render
BOT_TOKEN = os.getenv("BOT_TOKEN") 
CHAT_ID = os.getenv("CHAT_ID")
# Lê o ID do admin. O valor padrão 0 garante que a conversão para int funcione mesmo se a variável não estiver setada
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", 0)) 

# A mensagem de erro será impressa, mas não impede o Flask de iniciar.
if not BOT_TOKEN or not CHAT_ID or ADMIN_USER_ID == 0:
    print("ERRO CRÍTICO: Token, Chat ID ou Admin ID não configurados no ambiente. Os comandos manuais não funcionarão.")

# Link do seu feed de produtos em CSV da Eneba
PLANILHA_URL = "https://www.eneba.com/rss/products.csv?version=3&influencer_id=WiillzeraTV"
RASTREAMENTO_FILE = 'sent_offers_ids.txt' 
PRECO_MAXIMO_FILTRO_BRL = 150.00 

# Nomes das colunas no seu arquivo CSV
COLUNA_ID_PRODUTO = 'id'        
COLUNA_PRODUTO = 'name'         
COLUNA_PRECO_USD = 'final_price' 
COLUNA_LINK = 'url'             

# Inicializa o Bot do Telegram para uso em funções (fora dos Handlers do PTB)
# Adicionamos um placeholder para evitar erro se o BOT_TOKEN for None
telegram_bot = Bot(token=BOT_TOKEN or "placeholder") 

# --- 💵 FUNÇÃO PARA BUSCAR A COTAÇÃO DE CÂMBIO ---

def get_exchange_rate():
    """Busca a taxa de câmbio USD/BRL atualizada."""
    API_URL = "https://api.exchangerate-api.com/v4/latest/USD"
    try:
        response = requests.get(API_URL, timeout=10) 
        response.raise_for_status() 
        return response.json()['rates']['BRL']
    except requests.exceptions.RequestException:
        print("⚠️ Erro ao obter câmbio. Usando taxa fallback (5.00).")
        return 5.00 

# --- 💾 RASTREAMENTO DE OFERTAS ---
def load_sent_ids():
    if not os.path.exists(RASTREAMENTO_FILE):
        return set()
    with open(RASTREAMENTO_FILE, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def save_sent_ids(ids_para_adicionar):
    with open(RASTREAMENTO_FILE, 'a') as f:
        for product_id in ids_para_adicionar:
            f.write(f"{product_id}\n")

# --- 🚀 FUNÇÕES DE FORMATAÇÃO E ENVIO ---

def formatar_oferta(row, exchange_rate):
    """Formata os dados da linha do CSV em uma mensagem com botão de compra."""
    produto = row[COLUNA_PRODUTO]
    # Trata valores não numéricos no preço, se necessário
    try:
        preco_usd = float(row[COLUNA_PRECO_USD])
    except ValueError:
        preco_usd = 0.0
    
    preco_brl = preco_usd * exchange_rate
    link = row[COLUNA_LINK]
    
    preco_brl_formatado = f"{preco_brl:.2f}".replace('.', ',')
    
    mensagem = (
        f"🔥 **NOVA OFERTA!** 🔥\n\n"
        f"🏷️ Jogo: **{produto}**\n"
        f"💸 Preço Estimado: **R$ {preco_brl_formatado}**\n"
        f"_Preço em USD: ${preco_usd:.2f} | Câmbio: {exchange_rate:.4f}_\n\n"
        f"[🛒 COMPRE AQUI! 🛒]({link})\n\n"
        f"---"
    )
    return mensagem

async def enviar_mensagem(chat_id_destino, texto):
    """Função assíncrona para envio de mensagens, usando o objeto Bot."""
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

# --- 🚀 LÓGICA DE BUSCA DE OFERTAS AGENDADAS ---

def buscar_e_enviar_ofertas(numero_de_ofertas):
    """Busca um número específico de ofertas novas e as envia."""
    print(f"Buscando {numero_de_ofertas} novas ofertas no feed CSV...")
    
    if not BOT_TOKEN or not CHAT_ID: return

    current_exchange_rate = get_exchange_rate()
    sent_ids = load_sent_ids()
    ids_enviados_nesta_execucao = []
    
    try:
        feed_response = requests.get(PLANILHA_URL, timeout=30)
        feed_response.raise_for_status()
        data = io.StringIO(feed_response.content.decode('utf-8'))
        df = pd.read_csv(data)
        
        df = df.dropna(subset=[COLUNA_ID_PRODUTO, COLUNA_PRECO_USD])
        df[COLUNA_ID_PRODUTO] = df[COLUNA_ID_PRODUTO].astype(str)
        df[COLUNA_PRECO_USD] = pd.to_numeric(df[COLUNA_PRECO_USD], errors='coerce')
        
        df['price_brl'] = df[COLUNA_PRECO_USD] * current_exchange_rate
        df_filtrado = df[df['price_brl'] <= PRECO_MAXIMO_FILTRO_BRL]
        
        ofertas_novas = df_filtrado[~df_filtrado[COLUNA_ID_PRODUTO].isin(sent_ids)]
        
        if ofertas_novas.empty:
            print("Nenhuma nova oferta que atenda aos filtros encontrada.")
            return

        ofertas_para_enviar = ofertas_novas.head(numero_de_ofertas)
        print(f"Enviando {len(ofertas_para_enviar)} ofertas...")
        
        import asyncio
        for _, row in ofertas_para_enviar.iterrows():
            mensagem_formatada = formatar_oferta(row, current_exchange_rate)
            
            # Executa a função assíncrona
            asyncio.run(enviar_mensagem(CHAT_ID, mensagem_formatada))
            
            product_id = row[COLUNA_ID_PRODUTO]
            ids_enviados_nesta_execucao.append(product_id)
            print(f"  -> Oferta '{row[COLUNA_PRODUTO]}' enviada.")

        if ids_enviados_nesta_execucao:
            save_sent_ids(ids_enviados_nesta_execucao)
            print(f"Rastreamento atualizado com {len(ids_enviados_nesta_execucao)} novos IDs.")

    except Exception as e:
        print(f"Ocorreu um erro geral no processo de busca agendada: {e}")

# --- 📅 FUNÇÕES DE AGENDAMENTO ESPECÍFICAS ---

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
    schedule.every().day.at("13:00").do(agendar_1300) 
    schedule.every().day.at("17:00").do(agendar_1700) 
    schedule.every().day.at("20:00").do(agendar_2000) 
    print("Agendamento diário configurado para 09:30, 11:00, 13:00, 17:00 e 20:00.")

# --- 🔑 FUNÇÕES PARA COMANDOS MANUAIS (PTB) ---

async def check_admin(update: Update) -> bool:
    """Verifica se o comando foi enviado no chat privado e pelo Admin."""
    user = update.effective_user
    
    if update.effective_chat.type != "private":
        await update.message.reply_text("Este comando só pode ser usado no chat privado com o bot.")
        return False
        
    if user.id != ADMIN_USER_ID:
        await update.message.reply_text("🚫 Acesso negado. Você não é o administrador deste bot.")
        return False
    
    return True

async def start_command(update: Update, context: CallbackContext) -> None:
    """Comando /start: Envia uma oferta aleatória do feed (Admin Only)."""
    if not await check_admin(update):
        return

    await update.message.reply_text("Buscando uma oferta aleatória para envio...")
    
    current_exchange_rate = get_exchange_rate()
    
    try:
        feed_response = requests.get(PLANILHA_URL, timeout=30)
        feed_response.raise_for_status()
        data = io.StringIO(feed_response.content.decode('utf-8'))
        df = pd.read_csv(data)
        
        sent_ids = load_sent_ids()
        df_filtrado = df[~df[COLUNA_ID_PRODUTO].isin(sent_ids)]
        
        if df_filtrado.empty:
            await update.message.reply_text("O feed está vazio ou todas as ofertas já foram enviadas recentemente!")
            return

        row = df_filtrado.sample(n=1).iloc[0]
        mensagem_formatada = formatar_oferta(row, current_exchange_rate)
        
        if await enviar_mensagem(CHAT_ID, mensagem_formatada):
            await update.message.reply_text(f"✅ Oferta aleatória ({row[COLUNA_PRODUTO]}) enviada com sucesso para o canal!")
            save_sent_ids([row[COLUNA_ID_PRODUTO]])
        else:
            await update.message.reply_text("❌ Falha ao enviar a oferta para o canal.")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao buscar/enviar oferta aleatória: {e}")


async def promo_command(update: Update, context: CallbackContext) -> None:
    """Comando /promo [link]: Envia uma oferta específica (Admin Only)."""
    if not await check_admin(update):
        return

    if not context.args or not context.args[0].startswith("http"):
        await update.message.reply_text("❌ Formato incorreto. Use: `/promo https://completa.com.br/`")
        return

    url_do_produto = context.args[0]
    await update.message.reply_text(f"Buscando detalhes do produto na URL: `{url_do_produto}`")
    
    current_exchange_rate = get_exchange_rate()
    
    try:
        feed_response = requests.get(PLANILHA_URL, timeout=30)
        feed_response.raise_for_status()
        data = io.StringIO(feed_response.content.decode('utf-8'))
        df = pd.read_csv(data)

        produto_encontrado = df[df[COLUNA_LINK] == url_do_produto].head(1)
        
        if produto_encontrado.empty:
            await update.message.reply_text("❌ Produto não encontrado no feed CSV da Eneba. Verifique a URL.")
            return

        row = produto_encontrado.iloc[0]
        mensagem_formatada = formatar_oferta(row, current_exchange_rate)
        
        if await enviar_mensagem(CHAT_ID, mensagem_formatada):
            await update.message.reply_text(f"✅ Oferta específica ({row[COLUNA_PRODUTO]}) enviada com sucesso para o canal!")
        else:
            await update.message.reply_text("❌ Falha ao enviar a oferta para o canal.")

    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao processar o link: {e}")

# --- 🌐 INICIALIZAÇÃO E INTEGRAÇÃO FLASK/PTB ---

app = Flask(__name__)
PORT = int(os.environ.get("PORT", 5000))

@app.route('/')
def home():
    """Endpoint para o Render e serviços de Keep-Alive/Monitoramento."""
    return "Bot de Ofertas está online e verificando o feed...", 200

# 1. Thread para o Scheduler (Agendamento)
def run_scheduler_loop():
    """Função que executa o loop do scheduler."""
    configurar_agendamento()
    print("Iniciando loop do scheduler em background...")
    while True:
        schedule.run_pending()
        time.sleep(1)

# 2. Thread para o Bot do Telegram (Comandos)
def run_telegram_bot_loop():
    """Função que executa o loop de escuta de comandos do Telegram."""
    if not BOT_TOKEN:
        print("Bot do Telegram (Comandos) não iniciado: BOT_TOKEN ausente.")
        return
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Handlers para os comandos
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("promo", promo_command))
        
        print("Bot do Telegram (Comandos) iniciado em modo polling...")
        # CORREÇÃO: run_until_terminated() é o método correto para rodar em um thread separado
        application.run_until_terminated() 
        
    except Exception as e:
        print(f"ERRO CRÍTICO no Bot do Telegram (Polling falhou): {e}")

# --- INÍCIO DO PROGRAMA ---

if __name__ == '__main__':
    print("===========================================")
    print("  Iniciando Bot de Ofertas Híbrido...      ")
    print("===========================================")
    
    # Inicia o loop do Scheduler (agendamento)
    scheduler_thread = Thread(target=run_scheduler_loop)
    scheduler_thread.start()
    
    # Inicia o loop do Bot (comandos)
    telegram_thread = Thread(target=run_telegram_bot_loop)
    telegram_thread.start()

    # Inicia o servidor Flask na thread principal (para que o Render não durma)
    print(f"Servidor Flask iniciado na porta {PORT} (Keep Alive)...")
    app.run(host='0.0.0.0', port=PORT)
