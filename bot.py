import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
import datetime

# ===============================
# CONFIGURAÇÕES DO BOT
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = -1001234567890  # substitua pelo ID real do seu canal
AFILIADO = "https://www.eneba.com/br/?af_id=WiillzeraTV&utm_medium=infl&utm_source=WiillzeraTV"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===============================
# TEMPLATE DE POSTAGEM
# ===============================
def montar_template(titulo, preco, link, imagem):
    texto = (
        f"🔥 *OFERTA ENEBA* 🔥\n\n"
        f"🎮 *{titulo}*\n"
        f"💰 Preço: *{preco}*\n\n"
        f"🔗 Clique no botão abaixo para comprar:"
    )

    teclado = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 COMPRE AQUI", url=link)]
        ]
    )

    return texto, teclado, imagem

# ===============================
# FUNÇÃO DE ENVIO SIMPLES (TESTE)
# ===============================
async def enviar_teste_canal():
    await bot.send_message(CHAT_ID, "🔥 TESTE DE ENVIO PARA O CANAL 🔥")

# ===============================
# FUNÇÃO DE ENVIO COMPLETA (COM FOTO)
# ===============================
async def enviar_promocao_teste():
    titulo = "Jogo Teste do Xbox (Exemplo)"
    preco = "R$ 19,90"
    imagem = "https://cdn-products.eneba.com/resized-products/some-image-example.jpg"
    link = AFILIADO + "&test=1"

    texto, teclado, imagem_url = montar_template(titulo, preco, link, imagem)

    await bot.send_photo(
        CHAT_ID,
        photo=imagem_url,
        caption=texto,
        reply_markup=teclado,
        parse_mode="Markdown"
    )

# ===============================
# HANDLER DO COMANDO /promo
# ===============================
async def cmd_promo(message: Message):
    # Mensagem para o usuário
    await message.answer("Enviando teste no canal...")

    # Primeiro envio de teste de texto
    await enviar_teste_canal()

    # Em seguida, envio do post completo com foto
    await enviar_promocao_teste()

# ===============================
# SISTEMA DE POSTAGENS AUTOMÁTICAS
# ===============================
async def agendador():
    horarios = ["11:00", "17:00", "20:00"]

    while True:
        agora = datetime.datetime.now().strftime("%H:%M")

        if agora in horarios:
            print(f"🟢 Postando ofertas automáticas ({agora})")
            for _ in range(4):
                await enviar_promocao_teste()
                await asyncio.sleep(3)
            await asyncio.sleep(60)

        await asyncio.sleep(20)

# ===============================
# INICIALIZAÇÃO DO BOT
# ===============================
async def main():
    dp.message.register(cmd_promo, F.text == "/promo")

    # Inicia agendador em segundo plano
    asyncio.create_task(agendador())

    print("🤖 BOT ONLINE")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
