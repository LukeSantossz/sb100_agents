FROM node:20-alpine

WORKDIR /app

# Instalar dependências primeiro (cache)
COPY package.json package-lock.json* ./
RUN npm install

# Copiar o resto do código fonte e .env
COPY . .

EXPOSE 5173

# Definimos HOST no script start ou aqui via variável
ENV HOST=0.0.0.0

CMD ["npm", "run", "dev", "--", "--host"]
