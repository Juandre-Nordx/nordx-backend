from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from pathlib import Path
import os

# Routers
from backend.routes import jobcards, admin, auth, users, health

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"

# ✅ CREATE APP FIRST
app = FastAPI(title="JobCard Pro API")

# ✅ ENSURE DIRECTORIES EXIST
(UPLOAD_DIR / "signatures").mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "jobcards").mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "before").mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "after").mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "materials").mkdir(parents=True, exist_ok=True)

# ✅ MOUNT STATIC FILES AFTER app EXISTS
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ✅ SESSION MIDDLEWARE FIRST
app.add_middleware(
    SessionMiddleware,
    secret_key="nordx_super_secure_session_key_2026_prod",
    same_site="none",
    https_only=True
)

# ✅ CORS SECOND
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nordx.co.za",
        "https://www.nordx.co.za",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ ROUTERS
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(jobcards.router)

# 🔎 DEBUG (keep this, it’s gold)
@app.get("/_debug/fs")
def debug_fs():
    def safe_ls(path):
        return os.listdir(path) if os.path.exists(path) else "MISSING"

    return {
        "cwd": os.getcwd(),
        "uploads": safe_ls("uploads"),
        "signatures": safe_ls("uploads/signatures"),
        "jobcards": safe_ls("uploads/jobcards"),
        "before": safe_ls("uploads/before"),
        "after": safe_ls("uploads/after"),
        "materials": safe_ls("uploads/materials"),
    }
