FROM node:24-bookworm-slim
WORKDIR /app
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --fetch-retries=5 --fetch-timeout=120000 --maxsockets=5
COPY . .
RUN npm run compile
EXPOSE 8545
CMD ["npx", "hardhat", "node", "--hostname", "0.0.0.0"]
