from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from starlette.middleware.sessions import SessionMiddleware
from backend.routes import clients
from backend.routes import auth, admin, jobcards, users
import os
from backend.database import Base, engine
from backend.routes import tasks
ENV = os.getenv("ENVIRONMENT", "production")
app = FastAPI(
    title="JobCard Pro API " if ENV == "production" else "JobCard Pro API",
    version="0.1.0"
)


UPLOAD_DIR = Path("/data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------
# 1️⃣ SESSIONS FIRST (required for request.session)
# -------------------------------------------------
SESSION_DOMAIN = ".nordx.co.za" if ENV in ("static", "production") else None

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "dev-secret"),
    same_site="none",
    https_only=True,
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

if ENV == "beta":
    ALLOWED_ORIGINS.extend([
        "https://beta.nordx.co.za",
    ])

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
app.include_router(clients.router)
app.include_router(tasks.router)

# -------------------------------------------------
# 4️⃣ HEALTH CHECK (Railway likes this)
# -------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "environment": ENV
    }


# -------------------------------------------------
# 5 Mount img to upload
# -------------------------------------------------
app.mount(
    "/uploads",
    StaticFiles(directory=UPLOAD_DIR),
    name="uploads"
)
## -------------------------------------------------
## 6️⃣ INIT BETA DATABASE SCHEMA (ONE-TIME)
## -------------------------------------------------
#if ENV == "beta":
#    Base.metadata.create_all(bind=engine)



