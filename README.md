# real2block

Photo → Minecraft skin 64×64 → printable papercraft PDF with assembly instructions.

Monorepo: `backend/` (Python 3.12, FastAPI, Pillow, OpenCV, reportlab) and `frontend/` (React, TypeScript, Vite, Tailwind, skinview3d).

## Backend

```bash
cd backend
uv sync
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src
uv run pytest -q
uv run uvicorn real2block.main:app_factory --factory --reload --port 8000
```

Configuration lives in `backend/.env` (see `backend/.env.example`). The YuNet model in `backend/models/` is checked against `SHA256SUMS` on startup.

## Frontend

```bash
cd frontend
npm ci
npm run gen:api   # regenerates src/api/schema.d.ts from a running backend
npx tsc --noEmit && npx eslint . && npx vitest run
npm run dev       # http://localhost:5173, proxies /api to :8000
```

End-to-end tests run against the Docker stack below:

```bash
npx playwright install chromium
npm run e2e        # E2E_BASE_URL defaults to http://localhost:8080
```

`http://localhost:5173/?dev=kitchen-sink` shows every UI component (dev builds only).

## Docker

```bash
docker compose -f docker/compose.yml up             # api + caddy on http://localhost:8080
docker compose -f docker/compose.yml --profile dev up  # plus vite on :5173
```

## Production

On a host with ports 80 and 443 open and a DNS record for the domain pointing at it:

```bash
cp docker/.env.example docker/.env            # set SITE_ADDRESS to the domain
echo "IP_HASH_SALT=$(openssl rand -hex 32)" > backend/.env
docker compose -f docker/compose.yml -f docker/compose.prod.yml up -d --build
docker/smoke-https.sh <domain>
```

Caddy gets the certificate over ACME, redirects HTTP to HTTPS and adds HSTS; certificates live in the `caddy_data` volume. The API runs with `APP_ENV=prod`: CORS off, HSTS on, and it refuses to start without a 32-byte salt.

## Git hooks

```bash
git config core.hooksPath .githooks
```

The pre-commit hook runs lint, types and tests for the part of the repo a commit touches.

## Golden fixtures

`backend/tests/fixtures/reference_*.png` are owner-approved geometry references. They are regenerated only by the owner with `uv run python scripts/make_fixtures.py`.
