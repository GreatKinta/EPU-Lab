FROM node:20-slim
WORKDIR /app
COPY package*.json ./
RUN apt-get update && apt-get install -y python3 make g++ && \
    npm install --omit=dev && \
    apt-get purge -y python3 make g++ && apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]