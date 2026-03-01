from pydantic import BaseModel, Field
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class JobCardItemCreate(BaseModel):
    description: str
    quantity: int

class JobCardCreate(BaseModel):
    client_name: str
    site_address: str
    contact_person: str
    contact_number: str
    technician_name: str
    hours_worked: float = Field(gt=0)
    job_description: str
    materials_used: str
    signature: str
    
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "technician"
    company_id: Optional[int] = None


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    company_id: Optional[int]

    class Config:
        from_attributes = True
        


class TaskCreate(BaseModel):
    client_id: int
    title: str
    description: Optional[str] = None
    priority: Optional[str] = "medium"
    status: Optional[str] = "scheduled"
    start_datetime: datetime
    end_datetime: datetime
    assigned_to: Optional[int] = None

class TaskOut(BaseModel):
    id: int
    client_id: int
    title: str
    description: Optional[str]
    status: str
    priority: str
    start_datetime: Optional[datetime]
    end_datetime: Optional[datetime]
    assigned_to: Optional[int]

    class Config:
        from_attributes = True