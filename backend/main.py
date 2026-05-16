from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware

from backend.routes import auth, admin, jobcards, users
import os
from backend.database import Base, engine
from backend.storage import (
    ensure_upload_root,
    resolve_upload_path,
    upload_storage_roots,
)

ENV = os.getenv("ENVIRONMENT", "development")
app = FastAPI(
    title="JobCard Pro API",
    version="0.1.0"
)


# -------------------------------------------------
# 1️⃣ SESSIONS FIRST (required for request.session)
# -------------------------------------------------
IS_PROD = ENV in ("static", "production")
SESSION_DOMAIN = ".nordx.co.za" if IS_PROD else None

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "dev-secret"),
    same_site="none" if IS_PROD else "lax",
    https_only=IS_PROD,
    domain=SESSION_DOMAIN,
    max_age=60 * 60 * 12,  # 12 hours
)


# -------------------------------------------------
# 2️⃣ CORS SECOND
# -------------------------------------------------

ALLOWED_ORIGINS = [
    "https://nordx.co.za",
    "https://api01.nordx.co.za",
]

if not IS_PROD:
    ALLOWED_ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------
# 3️⃣ ROUTES
# -------------------------------------------------
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(jobcards.router)
app.include_router(users.router)

# -------------------------------------------------
# 4️⃣ HEALTH CHECK
# -------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "environment": ENV
    }


# -------------------------------------------------
# 5️⃣ Upload file serving
# -------------------------------------------------
@app.get("/uploads/{file_path:path}", include_in_schema=False)
@app.head("/uploads/{file_path:path}", include_in_schema=False)
def serve_upload(file_path: str):
    """Serve uploaded files from the configured upload root or legacy /data layout."""
    try:
        upload_path = resolve_upload_path(f"/uploads/{file_path}")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Upload not found") from exc

    if not upload_path.is_file():
        print(
            "Upload not found:",
            file_path,
            "resolved_to=",
            upload_path,
            "roots_checked=",
            [str(root) for root in upload_storage_roots()],
        )
        raise HTTPException(status_code=404, detail="Upload not found")

    return FileResponse(str(upload_path))


# -------------------------------------------------
# 6️⃣ Mount uploads
# -------------------------------------------------
# Ensure the uploads directory exists before mounting so that StaticFiles
# doesn't fail silently when the volume is freshly attached or the path
# hasn't been written to yet.
uploads_dir = ensure_upload_root()
print(f"Uploads directory: {uploads_dir} (exists: {uploads_dir.exists()})")

app.mount(
    "/uploads",
    StaticFiles(directory=str(uploads_dir)),
    name="uploads"
)

# -------------------------------------------------
# 7️⃣ INIT DATABASE SCHEMA
# -------------------------------------------------
Base.metadata.create_all(bind=engine)
