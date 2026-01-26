from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, Request
from sqlalchemy.orm import Session
from pathlib import Path
import uuid
import base64
import os

from backend.database import get_db
from backend.models import JobCard
from backend.services import pdf_service
from backend.services.job_number import generate_job_number
from backend.auth import get_current_user

router = APIRouter(prefix="/jobcards", tags=["Job Cards"])

# =========================
# PATHS
# =========================

BASE_DIR = Path.cwd()
UPLOAD_DIR = BASE_DIR / "uploads"

for sub in ["before", "after", "materials", "signatures", "jobcards"]:
    (UPLOAD_DIR / sub).mkdir(parents=True, exist_ok=True)

# =========================
# HELPERS
# =========================

def save_upload_file(file: UploadFile, folder: str) -> str:
    ext = Path(file.filename).suffix
    filename = f"{uuid.uuid4().hex}{ext}"
    save_path = UPLOAD_DIR / folder / filename

    with open(save_path, "wb") as f:
        f.write(file.file.read())

    # ✅ RETURN PUBLIC URL
    return f"/uploads/{folder}/{filename}"


def save_base64_image(data_url: str | None) -> str | None:
    if not data_url:
        return None

    try:
        header, encoded = data_url.split(",", 1)
        ext = header.split("/")[1].split(";")[0]
        filename = f"{uuid.uuid4().hex}.{ext}"

        save_path = UPLOAD_DIR / "signatures" / filename

        with open(save_path, "wb") as f:
            f.write(base64.b64decode(encoded))

        # ✅ RETURN PUBLIC URL
        return f"/uploads/signatures/{filename}"

    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid signature data")


def calculate_hours(arrival: str, departure: str) -> float:
    ah, am = map(int, arrival.split(":"))
    dh, dm = map(int, departure.split(":"))

    start = ah * 60 + am
    end = dh * 60 + dm

    diff = (end - start) / 60
    if diff < 0:
        diff += 24

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
    hours_worked: float = Form(...),  # recalculated anyway

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
    company_id = current_user["company_id"]
    created_by = current_user["id"]

    # 🔒 Server is source of truth
    hours_worked = calculate_hours(arrival_time, departure_time)

    # Signature
    signature_path = save_base64_image(signature)

    # Photos
    before_paths = [save_upload_file(f, "before") for f in before_photos or []]
    after_paths = [save_upload_file(f, "after") for f in after_photos or []]
    material_paths = [save_upload_file(f, "materials") for f in material_photos or []]

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

    # PDF
    pdf_path = UPLOAD_DIR / "jobcards" / f"{jobcard.job_number}.pdf"
    pdf_service.generate_jobcard_pdf(jobcard, str(pdf_path))

    return {
        "status": "success",
        "job_number": jobcard.job_number,
        "hours_worked": hours_worked,
    }
