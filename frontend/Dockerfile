# syntax=docker/dockerfile:1.7
FROM node:26-alpine AS base

ENV PNPM_HOME="/pnpm" \
    PATH="/pnpm:$PATH"

RUN npm install --ignore-scripts --global pnpm@12.16.1

WORKDIR /workspace

# -------------------------------------------------------------------
# install dependencies into cached layer
# -------------------------------------------------------------------
FROM base AS deps

COPY package.json pnpm-lock.yaml ./

RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm install --frozen-lockfile

# -------------------------------------------------------------------
# dev
# -------------------------------------------------------------------
FROM deps AS dev

ENV NODE_ENV=development
ENV CI=true

EXPOSE 5173

CMD ["pnpm", "dev", "--host", "0.0.0.0"]

# -------------------------------------------------------------------
# production build & runtime (nginx)
# -------------------------------------------------------------------
FROM deps AS builder

ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=${VITE_API_URL}

COPY . .
RUN pnpm build

FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

COPY --chown=nginx:nginx nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder --chown=nginx:nginx /workspace/dist /usr/share/nginx/html

USER nginx

EXPOSE 8080 8443
CMD ["nginx", "-g", "daemon off;"]
