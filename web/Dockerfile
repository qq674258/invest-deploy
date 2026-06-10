# syntax=docker/dockerfile:1.4
FROM node:20-alpine AS deps
WORKDIR /app

COPY package.json package-lock.json ./

RUN npm ci --registry=https://registry.npmmirror.com --legacy-peer-deps \
    && test -d node_modules/next

FROM node:20-alpine AS builder
WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1
ENV CI=1
# 编译 ECharts + Next 较吃内存；Docker Desktop 建议分配 ≥4GB
ENV NODE_OPTIONS=--max-old-space-size=4096
ENV API_INTERNAL_URL=http://api:8001

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# 缓存 .next/cache，二次构建会快很多；首次仍可能 5～15 分钟
RUN --mount=type=cache,target=/app/.next/cache \
    npm run build

FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup -g 1001 nodejs && adduser -u 1001 -G nodejs -D nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
ENV API_INTERNAL_URL=http://api:8001

CMD ["node", "server.js"]
