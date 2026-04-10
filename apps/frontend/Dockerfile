# syntax=docker/dockerfile:1
#
# From https://v2.vuejs.org/v2/cookbook/dockerize-vuejs-app.html?redirect=true#Real-World-Example
# and https://docs.docker.com/compose/how-tos/file-watch/
#
# build stage
FROM node:lts-alpine AS build-stage
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# production stage
FROM nginx:stable-alpine AS production-stage
ENV NGINX_PORT=80
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY docker/nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY docker/nginx/runtime-config.js.template /usr/share/nginx/html/runtime-config.js.template
COPY docker/nginx/40-generate-runtime-config.sh /docker-entrypoint.d/40-generate-runtime-config.sh
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
