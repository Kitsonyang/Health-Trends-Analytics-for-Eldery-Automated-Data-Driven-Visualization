FROM node:18-alpine AS build
WORKDIR /app

# Install deps
COPY package*.json ./
RUN npm install --silent

# Copy source code
COPY . .

# Accept build args for environment variables
ARG VITE_PBI_EMBED_URL
ARG VITE_API_BASE
ARG VITE_MAX_UPLOAD_MB

# Set environment variables for Vite build
ENV VITE_PBI_EMBED_URL=${VITE_PBI_EMBED_URL}
ENV VITE_API_BASE=${VITE_API_BASE}
ENV VITE_MAX_UPLOAD_MB=${VITE_MAX_UPLOAD_MB}

# Build with environment variables
RUN npm run build

# --- Runtime image ---
FROM nginx:alpine

# Replace default server config with SPA-friendly config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy build output
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

# Healthcheck (optional)
HEALTHCHECK CMD wget -qO- http://localhost/ >/dev/null || exit 1


