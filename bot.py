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

# Parâmetros do seu link de afiliado
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
# TEMPLATE DE POSTAGEM
# ===============================
def montar_template(titulo, preco, link, imagem):
    link_afiliado = gerar_link_afiliado(link)
    
    texto = (
        f"🔥 *OFERTA ENEBA* 🔥\n\n"
        f"🎮 *{titulo}*\n"
        f"💰 Preço: *{preco}*\n\n"
        f"🔗 Clique no botão abaixo para comprar:"
    )

    teclado = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 COMPRE AQUI", url=link_afiliado)]
        ]
    )

    return texto, teclado, imagem

# ===============================
# ENVIO DE OFERTA REAL (EXEMPLO)
# ===============================
async def enviar_oferta_real():
    titulo = "Jogo Real do Xbox (Exemplo)"
    preco = "R$ 19,90"  # você pode buscar preço real ou atualizar manualmente
    imagem = "https://cdn-products.eneba.com/resized-products/some-image-example.jpg"
    link = "https://www.eneba.com/br/other-dungeon-defenders-ii-500-gems-shutter-shades-flair-in-game-key-global"

    texto, teclado, imagem_url = montar_template(titulo, preco, link, imagem)

    await bot.send_photo(
        CHAT_ID,
        photo=imagem_url,
        caption=texto,
        reply_markup=teclado,
        parse_mode="Markdown"
    )

# ===============================
# ENVIO DE OFERTA MANUAL
# ===============================
async def enviar_oferta_manual(link_normal, message: Message):
    titulo = "Oferta Manual"
    preco = "Ver no site"
    imagem = "https://cdn-products.eneba.com/resized-products/some-image-example.jpg"

    texto, teclado, imagem_url = montar_template(titulo, preco, link_normal, imagem)

    await bot.send_photo(
        CHAT_ID,
        photo=imagem_url,
        caption=texto,
        reply_markup=teclado,
        parse_mode="Markdown"
    )
    await message.answer("✅ Oferta enviada manualmente!")

# ===============================
# HANDLER DO COMANDO /promo
# ===============================
async def cmd_promo(message: Message):
    args = message.text.split(" ", 1)
    
    if len(args) == 1:
        # /promo sozinho → envia ofertas reais
        await message.answer("Enviando oferta real no canal...")
        await enviar_oferta_real()
    else:
        # /promo <link> → envia oferta manual
        link_normal = args[1]
        await enviar_oferta_manual(link_normal, message)

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
                await enviar_oferta_real()
                await asyncio.sleep(3)
            await asyncio.sleep(60)

        await asyncio.sleep(20)

# ===============================
# INICIALIZAÇÃO DO BOT
# ===============================
async def main():
    dp.message.register(cmd_promo, F.text.startswith("/promo"))

    # Inicia agendador em segundo plano
    asyncio.create_task(agendador())

    print("🤖 BOT ONLINE")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
