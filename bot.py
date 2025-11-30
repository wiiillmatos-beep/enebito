import os
import asyncio
import datetime
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

# ===============================
# CONFIGURAÇÕES DO BOT
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN")  # ou coloque seu token direto para teste
CHAT_ID = -1001872183962  # ID do grupo/canal
AFILIADO_PARAMS = "af_id=WiillzeraTV&currency=BRL&region=global&utm_source=WiillzeraTV&utm_medium=infl"

# URL de ofertas da Eneba
URL_OFERTAS = "https://www.eneba.com/br/store/xbox?drms[]=xbox&page=1&regions[]=argentina&regions[]=saudi_arabia&regions[]=turkey&regions[]=latam&types[]=game"

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
def montar_template(titulo, preco, link, imagem):
    link_afiliado = gerar_link_afiliado(link)
    texto = f"🔥 *OFERTA ENEBA* 🔥\n\n🎮 *{titulo}*\n💰 Preço: *{preco}*\n\nClique no botão abaixo para comprar:"
    teclado = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🛒 COMPRE AQUI", url=link_afiliado)]]
    )
    return texto, teclado, imagem

# ===============================
# FUNÇÃO PARA BUSCAR OFERTAS AUTOMÁTICAS
# ===============================
def buscar_ofertas():
    ofertas = []
    try:
        r = requests.get(URL_OFERTAS)
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".product-item")  # Ajuste se necessário
        for item in items:
            titulo_tag = item.select_one(".product-title")
            preco_tag = item.select_one(".price")
            link_tag = item.select_one("a")
            imagem_tag = item.select_one("img")

            if titulo_tag and preco_tag and link_tag and imagem_tag:
                titulo = titulo_tag.text.strip()
                preco = preco_tag.text.strip()
                link = "https://www.eneba.com" + link_tag["href"]
                imagem = imagem_tag["src"]
                ofertas.append((titulo, preco, link, imagem))
    except Exception as e:
        print("Erro ao buscar ofertas:", e)
    return ofertas

# ===============================
# FUNÇÃO PARA ENVIAR OFERTA
# ===============================
async def enviar_oferta(titulo, preco, link, imagem):
    texto, teclado, imagem_url = montar_template(titulo, preco, link, imagem)
    await bot.send_photo(CHAT_ID, photo=imagem_url, caption=texto, reply_markup=teclado, parse_mode="Markdown")

# ===============================
# ENVIO AUTOMÁTICO
# ===============================
async def agendador():
    horarios = ["11:00", "17:00", "20:00"]
    while True:
        agora = datetime.datetime.now().strftime("%H:%M")
        if agora in horarios:
            print(f"🟢 Postando ofertas automáticas ({agora})")
            ofertas = buscar_ofertas()
            for titulo, preco, link, imagem in ofertas[:4]:  # envia até 4 ofertas
                await enviar_oferta(titulo, preco, link, imagem)
                await asyncio.sleep(3)
            await asyncio.sleep(60)
        await asyncio.sleep(20)

# ===============================
# ENVIO MANUAL DAS ÚLTIMAS OFERTAS
# ===============================
async def cmd_send_now(message: Message):
    await message.answer("⚡ Envio imediato de ofertas ativado! Aguarde alguns segundos...")
    ofertas = buscar_ofertas()
    for titulo, preco, link, imagem in ofertas[:4]:
        await enviar_oferta(titulo, preco, link, imagem)
        await asyncio.sleep(3)
    await message.answer("✅ Ofertas enviadas!")

# ===============================
# ENVIO VIA LINK DIRETO
# ===============================
async def cmd_send_link(message: Message):
    args = message.text.split(" ", 1)
    if len(args) != 2:
        await message.answer("❌ Use: /send_link <URL do produto>")
        return

    link_normal = args[1].strip()
    titulo = "Oferta Direta"
    preco = "Ver no site"
    imagem = "https://cdn-products.eneba.com/resized-products/some-image-example.jpg"  # fallback se não tiver imagem

    # Envia a oferta
    texto, teclado, imagem_url = montar_template(titulo, preco, link_normal, imagem)
    await bot.send_photo(CHAT_ID, photo=imagem_url, caption=texto, reply_markup=teclado, parse_mode="Markdown")
    await message.answer("✅ Oferta enviada via link!")

# ===============================
# INICIALIZAÇÃO DO BOT
# ===============================
async def main():
    dp.message.register(cmd_send_now, F.text.startswith("/send_now"))
    dp.message.register(cmd_send_link, F.text.startswith("/send_link"))

    # Inicia agendador em segundo plano
    asyncio.create_task(agendador())

    print("🤖 BOT ONLINE")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
