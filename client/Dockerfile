FROM node:22-alpine AS build

WORKDIR /app

COPY client/package.json client/package-lock.json ./
RUN npm ci

COPY client .
RUN npm run build

FROM nginx:1.29-alpine

COPY client/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
