# ---- Build stage ----
FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY . .
RUN npm run build

# ---- Production stage ----
FROM nginx:alpine

# Create non-root user
RUN addgroup -S ilews && adduser -S ilews -G ilews

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Nginx runs as root to bind port 80, but worker processes run as nobody
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
