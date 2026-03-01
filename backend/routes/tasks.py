from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from backend.database import get_db
from backend.models import Task, Client
from backend.schemas import TaskCreate, TaskOut
from backend.routes.auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/", response_model=TaskOut)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    company_id = current_user["company_id"]
    user_id = current_user["id"]

    # 1️⃣ Validate client belongs to company
    client = (
        db.query(Client)
        .filter(
            Client.id == task_data.client_id,
            Client.company_id == company_id
        )
        .first()
    )

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # 2️⃣ Validate booking times
    if task_data.end_datetime <= task_data.start_datetime:
        raise HTTPException(
            status_code=400,
            detail="End time must be after start time"
        )

    # 3️⃣ Create task
    new_task = Task(
        company_id=company_id,
        client_id=task_data.client_id,
        title=task_data.title,
        description=task_data.description,
        start_datetime=task_data.start_datetime,
        end_datetime=task_data.end_datetime,
        created_by=user_id,
        status="open",
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return new_task


@router.get("/client/{client_id}", response_model=list[TaskOut])
def get_tasks_for_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    company_id = current_user["company_id"]

    tasks = (
        db.query(Task)
        .filter(
            Task.client_id == client_id,
            Task.company_id == company_id
        )
        .order_by(Task.start_datetime.asc())
        .all()
    )

    return tasks