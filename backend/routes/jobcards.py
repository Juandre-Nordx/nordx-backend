from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import JobCard, JobCardAudit, Company
from backend.services import pdf_service
from backend.services.job_number import generate_job_number
from fastapi import Request
from backend.routes.auth import get_current_user
from backend.services.email_service import send_jobcard_email
from backend.logger import get_logger
from backend.storage import ensure_upload_subdir, public_upload_path, resolve_upload_path
from datetime import datetime
import os
import uuid
import base64

logger = get_logger("jobcards")
router = APIRouter(prefix="/jobcards", tags=["Job Cards"])


# =========================
# HELPERS
# =========================

def save_upload_file(upload_file: UploadFile, subfolder: str) -> str:
    folder = ensure_upload_subdir(subfolder)

    ext = os.path.splitext(upload_file.filename)[1] or ".bin"
    filename = f"{uuid.uuid4().hex}{ext}"
    disk_path = folder / filename

    with open(disk_path, "wb") as f:
        f.write(upload_file.file.read())

    upload_file.file.seek(0)
    return public_upload_path(subfolder, filename)


def save_base64_image(data_url: str | None, subfolder="signatures") -> str | None:
    if not data_url:
        return None

    if "," in data_url:
        _, b64 = data_url.split(",", 1)
    else:
        b64 = data_url

    data = base64.b64decode(b64)

    folder = ensure_upload_subdir(subfolder)

    filename = f"{uuid.uuid4().hex}.png"
    disk_path = folder / filename

    with open(disk_path, "wb") as f:
        f.write(data)

    return public_upload_path(subfolder, filename)


def calculate_hours(arrival: str, departure: str) -> float:
    ah, am = map(int, arrival.split(":"))
    dh, dm = map(int, departure.split(":"))

    diff = ((dh * 60 + dm) - (ah * 60 + am)) / 60
    if diff < 0:
        diff += 24

    return round(diff, 2)


# ---------------------------------------------------------------------------
# Internal audit helper
# ---------------------------------------------------------------------------

def _write_jobcard_audit(
    db: Session,
    *,
    job_number,
    user_id,
    email,
    technician_name,
    client_name,
    site_address,
    hours_worked,
    event: str,
    status: str,
    detail=None,
) -> None:
    """Persist a JobCardAudit row.  Never raises — audit must not break the flow."""
    try:
        row = JobCardAudit(
            timestamp=datetime.utcnow(),
            job_number=job_number,
            user_id=user_id,
            email=email,
            technician_name=technician_name,
            client_name=client_name,
            site_address=site_address,
            hours_worked=hours_worked,
            event=event,
            status=status,
            detail=str(detail) if detail is not None else None,
        )
        db.add(row)
        db.commit()
    except Exception as exc:
        logger.error(
            "AUDIT | JOBCARD | DB_WRITE_FAILED | job_number=%s | event=%s | error=%s",
            job_number,
            event,
            exc,
        )
        try:
            db.rollback()
        except Exception:
            pass


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
    user_email = current_user["email"]

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

    # ------------------------------------------------------------------ SAVE
    try:
        db.add(jobcard)
        db.commit()
        db.refresh(jobcard)
    except Exception as exc:
        db.rollback()

        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        logger.error(
            "AUDIT | JOBCARD | %s | %s | %s | %s | %s | %s | %s | %s | %s | DB_ERROR",
            now,
            "N/A",          # job_number not yet assigned
            created_by,
            user_email,
            technician_name,
            client_name,
            site_address,
            hours_worked,
            str(exc),
        )

        _write_jobcard_audit(
            db,
            job_number=None,
            user_id=created_by,
            email=user_email,
            technician_name=technician_name,
            client_name=client_name,
            site_address=site_address,
            hours_worked=hours_worked,
            event="db_error",
            status="failure",
            detail=str(exc),
        )

        raise HTTPException(status_code=500, detail="Failed to save job card")

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    logger.info(
        "AUDIT | JOBCARD | %s | %s | %s | %s | %s | %s | %s | %.2f | SAVED",
        now,
        jobcard.job_number,
        created_by,
        user_email,
        technician_name,
        client_name,
        site_address,
        hours_worked,
    )

    _write_jobcard_audit(
        db,
        job_number=jobcard.job_number,
        user_id=created_by,
        email=user_email,
        technician_name=technician_name,
        client_name=client_name,
        site_address=site_address,
        hours_worked=hours_worked,
        event="saved",
        status="success",
    )

    # ------------------------------------------------------------------- PDF
    pdf_dir = ensure_upload_subdir("jobcards")
    pdf_path = pdf_dir / f"{jobcard.job_number}.pdf"

    try:
        pdf_service.generate_jobcard_pdf(jobcard, pdf_path)

        if not pdf_path.exists():
            raise RuntimeError("PDF file was not written to disk")

        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(
            "AUDIT | JOBCARD | %s | %s | %s | %s | %s | %s | %s | %.2f | PDF_OK",
            now,
            jobcard.job_number,
            created_by,
            user_email,
            technician_name,
            client_name,
            site_address,
            hours_worked,
        )

        _write_jobcard_audit(
            db,
            job_number=jobcard.job_number,
            user_id=created_by,
            email=user_email,
            technician_name=technician_name,
            client_name=client_name,
            site_address=site_address,
            hours_worked=hours_worked,
            event="pdf_ok",
            status="success",
            detail=str(pdf_path),
        )

    except Exception as exc:
        import traceback

        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        logger.error(
            "AUDIT | JOBCARD | %s | %s | %s | %s | %s | %s | %s | %.2f | PDF_FAILED | %s\n%s",
            now,
            jobcard.job_number,
            created_by,
            user_email,
            technician_name,
            client_name,
            site_address,
            hours_worked,
            exc,
            traceback.format_exc(),
        )

        _write_jobcard_audit(
            db,
            job_number=jobcard.job_number,
            user_id=created_by,
            email=user_email,
            technician_name=technician_name,
            client_name=client_name,
            site_address=site_address,
            hours_worked=hours_worked,
            event="pdf_failed",
            status="failure",
            detail=str(exc),
        )

    # ------------------------------------------------------------------ EMAIL
    company = db.query(Company).filter(Company.id == company_id).first()

    if company and company.contact_email:
        if pdf_path.exists():
            try:
                send_jobcard_email(
                    to_email=company.contact_email,
                    company_name=company.name,
                    job_number=jobcard.job_number,
                    pdf_path=str(pdf_path),
                )

                now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                logger.info(
                    "AUDIT | JOBCARD | %s | %s | %s | %s | %s | %s | %s | %.2f | EMAIL_SENT | to=%s",
                    now,
                    jobcard.job_number,
                    created_by,
                    user_email,
                    technician_name,
                    client_name,
                    site_address,
                    hours_worked,
                    company.contact_email,
                )

                _write_jobcard_audit(
                    db,
                    job_number=jobcard.job_number,
                    user_id=created_by,
                    email=user_email,
                    technician_name=technician_name,
                    client_name=client_name,
                    site_address=site_address,
                    hours_worked=hours_worked,
                    event="email_sent",
                    status="success",
                    detail=f"to={company.contact_email}",
                )

            except Exception as exc:
                now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                logger.error(
                    "AUDIT | JOBCARD | %s | %s | %s | %s | %s | %s | %s | %.2f | EMAIL_FAILED | to=%s | error=%s",
                    now,
                    jobcard.job_number,
                    created_by,
                    user_email,
                    technician_name,
                    client_name,
                    site_address,
                    hours_worked,
                    company.contact_email,
                    exc,
                )

                _write_jobcard_audit(
                    db,
                    job_number=jobcard.job_number,
                    user_id=created_by,
                    email=user_email,
                    technician_name=technician_name,
                    client_name=client_name,
                    site_address=site_address,
                    hours_worked=hours_worked,
                    event="email_failed",
                    status="failure",
                    detail=f"to={company.contact_email} | error={exc}",
                )
        else:
            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            logger.warning(
                "AUDIT | JOBCARD | %s | %s | %s | %s | %s | %s | %s | %.2f | EMAIL_SKIPPED | reason=PDF not found",
                now,
                jobcard.job_number,
                created_by,
                user_email,
                technician_name,
                client_name,
                site_address,
                hours_worked,
            )

            _write_jobcard_audit(
                db,
                job_number=jobcard.job_number,
                user_id=created_by,
                email=user_email,
                technician_name=technician_name,
                client_name=client_name,
                site_address=site_address,
                hours_worked=hours_worked,
                event="email_skipped",
                status="failure",
                detail="PDF not found on disk",
            )
    else:
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        logger.warning(
            "AUDIT | JOBCARD | %s | %s | %s | %s | %s | %s | %s | %.2f | EMAIL_SKIPPED | reason=no company email configured",
            now,
            jobcard.job_number,
            created_by,
            user_email,
            technician_name,
            client_name,
            site_address,
            hours_worked,
        )

        _write_jobcard_audit(
            db,
            job_number=jobcard.job_number,
            user_id=created_by,
            email=user_email,
            technician_name=technician_name,
            client_name=client_name,
            site_address=site_address,
            hours_worked=hours_worked,
            event="email_skipped",
            status="failure",
            detail="no company email configured",
        )

    # ----------------------------------------------------------- FINAL SUCCESS
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(
        "AUDIT | JOBCARD | %s | %s | %s | %s | %s | %s | %s | %.2f | SUCCESS",
        now,
        jobcard.job_number,
        created_by,
        user_email,
        technician_name,
        client_name,
        site_address,
        hours_worked,
    )

    _write_jobcard_audit(
        db,
        job_number=jobcard.job_number,
        user_id=created_by,
        email=user_email,
        technician_name=technician_name,
        client_name=client_name,
        site_address=site_address,
        hours_worked=hours_worked,
        event="success",
        status="success",
    )

    return {
        "status": "success",
        "job_number": jobcard.job_number,
        "hours_worked": hours_worked,
    }


# =========================
# DOWNLOAD PDF
# =========================

@router.get("/{jobcard_id}/pdf")
def get_jobcard_pdf(
    jobcard_id: int,
    db: Session = Depends(get_db),
):
    jobcard = db.query(JobCard).filter(JobCard.id == jobcard_id).first()

    if not jobcard:
        raise HTTPException(status_code=404, detail="Job card not found")

    pdf_path = resolve_upload_path(f"/uploads/jobcards/{jobcard.job_number}.pdf")

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF missing")

    return FileResponse(
        str(pdf_path),
        media_type="application/pdf",
        filename=f"{jobcard.job_number}.pdf",
    )
