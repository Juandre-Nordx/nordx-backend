from fastapi import APIRouter, Request, HTTPException, Response, Depends
from fastapi import Form
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from uuid import uuid4
from datetime import datetime, timedelta

from backend.database import SessionLocal
from backend.models import User, LoginAudit
from backend.services.email_service import send_reset_email
from backend.logger import get_logger

logger = get_logger("auth")

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Guards / helpers
# ---------------------------------------------------------------------------

def require_super(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(401)
    if user["role"] != "super":
        raise HTTPException(403)
    return user


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
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user


# ---------------------------------------------------------------------------
# Internal audit helper
# ---------------------------------------------------------------------------

def _write_login_audit(
    db,
    *,
    email: str,
    user_id,
    role,
    company_id,
    ip_address: str,
    status: str,
    reason,
) -> None:
    """Persist a LoginAudit row.  Never raises — audit must not break auth."""
    try:
        row = LoginAudit(
            timestamp=datetime.utcnow(),
            email=email,
            user_id=user_id,
            role=role,
            company_id=company_id,
            ip_address=ip_address,
            status=status,
            reason=reason,
        )
        db.add(row)
        db.commit()
    except Exception as exc:
        logger.error(
            "AUDIT | LOGIN | DB_WRITE_FAILED | email=%s | error=%s",
            email,
            exc,
        )
        try:
            db.rollback()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    db = SessionLocal()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    client_ip = request.client.host if request.client else "unknown"

    user = (
        db.query(User)
        .filter(User.email == email, User.is_active == True)
        .first()
    )

    # ------------------------------------------------------------------ FAIL
    if not user or not verify_password(password, user.password_hash):
        reason = "user not found" if not user else "wrong password"

        logger.warning(
            "AUDIT | LOGIN | %s | %s | %s | %s | %s | %s | FAILURE | %s",
            now,
            email,
            "N/A",   # user_id
            "N/A",   # role
            "N/A",   # company_id
            client_ip,
            reason,
        )

        _write_login_audit(
            db,
            email=email,
            user_id=None,
            role=None,
            company_id=None,
            ip_address=client_ip,
            status="failure",
            reason=reason,
        )

        db.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # ----------------------------------------------------------------- SUCCESS
    request.session["user"] = {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "company_id": user.company_id,
    }

    logger.info(
        "AUDIT | LOGIN | %s | %s | %s | %s | %s | %s | SUCCESS | none",
        now,
        user.email,
        user.id,
        user.role,
        user.company_id,
        client_ip,
    )

    _write_login_audit(
        db,
        email=user.email,
        user_id=user.id,
        role=user.role,
        company_id=user.company_id,
        ip_address=client_ip,
        status="success",
        reason=None,
    )

    db.close()
    return {
        "ok": True,
        "role": user.role,
    }


@router.post("/logout")
def logout(request: Request, response: Response):
    request.session.clear()
    response.delete_cookie("session")
    return {"status": "logged_out"}


@router.post("/forgot-password")
def forgot_password(email: str = Form(...)):
    db = SessionLocal()

    user = (
        db.query(User)
        .filter(User.email == email, User.is_active == True)
        .first()
    )

    if not user:
        db.close()
        return {"ok": True}  # silent success

    token = str(uuid4())
    user.reset_token = token
    user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)

    db.commit()
    db.close()

    try:
        send_reset_email(email, token)
    except Exception as e:
        print("❌ Password reset email failed:", e)

    return {"ok": True}


@router.post("/reset-password")
def reset_password(
    token: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    if password != confirm_password:
        raise HTTPException(400, "Passwords do not match")

    db = SessionLocal()
    user = db.query(User).filter(
        User.reset_token == token,
        User.reset_token_expiry > datetime.utcnow(),
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
def me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "role": current_user["role"],
        "company_id": current_user["company_id"],
    }
