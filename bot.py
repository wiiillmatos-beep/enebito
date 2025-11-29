import os
import asyncio
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

# ===============================
# CONFIGURAÇÕES DO BOT
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = -1001872183962  # substitua pelo ID real do seu canal
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
# BUSCAR INFORMAÇÕES DO PRODUTO
# ===============================
def buscar_info_produto(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")

        # Título
        titulo_tag = soup.find("h1", class_="product-title")
        titulo = titulo_tag.get_text(strip=True) if titulo_tag else "Sem título"

        # Preço
        preco_tag = soup.find("span", class_="price")
        preco = preco_tag.get_text(strip=True) if preco_tag else "Ver no site"

        # Imagem
        img_tag = soup.find("img", class_="product-image")
        imagem = img_tag.get("data-src") or img_tag.get("src") if img_tag else "https://cdn-products.eneba.com/resized-products/some-image-example.jpg"
        if imagem.startswith("//"):
            imagem = "https:" + imagem

        return titulo, preco, imagem

    except Exception as e:
        print(f"❌ Erro ao buscar produto: {e}")
        return "Produto Eneba", "Ver no site", "https://cdn-products.eneba.com/resized-products/som
