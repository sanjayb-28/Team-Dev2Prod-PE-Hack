FROM node:22-alpine AS build

WORKDIR /app

COPY client/package.json client/package-lock.json ./
RUN npm ci

COPY client .
RUN npm run build

FROM nginx:1.29-alpine

COPY client/nginx.http.conf /etc/nginx/templates/http.conf
COPY client/nginx.https.conf /etc/nginx/templates/https.conf
COPY client/entrypoint.sh /entrypoint.sh
COPY --from=build /app/dist /usr/share/nginx/html
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
