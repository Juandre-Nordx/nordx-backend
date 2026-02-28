
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Client
from backend.routes.auth import get_current_user

router = APIRouter(
    prefix="/clients",
    tags=["Clients"]
)

@router.post("/")
def create_client(
    client_code: str = Form(None),
    name: str = Form(...),
    site_address: str = Form(None),
    contact_person: str = Form(None),
    contact_number: str = Form(None),
    email: str = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    client = Client(
        company_id=current_user["company_id"],
        client_code=client_code,
        name=name,
        site_address=site_address,
        contact_person=contact_person,
        contact_number=contact_number,
        email=email,
    )

    db.add(client)
    db.commit()
    db.refresh(client)

    return {"id": client.id}


@router.get("/")
def list_clients(
    search: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = db.query(Client).filter(
        Client.company_id == current_user["company_id"]
    )

    if search:
        query = query.filter(Client.name.ilike(f"%{search}%"))

    return query.order_by(Client.name).all()

@router.get("/{client_id}")
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.company_id == current_user["company_id"],
    ).first()

    if not client:
        raise HTTPException(404, "Client not found")

    return client