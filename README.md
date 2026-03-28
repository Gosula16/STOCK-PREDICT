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

All `/api/v1/*` routes below expect `Authorization: Bearer <API_SECRET>` when `API_SECRET` is set (except gateway `/api/health`).

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Gateway health (no auth) |
| GET | `/api/v1/signals` | Signals (+ optional Groww LTP, optional HF sentiment) |
| GET | `/api/v1/control/status` | Kill switch state |
| POST | `/api/v1/control/trading` | Body: `{"enabled": true\|false}` |
| POST | `/api/v1/pipeline/tick` | Run one pipeline tick |
| GET | `/api/v1/broker/status` | Groww profile + risk flags |
| GET | `/api/v1/broker/orders` | Query: `page`, `page_size`, `segment` |
| GET | `/api/v1/broker/holdings` | Holdings |
| GET | `/api/v1/broker/orders/status` | Query: `groww_order_id`, `segment` |
| POST | `/api/v1/broker/margins/preview` | Body: `segment`, `orders` (Groww margin API) |
| POST | `/api/v1/broker/orders/place` | Place order (mutations + live + risk + kill switch) |
| POST | `/api/v1/broker/orders/cancel` | Body: `groww_order_id`, `segment` |
| POST | `/api/v1/broker/orders/modify` | Body: `groww_order_id`, `segment`, `quantity`, `order_type`, … |
| POST | `/api/v1/ml/sentiment` | Body: `text` — HF Inference (token from env) |

**Audit:** orchestrator appends JSON lines to `logs/audit.jsonl` (and stdout) for kill switch, orders, and failures. The `logs/` directory is gitignored.

Direct orchestrator URLs mirror `/v1/*` on port `8000`.

## Groww (live LTP + optional orders)

1. Create API credentials in the [Groww Trade API](https://www.groww.in/trade-api) flow and copy the **auth token** (JWT).
2. On the orchestrator host (or `orchestrator/.env`), set:
   - `GROWW_AUTH_TOKEN` — Groww JWT (**not** the same as `API_SECRET`).
   - `GROWW_INSTRUMENTS_JSON` — JSON array of instruments. Each row needs `exchange`, `segment`, `exchange_token` (from the official [instrument CSV](https://growwapi-assets.groww.in/instruments/instrument.csv)), and optional `symbol` for display.

   Example:

   ```json
   [{"exchange":"NSE","segment":"CASH","exchange_token":"2885","symbol":"RELIANCE"}]
   ```

3. Restart the orchestrator. The dashboard **LTP** column and signals rationale will use real last traded prices from Groww when the token and tokens are valid.

**Placing real orders** (off by default):

- `BROKER_MODE=live`
- `GROWW_ALLOW_BROKER_MUTATIONS=true` (or legacy `GROWW_ALLOW_PLACE_ORDER=true`)
- Kill switch **on** (trading enabled) for **new** orders; cancel/modify are allowed when mutations are enabled so you can flatten risk.
- Optional risk env vars: `RISK_MAX_ORDER_QUANTITY`, `RISK_MAX_ORDERS_PER_DAY`, `RISK_MAX_NOTIONAL_PER_ORDER`, `RISK_REQUIRE_LIMIT_PRICE`.
- `POST /api/v1/broker/orders/place` with JSON body, e.g. `trading_symbol`, `quantity`, `order_type` (`LIMIT`/`MARKET`), `transaction_type` (`BUY`/`SELL`), `product` (`CNC`/`MIS`), and `price` for limit orders.

Never commit `GROWW_AUTH_TOKEN` or API keys to git.

## Hugging Face (optional)

- Set **`HUGGINGFACE_API_TOKEN`**, **`HF_TOKEN`**, or **`HUGGINGFACE_HUB_TOKEN`** on the orchestrator only (never in Git, chat, or the frontend).
- **`HF_ENABLE_IN_PIPELINE=true`** — runs FinBERT-style sentiment (default model `ProsusAI/finbert`) on a short synthetic line per symbol (rate-limited by `HF_MAX_SYMBOLS_PER_TICK`). This nudges confidence slightly; it is **not** a substitute for a proper trading model.
- **`POST /api/v1/ml/sentiment`** with `{"text":"..."}` for manual checks.

If a token is ever exposed, **revoke it** at [Hugging Face token settings](https://huggingface.co/settings/tokens) and create a new one.

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
