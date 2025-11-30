import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

# ===============================
# CONFIGURAÇÕES DO BOT
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN")  # ou coloque o token direto para teste
CHAT_ID = -1001872183962  # substitua pelo chat ID real do seu canal

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===============================
# FUNÇÃO DE ENVIO DE PROMOÇÃO
# ===============================
async def enviar_promocao(link: str):
    texto = "🔥 OFERTA ENEBA 🔥\n\nClique no botão abaixo para comprar:"
    teclado = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 COMPRE AQUI", url=link)]
        ]
    )
    await bot.send_message(
        CHAT_ID,
        text=texto,
        reply_markup=teclado
    )

# ===============================
# HANDLER DO COMANDO /promo
# ===============================
# Envia qualquer link de promoção manualmente
async def cmd_promo(message: Message):
    args = message.text.split(" ", 1)
    if len(args) == 1:
        await message.answer("⚡ Use: /promo <link> para enviar uma oferta")
        return
    link = args[1].strip()
    await enviar_promocao(link)
    await message.answer("✅ Oferta enviada para o canal!")

# ===============================
# INICIALIZAÇÃO DO BOT
# ===============================
async def main():
    dp.message.register(cmd_promo, F.text.startswith("/promo"))

    print("🤖 BOT ONLINE")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
