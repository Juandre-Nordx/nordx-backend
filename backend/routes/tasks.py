from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from backend.database import get_db
from backend.models import Task, User, Client
from backend.schemas import TaskCreate, TaskOut
from backend.routes.auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.post("/", response_model=TaskOut)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if task.end_datetime <= task.start_datetime:
        raise HTTPException(status_code=400, detail="End must be after start")

    new_task = Task(
        company_id=current_user.company_id,
        client_id=task.client_id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        start_datetime=task.start_datetime,
        end_datetime=task.end_datetime,
        assigned_to=task.assigned_to,
        created_by=current_user.id
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