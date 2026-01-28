from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from backend.routes import auth, admin, jobcards, users

app = FastAPI(
    title="JobCard Pro API",
    version="0.1.0"
)

# -------------------------------------------------
# 1️⃣ SESSIONS FIRST (required for request.session)
# -------------------------------------------------
app.add_middleware(
    SessionMiddleware,
    secret_key="CHANGE_THIS_TO_A_LONG_RANDOM_SECRET",
    same_site="lax",      # important
    https_only=True       # REQUIRED for production
)

# -------------------------------------------------
# 2️⃣ CORS SECOND
# -------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nordx.co.za",
    ],
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
# 4️⃣ HEALTH CHECK (Railway likes this)
# -------------------------------------------------
@app.get("/")
def root():
    return {"status": "ok"}
