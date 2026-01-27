from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from pathlib import Path
from backend.routes import auth, admin, jobcards, users, health
import os



load_dotenv()

# ✅ POINT TO REAL UPLOAD LOCATION
UPLOAD_DIR = Path("uploads").resolve()

app = FastAPI(title="JobCard Pro API")

# ✅ ENSURE DIRECTORIES EXIST
for sub in ["signatures", "jobcards", "before", "after", "materials", "company"]:
    (UPLOAD_DIR / sub).mkdir(parents=True, exist_ok=True)

# ✅ STATIC FILES (THIS WAS THE BUG)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ✅ SESSION
app.add_middleware(
    SessionMiddleware,
    secret_key="nordx_super_secure_session_key_2026_prod",
    same_site="none",
    https_only=True
)

# ✅ CORS
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
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(jobcards_router)
app.include_router(health_router)


# 🔎 DEBUG (KEEP THIS)
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
