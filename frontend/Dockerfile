# =============== 🧱 BUILD STAGE ===============
FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# =============== 🚀 DEPLOY STAGE ===============
FROM nginx:latest AS deploy

COPY --from=build /app/dist /usr/share/nginx/html
