FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

ENV VITE_API_URL=http://web:5000/api

CMD ["npm", "run", "dev", "--", "--host"]
