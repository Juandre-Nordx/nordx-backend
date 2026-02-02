from fastapi import APIRouter, Request, HTTPException, Response, Form, Depends
from sqlalchemy.orm import Session
from typing import List

from backend.database import SessionLocal
from backend.models import User, Company
from backend.schemas import UserCreate, UserOut
from backend.routes.auth import hash_password
from backend.database import get_db
from backend.routes.auth import require_super
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
#@router.get("/", response_model=List[UserOut])
#def list_users(db: Session = Depends(get_db)):
#    users = db.query(User).all()
#    return users
@router.get("/")
def list_users(
    current_user=Depends(require_super),
    company_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(User)

    # Optional filter (from UI)
    if company_id is not None:
        query = query.filter(User.company_id == company_id)

    users = query.all()

    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "company_id": u.company_id,
            "is_active": u.is_active,
        }
        for u in users
    ]


@router.get("/companies")
def list_companies(db: Session = Depends(get_db)):
    return db.query(Company).all()

# -----------------------------
# POST: create user
# -----------------------------

@router.post("/", response_model=UserOut)
def create_user(
    user: UserCreate,
    current_user=Depends(require_super),
    db: Session = Depends(get_db),
):

@router.post("/{user_id}/pause")
def pause_user(
    user_id: int,
    current_user=Depends(require_super),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(404, "User not found")

    if user.role == "super":
        raise HTTPException(400, "Cannot pause super admin")

    user.is_active = False
    db.commit()

    return {"status": "paused", "user_id": user_id}


@router.post("/{user_id}/activate")
def activate_user(
    user_id: int,
    current_user=Depends(require_super),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(404, "User not found")

    user.is_active = True
    db.commit()

    return {"status": "active", "user_id": user_id}


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user=Depends(require_super),
    db: Session = Depends(get_db)
):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(404)

    db.delete(user)
    db.commit()
    return {"ok": True}
