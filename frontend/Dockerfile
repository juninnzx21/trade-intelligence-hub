FROM node:22-alpine

WORKDIR /app

COPY package.json .
RUN npm install

COPY tsconfig.json vite.config.ts index.html ./
COPY src ./src

CMD ["npm", "run", "dev"]
