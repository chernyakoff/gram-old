# Agent Rules (neurogram)

## OpenAPI Types

- Do not edit `web/src/types/openapi.d.ts` manually.
- When API schemas change, regenerate types:
  - `cd docker/dev && docker compose up -d api` (safe even if already running)
  - `cd web && npm run openapi-gen`

## Containers Safety

- Never run/build/restart `base` or `dialog` containers without an explicit user request in the current chat.
- If such action may be needed, ask for confirmation first.
