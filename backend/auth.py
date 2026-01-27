from fastapi import Request, HTTPException, status
from jose import jwt, JWTError
from datetime import datetime, timedelta
from passlib.context import CryptContext
from backend.database import SessionLocal
from backend.models import User
import os
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# -------------------------
# Password helpers
# -------------------------
def hash_password(password: str) -> str:
    # bcrypt limit: 72 bytes → enforce BEFORE hashing
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password too long (max 72 bytes)")
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# -------------------------
# JWT helpers
# -------------------------
def create_access_token(data: dict, expires_minutes: int = 480):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)



# -------------------------
# Guards
# -------------------------
def require_admin(request: Request):
    user = get_current_user(request)

    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return user
def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
        

#SUPER_ADMIN_EMAIL = "you@revenuerelay.co.za"  # ← change this
#
#def require_super_admin(request: Request):
#    user_id = request.session.get("user_id")
#
#    if not user_id:
#        raise HTTPException(status_code=401, detail="Not authenticated")
#
#    db = SessionLocal()
#    user = db.query(User).filter(User.id == user_id).first()
#    db.close()
#
#    if not user or user.email != SUPER_ADMIN_EMAIL:
#        raise HTTPException(status_code=403, detail="Super admin only")
#
#    return user