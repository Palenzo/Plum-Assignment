FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# No build-time backend URL needed: the app proxies /api/* through its own
# server at runtime (see src/app/api/[...path]/route.ts), reading BACKEND_URL
# when the container starts.
RUN npm run build

EXPOSE 3000
# Honour the platform-injected $PORT (Render, etc.); default to 3000 locally.
CMD ["sh", "-c", "npm start -- -p ${PORT:-3000}"]
