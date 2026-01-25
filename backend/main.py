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
app.include_router(admin.router)


app.add_middleware(
    SessionMiddleware,
    secret_key="CHANGE_THIS_TO_A_LONG_RANDOM_STRING"
)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
# CORS (keep wide open for now)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router)

app.include_router(users.router)
# Create tables
#Base.metadata.create_all(bind=engine)

# Register routes
app.include_router(jobcards.router)
app.include_router(admin.router)
app.include_router(auth.router)

