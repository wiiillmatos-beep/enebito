import pandas as pd
import requests
import time
import schedule
import os
import io
import json 

# --- ⚙️ CONFIGURAÇÕES QUE VOCÊ DEVE ALTERAR ---

# 🛑 1. Substitua pelo token do seu bot (Obtido com o BotFather)
BOT_TOKEN = "SEU_BOT_TOKEN_AQUI" 

# 🛑 2. Substitua pelo ID do seu grupo/canal (deve ser negativo, ex: -100123456789)
CHAT_ID = "ID_DO_SEU_GRUPO_AQUI"

# Link do seu feed de produtos em CSV da Eneba
PLANILHA_URL = "https://www.eneba.com/rss/products.csv?version=3&influencer_id=WiillzeraTV"

# Nomes das colunas no seu arquivo CSV da Eneba
COLUNA_ID_PRODUTO = 'id'        
COLUNA_PRODUTO = 'name'         
COLUNA_PRECO_USD = 'final_price' 
COLUNA_LINK = 'url'             # Contém seu ID de afiliado

# Arquivo para armazenar os IDs dos produtos já enviados
RASTREAMENTO_FILE = 'sent_offers_ids.txt' 

# Valor máximo (em BRL) para filtrar ofertas (AJUSTE ESTE VALOR)
PRECO_MAXIMO_FILTRO_BRL = 150.00 

# --- 💵 FUNÇÃO PARA BUSCAR A COTAÇÃO DE CÂMBIO AUTOMATICAMENTE ---

def get_exchange_rate():
    """Busca a taxa de câmbio USD/BRL atualizada de uma API pública."""
    
    API_URL = "https://api.exchangerate-api.com/v4/latest/USD"
    
    try:
        response = requests.get(API_URL, timeout=10) 
        response.raise_for_status() 
        
        data = response.json()
        rate = data['rates']['BRL']
        
        print(f"Taxa de câmbio USD->BRL obtida: {rate:.4f}")
        return rate
        
    except requests.exceptions.RequestException as e:
        print(f"⚠️ ERRO: Não foi possível obter a taxa de câmbio. Usando taxa fallback (5.00). Erro: {e}")
        # Valor de segurança (fallback) caso a API falhe
        return 5.00 

# --- 💾 RASTREAMENTO DE OFERTAS JÁ ENVIADAS ---

def load_sent_ids():
    """Carrega os IDs de produtos já enviados do arquivo local."""
    if not os.path.exists(RASTREAMENTO_FILE):
        return set()
    with open(RASTREAMENTO_FILE, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def save_sent_ids(ids_para_adicionar):
    """Adiciona novos IDs à lista de rastreamento no arquivo local."""
    with open(RASTREAMENTO_FILE, 'a') as f:
        for product_id in ids_para_adicionar:
            f.write(f"{product_id}\n")

# --- 🚀 FUNÇÕES PRINCIPAIS ---

def enviar_mensagem(texto):
    """Função que envia a mensagem para o Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": texto,
        "parse_mode": "Markdown", 
        "disable_web_page_preview": False 
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status() 
        return True
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar mensagem: {e}")
        return False

def formatar_oferta(row, exchange_rate):
    """
    Formata os dados da linha do CSV em uma mensagem com o novo layout 
    e o botão de compra.
    """
    produto = row[COLUNA_PRODUTO]
    preco_usd = float(row[COLUNA_PRECO_USD])
    preco_brl = preco_usd * exchange_rate
    link = row[COLUNA_LINK] # Link já contém o ID de afiliado
    
    preco_brl_formatado = f"{preco_brl:.2f}".replace('.', ',')
    
    # *** ALTERAÇÃO SOLICITADA AQUI ***
    mensagem = (
        f"🔥 **NOVA OFERTA!** 🔥\n\n"
        f"🏷️ Jogo: **{produto}**\n"
        f"💸 Preço Estimado: **R$ {preco_brl_formatado}**\n"
        f"_Preço em USD: ${preco_usd:.2f} | Câmbio: {exchange_rate:.4f}_\n\n"
        f"[🛒 COMPRE AQUI! 🛒]({link})\n\n"
        f"---"
    )
    return mensagem

def verificar_e_enviar_ofertas():
    """Lógica principal: busca câmbio, lê o feed, aplica filtros, rastreia e envia."""
    print(f"\n[{time.strftime('%H:%M:%S')}] Iniciando verificação de ofertas no feed CSV...")
    
    # 1. BUSCAR A TAXA DE CÂMBIO ATUALIZADA
    current_exchange_rate = get_exchange_rate()
    
    # 2. Carrega os IDs já enviados
    sent_ids = load_sent_ids()
    ids_enviados_nesta_execucao = []
    
    try:
        # 3. LER O FEED CSV
        feed_response = requests.get(PLANILHA_URL, timeout=30)
        feed_response.raise_for_status()
        
        data = io.StringIO(feed_response.content.decode('utf-8'))
        df = pd.read_csv(data)
        
        # 4. PRÉ-FILTRAGEM E CONVERSÃO
        df = df.dropna(subset=[COLUNA_ID_PRODUTO, COLUNA_PRECO_USD])
        df[COLUNA_ID_PRODUTO] = df[COLUNA_ID_PRODUTO].astype(str)
        df[COLUNA_PRECO_USD] = pd.to_numeric(df[COLUNA_PRECO_USD], errors='coerce')
        
        # Filtro de preço: Converte para BRL e filtra
        df['price_brl'] = df[COLUNA_PRECO_USD] * current_exchange_rate
        df_filtrado = df[df['price_brl'] <= PRECO_MAXIMO_FILTRO_BRL]
        
        # 5. FILTRAR POR IDS JÁ ENVIADOS
        ofertas_novas = df_filtrado[~df_filtrado[COLUNA_ID_PRODUTO].isin(sent_ids)]
        
        if ofertas_novas.empty:
            print("Nenhuma nova oferta que atenda aos filtros encontrada.")
            return

        print(f"{len(ofertas_novas)} novas ofertas encontradas para envio.")
        
        # 6. ENVIAR E RASTREAR
        for index, row in ofertas_novas.iterrows():
            mensagem_formatada = formatar_oferta(row, current_exchange_rate)
            
            if enviar_mensagem(mensagem_formatada):
                product_id = row[COLUNA_ID_PRODUTO]
                ids_enviados_nesta_execucao.append(product_id)
                print(f"  -> Oferta '{row[COLUNA_PRODUTO]}' enviada.")
            else:
                print(f"  -> Falha ao enviar oferta '{row[COLUNA_PRODUTO]}'.")

        # 7. SALVAR OS NOVOS IDs
        if ids_enviados_nesta_execucao:
            save_sent_ids(ids_enviados_nesta_execucao)
            print(f"Rastreamento atualizado com {len(ids_enviados_nesta_execucao)} novos IDs.")

    except requests.exceptions.HTTPError as e:
        print(f"ERRO DE CONEXÃO COM O FEED: O link retornou um erro HTTP. Código: {e.response.status_code}")
    except Exception as e:
        print(f"Ocorreu um erro geral no processo: {e}")

# --- ⏰ AGENDAMENTO ---

# Roda a função principal a cada 10 minutos
schedule.every(10).minutes.do(verificar_e_enviar_ofertas) 

print("===========================================")
print("  Bot de ofertas iniciado. Checando feed...  ")
print("===========================================")

# Loop infinito para manter o agendador rodando
while True:
    schedule.run_pending()
    time.sleep(1)
