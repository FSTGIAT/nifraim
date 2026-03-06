import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth, uploads, records, commission_rates, comparison, production, recruits, paying_companies, company_contacts, subscription, admin

app = FastAPI(title="Nifraim - Insurance Reconciliation Dashboard", version="1.0.0")

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
