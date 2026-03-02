from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    ForeignKey,
    DateTime,
    Numeric,
    JSON,
    Text,
    Index
)
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base


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

    role = Column(String, default="technician")
    company_id = Column(Integer, ForeignKey("companies.id"))

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    reset_token = Column(String)
    reset_token_expiry = Column(DateTime)


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)

    client_code = Column(String, nullable=False)
    company_name = Column(String, nullable=False)

    contact_person = Column(String)
    phone = Column(String)
    email = Column(String)
    physical_address = Column(String)

    vat_number = Column(String)
    payment_terms = Column(String)
    credit_limit = Column(Numeric(12, 2))
    account_status = Column(String, default="active")

    created_at = Column(DateTime, default=datetime.utcnow)

    tasks = relationship("Task", back_populates="client", cascade="all, delete-orphan")
    jobcards = relationship("JobCard", back_populates="client")

    __table_args__ = (
        Index("ix_clients_company_clientcode", "company_id", "client_code"),
    )


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)

    title = Column(String, nullable=False)
    description = Column(Text)

    status = Column(String, default="scheduled")
    priority = Column(String, default="medium")

    start_datetime = Column(DateTime)
    end_datetime = Column(DateTime)

    assigned_to = Column(Integer, ForeignKey("users.id"))
    created_by = Column(Integer, ForeignKey("users.id"))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="tasks")
    jobcards = relationship("JobCard", back_populates="task")


class JobCard(Base):
    __tablename__ = "jobcards"

    id = Column(Integer, primary_key=True)
    job_number = Column(String, unique=True, nullable=False)

    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)

    created_by = Column(Integer, ForeignKey("users.id"))

    client_name = Column(String, nullable=False)
    site_address = Column(String, nullable=False)
    contact_person = Column(String, nullable=False)
    contact_number = Column(String, nullable=False)

    technician_name = Column(String, nullable=False)

    arrival_time = Column(String)
    departure_time = Column(String)
    hours_worked = Column(Float)

    instruction_given_by = Column(String)
    customer_email = Column(String)

    job_description = Column(Text, nullable=False)
    materials_used = Column(Text, nullable=False)

    material_photos = Column(JSON, default=list)
    signature_path = Column(String, nullable=False)
    before_photos = Column(JSON, default=list)
    after_photos = Column(JSON, default=list)

    status = Column(String, default="submitted")
    created_at = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="jobcards")
    task = relationship("Task", back_populates="jobcards")


class JobCardItem(Base):
    __tablename__ = "jobcard_items"

    id = Column(Integer, primary_key=True, index=True)
    jobcard_id = Column(Integer, ForeignKey("jobcards.id"), nullable=False)

    description = Column(String, nullable=False)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, default=0.0)


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    is_active = Column(Boolean, default=True)