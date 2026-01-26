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


load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="JobCard Pro API")
# 1️⃣ Sessions FIRST (required for request.session)
app.add_middleware(
    SessionMiddleware,
    secret_key="CHANGE_THIS_TO_A_LONG_RANDOM_SECRET_32+_CHARS",
    same_site="none",     # REQUIRED for cross-domain cookies
    https_only=True       # REQUIRED because Railway is HTTPS
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



app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


app.include_router(health.router)

app.include_router(users.router)
# Create tables
#Base.metadata.create_all(bind=engine)

# Register routes
app.include_router(jobcards.router)
app.include_router(admin.router)
app.include_router(auth.router)

