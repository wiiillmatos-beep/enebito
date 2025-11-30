import os
import logging
from threading import Thread
import time
import asyncio
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
        "**Modo de Uso:**\n"
        "Como administrador, use o comando `/oferta` para enviar ofertas para o canal.\n\n"
        "**Formato:**\n"
        "`/oferta <link da eneba> >> <Nome do Jogo> >> <Preço em BRL>`\n\n"
        "**Exemplo:**\n"
        "`/oferta https://www.eneba.com/exemplo >> Nome do Jogo Teste >> R$123,45`\n\n"
        "O bot montará a mensagem com a imagem de pré-visualização, o nome, o preço e um botão de compra com seu link de afiliado.",
        parse_mode=ParseMode.MARKDOWN
    )

async def send_oferta_command(update: Update, context: CallbackContext) -> None:
    """Processa o comando /oferta com link, nome e preço."""
    
    if not await check_admin(update):
        return
        
    full_text = context.args
    if not full_text:
        await update.message.reply_text(
            "❌ Formato incorreto. Use: `/oferta <link da eneba> >> <Nome do Jogo> >> <Preço em BRL>`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Junta os argumentos para o caso de espaços e então divide pelo novo separador " >> "
    full_text_str = " ".join(full_text)
    parts = full_text_str.split(' >> ', 2) # Divide em no máximo 3 partes
    
    if len(parts) != 3:
        await update.message.reply_text(
            "❌ Formato incorreto. Certifique-se de usar `>>` para separar Link, Nome e Preço.\n"
            "Ex: `/oferta https://www.eneba.com/exemplo >> Nome do Jogo Teste >> R$123,45`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    url_original = parts[0].strip()
    nome_jogo = parts[1].strip()
    preco_str = parts[2].strip()

    # Validação básica do link
    if not url_original.startswith("http") or "eneba.com" not in url_original:
        await update.message.reply_text("❌ Link inválido. Por favor, forneça uma URL completa da Eneba.")
        return

    # Validação do preço
    try:
        # Remove "R$" e substitui vírgula por ponto para float
        preco_limpo = preco_str.replace("R$", "").replace(",", ".").strip()
        preco_float = float(preco_limpo)
        preco_brl_formatado = f"R$ {preco_float:.2f}".replace('.', ',')
    except ValueError:
        await update.message.reply_text(
            f"❌ Preço inválido: `{preco_str}`. Certifique-se de que é um número válido (ex: 149,90).",
            parse_mode=ParseMode.MARKDOWN
        )
        return
        
    await update.message.reply_text("Gerando oferta para o canal...")

    link_afiliado = transformar_em_afiliado(url_original)
    
    # Template da mensagem para o canal (com nova instrução)
    mensagem_canal = (
        f"🎮 {nome_jogo}\n\n"
        f"💰 Preço: {preco_brl_formatado}\n\n"
        # Instrução clara para o usuário
        f"🚨 **Atenção!** Para garantir que você apoie o canal, use **SEMPRE** o botão abaixo, e **NÃO** o link de 'Ver Produto'.\n\n"
        # Link discreto e clicável para garantir a pré-visualização da imagem
        f"[Ver Produto]({url_original})" 
    )

    # Cria o Botão Clicável (Inline Keyboard)
    # ALTERAÇÃO AQUI: Adicionando o emoji de fogo 🔥
    keyboard = [[InlineKeyboardButton("🛒 🔥 COMPRE AGORA E APOIE O CANAL! 🔥 🛒", url=link_afiliado)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Envia a mensagem para o canal público
    try:
        await context.bot.send_message(
            chat_id=CHAT_ID_DESTINO,
            text=mensagem_canal,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN, 
            disable_web_page_preview=False 
        )
        await update.message.reply_text(
            f"✅ Oferta de afiliado enviada com sucesso para o canal: `{CHAT_ID_DESTINO}`\n"
            "Pré-visualização da imagem garantida, com instrução clara para usar o botão de afiliado.",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(f"❌ ERRO ao enviar para o canal. Verifique permissões/ID: `{e}`")
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
    try:
        # Usa o servidor Flask embutido (desenvolvimento) por ser simples e em uma thread separada
        app_flask.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"ERRO ao iniciar o servidor Flask Keep-Alive: {e}")

# --- 🏃 INÍCIO DO PROGRAMA ---

async def init_application(application_instance: Application):
    """Função assíncrona para excluir o webhook antes de iniciar o polling."""
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

    # Handlers do Telegram (deve vir depois da criação da application)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("oferta", send_oferta_command))

    # 4. Inicia o Polling na thread principal (mantém o processo vivo)
    logger.info("Iniciando Polling do Telegram Bot na thread principal...")
    try:
        # run_polling é síncrono e mantém o programa em execução
        application.run_polling(poll_interval=5, timeout=30)
    except Exception as e:
        logger.critical(f"ERRO CRÍTICO no Polling (Thread Principal): {e}")
        
    logger.info("Polling encerrado.")


if __name__ == '__main__':
    main()
