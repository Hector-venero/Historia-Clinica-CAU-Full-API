# frontend/Dockerfile

# === Build Stage ===
FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
# npm ci y no npm install: instala exactamente lo que fija el package-lock.json
# y falla si el lockfile no coincide con package.json, en vez de resolver
# versiones nuevas en silencio.
RUN npm ci

# Copiamos el código fuente
COPY . .

# Argumentos de construcción (necesarios para que Vite "queme" la variable en el JS)
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# === Deploy Stage ===
FROM nginx:latest

COPY --from=build /app/dist /usr/share/nginx/html

# La config va en un archivo aparte y no embebida en un `RUN echo`: asi se puede
# leer, comentar y versionar. La anterior no declaraba cache, y por eso el
# navegador se quedaba con un index.html viejo que seguia pidiendo los assets
# anteriores aunque se reconstruyera la imagen. Ver frontend/nginx.conf.
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80