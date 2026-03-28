from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agents.pipeline import run_pipeline_tick
from app.brokers.groww import (
    cancel_order_by_id,
    get_holdings,
    get_order_status,
    get_user_profile,
    list_orders,
    modify_order_by_id,
    order_margin_preview,
    parse_instruments_json,
    place_order,
)
from app.config import Settings, cors_origin_list, get_settings
from app.core.production import validate_production_settings
from app.ml.hf_infer import infer_text_sentiment
from app.observability.audit import audit_event, setup_audit_logging
from app.risk.execution import (
    broker_mutations_allowed,
    record_order_placed,
    validate_order_request,
)
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
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        setup_audit_logging()
        s = get_settings()
        validate_production_settings(s)
        audit_event(
            "orchestrator_start",
            broker_mode=s.broker_mode,
            environment=s.environment,
        )
        yield

    _settings = get_settings()
    app = FastAPI(title="RentAI Orchestrator", version="0.3.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origin_list(_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/ready")
    def ready(settings: Settings = Depends(get_settings)):
        if not settings.redis_url:
            return {
                "ready": True,
                "service": "orchestrator",
                "dependencies": {"redis": "not_configured"},
            }
        try:
            import redis as redis_lib

            r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=2)
            r.ping()
            return {
                "ready": True,
                "service": "orchestrator",
                "dependencies": {"redis": "ok"},
            }
        except Exception as e:
            return JSONResponse(
                status_code=503,
                content={
                    "ready": False,
                    "service": "orchestrator",
                    "dependencies": {"redis": f"unavailable: {e!s}"},
                },
            )

    @app.get("/health")
    def health(settings: Settings = Depends(get_settings)) -> dict:
        return {
            "status": "ok",
            "service": "orchestrator",
            "market": settings.market,
            "universe": settings.universe,
            "broker_mode": settings.broker_mode,
            "hf_pipeline": bool(
                settings.huggingface_api_token and settings.hf_enable_in_pipeline
            ),
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
                    "last_price": r.last_price,
                    "hf_label": r.hf_label,
                    "hf_score": r.hf_score,
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
        audit_event("kill_switch", trading_enabled=enabled)
        return {"trading_enabled": enabled}

    @app.post("/v1/pipeline/tick")
    def pipeline_tick(_: None = Depends(verify_secret)) -> dict:
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
                    "last_price": r.last_price,
                    "hf_label": r.hf_label,
                    "hf_score": r.hf_score,
                }
                for r in rows
            ],
        }

    @app.get("/v1/broker/status")
    def broker_status(
        _: None = Depends(verify_secret),
        settings: Settings = Depends(get_settings),
    ) -> dict:
        token = settings.groww_auth_token
        if not token:
            return {
                "groww_configured": False,
                "profile": None,
                "instruments": 0,
                "groww_allow_place_order": settings.groww_allow_place_order,
                "groww_allow_broker_mutations": settings.groww_allow_broker_mutations,
                "broker_mode": settings.broker_mode,
                "risk": {
                    "max_order_qty": settings.risk_max_order_quantity,
                    "max_orders_per_day": settings.risk_max_orders_per_day,
                    "require_limit_price": settings.risk_require_limit_price,
                },
            }
        try:
            profile = get_user_profile(token)
            try:
                inst = parse_instruments_json(settings.groww_instruments_json)
            except ValueError:
                inst = []
            return {
                "groww_configured": True,
                "profile": profile,
                "instruments": len(inst),
                "groww_allow_place_order": settings.groww_allow_place_order,
                "groww_allow_broker_mutations": settings.groww_allow_broker_mutations,
                "broker_mutations_enabled": broker_mutations_allowed(settings),
                "broker_mode": settings.broker_mode,
                "risk": {
                    "max_order_qty": settings.risk_max_order_quantity,
                    "max_orders_per_day": settings.risk_max_orders_per_day,
                    "require_limit_price": settings.risk_require_limit_price,
                },
            }
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Groww profile error: {e!s}",
            ) from e

    @app.get("/v1/broker/orders")
    def broker_orders(
        _: None = Depends(verify_secret),
        settings: Settings = Depends(get_settings),
        page: int = Query(0, ge=0),
        page_size: int = Query(25, ge=1, le=100),
        segment: str = Query("CASH"),
    ) -> dict:
        if not settings.groww_auth_token:
            raise HTTPException(status_code=400, detail="GROWW_AUTH_TOKEN not set")
        try:
            return list_orders(
                settings.groww_auth_token,
                page=page,
                page_size=page_size,
                segment=segment,
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e)) from e

    @app.get("/v1/broker/holdings")
    def broker_holdings(
        _: None = Depends(verify_secret),
        settings: Settings = Depends(get_settings),
    ) -> dict:
        if not settings.groww_auth_token:
            raise HTTPException(status_code=400, detail="GROWW_AUTH_TOKEN not set")
        try:
            return get_holdings(settings.groww_auth_token)
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e)) from e

    @app.get("/v1/broker/orders/status")
    def broker_order_status(
        _: None = Depends(verify_secret),
        settings: Settings = Depends(get_settings),
        groww_order_id: str = Query(..., min_length=3),
        segment: str = Query("CASH"),
    ) -> dict:
        if not settings.groww_auth_token:
            raise HTTPException(status_code=400, detail="GROWW_AUTH_TOKEN not set")
        try:
            return get_order_status(
                settings.groww_auth_token,
                groww_order_id=groww_order_id,
                segment=segment,
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e)) from e

    @app.post("/v1/broker/margins/preview")
    def broker_margin_preview(
        body: dict,
        _: None = Depends(verify_secret),
        settings: Settings = Depends(get_settings),
    ) -> dict:
        if not settings.groww_auth_token:
            raise HTTPException(status_code=400, detail="GROWW_AUTH_TOKEN not set")
        seg = body.get("segment", "CASH")
        orders = body.get("orders")
        if not isinstance(orders, list) or not orders:
            raise HTTPException(status_code=400, detail="body.orders must be a non-empty list")
        try:
            return order_margin_preview(
                settings.groww_auth_token,
                segment=str(seg),
                orders=orders,
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e)) from e

    @app.post("/v1/broker/orders/place")
    def broker_place_order(
        body: dict,
        _: None = Depends(verify_secret),
        settings: Settings = Depends(get_settings),
    ) -> dict:
        if not broker_mutations_allowed(settings):
            raise HTTPException(
                status_code=403,
                detail="Set GROWW_ALLOW_BROKER_MUTATIONS=true (or legacy GROWW_ALLOW_PLACE_ORDER).",
            )
        if settings.broker_mode != "live":
            raise HTTPException(
                status_code=403,
                detail="broker_mode must be 'live' to place orders.",
            )
        if not get_state_store().is_trading_enabled():
            raise HTTPException(status_code=403, detail="trading_disabled")
        if not settings.groww_auth_token:
            raise HTTPException(status_code=400, detail="GROWW_AUTH_TOKEN not set")

        sym = body.get("trading_symbol")
        qty = body.get("quantity")
        if not sym or qty is None:
            raise HTTPException(
                status_code=400,
                detail="trading_symbol and quantity are required",
            )
        try:
            validate_order_request(settings, body)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        try:
            result = place_order(
                settings.groww_auth_token,
                trading_symbol=str(sym),
                quantity=int(qty),
                order_type=str(body.get("order_type", "LIMIT")),
                transaction_type=str(body.get("transaction_type", "BUY")),
                product=str(body.get("product", "CNC")),
                price=body.get("price"),
                trigger_price=body.get("trigger_price"),
                order_reference_id=body.get("order_reference_id"),
            )
            record_order_placed()
            audit_event(
                "order_placed",
                trading_symbol=sym,
                quantity=qty,
                order_type=body.get("order_type"),
                groww_order_id=result.get("groww_order_id"),
            )
            return result
        except ValueError as e:
            audit_event("order_place_failed", trading_symbol=sym, error=str(e))
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            audit_event("order_place_failed", trading_symbol=sym, error=str(e))
            raise HTTPException(status_code=502, detail=str(e)) from e

    @app.post("/v1/broker/orders/cancel")
    def broker_cancel_order(
        body: dict,
        _: None = Depends(verify_secret),
        settings: Settings = Depends(get_settings),
    ) -> dict:
        if not broker_mutations_allowed(settings):
            raise HTTPException(status_code=403, detail="Broker mutations disabled")
        if not settings.groww_auth_token:
            raise HTTPException(status_code=400, detail="GROWW_AUTH_TOKEN not set")
        oid = body.get("groww_order_id")
        seg = body.get("segment", "CASH")
        if not oid:
            raise HTTPException(status_code=400, detail="groww_order_id required")
        try:
            out = cancel_order_by_id(
                settings.groww_auth_token,
                groww_order_id=str(oid),
                segment=str(seg),
            )
            audit_event("order_cancelled", groww_order_id=oid, segment=seg)
            return out
        except Exception as e:
            audit_event("order_cancel_failed", groww_order_id=oid, error=str(e))
            raise HTTPException(status_code=502, detail=str(e)) from e

    @app.post("/v1/broker/orders/modify")
    def broker_modify_order(
        body: dict,
        _: None = Depends(verify_secret),
        settings: Settings = Depends(get_settings),
    ) -> dict:
        if not broker_mutations_allowed(settings):
            raise HTTPException(status_code=403, detail="Broker mutations disabled")
        if not settings.groww_auth_token:
            raise HTTPException(status_code=400, detail="GROWW_AUTH_TOKEN not set")
        oid = body.get("groww_order_id")
        seg = body.get("segment", "CASH")
        qty = body.get("quantity")
        ot = body.get("order_type", "LIMIT")
        if not oid or qty is None:
            raise HTTPException(
                status_code=400,
                detail="groww_order_id and quantity required",
            )
        try:
            out = modify_order_by_id(
                settings.groww_auth_token,
                groww_order_id=str(oid),
                segment=str(seg),
                quantity=int(qty),
                order_type=str(ot),
                price=body.get("price"),
                trigger_price=body.get("trigger_price"),
            )
            audit_event("order_modified", groww_order_id=oid, segment=seg, quantity=qty)
            return out
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            audit_event("order_modify_failed", groww_order_id=oid, error=str(e))
            raise HTTPException(status_code=502, detail=str(e)) from e

    @app.post("/v1/ml/sentiment")
    def ml_sentiment(
        body: dict,
        _: None = Depends(verify_secret),
        settings: Settings = Depends(get_settings),
    ) -> dict:
        text = body.get("text") or ""
        if not settings.huggingface_api_token:
            raise HTTPException(
                status_code=400,
                detail="Set HUGGINGFACE_API_TOKEN or HF_TOKEN (never commit it).",
            )
        label, score = infer_text_sentiment(
            settings.huggingface_api_token,
            settings.hf_inference_model,
            str(text),
        )
        return {"label": label, "score": score, "model": settings.hf_inference_model}

    return app


app = create_app()
