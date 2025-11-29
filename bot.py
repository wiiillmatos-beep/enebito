import os
import asyncio
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
import datetime

# ===============================
# CONFIGURAÇÕES DO BOT
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = -1001234567890  # substitua pelo ID real do seu canal
AFILIADO_PARAMS = "af_id=WiillzeraTV&currency=BRL&region=global&utm_source=WiillzeraTV&utm_medium=infl"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===============================
# GERAR LINK DE AFILIADO
# ===============================
def gerar_link_afiliado(link_normal):
    if "?" in link_normal:
        return f"{link_normal}&{AFILIADO_PARAMS}"
    else:
        return f"{link_normal}?{AFILIADO_PARAMS}"

# ===============================
# MONTAR TEMPLATE DE POSTAGEM
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
            [InlineKeyboardButton(text="🛒 COMPRE AGORA", url=link_afiliado)]
        ]
    )

    return texto, teclado, imagem

# ===============================
# BUSCAR OFERTAS REAIS
# ===============================
def buscar_ofertas_eneba():
    url = "https://www.eneba.com/br/sale"  # página de ofertas
    ofertas = []

    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")

        produtos = soup.find_all("div", class_="product-card")[:4]  # pegar 4 primeiros
        for p in produtos:
            # Título
            titulo_tag = p.find("span", class_="product-title")
            titulo = titulo_tag.get_text(strip=True) if titulo_tag else "Sem título"

            # Preço
            preco_tag = p.find("span", class_="price")
            preco = preco_tag.get_text(strip=True) if preco_tag else "Ver no site"

            # Link do produto
            link_tag = p.find("a", href=True)
            link = "https://www.eneba.com" + link_tag["href"] if link_tag else "https://www.eneba.com"

            # Imagem do produto
            img_tag = p.find("img")
            if img_tag:
                imagem = img_tag.get("data-src") or img_tag.get("src")
                if imagem.startswith("//"):
                    imagem = "https:" + imagem
            else:
                imagem = "https://cdn-products.eneba.com/resized-products/some-image-example.jpg"

            ofertas.append((titulo, preco, link, imagem))

    except Exception as e:
        print(f"❌ Erro ao buscar ofertas: {e}")

    return ofertas

# ===============================
# ENVIO DE OFERTA
# ===============================
async def enviar_oferta(titulo, preco, link, imagem):
    texto, teclado, imagem_url = montar_template(titulo, preco, link, imagem)
    await bot.send_photo(
        CHAT_ID,
        photo=imagem_url,
        caption=texto,
        reply_markup=teclado,
        parse_mode="Markdown"
    )

# ===============================
# ENVIO AUTOMÁTICO
# ===============================
async def agendador():
    horarios = ["11:00", "17:00", "20:00"]

    while True:
        agora = datetime.datetime.now().strftime("%H:%M")

        if agora in horarios:
            print(f"🟢 Postando ofertas automáticas ({agora})")
            ofertas = buscar_ofertas_eneba()
            for titulo, preco, link, imagem in ofertas:
                await enviar_oferta(titulo, preco, link, imagem)
                await asyncio.sleep(3)
            await asyncio.sleep(60)

        await asyncio.sleep(20)

# ===============================
# ENVIO MANUAL VIA /promo
# ===============================
async def cmd_promo(message: Message):
    args = message.text.split(" ", 1)

    if len(args) == 1:
        # /promo sozinho → envia ofertas reais
        await message.answer("Enviando ofertas reais no canal...")
        ofertas = buscar_ofertas_eneba()
        for titulo, preco, link, imagem in ofertas:
            await enviar_oferta(titulo, preco, link, imagem)
            await asyncio.sleep(3)
    else:
        # /promo <link> → envia oferta manual
        link_normal = args[1]
        titulo = "Oferta Manual"
        preco = "Ver no site"
        imagem = "https://cdn-products.eneba.com/resized-products/some-image-example.jpg"

        await enviar_oferta(titulo, preco, link_normal, imagem)
        await message.answer("✅ Oferta manual enviada!")

# ===============================
# INICIALIZAÇÃO DO BOT
# ===============================
async def main():
    dp.message.register(cmd_promo, F.text.startswith("/promo"))
    asyncio.create_task(agendador())
    print("🤖 BOT ONLINE")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
