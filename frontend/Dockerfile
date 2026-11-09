FROM node:24-slim AS build
WORKDIR /app
# Next fija los rewrites (/api/v1, /media) y las variables NEXT_PUBLIC_* al compilar.
ARG API_URL
ARG NEXT_PUBLIC_SITE_URL
ARG NEXT_PUBLIC_IMAGE_HOSTS
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build && npm prune --omit=dev

FROM node:24-slim
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
COPY --from=build /app ./
CMD ["sh", "-c", "exec npx next start -H 0.0.0.0 -p ${PORT:-3000}"]
