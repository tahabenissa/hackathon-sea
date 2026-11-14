# Build the React app, then serve it with Caddy (auto HTTPS + reverse proxy to the API).
# Build context = project root (see docker-compose.yml), so the Caddyfile in infra/ is reachable.
FROM node:22-alpine AS build
WORKDIR /app
COPY dashboard/package*.json ./
RUN npm ci
COPY dashboard/ .
RUN npm run build

FROM caddy:2-alpine
COPY --from=build /app/dist /srv
COPY infra/caddy/Caddyfile /etc/caddy/Caddyfile
