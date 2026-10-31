# Built from the repository root (see docker-compose.yml), because the app reads
# docs/brand/. web/Dockerfile.dockerignore limits the context to what it needs.

FROM node:22-alpine AS build
WORKDIR /repo/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY docs/brand /repo/docs/brand
COPY web/ ./
RUN npm run build

FROM nginx:1.29-alpine
COPY web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /repo/web/dist /usr/share/nginx/html
EXPOSE 8080
