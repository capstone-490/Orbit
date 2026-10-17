# Workflow

## Lint & Format

```bash
pnpm lint
pnpm check
pnpm biome format ./src


# apply fixes
pnpm biome lint --write ./src
npm biome check --write ./dir
pnpm biome format --write ./dir

```

## Test

```bash
pnpm vitest run --coverage
```
