#from fastapi import FastAPI
#from fastapi.middleware.cors import CORSMiddleware
#from fastapi.staticfiles import StaticFiles
#
#from pathlib import Path
## Database
#from backend.database import Base, engine
#from backend import models
## Routers
#from backend.routes import jobcards, admin, auth
#from backend.routes import users
#from starlette.middleware.sessions import SessionMiddleware
#from dotenv import load_dotenv
#from backend.routes import health
#from fastapi.staticfiles import StaticFiles
#
#import os
#
#load_dotenv()
#BASE_DIR = Path(__file__).resolve().parent
#app = FastAPI()
# 
#
#
#    
## 1️⃣ Sessions FIRST
#app.add_middleware(
#    SessionMiddleware,
#     secret_key=os.environ["SECRET_KEY"],
#    same_site="lax",
#    https_only=True,
#    domain=".nordx.co.za",  # 👈 THIS LINE
#)
#
## 2️⃣ CORS SECOND
#app.add_middleware(
#    CORSMiddleware,
#    allow_origins=[
#        "https://nordx.co.za",
#    ],
#    allow_credentials=True,
#    allow_methods=["*"],
#    allow_headers=["*"],
#)
#
#app.include_router(admin.router)
#app.mount(
#    "/uploads",
#    StaticFiles(directory="/data/uploads"),
#    name="uploads"
#)
#
#
#@app.get("/_debug/fs")
#def debug_fs():
#    def safe_ls(path):
#        return os.listdir(path) if os.path.exists(path) else "MISSING"
#
#    return {
#        "cwd": os.getcwd(),
#        "root": safe_ls("."),
#        "uploads": safe_ls("/data/uploads"),
#        "signatures": safe_ls("/data/uploads/signatures"),
#        "jobcards": safe_ls("/data/uploads/jobcards"),
#
#    }
#
#
#
#app.include_router(health.router)
#
#app.include_router(users.router)
## Create tables
##Base.metadata.create_all(bind=engine)
#
## Register routes
#app.include_router(jobcards.router)
#app.include_router(auth.router)
#
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

# -----------------------------------
# Create app
# -----------------------------------
app = FastAPI(
    title="JobCard Pro API",
    version="0.1.0"
)

# -----------------------------------
# CORS (MUST BE FIRST)
# -----------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nordx.co.za",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------
# Sessions (MUST BE SECOND)
# -----------------------------------
app.add_middleware(
    SessionMiddleware,
    secret_key="CHANGE_THIS_TO_A_LONG_RANDOM_SECRET",
    same_site="none",          # REQUIRED for cross-subdomain cookies
    https_only=True,           # REQUIRED for HTTPS
    domain=".nordx.co.za",     # 🔥 allows api01.nordx.co.za + nordx.co.za
)

# -----------------------------------
# Routers (AFTER middleware)
# -----------------------------------
from backend.routes import auth, admin, users

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(users.router)

# -----------------------------------
# Health check (optional but useful)
# -----------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}
