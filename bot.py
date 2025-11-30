import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.filters import Text

# ===============================
# CONFIGURAÇÕES DO BOT
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN")  # ou coloque seu token direto para teste
CHAT_ID = -1001872183962  # ID do grupo/canal
AFILIADO_PARAMS = "af_id=WiillzeraTV&currency=BRL&region=global&utm_source=WiillzeraTV&utm_medium=infl"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===============================
# FUNÇÃO PARA GERAR LINK DE AFILIADO
# ===============================
def gerar_link_afiliado(link_normal):
    if "?" in link_normal:
        return f"{link_normal}&{AFILIADO_PARAMS}"
    else:
        return f"{link_normal}?{AFILIADO_PARAMS}"

# ===============================
# FUNÇÃO PARA MONTAR POST
# ===============================
def montar_template(link):
    link_afiliado = gerar_link_afiliado(link)
    texto = "🔥 *OFERTA ENEBA* 🔥\n\nClique no botão abaixo para comprar:"
    teclado = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🛒 COMPRE AQUI", url=link_afiliado)]]
    )
    return texto, teclado

# ===============================
# ENVIO DE UM LINK COM PRÉ-VISUALIZAÇÃO
# ===============================
async def cmd_send_link(message: Message):
    args = message.text.split(" ", 1)
    if len(args) != 2:
        await message.answer("❌ Use: /send_link <URL do produto>")
        return

    link_normal = args[1].strip()
    texto, teclado = montar_template(link_normal)

    # Envia pré-visualização no chat
    await message.answer("👀 Pré-visualização da oferta:")
    await message.answer(texto, reply_markup=teclado, parse_mode="Markdown")

    # Pergunta se deseja enviar
    enviar_teclado = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✅ Enviar ao canal", callback_data=f"send|{link_normal}")]]
    )
    await message.answer("Deseja enviar esta oferta ao canal?", reply_markup=enviar_teclado)

# ===============================
# ENVIO DE OFERTAS APÓS CONFIRMAÇÃO
# ===============================
@dp.callback_query(Text(startswith="send|"))
async def callback_send_offer(query: CallbackQuery):
    link_normal = query.data.split("|", 1)[1]
    texto, teclado = montar_template(link_normal)

    await bot.send_message(CHAT_ID, texto, reply_markup=teclado, parse_mode="Markdown")
    await query.message.edit_text("✅ Oferta enviada ao canal!")
    await query.answer()

# ===============================
# ENVIO DE VÁRIOS LINKS (sem pré-visualização)
# ===============================
async def cmd_send_links(message: Message):
    args = message.text.split("\n")[1:]
    if not args:
        await message.answer("❌ Use o comando seguido de links, um por linha:\n/send_links <link1>\n<link2>\n<link3>")
        return

    await message.answer(f"⚡ Envio de {len(args)} ofertas iniciado...")

    for link_normal in args:
        link_normal = link_normal.strip()
        if not link_normal:
            continue
        texto, teclado = montar_template(link_normal)
        await bot.send_message(CHAT_ID, texto, reply_markup=teclado, parse_mode="Markdown")
        await asyncio.sleep(1)

    await message.answer("✅ Todas as ofertas foram enviadas!")

# ===============================
# INICIALIZAÇÃO DO BOT
# ===============================
async def main():
    dp.message.register(cmd_send_link, F.text.startswith("/send_link"))
    dp.message.register(cmd_send_links, F.text.startswith("/send_links"))

    print("🤖 BOT ONLINE")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
