FROM nginx:latest

# Copiamos la configuración
COPY default.conf /etc/nginx/conf.d/default.conf

# Copiamos el frontend producido por el build
COPY ../frontend/dist /usr/share/nginx/html
