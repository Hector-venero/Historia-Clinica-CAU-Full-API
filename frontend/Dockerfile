# frontend/Dockerfile

# === Build Stage ===
FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm install

# Copiamos el código fuente
COPY . .

# Argumentos de construcción (necesarios para que Vite "queme" la variable en el JS)
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# === Deploy Stage ===
FROM nginx:latest

# Aquí usamos el default.conf que trae Nginx por defecto o creamos uno simple inline.
# Como este Nginx está DETRÁS del proxy principal, una config básica sirve.
COPY --from=build /app/dist /usr/share/nginx/html

# Configuración básica para SPA (React/Vue) para que no de 404 al recargar
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80