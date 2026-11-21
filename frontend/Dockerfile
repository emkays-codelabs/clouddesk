# Frontend image (Next.js standalone). Build from the repository root or from frontend/:
#   docker build -f frontend/Dockerfile --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 frontend
# NEXT_PUBLIC_* values are inlined at build time, so rebuild the image per environment.
# Base images are pinned by tag only: pin by digest before production.

FROM node:22-alpine AS deps
# Pin by digest before production.
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
# Pin by digest before production.
WORKDIR /app
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS runner
# Pin by digest before production.
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
WORKDIR /app
RUN addgroup -S app && adduser -S app -G app
# There is no public/ folder yet; add a COPY line for it when one exists.
COPY --from=builder --chown=app:app /app/.next/standalone ./
COPY --from=builder --chown=app:app /app/.next/static ./.next/static
USER app
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:3000/api/health || exit 1
CMD ["node", "server.js"]
