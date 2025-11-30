import requests
from bs4 import BeautifulSoup
import time
import schedule
import os
import io
import json
import random 
import asyncio
from flask import Flask
from threading import Thread

# Importações do Python Telegram Bot (PTB)
from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackContext, filters

# --- ⚙️ CONFIGURAÇÕES (LENDO VARIÁVEIS DE AMBIENTE) ---

BOT_TOKEN = os.getenv("BOT_TOKEN") 
CHAT_ID = os.getenv("CHAT_ID")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", 0)) 

# ** ALERTA: SUBSTITUA ESTE LINK **
# Use a URL exata da página de ofertas da Eneba que você quer monitorar (ex: Xbox)
SCRAPING_URL = "https://www.eneba.com/store/xbox-games?page=1&sortBy=PRICE_ASC" 

PRECO_MAXIMO_FILTRO_BRL = 150.00 
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
RASTREAMENTO_FILE = 'sent_offers_ids.txt' 

telegram_bot = Bot(token=BOT_TOKEN or "placeholder") 

# --- 💵 FUNÇÃO PARA BUSCAR A COTAÇÃO DE CÂMBIO (EUR/BRL) ---

def get_exchange_rate():
    """Busca a taxa de câmbio EUR/BRL atualizada."""
    API_URL = "https://api.exchangerate-api.com/v4/latest/EUR"
    try:
        response = requests.get(API_URL, timeout=10) 
        response.raise_for_status() 
        # Busca a taxa BRL dentro da lista de taxas do EUR.
        return response.json()['rates']['BRL']
    except requests.exceptions.RequestException:
        print("⚠️ Erro ao obter câmbio EUR/BRL. Usando taxa fallback (5.50).")
        return 5.50 # Taxa fallback ajustada para refletir um valor de Euro mais realista

# --- 💾 RASTREAMENTO E ENVIO ---

def load_sent_ids():
    """Carrega IDs de ofertas já enviadas."""
    if not os.path.exists(RASTREAMENTO_FILE):
        return set()
    with open(RASTREAMENTO_FILE, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def save_sent_ids(ids_para_adicionar):
    """Salva novos IDs de ofertas enviadas."""
    with open(RASTREAMENTO_FILE, 'a') as f:
        for product_id in ids_para_adicionar:
            f.write(f"{product_id}\n")

async def enviar_mensagem(chat_id_destino, texto):
    """Envia a mensagem ao Telegram."""
    if not telegram_bot.token or not chat_id_destino:
        return False
        
    try:
        await telegram_bot.send_message(
            chat_id=chat_id_destino,
            text=texto,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False
        )
        return True
    except Exception as e:
        print(f"Erro ao enviar mensagem para {chat_id_destino}: {e}")
        return False

def formatar_oferta(oferta, exchange_rate):
    """Formata os dados extraídos em uma mensagem."""
    produto = oferta.get('name', 'Produto Desconhecido')
    preco_eur = oferta.get('price_usd', 0.0) # Renomeado internamente para price_eur
    link = oferta.get('url', '#')
    
    try:
        preco_eur = float(preco_eur)
        preco_brl = preco_eur * exchange_rate
    except (ValueError, TypeError):
        preco_brl = 0.0
        
    preco_brl_formatado = f"{preco_brl:.2f}".replace('.', ',')
    
    mensagem = (
        f"🔥 **NOVA OFERTA!** 🔥\n\n"
        f"🏷️ Jogo: **{produto}**\n"
        f"💸 Preço Estimado: **R$ {preco_brl_formatado}**\n"
        f"_Preço em EUR: €{preco_eur:.2f} | Câmbio: {exchange_rate:.4f}_\n\n"
        f"[🛒 COMPRE AQUI! 🛒]({link})\n\n"
        f"---"
    )
    return mensagem

# --- 🕷️ FUNÇÃO DE WEB SCRAPING ---

def perform_scraping(url):
    """Extrai nome, preço e link dos produtos da Eneba usando BeautifulSoup."""
    headers = {'User-Agent': USER_AGENT}
    ofertas = []
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Seletor genérico para os cards de produto da Eneba (pode precisar de ajuste)
        product_cards = soup.find_all('div', class_=lambda c: c and 'product-list-item' in c)
        
        if not product_cards:
            print("⚠️ Scraping: Não encontrou cards de produto. O seletor pode estar desatualizado.")
            return ofertas

        for card in product_cards:
            # Extrai Link e ID
            link_tag = card.find('a', href=True)
            link = "https://www.eneba.com" + link_tag['href'] if link_tag else None
            product_id = link.split('/')[-1] if link else None
            
            # Extrai Nome
            name_tag = card.find('span', class_=lambda c: c and 'product-title' in c)
            name = name_tag.text.strip() if name_tag else None
            
            # Extrai Preço (muito sensível ao layout do site!)
            price_tag = card.find('div', class_=lambda c: c and 'product-price' in c)
            price_eur = None
            if price_tag:
                # Remove símbolos de moeda ($, €, R) e substitui vírgula por ponto para float
                price_text = price_tag.text.replace('$', '').replace('€', '').replace('R', '').replace(',', '.').strip()
                try:
                    price_eur = float(price_text)
                except ValueError:
                    price_eur = None
            
            if name and link and price_eur:
                 ofertas.append({
                    'id': product_id,
                    'name': name,
                    'price_usd': price_eur, # Mantemos o nome 'price_usd' para compatibilidade, mas é EUR
                    'url': link
                })

        print(f"Scraping concluído: Encontradas {len(ofertas)} ofertas.")
        return ofertas

    except requests.exceptions.RequestException as e:
        print(f"ERRO DE CONEXÃO/SCRAPING: {e}")
        return []

# --- 🚀 LÓGICA DE BUSCA DE OFERTAS AGENDADAS (COM SCRAPING) ---

def buscar_e_enviar_ofertas(numero_de_ofertas):
    """Faz o scraping, filtra e envia ofertas novas."""
    print(f"Iniciando Scraping e buscando {numero_de_ofertas} novas ofertas...")
    
    if not BOT_TOKEN or not CHAT_ID: return

    current_exchange_rate = get_exchange_rate()
    sent_ids = load_sent_ids()
    ids_enviados_nesta_execucao = []
    
    ofertas_extraidas = perform_scraping(SCRAPING_URL)
    
    if not ofertas_extraidas:
        print("Scraping falhou ou não retornou dados. Nenhuma oferta para processar.")
        return

    ofertas_para_enviar = []
    
    for oferta in ofertas_extraidas:
        product_id = oferta.get('id')
        price_eur = oferta.get('price_usd', 0.0) # É o valor em Euro
        
        # Filtros
        if product_id not in sent_ids:
            try:
                price_brl = price_eur * current_exchange_rate
                if price_brl <= PRECO_MAXIMO_FILTRO_BRL:
                    ofertas_para_enviar.append(oferta)
            except (TypeError, ValueError):
                continue

    # Seleciona o número desejado de ofertas novas
    ofertas_para_enviar = ofertas_para_enviar[:numero_de_ofertas]

    if not ofertas_para_enviar:
        print("Nenhuma nova oferta que atenda aos filtros foi encontrada após o scraping.")
        return
    
    # ... (Restante do loop de envio)
    print(f"Enviando {len(ofertas_para_enviar)} ofertas...")
    
    for oferta in ofertas_para_enviar:
        mensagem_formatada = formatar_oferta(oferta, current_exchange_rate)
        
        asyncio.run(enviar_mensagem(CHAT_ID, mensagem_formatada))
        
        product_id = oferta.get('id')
        ids_enviados_nesta_execucao.append(product_id)
        print(f"  -> Oferta '{oferta.get('name', 'N/A')}' enviada.")

    if ids_enviados_nesta_execucao:
        save_sent_ids(ids_enviados_nesta_execucao)
        print(f"Rastreamento atualizado com {len(ids_enviados_nesta_execucao)} novos IDs.")

# --- 📅 FUNÇÕES DE AGENDAMENTO E COMANDOS MANUAIS (Inalteradas) ---

def enviar_mensagem_personalizada(mensagem):
    """Envia uma mensagem de texto simples e depois busca 4 ofertas."""
    import asyncio
    asyncio.run(enviar_mensagem(CHAT_ID, mensagem))
    buscar_e_enviar_ofertas(4) 

def agendar_0930():
    mensagem = "☀️ **BOM DIA, CHAT! É HORA DE ECONOMIZAR!** 🚀\n\nAcompanhe as ofertas fresquinhas para começar o dia no game!"
    enviar_mensagem_personalizada(
