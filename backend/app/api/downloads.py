from pathlib import Path

from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse

router = APIRouter()

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_APK_PATH = _DATA_DIR / "nifraim-sms.apk"


@router.get("/android")
async def download_android_apk():
    if not _APK_PATH.is_file():
        raise HTTPException(status_code=404, detail="APK not yet published — run CI first")
    return FileResponse(
        _APK_PATH,
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
