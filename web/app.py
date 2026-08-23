from __future__ import annotations

import base64
import os
import secrets
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware

from web.routes import status, p2p, stream, rate_trend, binance_status, analytics, spot, journal, xrp_swing, agents

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

_DASHBOARD_USER = "cryptotrada"


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """Require HTTP Basic Auth when DASHBOARD_PASSWORD env var is set."""

    def __init__(self, app, password: str) -> None:
        super().__init__(app)
        self._password = password

    async def dispatch(self, request: Request, call_next):
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth[6:]).decode()
                user, _, pw = decoded.partition(":")
                if secrets.compare_digest(user, _DASHBOARD_USER) and secrets.compare_digest(pw, self._password):
                    return await call_next(request)
            except Exception:
                pass
        return Response(
            "Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="CryptoTrada"'},
        )


def create_app(lifespan=None) -> FastAPI:
    app = FastAPI(title="Crypto Trading Dashboard", version="1.0.0", lifespan=lifespan)

    dashboard_password = os.getenv("DASHBOARD_PASSWORD", "")
    if dashboard_password:
        app.add_middleware(BasicAuthMiddleware, password=dashboard_password)

    # Allow Vite dev server (port 5173) during development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(GZipMiddleware, minimum_size=1000)

    app.include_router(status.router)
    app.include_router(p2p.router)
    app.include_router(stream.router)
    app.include_router(rate_trend.router)
    app.include_router(binance_status.router)
    app.include_router(analytics.router)
    app.include_router(spot.router)
    app.include_router(journal.router)
    app.include_router(xrp_swing.router)
    app.include_router(agents.router)

    # Serve built Vue SPA in production (after `npm run build`)
    if FRONTEND_DIST.exists():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="spa")

    return app


app = create_app()
