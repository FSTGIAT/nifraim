from pathlib import Path

from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse

router = APIRouter()

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_APK_PATH = _DATA_DIR / "nifraim-sms.apk"
# Baked-into-the-image copy. `data/` is .railwayignore'd (per-replica ephemeral)
# so the CI-upload path above does NOT survive deploys and only ever lands on one
# replica. The shipped asset under app/ deploys to every replica and persists, so
# it's the reliable source — prefer it, fall back to the CI-uploaded data/ copy.
_ASSET_APK_PATH = Path(__file__).resolve().parent.parent / "assets" / "nifraim-sms.apk"


@router.get("/android")
async def download_android_apk():
    apk_path = _ASSET_APK_PATH if _ASSET_APK_PATH.is_file() else _APK_PATH
    if not apk_path.is_file():
        raise HTTPException(status_code=404, detail="APK not yet published — run CI first")
    return FileResponse(
        apk_path,
        media_type="application/vnd.android.package-archive",
        filename="nifraim-sms.apk",
        headers={"Content-Disposition": 'attachment; filename="nifraim-sms.apk"'},
    )


@router.post("/android", status_code=200)
async def upload_android_apk(
    file: UploadFile = File(...),
    x_apk_secret: str | None = Header(default=None),
):
    from app.config import settings
    if not settings.ANDROID_APK_SECRET or x_apk_secret != settings.ANDROID_APK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    _APK_PATH.write_bytes(content)
    return {"status": "ok", "bytes": len(content)}
