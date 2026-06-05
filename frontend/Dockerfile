# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies (cached unless package.json changes)
COPY package.json package-lock.json* ./
RUN npm install

# Copy source and build the production bundle
COPY . .
RUN npm run build

# ── Stage 2: Minimal image to hold the built artifacts ────────────────────────
# We use a tiny alpine image just so the container can run and share the
# built files via a Docker volume.  The actual serving is done by nginx.
FROM alpine:3.20

RUN apk add --no-cache tini
COPY --from=build /app/dist /usr/share/nginx/html

# Keep container alive so docker-compose doesn't restart it
ENTRYPOINT ["tini", "--"]
CMD ["sleep", "infinity"]
