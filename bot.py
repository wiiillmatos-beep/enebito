import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
import datetime
import requests
from bs4 import BeautifulSoup

# ===============================
# CONFIGURAÇÕES DO BOT
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = -1001872183962  # ID do canal
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
        inline_keyboard=[[InlineKeyboardButton(text="🛒 COMPRE AGORA", url=link_afiliado)]]
    )

    return texto, teclado, imagem

# ===============================
# ENVIO DE PROMOÇÃO
# ===============================
async def enviar_promocao(titulo, preco, link, imagem):
    texto, teclado, imagem_url = montar_template(titulo, preco, link, imagem)
    try:
        await bot.send_photo(
            CHAT_ID,
            photo=imagem_url,
            caption=texto,
            reply_markup=teclado,
            parse_mode="Markdown"
        )
        print(f"✅ Enviado: {titulo}")
    except Exception as e:
        print(f"❌ Falha ao enviar {titulo}: {e}")

# ===============================
# FUNÇÃO PARA BUSCAR OFERTAS REAIS DA ENEBA
# ===============================
def buscar_ofertas_eneba():
    url = "https://www.eneba.com/br/sale"  # página de ofertas
    try:
        r = requests.get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        ofertas = []

        produtos = soup.select("div.product-card")[:4]  # pegar os 4 primeiros produtos
        for p in produtos:
            titulo = p.select_one("span.product-title").get_text(strip=True)
            preco = p.select_one("span.price").get_text(strip=True)
            link = "https://www.eneba.com" + p.select_one("a")["href"]
            imagem = p.select_one("img")["src"]
            ofertas.append((titulo, preco, link, imagem))
        return ofertas
    except Exception as e:
        print(f"❌ Erro ao buscar ofertas: {e}")
        return []

# ===============================
# ENVIO AUTOMÁTICO DE OFERTAS REAIS
# ===============================
async def enviar_ofertas_reais():
    ofertas = buscar_ofertas_eneba()
    if not ofertas:
        print("⚠️ Nenhuma oferta encontrada.")
        return
    for titulo, preco, link, imagem in ofertas:
        await enviar_promocao(titulo, preco, link, imagem)
        await asyncio.sleep(2)

# ===============================
# HANDLER DO COMANDO /promo
# ===============================
async def cmd_promo(message: Message):
    args = message.text.split(" ", 1)
    
    if len(args) == 1:
        # /promo sozinho → envia últimas ofertas reais
        await message.answer("Enviando últimas ofertas reais no canal...")
        await enviar_ofertas_reais()
    else:
        # /promo <link> → envia oferta manual
        link_normal = args[1]
        titulo = "Oferta Manual"
        preco = "Ver no site"
        imagem = "https://cdn-products.eneba.com/resized-products/some-image-example.jpg"
        await enviar_promocao(titulo, preco, link_normal, imagem)
        await message.answer("✅ Oferta enviada manualmente!")

# ===============================
# SISTEMA DE POSTAGENS AUTOMÁTICAS
# ===============================
async def agendador():
    horarios = ["11:00", "17:00", "20:00"]
    while True:
        agora = datetime.datetime.now().strftime("%H:%M")
        if agora in horarios:
            print(f"🟢 Postando ofertas automáticas ({agora})")
            await enviar_ofertas_reais()
            await asyncio.sleep(60)
        await asyncio.sleep(20)

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
