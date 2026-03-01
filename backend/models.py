# backend/models.py

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    ForeignKey,
    DateTime,
    JSON, 
    Text
)

#from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base
from sqlalchemy import Time


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)

    address = Column(String)
    contact_email = Column(String)
    contact_phone = Column(String)

    logo_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)

    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    role = Column(String, default="technician")  # admin | technician
    company_id = Column(Integer, ForeignKey("companies.id"))

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    reset_token = Column(String, nullable=True)
    reset_token_expiry = Column(DateTime, nullable=True)
    

class JobCard(Base):
    __tablename__ = "jobcards"

    id = Column(Integer, primary_key=True)
    job_number = Column(String, unique=True, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    client_name = Column(String, nullable=False)
    site_address = Column(String, nullable=False)
    
    contact_person = Column(String, nullable=False)
    contact_number = Column(String, nullable=False)
    
    technician_name = Column(String, nullable=False)
    
    arrival_time = Column(String, nullable=True)
    departure_time = Column(String, nullable=True)
    hours_worked = Column(Float, nullable=True)
    
    instruction_given_by = Column(String, nullable=True)
    customer_email = Column(String, nullable=True)
    job_description = Column(Text, nullable=False)
    materials_used = Column(Text, nullable=False)
    material_photos = Column(JSON, default=list)
    signature_path = Column(String, nullable=False)
    before_photos = Column(JSON, default=list)
    after_photos = Column(JSON, default=list)
    status = Column(String, default="submitted", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    
class JobCardItem(Base):
    __tablename__ = "jobcard_items"

    id = Column(Integer, primary_key=True, index=True)
    jobcard_id = Column(Integer, ForeignKey("jobcards.id"), nullable=False)

    description = Column(String, nullable=False)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, default=0.0)

    #jobcard = relationship("JobCard", back_populates="items")

    
class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    is_active = Column(Boolean, default=True)    
    
    
    
class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    client_code = Column(String, index=True)

    name = Column(String, nullable=False)

    # NEW STANDARDIZED FIELD
    site_address = Column(String)

   

    contact_person = Column(String)
    contact_number = Column(String)
    email = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)