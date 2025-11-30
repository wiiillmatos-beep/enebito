import requests
from bs4 import BeautifulSoup
import time
import schedule
import os
import asyncio
from threading import Thread
import logging
from flask import Flask

# Importações do Python Telegram Bot (PTB)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackContext

# Configuração de Log
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- ⚙️ CONFIGURAÇÕES ---

BOT_TOKEN = os.getenv("BOT_TOKEN") 
CHAT_ID_DESTINO = os.getenv("CHAT_ID") 
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID") 

# Parâmetros fixos do seu link de afiliado
AFILIADO_ID = "WiillzeraTV"
PARAMS_AFILIADO = f"af_id={AFILIADO_ID}&currency=BRL&region=global&utm_source={AFILIADO_ID}&utm_medium=infl"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Variáveis globais
application = None 
admin_user_id_int = 0
# O Render define a porta que deve ser usada via variável de ambiente 'PORT'
PORT = int(os.environ.get("PORT", 5000)) 

# --- 💵 FUNÇÕES DE SUPORTE ---

def get_exchange_rate():
    """Busca a taxa de câmbio EUR/BRL atualizada (Síncrono)."""
    API_URL = "https://api.exchangerate-api.com/v4/latest/EUR"
    try:
        response = requests.get(API_URL, timeout=10) 
        response.raise_for_status() 
        return response.json()['rates']['BRL']
    except requests.exceptions.RequestException:
        logger.warning("Erro ao obter câmbio EUR/BRL. Usando taxa fallback (5.50).")
        return 5.50

def transformar_em_afiliado(url_original: str) -> str:
    """Adiciona os parâmetros de afiliado ao link da Eneba."""
    if "?" in url_original:
        return f"{url_original}&{PARAMS_AFILIADO}"
    else:
        return f"{url_original}?{PARAMS_AFILIADO}"

def scrape_detalhes_produto(url: str) -> dict:
    """Extrai nome e preço de uma página de produto específica da Eneba (Síncrono)."""
    headers = {'User-Agent': USER_AGENT}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Seletor para o título do produto (pdp-title)
        name_tag = soup.find('h1', class_=lambda c: c and 'pdp-title' in c) 
        name = name_tag.text.strip() if name_tag else "Produto Desconhecido"

        # Seletor para o preço (pdp-price)
        price_tag = soup.find('div', class_=lambda c: c and 'pdp-price' in c) 
        price_eur = 0.0
        if price_tag:
             # Limpa o texto do preço e tenta converter para float
             price_text = price_tag.text.replace('$', '').replace('€', '').replace('R', '').replace(',', '.').strip()
             try:
                price_eur = float(price_text)
             except ValueError:
                price_eur = 0.0

        return {
            'name': name,
            'price_eur': price_eur, 
            'url': url
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"ERRO DE CONEXÃO/SCRAPING para {url}: {e}")
        return {'name': 'ERRO DE SCRAPING', 'price_eur': 0.0, 'url': url}

# --- 💬 HANDLERS (Comandos do Telegram) ---

async def check_admin(update: Update) -> bool:
    """Verifica se o usuário é o Admin (para comandos de envio)."""
    global admin_user_id_int
    user = update.effective_user
    
    if update.effective_chat.type != "private" or user.id != admin_user_id_int:
        if update.effective_chat.type == "private" and user.id != admin_user_id_int:
             await update.message.reply_text("🚫 Acesso negado. Esta funcionalidade é apenas para o administrador.")
        return False
    return True

async def start_command(update: Update, context: CallbackContext) -> None:
    """Comando /start."""
    user = update.effective_user
    await update.message.reply_text(
        f"Olá, {user.first_name}! 👋\n\n"
        "Este é o seu bot de afiliados Eneba.\n\n"
        "**Modo de Uso (Admin):**\n"
        "1. Cole um link completo de produto da Eneba (ex: `https://www.eneba.com/br/xbox...`).\n"
        "2. Eu farei o *scraping* e enviarei uma oferta formatada com seu link de afiliado para o canal/grupo.",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_link(update: Update, context: CallbackContext) -> None:
    """Processa o link enviado pelo administrador, faz o scraping e envia a oferta."""
    
    if not await check_admin(update):
        return
        
    url_original = update.message.text
    
    if "eneba.com" not in url_original or not url_original.startswith("http"):
        await update.message.reply_text("❌ Link inválido. Por favor, cole uma URL completa da Eneba.")
        return
        
    await update.message.reply_text("Processando link... Iniciando scraping para obter detalhes...")
    
    # Executa as funções síncronas em um thread pool para não bloquear o loop asyncio
    detalhes = await asyncio.to_thread(scrape_detalhes_produto, url_original)
    
    if detalhes['name'] == 'ERRO DE SCRAPING' or detalhes['price_eur'] == 0.0:
        await update.message.reply_text(
            f"❌ Falha ao extrair o nome/preço do produto no link. Verifique o link."
        )
        return
        
    link_afiliado = transformar_em_afiliado(url_original)
    
    current_exchange_rate = await asyncio.to_thread(get_exchange_rate)
    preco_brl = detalhes['price_eur'] * current_exchange_rate
    preco_brl_formatado = f"{preco_brl:.2f}".replace('.', ',')
    
    mensagem = (
        f"🚨 **SUPER OFERTA EXCLUSIVA!** 🚨\n\n"
        f"🎮 **{detalhes['name']}**\n"
        f"💰 Preço Estimado: **R$ {preco_brl_formatado}**\n"
        f"_Preço original em EUR: €{detalhes['price_eur']:.2f}_\n\n"
        f"Seu código de afiliado: `{AFILIADO_ID}`"
    )

    # Cria o Botão Clicável (Inline Keyboard)
    keyboard = [[InlineKeyboardButton("🔥 COMPRE AQUI E APOIE O CANAL! 🔥", url=link_afiliado)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Envia a mensagem para o canal público
    try:
        await context.bot.send_message(
            chat_id=CHAT_ID_DESTINO,
            text=mensagem,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        await update.message.reply_text(
            f"✅ Oferta de afiliado enviada com sucesso para o canal: {CHAT_ID_DESTINO}\n"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ ERRO ao enviar para o canal. Verifique permissões/ID.")
        logger.error(f"ERRO DE ENVIO para {CHAT_ID_DESTINO}: {e}")

# --- ⏰ AGENDAMENTO DE MENSAGENS DIÁRIAS ---

async def enviar_mensagem_diaria(mensagem: str):
    """Função assíncrona para enviar as mensagens agendadas."""
    global application, CHAT_ID_DESTINO
    if not application or not CHAT_ID_DESTINO: return

    try:
        await application.bot.send_message(
            chat_id=CHAT_ID_DESTINO,
            text=mensagem,
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"Mensagem agendada enviada para {CHAT_ID_DESTINO}.")
    except Exception as e:
        logger.error(f"ERRO ao enviar mensagem agendada: {e}")

def agendar_0930():
    mensagem = "☀️ **BOM DIA, CHAT!** 🚀 Fique de olho, o Admin logo enviará novidades!"
    # Usa o loop do Polling para executar a corrotina (Thread-safe)
    asyncio.run_coroutine_threadsafe(enviar_mensagem_diaria(mensagem), application.loop)

def agendar_1300():
    mensagem = "🍕 **PAUSA PARA O ALMOÇO!** 🍽️ O Admin está monitorando os melhores preços."
    asyncio.run_coroutine_threadsafe(enviar_mensagem_diaria(mensagem), application.loop)

def agendar_2000():
    mensagem = "🌙 **BOA NOITE, GAMERS!** ✨ As ofertas noturnas estão a caminho!"
    asyncio.run_coroutine_threadsafe(enviar_mensagem_diaria(mensagem), application.loop)

def configurar_agendamento():
    schedule.every().day.at("09:30").do(agendar_0930) 
    schedule.every().day.at("13:00").do(agendar_1300) 
    schedule.every().day.at("20:00").do(agendar_2000) 
    logger.info("Agendamento diário configurado.")

# --- 🔄 LOOP DO SCHEDULER EM THREAD ---

def run_scheduler_loop():
    """Executa o loop do scheduler."""
    time.sleep(5) # Espera o Polling iniciar antes de configurar o agendamento
    configurar_agendamento()
    logger.info("Iniciando loop do scheduler em background...")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logger.error(f"ERRO no loop do Scheduler: {e}")
            time.sleep(5)

# --- 🌐 WEB SERVICE (KEEP-ALIVE) ---

app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    """Endpoint essencial para o Render manter o serviço ativo."""
    return "Bot de Ofertas Híbrido está online. O Polling do Telegram está ativo na thread principal.", 200

def run_flask_server():
    """Inicia o servidor Flask em uma thread separada para não bloquear o Polling."""
    global PORT
    logger.info(f"Iniciando servidor Flask (Keep-Alive) na porta {PORT}...")
    # Usa o servidor Flask embutido (desenvolvimento) por ser simples e em uma thread separada
    try:
        app_flask.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"ERRO ao iniciar o servidor Flask Keep-Alive: {e}")


# --- 🏃 INÍCIO DO PROGRAMA ---

def main():
    global application, admin_user_id_int
    print("===========================================")
    print("  Iniciando Bot Keep-Alive (Render Free)   ")
    print("===========================================")
    
    # 1. Validações e Configurações
    if not BOT_TOKEN or not CHAT_ID_DESTINO or not ADMIN_USER_ID:
        logger.error("ERRO: BOT_TOKEN, CHAT_ID ou ADMIN_USER_ID não configurados. Abortando.")
        return
        
    if ADMIN_USER_ID.isdigit():
        admin_user_id_int = int(ADMIN_USER_ID)
    else:
        logger.error("ERRO: ADMIN_USER_ID não é um número válido.")
        return
        
    logger.info(f"DEBUG: Porta lida: {PORT}")

    # 2. Configura a aplicação do Telegram (Polling)
    application = Application.builder().token(BOT_TOKEN).build()
    
    # 3. Inicia o Web Server (Keep-Alive) em uma thread separada
    flask_thread = Thread(target=run_flask_server)
    flask_thread.start()

    # Handlers do Telegram (deve vir depois da criação da application)
    application.add_handler(CommandHandler("start", start_command))
    # Filtro para identificar URLs da Eneba (o Regex 'https?:\/\/...' faz o trabalho)
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'https?:\/\/(?:www\.)?eneba\.com'), handle_link))

    # 4. Inicia o loop do Scheduler em uma thread separada
    scheduler_thread = Thread(target=run_scheduler_loop)
    scheduler_thread.start()

    # 5. Inicia o Polling na thread principal (mantém o processo vivo)
    logger.info("Iniciando Polling do Telegram Bot na thread principal...")
    try:
        # run_polling é síncrono e mantém o programa em execução
        application.run_polling(poll_interval=5, timeout=30)
    except Exception as e:
        logger.critical(f"ERRO CRÍTICO no Polling (Thread Principal): {e}")
        
    logger.info("Polling encerrado.")


if __name__ == '__main__':
    main()
