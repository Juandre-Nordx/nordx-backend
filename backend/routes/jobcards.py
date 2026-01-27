from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import JobCard
from backend.services import pdf_service
from backend.services.job_number import generate_job_number
from backend.auth import get_current_user
from backend.models import User
from datetime import datetime
from fastapi import Request
from backend.routes.auth import get_current_user
import os
import uuid
import base64

router = APIRouter(prefix="/jobcards", tags=["Job Cards"])

UPLOAD_DIR = "/data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================
# HELPERS
# =========================

def save_upload_file(upload_file: UploadFile, subfolder: str) -> str:
    folder = os.path.join(UPLOAD_DIR, subfolder)
    os.makedirs(folder, exist_ok=True)

    ext = os.path.splitext(upload_file.filename)[1] or ".bin"
    filename = f"{uuid.uuid4().hex}{ext}"
    disk_path = os.path.join(folder, filename)

    with open(disk_path, "wb") as f:
        f.write(upload_file.file.read())

    upload_file.file.seek(0)
    return f"/uploads/{subfolder}/{filename}"


def save_base64_image(data_url: str, subfolder="signatures") -> str:
    if not data_url:
        return None

    if "," in data_url:
        _, b64 = data_url.split(",", 1)
    else:
        b64 = data_url

    data = base64.b64decode(b64)

    folder = os.path.join(UPLOAD_DIR, subfolder)
    os.makedirs(folder, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.png"
    disk_path = os.path.join(folder, filename)

    with open(disk_path, "wb") as f:
        f.write(data)

    return f"/uploads/{subfolder}/{filename}"


def calculate_hours(arrival: str, departure: str) -> float:
    ah, am = map(int, arrival.split(":"))
    dh, dm = map(int, departure.split(":"))

    arrival_minutes = ah * 60 + am
    departure_minutes = dh * 60 + dm

    diff = (departure_minutes - arrival_minutes) / 60
    if diff < 0:
        diff += 24  # overnight work

    return round(diff, 2)

# =========================
# CREATE JOBCARD
# =========================
@router.post("/")
async def create_jobcard(
     request: Request,
    current_user: dict = Depends(get_current_user),
    client_name: str = Form(...),
    site_address: str = Form(...),
    contact_person: str = Form(...),
    contact_number: str = Form(None),
    technician_name: str = Form(...),

    arrival_time: str = Form(...),
    departure_time: str = Form(...),
    hours_worked: float = Form(...),

    instruction_given_by: str = Form(None),
    customer_email: str = Form(None),

    job_description: str = Form(...),
    materials_used: str = Form(None),

    signature: str = Form(None),

    before_photos: list[UploadFile] | None = File(None),
    after_photos: list[UploadFile] | None = File(None),
    material_photos: list[UploadFile] | None = File(None),

    db: Session = Depends(get_db),
):
    # --------------------------------
    # Company + User context
    # --------------------------------
    company_id = current_user["company_id"]
    created_by = current_user["id"]

    # --------------------------------
    # Calculate hours (server is source of truth)
    # --------------------------------
    try:
        hours_worked = calculate_hours(arrival_time, departure_time)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid time format")

    # --------------------------------
    # Signature
    # --------------------------------
    signature_path = save_base64_image(signature)

    # --------------------------------
    # Photos
    # --------------------------------
    before_paths, after_paths, material_paths = [], [], []

    if before_photos:
        for f in before_photos:
            before_paths.append(save_upload_file(f, "before"))

    if after_photos:
        for f in after_photos:
            after_paths.append(save_upload_file(f, "after"))

    if material_photos:
        for f in material_photos:
            material_paths.append(save_upload_file(f, "materials"))

    # --------------------------------
    # Create JobCard
    # --------------------------------
    jobcard = JobCard(
        job_number=generate_job_number(db),

        company_id=company_id,
        created_by=created_by,

        client_name=client_name,
        site_address=site_address,
        contact_person=contact_person,
        contact_number=contact_number,
        technician_name=technician_name,

        arrival_time=arrival_time,
        departure_time=departure_time,
        hours_worked=hours_worked,

        instruction_given_by=instruction_given_by,
        customer_email=customer_email,

        job_description=job_description,
        materials_used=materials_used,

        signature_path=signature_path,
        before_photos=before_paths,
        after_photos=after_paths,
        material_photos=material_paths,

        status="submitted",
    )

    db.add(jobcard)
    db.commit()
    db.refresh(jobcard)

    # --------------------------------
    # Generate PDF
    # --------------------------------
    pdf_dir = os.path.join(UPLOAD_DIR, "jobcards")
    os.makedirs(pdf_dir, exist_ok=True)

    pdf_path = os.path.join(pdf_dir, f"{jobcard.job_number}.pdf")
    pdf_service.generate_jobcard_pdf(jobcard, pdf_path)

    return {
        "status": "success",
        "job_number": jobcard.job_number,
        "hours_worked": hours_worked,
    }
