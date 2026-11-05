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

COPY . .
RUN pnpm build

FROM nginx:1.27-alpine AS runtime
COPY --from=builder /workspace/dist /usr/share/nginx/html

USER nginx

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
