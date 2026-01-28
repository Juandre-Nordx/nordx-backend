from fastapi import APIRouter, Request, HTTPException
from backend.database import SessionLocal
from backend.models import User
from passlib.context import CryptContext
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import JSONResponse
from backend.database import SessionLocal
from backend.models import User
from backend.services.email_service import send_reset_email


router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)


def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_admin(request: Request):
    user = get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user


@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = db.query(User).filter(User.email == email, User.is_active == True).first()
    db.close()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    request.session["user"] = {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "company_id": user.company_id
    }

    print("LOGIN DEBUG → returning role:", user.role)

    return {
        "ok": True,
        "role": user.role
    }



@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return JSONResponse({"message": "Logged out"})


@router.post("/forgot-password")
def forgot_password(email: str = Form(...)):
    db = SessionLocal()
    user = db.query(User).filter(User.email == email, User.is_active == True).first()

    if not user:
        db.close()
        return {"ok": True}  # silent success

    token = str(uuid4())
    user.reset_token = token
    user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)

    db.commit()
    db.close()

    send_reset_email(email, token)
    return {"ok": True}

@router.post("/reset-password")
def reset_password(
    token: str = Form(...),
    password: str = Form(...)
):
    db = SessionLocal()
    user = db.query(User).filter(
        User.reset_token == token,
        User.reset_token_expiry > datetime.utcnow()
    ).first()

    if not user:
        db.close()
        raise HTTPException(400, "Invalid or expired token")

    user.password_hash = pwd_context.hash(password)
    user.reset_token = None
    user.reset_token_expiry = None

    db.commit()
    db.close()

    return {"ok": True}

@router.get("/me")
def me(request: Request):
    return get_current_user(request)