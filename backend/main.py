from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from starlette.middleware.sessions import SessionMiddleware

from backend.routes import auth, admin, jobcards, users
import os
from backend.database import Base, engine

ENV = os.getenv("ENVIRONMENT", "development")
app = FastAPI(
    title="JobCard Pro API",
    version="0.1.0"
)


UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/home/runner/workspace/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

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
# 5️⃣ Mount uploads
# -------------------------------------------------
app.mount(
    "/uploads",
    StaticFiles(directory=UPLOAD_DIR),
    name="uploads"
)

# -------------------------------------------------
# 6️⃣ INIT DATABASE SCHEMA
# -------------------------------------------------
Base.metadata.create_all(bind=engine)
