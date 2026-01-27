from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path
from backend.routes import auth, admin, jobcards, users, health

app = FastAPI(title="JobCard Pro API")

UPLOAD_DIR = Path("uploads").resolve()
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

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

# ✅ INCLUDE ROUTERS
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(jobcards.router)
app.include_router(users.router)
app.include_router(health.router)
