from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import JobCard
from backend.services import pdf_service
from backend.services.job_number import generate_job_number
from fastapi import Request
from backend.routes.auth import get_current_user
from backend.services.email_service import send_jobcard_email
from backend.models import Company
import os
import uuid
import base64
from io import BytesIO
from fastapi import BackgroundTasks
from PIL import Image, ImageOps

router = APIRouter(prefix="/jobcards", tags=["Job Cards"])

UPLOAD_DIR = "/data/uploads"
MAX_IMAGE_DIMENSION = 1920
JPEG_QUALITY = 75
os.makedirs(UPLOAD_DIR, exist_ok=True)

if not os.path.exists(UPLOAD_DIR):
    raise RuntimeError("Uploads directory not mounted — check Railway Volume")

# =========================
# HELPERS
# =========================

def compress_image(image_bytes: bytes, extension: str) -> tuple[bytes, str]:
    """Compress image uploads to reduce storage size for jobcard photos."""
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)

            output = BytesIO()
            has_alpha = image.mode in ("RGBA", "LA") or (
                image.mode == "P" and "transparency" in image.info
            )

            if has_alpha:
                image.save(output, format="PNG", optimize=True)
                return output.getvalue(), ".png"

            image = image.convert("RGB")
            image.save(
                output,
                format="JPEG",
                optimize=True,
                quality=JPEG_QUALITY,
                progressive=True,
            )
            return output.getvalue(), ".jpg"
    except Exception:
        # If file isn't a valid image, keep original bytes and extension.
        return image_bytes, extension

def save_upload_file(upload_file: UploadFile, subfolder: str) -> str:
    folder = os.path.join(UPLOAD_DIR, subfolder)
    os.makedirs(folder, exist_ok=True)

    ext = os.path.splitext(upload_file.filename)[1] or ".bin"
    raw_data = upload_file.file.read()
    compressed_data, ext = compress_image(raw_data, ext)

    filename = f"{uuid.uuid4().hex}{ext}"
    disk_path = os.path.join(folder, filename)

    with open(disk_path, "wb") as f:
        f.write(compressed_data)

    upload_file.file.seek(0)
    return f"/uploads/{subfolder}/{filename}"


def save_base64_image(data_url: str | None, subfolder="signatures") -> str | None:
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

    diff = ((dh * 60 + dm) - (ah * 60 + am)) / 60
    if diff < 0:
        diff += 24

    return round(diff, 2)

# =========================
# CREATE JOBCARD
# =========================

@router.post("/")
async def create_jobcard(
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: dict = Depends(get_current_user),

    client_name: str = Form(...),
    site_address: str = Form(...),
    contact_person: str = Form(...),
    contact_number: str = Form(None),
    technician_name: str = Form(...),

    arrival_time: str = Form(...),
    departure_time: str = Form(...),

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

    hours_worked = calculate_hours(arrival_time, departure_time)
    signature_path = save_base64_image(signature)

    before_paths, after_paths, material_paths = [], [], []

    for f in before_photos or []:
        before_paths.append(save_upload_file(f, "before"))

    for f in after_photos or []:
        after_paths.append(save_upload_file(f, "after"))

    for f in material_photos or []:
        material_paths.append(save_upload_file(f, "materials"))

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
    
    company = db.query(Company).filter(Company.id == company_id).first()

    background_tasks.add_task(
        process_jobcard_async,
        jobcard.id,
        company.contact_email if company else None,
        company.name if company else "",
    )
    return {
    "status": "success",
    "job_number": jobcard.job_number,
    "hours_worked": hours_worked,
    }
    # -------- PDF GENERATION (ONLY PLACE IT BELONGS) --------
    pdf_dir = os.path.join(UPLOAD_DIR, "jobcards")
    os.makedirs(pdf_dir, exist_ok=True)

    pdf_path = os.path.join(pdf_dir, f"{jobcard.job_number}.pdf")

    #try:
    #    print("📄 Generating PDF:", pdf_path)
    #    pdf_service.generate_jobcard_pdf(jobcard, pdf_path)
#
    #    if not os.path.exists(pdf_path):
    #        raise RuntimeError("PDF not created")
#
    #    print("✅ PDF generated")
#
    #except Exception:
    #    import traceback
    #    print("❌ PDF generation failed")
    #    traceback.print_exc()

    #return {
    #    "status": "success",
    #    "job_number": jobcard.job_number,
    #    "hours_worked": hours_worked,
    #}
    
    ## --------------------------------
    ## EMAIL PDF TO COMPANY
    ## --------------------------------
    #company = db.query(Company).filter(Company.id == company_id).first()
#
    #if company and company.contact_email:
    #    try:
    #        send_jobcard_email(
    #            to_email=company.contact_email,
    #            company_name=company.name,
    #            job_number=jobcard.job_number,
    #            pdf_path=pdf_path,
    #        )
    #        print("📧 Jobcard email sent")
    #    except Exception as e:
    #        print("❌ Failed to send jobcard email:", e)
    #else:
    #    print("⚠️ No company contact_email configured — skipping email")
#
#
    #return {
    #    "status": "success",
    #    "job_number": jobcard.job_number,
    #    "hours_worked": hours_worked,
    #}

def process_jobcard_async(jobcard_id: int, company_email: str | None, company_name: str):
    from backend.database import SessionLocal

    db = SessionLocal()
    try:
        jobcard = db.query(JobCard).filter(JobCard.id == jobcard_id).first()
        if not jobcard:
            return

        pdf_dir = os.path.join(UPLOAD_DIR, "jobcards")
        os.makedirs(pdf_dir, exist_ok=True)

        pdf_path = os.path.join(pdf_dir, f"{jobcard.job_number}.pdf")

        pdf_service.generate_jobcard_pdf(jobcard, pdf_path)

        if company_email:
            send_jobcard_email(
                to_email=company_email,
                company_name=company_name,
                job_number=jobcard.job_number,
                pdf_path=pdf_path,
            )
    finally:
        db.close()

# =========================
# DOWNLOAD PDF
# =========================

@router.get("/{jobcard_id}/pdf")
def get_jobcard_pdf(
    jobcard_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    jobcard = (
        db.query(JobCard)
        .filter(
            JobCard.id == jobcard_id,
            JobCard.company_id == current_user["company_id"],
        )
        .first()
    )

    if not jobcard:
        raise HTTPException(status_code=404, detail="Job card not found")

    pdf_path = os.path.join(
        UPLOAD_DIR,
        "jobcards",
        f"{jobcard.job_number}.pdf"
    )

    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF missing")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"{jobcard.job_number}.pdf",
    )
