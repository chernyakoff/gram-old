# Agent Rules (GRAM-OLD Project)

## Migrations (Mandatory Workflow)

When migrations are needed, use this flow in the target repo:

1. Go to service dev docker directory:
   - `cd /home/mike/work/python/gram-old/docker/dev`
2. Enter API container:
   - `docker compose exec api bash`
3. Run migration commands:
   - `./task migration`
   - `./task migrate`

Alternative (inside API container):
- `uv run aerich migrate --name <message>`
- `uv run aerich upgrade`

Migration rule:
- Use the workflow above (or direct `uv run aerich ...`) for all migration operations.

## OpenAPI Types

- Do not edit `web/src/types/openapi.d.ts` manually.
- When API schemas change, regenerate types:
  - `cd docker/dev && docker compose up -d api` (safe even if already running)
  - `cd web && npm run openapi-gen`

## Containers Safety

- Never run/build/restart `base-worker` or `dialog-work` containers without an explicit user request in the current chat.
- If such action may be needed, ask for confirmation first.

## Hatchet Stubs

- Use `./sync` (not `./task cli sync`) for worker sync operations.
- After any change under `api/app/common`, run:
  - `cd /home/mike/work/python/gram-old/workers/base && ./sync`
  - `cd /home/mike/work/python/gram-old/workers/dialog && ./sync`
- After adding any new task or workflow in `/home/mike/work/python/gram-old/workers/base/app/worker.py`, run:
  - `cd /home/mike/work/python/gram-old/workers/base && ./sync`
