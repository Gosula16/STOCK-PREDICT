# RentAI / STOCK-PREDICT — AI-assisted trading control plane

Monorepo for a **personal AI-driven trading system**: Next.js dashboard, NestJS gateway, FastAPI orchestrator, optional Groww broker + Hugging Face inference.

> **Not financial advice.** Live trading can lose money. Use paper mode and small size until you trust the stack.

---

## Live links

| What | URL |
|------|-----|
| **Production dashboard (Vercel)** | [https://frontend-rho-flame-38.vercel.app](https://frontend-rho-flame-38.vercel.app) |
| **Vercel project (deployments & env)** | [https://vercel.com/125015164-4269s-projects/frontend](https://vercel.com/125015164-4269s-projects/frontend) |
| **Source repository (GitHub)** | [https://github.com/Gosula16/STOCK-PREDICT](https://github.com/Gosula16/STOCK-PREDICT) |

**Important:** The dashboard loads on Vercel, but **signals and broker panels need a public API**. Set **`GATEWAY_URL`** and **`API_SECRET`** in the Vercel project (Settings → Environment Variables) after you deploy the gateway (see [Production deployment](#production-deployment-full-stack) below). Until then, the UI may show an API error or empty data.

---

## Contents

- [Architecture](#architecture)
- [Quick start (local)](#quick-start-local)
- [Production deployment (full stack)](#production-deployment-full-stack)
- [Environment variables](#environment-variables-reference)
- [API surface](#api-surface-via-gateway)
- [Groww broker](#groww-live-ltp--optional-orders)
- [Hugging Face (optional)](#hugging-face-optional)
- [Security & compliance](#security-and-compliance)
- [Wind demo (legacy)](#wind-demo-legacy)

---

## Architecture

```
Browser → Next.js (Vercel) → /api/gateway/* (server proxy)
         → NestJS gateway (public URL) → FastAPI orchestrator → Redis (optional) / Groww / HF
```

- **`frontend/`** — Next.js 15 dashboard (signals, LTP column, kill switch, Groww status).
- **`gateway/`** — NestJS: forwards `Authorization: Bearer` to the orchestrator.
- **`orchestrator/`** — FastAPI: pipeline, Groww integration, risk checks, audit log, optional HF.
- **`app/`** — Legacy Streamlit wind app (optional).

---

## Quick start (local)

### 1) Backend with Docker

From the repo root:

```powershell
copy .env.example .env
docker compose up --build
```

Defaults: Redis `6379`, orchestrator `http://localhost:8000`, gateway `http://localhost:3001`, `API_SECRET=dev-change-me`.

### 2) Frontend

```powershell
cd frontend
copy ..\.env.example .env.local
```

Edit `frontend/.env.local`:

- `GATEWAY_URL=http://localhost:3001`
- `API_SECRET` — same as gateway/orchestrator (`dev-change-me` unless changed)

```powershell
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### 3) Without Docker

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

---

## Production deployment (full stack)

### Prerequisites

- GitHub repo pushed (e.g. [STOCK-PREDICT](https://github.com/Gosula16/STOCK-PREDICT)).
- Strong random **`API_SECRET`** (shared across gateway, orchestrator, and Vercel server env).
- **Never** commit `.env`, Groww JWT, or Hugging Face tokens.

### Step 1 — Deploy the orchestrator (API backend)

Use any host that runs Docker or Python (examples: [Render](https://render.com), [Railway](https://railway.app), [Fly.io](https://fly.io), AWS, VPS).

**Render (Docker) example**

1. [Render Dashboard](https://dashboard.render.com) → **New +** → **Web Service**.
2. Connect **GitHub** → select `Gosula16/STOCK-PREDICT`.
3. **Root Directory:** leave empty or repo root.
4. **Runtime:** Docker. **Dockerfile path:** `orchestrator/Dockerfile`. **Docker build context:** `orchestrator` (if the UI asks for context directory).
5. **Instance type:** Free (cold starts apply).
6. **Environment variables:**
   - `API_SECRET` — long random string (save it).
   - Optional: `REDIS_URL`, `GROWW_*`, `HUGGINGFACE_*`, `BROKER_MODE`, risk vars — see [Environment variables](#environment-variables-reference).
7. Deploy and copy the public URL, e.g. `https://stock-predict-orchestrator.onrender.com`.

Health check (browser or curl): `https://<your-orchestrator-host>/health`

### Step 2 — Deploy the gateway

1. **New Web Service** on the same or another host.
2. **Dockerfile path:** `gateway/Dockerfile`. **Docker build context:** `gateway`.
3. **Environment variables:**
   - `API_SECRET` — **same** as orchestrator.
   - `ORCHESTRATOR_URL` — `https://<your-orchestrator-host>` (no trailing slash).
   - `PORT` — often injected by the platform (Render/Railway set `PORT` automatically; the app reads it).
   - Optional: `CORS_ORIGIN=https://frontend-rho-flame-38.vercel.app` (your real dashboard origin).
4. Deploy and copy the URL, e.g. `https://stock-predict-gateway.onrender.com`.

Check: `https://<your-gateway-host>/api/health` should return JSON.

### Step 3 — Connect the Vercel dashboard to the gateway

1. Open [Vercel project → Settings → Environment Variables](https://vercel.com/125015164-4269s-projects/frontend/settings/environment-variables).
2. Add for **Production** (and Preview if you want):
   - **`GATEWAY_URL`** = `https://<your-gateway-host>` (no `/api` suffix).
   - **`API_SECRET`** = same secret as gateway/orchestrator.
3. **Redeploy** the latest deployment (Deployments → ⋮ → Redeploy), or push a commit to trigger a Git-connected build.

**CLI alternative** (from `frontend/`):

```powershell
cd frontend
npx vercel env add GATEWAY_URL production
npx vercel env add API_SECRET production
npx vercel deploy --prod --yes
```

### Step 4 — GitHub ↔ Vercel (automatic deploys on push)

1. Vercel → project **Settings → Git** → connect [https://github.com/Gosula16/STOCK-PREDICT](https://github.com/Gosula16/STOCK-PREDICT).
2. Set **Root Directory** to `frontend`.
3. Each push to the linked branch triggers a new production (or preview) build.

### Current production frontend (already deployed)

- **URL:** [https://frontend-rho-flame-38.vercel.app](https://frontend-rho-flame-38.vercel.app)
- Deployed with Vercel CLI under project `frontend`; alias may change if the project is renamed — check the Vercel dashboard for the canonical production domain.

---

## Environment variables reference

| Variable | Where | Purpose |
|----------|--------|---------|
| `API_SECRET` | Gateway, orchestrator, **Vercel** | Bearer token for internal API |
| `GATEWAY_URL` | **Vercel only** | Public gateway base URL |
| `ORCHESTRATOR_URL` | Gateway | Orchestrator base URL |
| `GROWW_AUTH_TOKEN` | Orchestrator | Groww JWT |
| `GROWW_INSTRUMENTS_JSON` | Orchestrator | Instrument list for LTP |
| `GROWW_ALLOW_BROKER_MUTATIONS` | Orchestrator | Enable place/cancel/modify |
| `BROKER_MODE` | Orchestrator | `paper` / `live` |
| `HUGGINGFACE_API_TOKEN` / `HF_TOKEN` | Orchestrator | HF Inference API |
| `HF_ENABLE_IN_PIPELINE` | Orchestrator | Optional sentiment in pipeline |
| `RISK_*` | Orchestrator | See `.env.example` |

See [`.env.example`](.env.example) for the full list and comments.

---

## API surface (via gateway)

All `/api/v1/*` routes expect `Authorization: Bearer <API_SECRET>` when `API_SECRET` is set (except `GET /api/health`).

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Gateway health |
| GET | `/api/v1/signals` | Signals (+ optional LTP / HF) |
| GET | `/api/v1/control/status` | Kill switch |
| POST | `/api/v1/control/trading` | `{"enabled": bool}` |
| POST | `/api/v1/pipeline/tick` | Pipeline tick |
| GET | `/api/v1/broker/status` | Groww + risk flags |
| GET | `/api/v1/broker/orders` | Orders list (query params) |
| GET | `/api/v1/broker/holdings` | Holdings |
| GET | `/api/v1/broker/orders/status` | Order status (query) |
| POST | `/api/v1/broker/margins/preview` | Margin preview |
| POST | `/api/v1/broker/orders/place` | Place order |
| POST | `/api/v1/broker/orders/cancel` | Cancel |
| POST | `/api/v1/broker/orders/modify` | Modify |
| POST | `/api/v1/ml/sentiment` | HF sentiment on `text` |

Orchestrator also exposes the same paths under `/v1/*` on port **8000** if called directly.

**Audit:** JSON lines to `logs/audit.jsonl` + stdout (`logs/` is gitignored).

---

## Groww (live LTP + optional orders)

1. [Groww Trade API](https://www.groww.in/trade-api) — create credentials and copy the **auth JWT**.
2. Orchestrator env: `GROWW_AUTH_TOKEN`, `GROWW_INSTRUMENTS_JSON` (tokens from [instrument CSV](https://growwapi-assets.groww.in/instruments/instrument.csv)).

Example instruments:

```json
[{"exchange":"NSE","segment":"CASH","exchange_token":"2885","symbol":"RELIANCE"}]
```

**Live orders:** `BROKER_MODE=live`, `GROWW_ALLOW_BROKER_MUTATIONS=true` (or legacy `GROWW_ALLOW_PLACE_ORDER`), kill switch on for new **places**; see README risk vars.

Never commit Groww tokens.

---

## Hugging Face (optional)

- `HUGGINGFACE_API_TOKEN` or `HF_TOKEN` on the orchestrator only.
- `HF_ENABLE_IN_PIPELINE=true` for optional FinBERT-style nudge (not a full trading model).
- Revoke leaked tokens at [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).

---

## Security and compliance

- Automation can amplify losses; use **paper** / tiny size first.
- Indian markets: follow **SEBI**, exchange, and broker rules.
- This project is **not** legal or investment advice.

---

## Wind demo (legacy)

```powershell
cd app
pip install -r requirements.txt
streamlit run app.py
```

---

## License

Add a `LICENSE` file if you open-source the repo publicly.
