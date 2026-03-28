from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agents.pipeline import run_pipeline_tick
from app.config import Settings, get_settings
from app.state_store import get_state_store


def verify_secret(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.api_secret:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if token != settings.api_secret:
        raise HTTPException(status_code=401, detail="Invalid token")


def create_app() -> FastAPI:
    app = FastAPI(title="RentAI Orchestrator", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health(settings: Settings = Depends(get_settings)) -> dict:
        return {
            "status": "ok",
            "service": "orchestrator",
            "market": settings.market,
            "universe": settings.universe,
            "broker_mode": settings.broker_mode,
        }

    @app.get("/v1/signals")
    def signals(_: None = Depends(verify_secret)) -> dict:
        store = get_state_store()
        rows = run_pipeline_tick()
        return {
            "trading_enabled": store.is_trading_enabled(),
            "signals": [
                {
                    "symbol": r.symbol,
                    "decision": r.decision,
                    "confidence": r.confidence,
                    "rationale": r.rationale,
                }
                for r in rows
            ],
        }

    @app.get("/v1/control/status")
    def control_status(_: None = Depends(verify_secret)) -> dict:
        return {"trading_enabled": get_state_store().is_trading_enabled()}

    @app.post("/v1/control/trading")
    def set_trading(body: dict, _: None = Depends(verify_secret)) -> dict:
        enabled = bool(body.get("enabled", True))
        get_state_store().set_trading_enabled(enabled)
        return {"trading_enabled": enabled}

    @app.post("/v1/pipeline/tick")
    def pipeline_tick(_: None = Depends(verify_secret)) -> dict:
        """Run one full cycle (for workers or manual trigger)."""
        store = get_state_store()
        if not store.is_trading_enabled():
            return {"ran": False, "reason": "trading_disabled", "signals": []}
        rows = run_pipeline_tick()
        return {
            "ran": True,
            "signals": [
                {
                    "symbol": r.symbol,
                    "decision": r.decision,
                    "confidence": r.confidence,
                    "rationale": r.rationale,
                }
                for r in rows
            ],
        }

    return app


app = create_app()
