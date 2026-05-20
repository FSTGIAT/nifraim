import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth, uploads, records, commission_rates, comparison, production, recruits, paying_companies, company_contacts, subscription, admin, portal, ai, volume, volume_rates, debts, portal_automation, ai_documents, funds, insights, yield_recommendations
from app.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Any portal_runs left in an "active" state at startup belong to a previous
    # process — the runner that owned them is gone, so they will never advance.
    # Mark them failed so the credential isn't permanently blocked by a stuck
    # run. Common trigger: uvicorn --reload mid-run, or a Railway redeploy.
    await _fail_orphaned_runs()
    start_scheduler()
    yield
    stop_scheduler()


async def _fail_orphaned_runs() -> None:
    from datetime import datetime
    from sqlalchemy import update
    from app.database import async_session
    from app.models.portal_run import PortalRun

    ACTIVE = ("pending", "running", "awaiting_otp", "downloading", "parsing")
    try:
        async with async_session() as db:
            await db.execute(
                update(PortalRun)
                .where(PortalRun.status.in_(ACTIVE))
                .values(
                    status="failed",
                    error_message="Run interrupted by server restart",
                    finished_at=datetime.utcnow(),
                )
            )
            await db.commit()
    except Exception:
        # Don't block startup if the cleanup query fails — runs being stuck is
        # less bad than the server failing to boot.
        pass


app = FastAPI(title="Nifraim - Insurance Reconciliation Dashboard", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["uploads"])
app.include_router(records.router, prefix="/api/records", tags=["records"])
app.include_router(commission_rates.router, prefix="/api/commission-rates", tags=["commission-rates"])
app.include_router(comparison.router, prefix="/api/comparison", tags=["comparison"])
app.include_router(production.router, prefix="/api/production", tags=["production"])
app.include_router(recruits.router, prefix="/api/recruits", tags=["recruits"])
app.include_router(paying_companies.router, prefix="/api/paying-companies", tags=["paying-companies"])
app.include_router(company_contacts.router, prefix="/api/company-contacts", tags=["company-contacts"])
app.include_router(subscription.router, prefix="/api/subscription", tags=["subscription"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(portal.router, prefix="/api/portal", tags=["portal"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(ai_documents.router, prefix="/api/ai/documents", tags=["ai-documents"])
app.include_router(volume.router, prefix="/api/volume", tags=["volume"])
app.include_router(volume_rates.router, prefix="/api/volume-rates", tags=["volume-rates"])
app.include_router(debts.router, prefix="/api/debts", tags=["debts"])
app.include_router(portal_automation.router, prefix="/api/portal-automation", tags=["portal-automation"])
app.include_router(funds.router, prefix="/api/funds", tags=["funds"])
app.include_router(insights.router, prefix="/api/insights", tags=["insights"])
app.include_router(yield_recommendations.router, prefix="/api/yield-recommendations", tags=["yield-recommendations"])


@app.get("/api/health")
async def health():
    # Surface the async pool state so we can spot connection leaks early on
    # Railway (see "garbage collector is trying to clean up non-checked-in
    # connection" warnings) without needing to attach a debugger.
    from app.database import engine
    pool = engine.pool
    pool_info = {}
    for attr in ("size", "checkedin", "checkedout", "overflow"):
        method = getattr(pool, attr, None)
        if callable(method):
            try:
                pool_info[attr] = method()
            except Exception:
                pool_info[attr] = None
    return {"status": "ok", "pool": pool_info}


# Serve Vue frontend static files in production
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # Never let the SPA swallow API paths — an unknown /api/* must 404 so
        # axios callers see a real error instead of getting index.html back as
        # "JSON" (which silently degrades to empty fields).
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            resp = FileResponse(file_path)
            # Hashed assets can be cached aggressively
            if full_path.startswith("assets/"):
                resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            return resp
        # index.html must never be cached — ensures fresh deploys are picked up
        resp = FileResponse(FRONTEND_DIR / "index.html")
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
