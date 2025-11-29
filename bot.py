import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message

# ===============================
# CONFIGURAÇÕES DO BOT
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN")  # ou coloque o token direto aqui para teste
CHAT_ID = -1001872183962  # substitua pelo chat ID real do seu canal

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===============================
# HANDLER DE TESTE
# ===============================
async def teste_envio(message: Message):
    await message.answer("✅ Recebi sua mensagem!")
    await bot.send_message(CHAT_ID, "🔥 TESTE DE ENVIO AO CANAL 🔥")

# ===============================
# INICIALIZAÇÃO DO BOT
# ===============================
async def main():
    # Registrar qualquer mensagem enviada ao bot
    dp.message.register(teste_envio)
    print("🤖 BOT ONLINE - envie qualquer mensagem e ele testará o envio ao canal")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
