from pydantic import BaseModel, Field
from pydantic import BaseModel, EmailStr
from typing import Optional
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