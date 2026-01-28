from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pathlib import Path
# Database
from backend.database import Base, engine
from backend import models
# Routers
from backend.routes import jobcards, admin, auth
from backend.routes import users
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from backend.routes import health
from fastapi.staticfiles import StaticFiles

import os

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="JobCard Pro API")
 1️⃣
Sessions FIRST (required for request.session)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ["SECRET_KEY"],
    same_site="none",
    https_only=True
)


# 2️⃣ CORS SECOND
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
app.include_router(admin.router)
app.mount(
    "/uploads",
    StaticFiles(directory="/data/uploads"),
    name="uploads"
)


@app.get("/_debug/fs")
def debug_fs():
    def safe_ls(path):
        return os.listdir(path) if os.path.exists(path) else "MISSING"

    return {
        "cwd": os.getcwd(),
        "root": safe_ls("."),
        "uploads": safe_ls("/data/uploads"),
        "signatures": safe_ls("/data/uploads/signatures"),
        "jobcards": safe_ls("/data/uploads/jobcards"),

    }



app.include_router(health.router)

app.include_router(users.router)
# Create tables
#Base.metadata.create_all(bind=engine)

# Register routes
app.include_router(jobcards.router)
app.include_router(auth.router)

