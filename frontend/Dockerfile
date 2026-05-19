FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# ▼ アプリケーションが使用するポートを明示（Viteなら5173、Create React Appなら3000）
EXPOSE 5173

# ▼ 起動コマンドを追記（package.jsonのscriptsに合わせて "npm run dev" や "npm start" にしてください）
CMD ["npm", "run", "dev"]