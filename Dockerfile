# Use a imagem oficial do Python 3.11
FROM python:3.11-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia os arquivos do projeto para o container
COPY . /app

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Define variável de ambiente para Deployra (porta)
ENV PORT=3000

# Comando para rodar o bot
CMD ["python", "bot.py"]
