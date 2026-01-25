from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.database import SessionLocal
from backend.models import User, Company
from backend.schemas import UserCreate, UserOut
from backend.auth import hash_password

router = APIRouter(prefix="/admin/users", tags=["Users"])


# -----------------------------
# DB dependency
# -----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -----------------------------
# GET: list users
# -----------------------------
@router.get("/", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@router.get("/companies")
def list_companies(db: Session = Depends(get_db)):
    return db.query(Company).all()

# -----------------------------
# POST: create user
# -----------------------------

@router.post("/", response_model=UserOut)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    if user.company_id:
        company = db.query(Company).filter(Company.id == user.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
          
    
    new_user = User(
        name=user.name,
        email=user.email,
        password_hash = hash_password(user.password),
        role=user.role,
        company_id=user.company_id,
    )
    if not user.password or len(user.password) < 6:
        raise HTTPException(status_code=400, detail="Password too short")

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

