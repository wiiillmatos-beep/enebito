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
BOT_TOKEN = 8335817419:AAEw-tmkLQgi8n53B4hiWTgE4yKDNtYNVRM
CHAT_ID = -1001234567890  # substitua pelo ID real do seu canal
AFILIADO_PARAMS = "af_id=WiillzeraTV&currency=BRL&region=global&utm_source=WiillzeraTV&utm_medium=infl"

# ===============================
# VARIÁVEIS DE CONTROLE
# ===============================
SEND_NOW = False          # True → envia ofertas imediatamente
NUM_OFERTAS = 4           # quantas ofertas enviar por vez
ENVIO_INTERVALO = 3       # segundos entre envio de cada oferta

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
# FUNÇÃO PARA BUSCAR OFERTAS NO SITE (Eneba)
# ===============================
def buscar_ofertas():
    url = "https://www.eneba.com/br/games"  # página de exemplo
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        req = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(req.text, "html.parser")
        ofertas = []

        produtos = soup.select("div.product-item")[:NUM_OFERTAS]  # pega X produtos
        for p in produtos:
            titulo_tag = p.select_one("a.product-title")
            preco_tag = p.select_one("span.price")
            imagem_tag = p.select_one("img.product-image")

            if titulo_tag and preco_tag and imagem_tag:
                titulo = titulo_tag.text.strip()
                preco = preco_tag.text.strip()
                link = "https://www.eneba.com" + titulo_tag['href']
                imagem = imagem_tag['src']
                ofertas.append({
                    "titulo": titulo,
                    "preco": preco,
                    "link": link,
                    "imagem": imagem
                })
        return ofertas
    except Exception as e:
        print("Erro ao buscar ofertas:", e)
        return []

# ===============================
# FUNÇÃO ROBUSTA PARA ENVIO DE OFERTA
# ===============================
async def enviar_oferta(oferta, chat_id=CHAT_ID):
    link_afiliado = gerar_link_afiliado(oferta["link"])
    
    texto = (
        f"🔥 *OFERTA ENEBA* 🔥\n\n"
        f"🎮 *{oferta['titulo']}*\n"
        f"💰 Preço: *{oferta['preco']}*\n\n"
        f"🔗 Clique no botão abaixo para comprar:"
    )

    teclado = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🛒 COMPRE AQUI", url=link_afiliado)]]
    )

    try:
        await bot.send_photo(
            chat_id,
            photo=oferta["imagem"],
            caption=texto,
            reply_markup=teclado,
            parse_mode="Markdown"
        )
        print(f"✅ Oferta enviada: {oferta['titulo']}")
    except Exception as e:
        print(f"⚠️ Erro ao enviar foto, enviando apenas texto: {e}")
        try:
            await bot.send_message(chat_id, f"{texto}\n{link_afiliado}", parse_mode="Markdown")
            print(f"✅ Oferta enviada como texto: {oferta['titulo']}")
        except Exception as e2:
            print(f"❌ Não foi possível enviar a oferta: {e2}")

# ===============================
# AGENDADOR DE OFERTAS AUTOMÁTICAS
# ===============================
async def agendador():
    global SEND_NOW
    horarios = ["11:00", "17:00", "20:00"]

    while True:
        agora = datetime.datetime.now().strftime("%H:%M")

        if agora in horarios or SEND_NOW:
            print(f"🟢 Postando ofertas ({'SEND_NOW' if SEND_NOW else agora})")
            ofertas = buscar_ofertas()
            for oferta in ofertas:
                await enviar_oferta(oferta)
                await asyncio.sleep(ENVIO_INTERVALO)

            if SEND_NOW:
                SEND_NOW = False  # reseta após enviar

            await asyncio.sleep(60)  # evita repetir no mesmo minuto

        await asyncio.sleep(20)

# ===============================
# HANDLER DO COMANDO /promo
# ===============================
async def cmd_promo(message: Message):
    args = message.text.split(" ", 1)
    if len(args) == 1:
        # /promo → envia ofertas reais
        await message.answer("Enviando ofertas reais no canal...")
        ofertas = buscar_ofertas()
        for oferta in ofertas:
            await enviar_oferta(oferta)
    else:
        # /promo <link> → envia link manual
        link_normal = args[1]
        oferta_manual = {
            "titulo": "Oferta Manual",
            "preco": "Ver no site",
            "link": link_normal,
            "imagem": "https://cdn-products.eneba.com/resized-products/some-image-example.jpg"
        }
        await enviar_oferta(oferta_manual)
        await message.answer("✅ Oferta enviada manualmente!")

# ===============================
# HANDLER DO COMANDO /sendnow
# ===============================
async def cmd_sendnow(message: Message):
    global SEND_NOW
    SEND_NOW = True
    await message.answer("⚡ Envio imediato de ofertas ativado! Aguarde alguns segundos...")

# ===============================
# INICIALIZAÇÃO DO BOT
# ===============================
async def main():
    dp.message.register(cmd_promo, F.text.startswith("/promo"))
    dp.message.register(cmd_sendnow, F.text.startswith("/sendnow"))

    asyncio.create_task(agendador())
    print("🤖 BOT ONLINE")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
