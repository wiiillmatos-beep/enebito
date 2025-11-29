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
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = -1001234567890  # substitua pelo ID real do seu canal
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
# FUNÇÃO PARA BUSCAR OFERTAS NO SITE (Eneba)
# ===============================
def buscar_ofertas():
    url = "https://www.eneba.com/br/games"  # página de exemplo
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        req = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(req.text, "html.parser")
        
        ofertas = []

        # Exemplo: seleciona produtos na página
        produtos = soup.select("div.product-item")[:4]  # pega 4 primeiros produtos
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
async def enviar_oferta(oferta):
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
            CHAT_ID,
            photo=oferta["imagem"],
            caption=texto,
            reply_markup=teclado,
            parse_mode="Markdown"
        )
        print(f"✅ Oferta enviada: {oferta['titulo']}")
    except Exception as e:
        print(f"⚠️ Erro ao enviar foto, enviando apenas texto: {e}")
        try:
            await bot.send_message(CHAT_ID, f"{texto}\n{link_afiliado}", parse_mode="Markdown")
            print(f"✅ Oferta enviada como texto: {oferta['titulo']}")
        except Exception as e2:
            print(f"❌ Não foi possível enviar a oferta: {e2}")

# ===============================
# AGENDADOR DE OFERTAS AUTOMÁTICAS
# ===============================
async def agendador():
    horarios = ["11:00", "17:00", "20:00"]

    while True:
        agora = datetime.datetime.now().strftime("%H:%M")
        if agora in horarios:
            print(f"🟢 Postando ofertas automáticas ({agora})")
            ofertas = buscar_ofertas()
            for oferta in ofertas:
                await enviar_oferta(oferta)
                await asyncio.sleep(3)
            await asyncio.sleep(60)  # evita repetir no mesmo minuto
        await asyncio.sleep(20)

# ===============================
# HANDLER DO COMANDO /promo
# ===============================
async def cmd_promo(message: Message):
    args = message.text.split(" ", 1)
    if len(args) == 1:
        # /promo → envia ofertas atuais
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
# INICIALIZAÇÃO DO BOT
# ===============================
async def main():
    dp.message.register(cmd_promo, F.text.startswith("/promo"))
    asyncio.create_task(agendador())  # inicia agendador em segundo plano
    print("🤖 BOT ONLINE")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
