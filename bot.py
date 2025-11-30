import pandas as pd
import requests
import time
import schedule
import os
import io # Necessário para lidar com o encoding do feed CSV

# --- ⚙️ CONFIGURAÇÕES QUE VOCÊ DEVE ALTERAR ---

# Substitua pelo token do seu bot (Obtido com o BotFather)
BOT_TOKEN = 8335817419:AAEw-tmkLQgi8n53B4hiWTgE4yKDNtYNVRM

# Substitua pelo ID do seu grupo/canal (deve ser negativo, ex: -100123456789)
CHAT_ID = -1001872183962
# Link do seu feed de produtos em CSV da Eneba
PLANILHA_URL = "https://www.eneba.com/rss/products.csv?version=3&influencer_id=WiillzeraTV"

# Taxa de câmbio USD para BRL (Atualize este valor regularmente!)
TAXA_DE_CAMBIO = 5.20 # Exemplo: 1 USD = 5.20 BRL

# Nomes das colunas no seu arquivo CSV da Eneba
COLUNA_ID_PRODUTO = 'id'        
COLUNA_PRODUTO = 'name'         
COLUNA_PRECO_USD = 'final_price' # O feed fornece o preço em USD
COLUNA_LINK = 'url'             

# Arquivo para armazenar os IDs dos produtos já enviados
RASTREAMENTO_FILE = 'sent_offers_ids.txt' 

# Valor máximo (em BRL) para filtrar ofertas (ajuste conforme seu público)
PRECO_MAXIMO_FILTRO_BRL = 150.00 

# --- 💾 RASTREAMENTO DE OFERTAS JÁ ENVIADAS ---

def load_sent_ids():
    """Carrega os IDs de produtos já enviados do arquivo local."""
    if not os.path.exists(RASTREAMENTO_FILE):
        return set()
    with open(RASTREAMENTO_FILE, 'r') as f:
        # Lê todas as linhas e remove espaços/linhas em branco
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
        "parse_mode": "Markdown", # Permite usar negrito, links, etc.
        "disable_web_page_preview": False # Mostra a pré-visualização do link
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status() # Lança exceção para erros HTTP
        return True
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar mensagem: {e}")
        return False

def formatar_oferta(row):
    """Formata os dados da linha do CSV em uma mensagem."""
    produto = row[COLUNA_PRODUTO]
    preco_usd = float(row[COLUNA_PRECO_USD])
    preco_brl = preco_usd * TAXA_DE_CAMBIO
    link = row[COLUNA_LINK]
    
    # Formatação para duas casas decimais
    preco_brl_formatado = f"{preco_brl:.2f}".replace('.', ',')
    
    mensagem = (
        f"🎮 **NOVIDADE NA ENEBA!** 🎮\n\n"
        f"🏷️ Jogo: **{produto}**\n"
        f"💸 Preço Estimado: **R$ {preco_brl_formatado}**\n"
        f"_Preço em USD: ${preco_usd:.2f}_\n\n"
        f"[👉 ACESSE A OFERTA AQUI! 👈]({link})\n\n"
        f"---"
    )
    return mensagem

def verificar_e_enviar_ofertas():
    """Lógica principal: lê o feed, aplica filtros, rastreia e envia."""
    print(f"\n[{time.strftime('%H:%M:%S')}] Iniciando verificação de ofertas no feed CSV...")
    
    # 1. Carrega os IDs já enviados
    sent_ids = load_sent_ids()
    ids_enviados_nesta_execucao = []
    
    try:
        # 2. LER O FEED CSV
        # Usamos requests para garantir o encoding correto (utf-8)
        feed_response = requests.get(PLANILHA_URL)
        feed_response.raise_for_status()
        
        # Leitura do conteúdo em memória usando io.StringIO
        data = io.StringIO(feed_response.content.decode('utf-8'))
        df = pd.read_csv(data)
        
        # 3. PRÉ-FILTRAGEM DE DADOS
        # Limpeza: Remove linhas onde o ID ou preço estejam faltando
        df = df.dropna(subset=[COLUNA_ID_PRODUTO, COLUNA_PRECO_USD])
        
        # Converte a coluna de ID para string e preço para float (se não for)
        df[COLUNA_ID_PRODUTO] = df[COLUNA_ID_PRODUTO].astype(str)
        df[COLUNA_PRECO_USD] = pd.to_numeric(df[COLUNA_PRECO_USD], errors='coerce')
        
        # Filtro de preço: Converte para BRL e filtra o que for muito caro
        df['price_brl'] = df[COLUNA_PRECO_USD] * TAXA_DE_CAMBIO
        df_filtrado = df[df['price_brl'] <= PRECO_MAXIMO_FILTRO_BRL]
        
        # 4. FILTRAR POR IDS JÁ ENVIADOS
        ofertas_novas = df_filtrado[~df_filtrado[COLUNA_ID_PRODUTO].isin(sent_ids)]
        
        if ofertas_novas.empty:
            print("Nenhuma nova oferta que atenda aos filtros encontrada.")
            return

        print(f"{len(ofertas_novas)} novas ofertas encontradas para envio.")
        
        # 5. ENVIAR E RASTREAR
        for index, row in ofertas_novas.iterrows():
            mensagem_formatada = formatar_oferta(row)
            
            if enviar_mensagem(mensagem_formatada):
                product_id = row[COLUNA_ID_PRODUTO]
                ids_enviados_nesta_execucao.append(product_id)
                print(f"  -> Oferta '{row[COLUNA_PRODUTO]}' enviada.")
            else:
                print(f"  -> Falha ao enviar oferta '{row[COLUNA_PRODUTO]}'.")

        # 6. SALVAR OS NOVOS IDs
        if ids_enviados_nesta_execucao:
            save_sent_ids(ids_enviados_nesta_execucao)
            print(f"Rastreamento atualizado com {len(ids_enviados_nesta_execucao)} novos IDs.")

    except requests.exceptions.HTTPError as e:
        print(f"ERRO DE CONEXÃO COM O FEED: O link retornou um erro HTTP. Código: {e.response.status_code}")
    except Exception as e:
        print(f"Ocorreu um erro geral no processo: {e}")

# --- ⏰ AGENDAMENTO ---

# Roda a função a cada 10 minutos
schedule.every(10).minutes.do(verificar_e_enviar_ofertas) 

print("===========================================")
print("  Bot de ofertas iniciado. Checando feed...  ")
print("===========================================")

# Loop infinito para manter o agendador rodando
while True:
    schedule.run_pending()
    time.sleep(1) # Espera 1 segundo para não consumir 100% da CPU
