FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# NEXT_PUBLIC_* is inlined at build time, so the backend URL must be present
# before `npm run build`. Render passes the service env var of the same name as
# this build arg; locally it defaults to the dev backend.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

EXPOSE 3000
# Honour the platform-injected $PORT (Render, etc.); default to 3000 locally.
CMD ["sh", "-c", "npm start -- -p ${PORT:-3000}"]
