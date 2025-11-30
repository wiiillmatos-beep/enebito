# Imagem base do Python
FROM python:3.11-slim

# Diretório de trabalho dentro do container
WORKDIR /app

# Copia e instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do projeto
COPY . .

# Comando para iniciar o bot
CMD ["python", "bot.py"]
