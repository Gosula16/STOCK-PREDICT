# RentAI / STOCK-PREDICT - AI-assisted trading control plane

Monorepo for a personal AI-driven trading system with a Next.js dashboard, NestJS gateway, FastAPI orchestrator, optional Groww broker integration, and optional Hugging Face sentiment inference.

> Not financial advice. Live trading can lose money. Use paper mode and tiny size until you trust the stack.

## Live links

Verified on March 28, 2026:

| What | Status | URL |
|------|--------|-----|
| Production dashboard | Public | [https://frontend-rho-flame-38.vercel.app](https://frontend-rho-flame-38.vercel.app) |
| Source repository | Public | [https://github.com/Gosula16/STOCK-PREDICT](https://github.com/Gosula16/STOCK-PREDICT) |
| Vercel project settings | Requires owner login | [https://vercel.com/125015164-4269s-projects/frontend/settings/environment-variables](https://vercel.com/125015164-4269s-projects/frontend/settings/environment-variables) |

Important: the dashboard is live, but signals, broker status, and control actions need a public gateway URL plus the shared `API_SECRET`. Without that backend deployment, the frontend can load while API panels stay empty or show an error.

## Architecture

```text
Browser -> Next.js (Vercel) -> /api/gateway/* proxy
        -> NestJS gateway -> FastAPI orchestrator -> Redis (optional) / Groww / HF
```

- `frontend/` - Next.js 15 dashboard and API proxy route.
- `gateway/` - NestJS public API facade and readiness endpoint.
- `orchestrator/` - FastAPI trading control plane, broker hooks, risk checks, audit logging.
- `app/` - legacy Streamlit demo.

This repo is production-oriented infrastructure, not a finished trading strategy. Broker connectivity and guardrails are here; alpha generation, backtests, compliance review, and operational maturity are still on you.

## Production status

What is already in place:

- Frontend production build succeeds.
- Frontend lint passes.
- Gateway build succeeds.
- Orchestrator test suite passes.
- CI builds frontend, gateway, orchestrator, and both Docker images on pushes and pull requests.
- Health and readiness endpoints exist for gateway and orchestrator.
- Production secret validation is enforced for gateway and orchestrator.

What still must be provided by the operator:

- Public hosting for the orchestrator.
- Public hosting for the gateway.
- Real environment variables in Vercel and backend hosts.
- Monitoring, alerting, backups, incident response, and legal/compliance review before live money.

## Quick start (local)

### Docker stack

From the repo root:

```powershell
copy .env.example .env
docker compose up --build
```

Defaults:

- Redis: `localhost:6379`
- Orchestrator: `http://localhost:8000`
- Gateway: `http://localhost:3001`
- Shared secret: `API_SECRET=dev-change-me`

### Frontend

```powershell
cd frontend
copy ..\.env.example .env.local
npm install
npm run dev
```

Set these in `frontend/.env.local`:

- `GATEWAY_URL=http://localhost:3001`
- `API_SECRET=dev-change-me`

Then open [http://localhost:3000](http://localhost:3000).

### Without Docker

Orchestrator:

```powershell
cd orchestrator
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:API_SECRET="dev-change-me"
uvicorn app.main:app --reload --port 8000
```

Gateway:

```powershell
cd gateway
npm install
$env:API_SECRET="dev-change-me"
$env:ORCHESTRATOR_URL="http://127.0.0.1:8000"
$env:PORT="3001"
npm run start:dev
```

## Production deployment

### 1. Deploy the orchestrator

Deploy `orchestrator/` to a host that supports Docker or Python, such as Render, Railway, Fly.io, AWS, or your own VPS.

Required environment variables:

- `API_SECRET` - 32+ random characters
- `ENVIRONMENT=production`

Optional environment variables:

- `REDIS_URL`
- `CORS_ORIGINS`
- `BROKER_MODE`
- `GROWW_AUTH_TOKEN`
- `GROWW_INSTRUMENTS_JSON`
- `GROWW_ALLOW_BROKER_MUTATIONS`
- `HUGGINGFACE_API_TOKEN` or `HF_TOKEN`
- `HF_ENABLE_IN_PIPELINE`
- `RISK_*`

Health checks:

- Liveness: `/health`
- Readiness: `/ready`

### 2. Deploy the gateway

Deploy `gateway/` separately and point it at the orchestrator.

Required environment variables:

- `API_SECRET` - same value as the orchestrator
- `ORCHESTRATOR_URL=https://your-orchestrator-host`
- `NODE_ENV=production`

Optional environment variables:

- `PORT`
- `CORS_ORIGIN=https://your-frontend-domain`

Health checks:

- Liveness: `/api/health`
- Readiness: `/api/ready`

### 3. Connect Vercel to the gateway

In the Vercel project environment settings, add:

- `GATEWAY_URL=https://your-gateway-host`
- `API_SECRET=the-same-shared-secret`

Then redeploy the frontend.

### 4. Enable automatic frontend deploys

Connect the Vercel project to the GitHub repo and set the root directory to `frontend`.

## Environment variables

| Variable | Service | Purpose |
|----------|---------|---------|
| `API_SECRET` | Gateway, orchestrator, Vercel | Shared bearer token for protected API routes |
| `GATEWAY_URL` | Vercel frontend | Public gateway base URL |
| `ORCHESTRATOR_URL` | Gateway | Base URL for orchestrator forwarding |
| `ENVIRONMENT` | Orchestrator | `development`, `staging`, or `production` |
| `NODE_ENV` | Gateway | Use `production` in hosted deployments |
| `CORS_ORIGINS` | Orchestrator | Allowed frontend origins |
| `CORS_ORIGIN` | Gateway | Allowed frontend origins |
| `REDIS_URL` | Orchestrator | Optional state and readiness dependency |
| `BROKER_MODE` | Orchestrator | `paper` or `live` |
| `GROWW_AUTH_TOKEN` | Orchestrator | Groww auth token |
| `GROWW_INSTRUMENTS_JSON` | Orchestrator | Instrument list for LTP lookup |
| `GROWW_ALLOW_BROKER_MUTATIONS` | Orchestrator | Enable place, cancel, modify |
| `HUGGINGFACE_API_TOKEN` / `HF_TOKEN` | Orchestrator | Hugging Face inference access |
| `HF_ENABLE_IN_PIPELINE` | Orchestrator | Optional sentiment hook in pipeline |
| `RISK_*` | Orchestrator | Risk caps and order validation |

See [`.env.example`](.env.example) for the full list.

## API surface

Via the gateway, all `/api/v1/*` routes expect `Authorization: Bearer <API_SECRET>` when `API_SECRET` is set.

Public routes:

- `GET /api/health`
- `GET /api/ready`

Protected routes:

- `GET /api/v1/signals`
- `GET /api/v1/control/status`
- `POST /api/v1/control/trading`
- `POST /api/v1/pipeline/tick`
- `GET /api/v1/broker/status`
- `GET /api/v1/broker/orders`
- `GET /api/v1/broker/holdings`
- `GET /api/v1/broker/orders/status`
- `POST /api/v1/broker/margins/preview`
- `POST /api/v1/broker/orders/place`
- `POST /api/v1/broker/orders/cancel`
- `POST /api/v1/broker/orders/modify`
- `POST /api/v1/ml/sentiment`

The orchestrator also exposes `/health`, `/ready`, and the same functional routes under `/v1/*`.

## Groww

To use Groww:

1. Create credentials through the [Groww Trade API](https://www.groww.in/trade-api).
2. Put the auth token in `GROWW_AUTH_TOKEN`.
3. Put instrument metadata in `GROWW_INSTRUMENTS_JSON`.
4. Keep `BROKER_MODE=paper` until you have validated the system.
5. Only set `GROWW_ALLOW_BROKER_MUTATIONS=true` when you intentionally want real broker actions enabled.

Example instrument payload:

```json
[{"exchange":"NSE","segment":"CASH","exchange_token":"2885","symbol":"RELIANCE"}]
```

## Hugging Face

Optional sentiment endpoint:

- Set `HUGGINGFACE_API_TOKEN` or `HF_TOKEN` on the orchestrator.
- Call `POST /api/v1/ml/sentiment` with `{"text":"..."}`.
- Optionally enable pipeline use with `HF_ENABLE_IN_PIPELINE=true`.

If any Hugging Face token was pasted into chat or any public place, revoke it and replace it.

## Security and compliance

- Never commit `.env` files, broker tokens, or Hugging Face tokens.
- Rotate any token that has already been exposed in chat or screenshots.
- Use paper trading and strict limits before live deployment.
- Follow SEBI, exchange, broker, tax, and legal requirements in your jurisdiction.

## Validation run

Checked locally on March 28, 2026:

- `frontend`: `npm run build`
- `frontend`: `npm run lint`
- `gateway`: `npm run build`
- `orchestrator`: `pytest`

All of the above passed in this workspace.

## License

Add a `LICENSE` file before publishing the repo broadly.
