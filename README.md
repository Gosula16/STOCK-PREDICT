# RentAI — AI-assisted trading platform (Phase 2 scaffold)

Monorepo for a **personal AI-driven trading system** aligned with a real-world architecture:

- **Frontend** (`frontend/`) — Next.js dashboard (signals, kill switch, status).
- **API gateway** (`gateway/`) — NestJS: auth header forwarding, routing to the orchestrator.
- **AI orchestrator** (`orchestrator/`) — FastAPI: agent pipeline stub, kill switch state (Redis optional).
- **Legacy demo** (`app/`) — Streamlit wind forecast app (unchanged; optional).

This repository is a **production-oriented scaffold**: it wires the control plane and APIs. You still need regulated data feeds, broker integration (e.g. Zerodha Kite), trained models, backtests, and compliance review before **live** capital.

## Quick start (local)

### 1) Backend with Docker

From the repo root:

```powershell
copy .env.example .env
docker compose up --build
```

Defaults: Redis `6379`, orchestrator `http://localhost:8000`, gateway `http://localhost:3001`, shared `API_SECRET=dev-change-me`.

### 2) Frontend

```powershell
cd frontend
copy ..\.env.example .env.local
```

Edit `frontend/.env.local`:

- `GATEWAY_URL=http://localhost:3001`
- `API_SECRET` — same value as gateway/orchestrator (`dev-change-me` unless you changed it)

```powershell
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The UI calls **Next.js server routes** under `/api/gateway/*`, which proxy to the Nest gateway with the bearer token (the secret is **not** exposed to the browser).

### 3) Without Docker (Python + Node)

**Orchestrator**

```powershell
cd orchestrator
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:API_SECRET="dev-change-me"
uvicorn app.main:app --reload --port 8000
```

**Gateway**

```powershell
cd gateway
npm install
$env:API_SECRET="dev-change-me"
$env:ORCHESTRATOR_URL="http://127.0.0.1:8000"
$env:PORT="3001"
npm run start:dev
```

Then run the frontend as above.

## API surface (via gateway)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Gateway health (no auth) |
| GET | `/api/v1/signals` | Demo signals (requires `Authorization: Bearer …` if `API_SECRET` set) |
| GET | `/api/v1/control/status` | Kill switch state |
| POST | `/api/v1/control/trading` | Body: `{"enabled": true\|false}` |
| POST | `/api/v1/pipeline/tick` | Run one pipeline tick |

Direct orchestrator URLs mirror `/v1/*` on port `8000`.

## Deploying the site (Vercel)

1. Push this repo to GitHub (or GitLab/Bitbucket).
2. In [Vercel](https://vercel.com), **New Project** → import the repo.
3. Set **Root Directory** to `frontend`.
4. Add environment variables:
   - `GATEWAY_URL` — public URL of your deployed gateway (e.g. `https://api.yourdomain.com`).
   - `API_SECRET` — same secret as production gateway/orchestrator.

Deploy the gateway and orchestrator to any container host (Railway, Fly.io, Render, AWS, etc.) and point `GATEWAY_URL` at it. Do **not** commit real secrets; use the host’s secret manager.

## Security and compliance

- Markets are risky; automation can amplify losses. Use **paper trading** until you trust the full stack.
- Indian markets: follow SEBI/broker rules, contract notes, and tax obligations.
- This scaffold does **not** constitute financial advice.

## Wind demo (legacy)

The Streamlit app in `app/` and notebook in `notebooks/` remain available; see previous commits or run `streamlit run app/app.py` from `app/` after `pip install -r app/requirements.txt`.
