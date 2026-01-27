from fastapi import APIRouter, Request, HTTPException
from backend.database import SessionLocal
from backend.models import User
from passlib.context import CryptContext
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import JSONResponse
from backend.database import SessionLocal
from backend.models import User
from backend.services.auth_service import verify_password
from backend.auth import verify_password, create_access_token
from backend.services.email_service import send_reset_email
from fastapi import Form
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError


security = HTTPBearer()
#router = APIRouter()   # 👈 IMPORTANT
router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_admin(request: Request):
    user = get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user




@router.post("/login")
def login(email: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = db.query(User).filter(
        User.email == email,
        User.is_active == True
    ).first()
    db.close()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({
        "user_id": user.id,
        "role": user.role,
        "company_id": user.company_id
    })

    return {
        "access_token": token,
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
