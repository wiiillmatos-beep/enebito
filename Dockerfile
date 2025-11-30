# Usa uma imagem base oficial do Python (versão 3.10 ou a mais estável)
FROM python:3.10-slim

# Define a pasta de trabalho dentro do contêiner
WORKDIR /usr/src/app

# Copia o arquivo de dependências (requirements.txt)
COPY requirements.txt ./

# Instala as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia todos os arquivos do seu projeto (incluindo bot_eneba.py)
COPY . .

# Comando principal que executa o script do bot
# Este comando substitui a necessidade do Procfile
CMD ["python", "bot_eneba.py"]
