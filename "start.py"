import os
import asyncio
import datetime
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

# ===============================
# VARIÁVEIS DE AMBIENTE
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Configure no Deployra
if not BOT_TOKEN:
    raise Exception("🚨 BOT_TOKEN não definido. Configure no Deployra.")

CHAT_ID = "@enebaofertas"   # Canal onde será enviado
AFILIADO = "https://www.eneba.com/br/?af_id=WiillzeraTV&utm_medium=infl&utm_source=WiillzeraTV"

# ===============================
# FUNÇÃO PARA GERAR LINK ENCURTADO
# ===============================
def encurtar(link):
    try:
        req = requests.get(f"https://tinyurl.com/api-create.php?url={link}")
        return req.text
    except:
        return link  # fallback

# ===============================
# TEMPLATE DE POSTAGEM
# ===============================
def montar_template(titulo, preco, link, imagem):
    link_curto = encurtar(link)

    texto = (
        f"🔥 *OFERTA ENEBA* 🔥\n\n"
        f"🎮 *{titulo}*\n"
        f"💰 Preço: *{preco}*\n\n"
        f"🔗 Clique no botão abaixo para comprar:"
    )

    teclado = InlineKeyboardBuilder()
    teclado.button(text="🛒 COMPRAR", url=link_curto)
    teclado.adjust(1)

    return texto, teclado, imagem

# ===============================
# TESTAR ENVIO MANUAL
# ===============================
async def enviar_promocao_teste(bot: Bot):
    titulo = "Jogo Teste do Xbox (Exemplo)"
    preco = "R$ 19,90"
    imagem = "https://cdn-products.eneba.com/resized-products/some-image-example.jpg"

    link = AFILIADO + "&test=1"

    texto, teclado, imagem_url = montar_template(titulo, preco, link, imagem)

    await bot.send_photo(
        CHAT_ID,
        photo=imagem_url,
        caption=texto,
        reply_markup=teclado.as_markup(),
        parse_mode="Markdown"
    )

# ===============================
# HANDLER DO COMANDO /promo
# ===============================
async def cmd_promo(message: Message, bot: Bot):
    await message.answer("Enviando promoção de teste no canal...")
    await enviar_promocao_teste(bot)

# ===============================
# SISTEMA DE POSTAGENS AUTOMÁTICAS
# HORÁRIOS: 11:00 / 17:00 / 20:00
# ===============================
async def agendador(bot: Bot):
    horarios = ["11:00", "17:00", "20:00"]

    while True:
        agora = datetime.datetime.now().strftime("%H:%M")
        if agora in horarios:
            print(f"🟢 Postando ofertas automáticas ({agora})")
            for _ in range(4):  # envia 4 promoções
                await enviar_promocao_teste(bot)
                await asyncio.sleep(3)
            await asyncio.sleep(60)
        await asyncio.sleep(20)

# ===============================
# SERVIDOR HTTP PARA DEPLOYRA
# ===============================
async def handle(request):
    return web.Response(text="Bot rodando!")

async def start_server():
    PORT = int(os.getenv("PORT", 3000))  # Deployra exige usar process.env.PORT
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Servidor HTTP rodando na porta {PORT}")

# ===============================
# INICIALIZAÇÃO DO BOT
# ===============================
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.message.register(cmd_promo, F.text == "/promo")

    # inicia agendador em segundo plano
    asyncio.create_task(agendador(bot))
    # inicia servidor HTTP para Deployra
    asyncio.create_task(start_server())

    print("🤖 BOT ONLINE")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
