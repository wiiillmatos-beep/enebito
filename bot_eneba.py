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
# USER AGENT não é mais necessário, pois o scraping foi removido.

# Variáveis globais
application = None 
admin_user_id_int = 0
# O Render define a porta que deve ser usada via variável de ambiente 'PORT'
PORT = int(os.environ.get("PORT", 5000)) 

# --- 💵 FUNÇÕES DE SUPORTE ---

def transformar_em_afiliado(url_original: str) -> str:
    """Adiciona os parâmetros de afiliado ao link da Eneba."""
    if "?" in url_original:
        return f"{url_original}&{PARAMS_AFILIADO}"
    else:
        return f"{url_original}?{PARAMS_AFILIADO}"

# As funções 'get_exchange_rate' e 'scrape_detalhes_produto' foram removidas, 
# pois o nome e o preço agora são fornecidos manualmente pelo administrador.

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
        "Este é o seu bot de afiliados Eneba, configurado para **entrada manual**.\n\n"
        "**Modo de Uso (Admin):**\n"
        "Use o comando `/oferta` no formato:\n"
        "**/oferta <link da Eneba> | <Nome do Jogo> | <Preço em BRL>**\n\n"
        "Exemplo:\n"
        "`/oferta https://www.eneba.com/game | God of War Ragnarok | 149,90`\n\n"
        "Eu montarei a mensagem com seu link de afiliado e a imagem de pré-visualização do jogo.",
        parse_mode=ParseMode.MARKDOWN
    )

async def send_oferta_command(update: Update, context: CallbackContext) -> None:
    """
    Processa o comando /oferta com input manual (link | nome | preço), 
    transforma o link e envia a oferta formatada para o canal.
    """
    
    if not await check_admin(update):
        return
        
    if not context.args:
        await update.message.reply_text(
            "❌ Comando incompleto. Use: `/oferta <link> | <Nome do Jogo> | <Preço em BRL>`"
        )
        return

    # Junta todos os argumentos e divide pela barra vertical (|), limitando a 3 partes
    full_text = " ".join(context.args)
    parts = [p.strip() for p in full_text.split('|', 2)] 

    if len(parts) != 3:
        await update.message.reply_text(
            "❌ Formato inválido. Use exatamente duas barras `|` para separar Link, Nome e Preço.\n"
            "Exemplo: `/oferta https://eneba.com/game | God of War Ragnarok | 149,90`"
        )
        return

    url_original, nome_jogo, preco_str = parts

    # 1. Validação do Link
    if "eneba.com" not in url_original or not url_original.startswith("http"):
        await update.message.reply_text("❌ Link inválido. Por favor, cole uma URL completa da Eneba.")
        return
        
    # 2. Formatação e Validação do Preço
    try:
        # Tenta limpar o preço para garantir que é um número (ex: 149,90 -> 149.90)
        # O replace('R$', '') é para permitir que o admin digite 'R$ 149,90'
        preco_brl_float = float(preco_str.replace('R$', '').replace('.', '').replace(',', '.').strip())
        preco_brl_formatado = f"R$ {preco_brl_float:.2f}".replace('.', ',')
    except ValueError:
        await update.message.reply_text(
            f"❌ Preço inválido: `{preco_str}`. Certifique-se de que é um número válido (ex: 149,90)."
        )
        return

    await update.message.reply_text(f"Processando oferta manual para: {nome_jogo}...")

    # 3. Geração do Link de Afiliado
    link_afiliado = transformar_em_afiliado(url_original)
    
    # 4. Construção da Mensagem
    # Incluímos o link original na mensagem para que o Telegram gere a pré-visualização (imagem/título).
    mensagem_canal = (
        f"🚨 **OFERTA QUENTE NA ENEBA!** 🚨\n\n"
        f"🎮 **{nome_jogo}**\n"
        f"💰 Preço: **{preco_brl_formatado}**\n\n"
        f"🔗 Link do Produto: {url_original}\n\n" # Link visível para preview
        f"Seu código de afiliado: `{AFILIADO_ID}`"
    )

    # 5. Botão Clicável
    keyboard = [[InlineKeyboardButton("🔥 COMPRE AQUI E APOIE O CANAL! 🔥", url=link_afiliado)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # 6. Envio para o canal público
    try:
        await context.bot.send_message(
            chat_id=CHAT_ID_DESTINO,
            text=mensagem_canal,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        await update.message.reply_text(
            f"✅ Oferta enviada com sucesso para o canal: {CHAT_ID_DESTINO}\n"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ ERRO CRÍTICO ao enviar para o canal. Verifique permissões/ID. O link gerado foi: {link_afiliado}")
        logger.error(f"ERRO DE ENVIO para {CHAT_ID_DESTINO}: {e}")


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

async def init_application(application_instance: Application):
    """Função assíncrona para excluir o webhook antes de iniciar o polling.
       Esta função é executada via hook post_init."""
    logger.info("Verificando e excluindo qualquer webhook remanescente para evitar conflitos...")
    try:
        # Chama a API do Telegram para garantir que o Webhook seja removido
        await application_instance.bot.delete_webhook()
        logger.info("✅ Webhook antigo limpo com sucesso. O Polling pode iniciar.")
    except Exception as e:
        # Se houver erro, apenas registra e prossegue, pois o erro pode ser 'não há webhook'
        logger.warning(f"Não foi possível excluir o webhook (normal se não houver um): {e}")

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
    application = Application.builder().token(BOT_TOKEN).post_init(init_application).build()
    
    # 3. Inicia o Web Server (Keep-Alive) em uma thread separada
    flask_thread = Thread(target=run_flask_server)
    flask_thread.start()

    # Handlers do Telegram
    application.add_handler(CommandHandler("start", start_command))
    # NOVO: Handler para o comando manual /oferta
    application.add_handler(CommandHandler("oferta", send_oferta_command))
    
    # O MessageHandler antigo (que tentava scraping) foi removido.

    # 4. Inicia o Polling na thread principal (mantém o processo vivo)
    logger.info("Iniciando Polling do Telegram Bot na thread principal...")
    try:
        application.run_polling(poll_interval=5, timeout=30)
    except Exception as e:
        logger.critical(f"ERRO CRÍTICO no Polling (Thread Principal): {e}")
        
    logger.info("Polling encerrado.")


if __name__ == '__main__':
    main()
