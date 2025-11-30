# bot.py
import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

# ===============================
# CONFIGURAÇÕES DO BOT
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = -1001872183962  # seu canal ou grupo
AFILIADO_PARAMS = "af_id=WiillzeraTV&currency=BRL&region=global&utm_source=WiillzeraTV&utm_medium=infl"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===============================
# FUNÇÃO PARA GERAR LINK DE AFILIADO
# ===============================
def gerar_link_afiliado(link_normal: str):
    if "?" in link_normal:
        return f"{link_normal}&{AFILIADO_PARAMS}"
    else:
        return f"{link_normal}?{AFILIADO_PARAMS}"

# ===============================
# FUNÇÃO PARA MONTAR MENSAGEM
# ===============================
def montar_mensagem(link: str):
    link_afiliado = gerar_link_afiliado(link)
    texto = "🔥 *OFERTA ENEBA* 🔥\n\nClique no botão abaixo para comprar:"
    teclado = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 COMPRE AQUI", url=link_afiliado)]
        ]
    )
    return texto, teclado

# ===============================
# HANDLER DO COMANDO /promo
# ===============================
async def cmd_promo(message: Message):
    args = message.text.split(" ", 1)
    if len(args) == 1:
        await message.answer("❌ Use /promo <link do produto> para enviar uma oferta!")
        return
    
    link_produto = args[1]
    texto, teclado = montar_mensagem(link_produto)
    
    await bot.send_message(
        CHAT_ID,
        text=texto,
        reply_markup=teclado,
        parse_mode="Markdown"
    )
    await message.answer("✅ Oferta enviada com sucesso!")

# ===============================
# INICIALIZAÇÃO DO BOT
# ===============================
async def main():
    dp.message.register(cmd_promo, F.text.startswith("/promo"))
    print("🤖 BOT ONLINE")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
