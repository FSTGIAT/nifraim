import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth, uploads, records, commission_rates, comparison, production, recruits, paying_companies, company_contacts, subscription, admin

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app):
    # Log startup info for debugging Railway deployments
    logger.info("=== InsureFlow starting ===")
    logger.info(f"DATABASE_URL set: {bool(os.environ.get('DATABASE_URL'))}")
    try:
        from app.database import engine
        async with engine.connect() as conn:
            await conn.execute(__import__('sqlalchemy').text("SELECT 1"))
        logger.info("Database connection: OK")
    except Exception as e:
        logger.error(f"Database connection FAILED: {e}")
    yield


app = FastAPI(title="Nifraim - Insurance Reconciliation Dashboard", version="1.0.0", lifespan=lifespan)

# CORS: allow localhost for dev, plus any CORS_ORIGINS env var for production
cors_origins = ["http://localhost:5173", "http://localhost:3000"]
extra_origins = os.environ.get("CORS_ORIGINS", "")
if extra_origins:
    cors_origins.extend([o.strip() for o in extra_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# Serve frontend static files in production
STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(STATIC_DIR / "index.html"))
