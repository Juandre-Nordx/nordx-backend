from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import get_db
from backend.models import JobCard
from backend.models import Company, User
from fastapi import UploadFile, File, Form
from backend.models import Company
from datetime import datetime
import os
import uuid
from fastapi import APIRouter, Request, Depends
from backend.database import SessionLocal
from backend.routes.auth import require_admin
from backend.routes.auth import get_current_user
from backend.storage import (
    UPLOAD_ROOT,
    ensure_upload_root,
    ensure_upload_subdir,
    public_upload_path,
    resolve_upload_path,
)
from fastapi import Depends

router = APIRouter(prefix="/admin", tags=["Admin"])
UPLOAD_BASE = "/uploads"

UPLOAD_DIR = ensure_upload_subdir("company")


# ===============================
# Company
# ===============================
@router.get("/company")
def get_company(db: Session = Depends(get_db)):
    company = db.query(Company).first()
    if not company:
        company = Company(name="New Company")
        db.add(company)
        db.commit()
        db.refresh(company)
    return company

@router.post("/company")
def update_company(
    name: str = Form(...),
    address: str = Form(""),
    contact_email: str = Form(""),
    contact_phone: str = Form(""),
    logo: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    company = db.query(Company).first()

    if not company:
        company = Company(name=name)
        db.add(company)

    company.name = name
    company.address = address
    company.contact_email = contact_email
    company.contact_phone = contact_phone

    if logo:
        filename = f"{uuid.uuid4()}_{logo.filename}"
        file_path = ensure_upload_subdir("company") / filename

        with open(file_path, "wb") as f:
            f.write(logo.file.read())

        company.logo_path = public_upload_path("company", filename)

    db.commit()
    return {"success": True}

@router.get("/jobcards")
def list_jobcards(
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_admin(request)

    jobcards = (
        db.query(JobCard)
        .filter(JobCard.company_id == user["company_id"])
        .order_by(JobCard.created_at.desc())
        .all()
    )

    return [
        {
            "id": jc.id,
            "job_number": jc.job_number,
            "client_name": jc.client_name,
            "technician_name": jc.technician_name,
            "hours_worked": jc.hours_worked,
            "created_at": jc.created_at,
            "status": jc.status,
            "pdf": f"/admin/jobcards/{jc.id}/pdf",
        }
        for jc in jobcards
    ]

# GET SINGLE JOBCARD
# ===============================
@router.get("/jobcards/{jobcard_id}")
def get_jobcard(
    jobcard_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_admin(request)

    jc = (
        db.query(JobCard)
        .filter(
            JobCard.id == jobcard_id,
           JobCard.company_id == user["company_id"],
        )
        .first()
    )


    if not jc:
        raise HTTPException(status_code=404, detail="Jobcard not found")

    return {
        "id": jc.id,
        "job_number": jc.job_number,
        "client_name": jc.client_name,
        "customer_email": jc.customer_email,
        "site_address": jc.site_address,
        "contact_person": jc.contact_person,
        "contact_number": jc.contact_number,
        "technician_name": jc.technician_name,
        "arrival_time": jc.arrival_time,
        "departure_time": jc.departure_time,
        "hours_worked": jc.hours_worked,
        "instruction_given_by": jc.instruction_given_by,
        "job_description": jc.job_description,
        "materials_used": jc.materials_used,
        "material_photos": jc.material_photos or [],
        "before_photos": jc.before_photos or [],
        "after_photos": jc.after_photos or [],
        "status": jc.status,
        "signature_path": jc.signature_path,
        "created_at": jc.created_at.isoformat(),
        "pdf": f"/uploads/jobcards/{jc.job_number}.pdf",
    }

@router.get("/debug/volume-check")
def debug_volume_check(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Diagnostic endpoint — lists everything under the configured upload
    directory so we can verify files are landing on the mounted volume.
    """
    require_admin(request)

    DATA_ROOT = ensure_upload_root()
    SUBDIRS = ["before", "after", "materials", "signatures", "jobcards", "company"]

    # ── 1. Does the configured upload root exist at all? ────────────────
    if not DATA_ROOT.exists():
        return {
            "data_root_exists": False,
            "data_root": str(DATA_ROOT),
            "error": f"Configured upload directory {DATA_ROOT} does not exist on this container",
        }

    # ── 2. Basic root info ───────────────────────────────────────────────
    root_stat = DATA_ROOT.stat()
    result = {
        "data_root_exists": True,
        "data_root": str(DATA_ROOT),
        "data_root_permissions": oct(root_stat.st_mode),
        "subdirectories": {},
        "total_files": 0,
        "upload_dir_env": os.getenv("UPLOAD_DIR", "(not set — defaulting to /data/uploads)"),
        "mounted_upload_root": str(UPLOAD_ROOT),
    }

    # ── 3. Walk each expected subdirectory ───────────────────────────────
    for subdir_name in SUBDIRS:
        subdir_path = DATA_ROOT / subdir_name
        entry: dict = {
            "path": str(subdir_path),
            "exists": subdir_path.exists(),
            "file_count": 0,
            "total_size_bytes": 0,
            "sample_files": [],
        }

        if subdir_path.exists():
            try:
                stat = subdir_path.stat()
                entry["permissions"] = oct(stat.st_mode)
                files = sorted(subdir_path.iterdir())
                file_entries = [f for f in files if f.is_file()]
                entry["file_count"] = len(file_entries)
                entry["total_size_bytes"] = sum(f.stat().st_size for f in file_entries)

                # Up to 5 sample files with metadata
                for f in file_entries[:5]:
                    f_stat = f.stat()
                    entry["sample_files"].append({
                        "name": f.name,
                        "size_bytes": f_stat.st_size,
                        "modified": datetime.utcfromtimestamp(f_stat.st_mtime).isoformat() + "Z",
                        "readable": os.access(f, os.R_OK),
                    })

                result["total_files"] += entry["file_count"]
            except PermissionError as exc:
                entry["error"] = f"Permission denied: {exc}"
        else:
            entry["error"] = "Directory does not exist"

        result["subdirectories"][subdir_name] = entry

    # ── 4. Cross-check DB image paths against the filesystem ─────────────
    jobcards = db.query(JobCard).order_by(JobCard.created_at.desc()).limit(10).all()
    db_checks = []

    for jc in jobcards:
        photos_to_check = []
        for url in (jc.before_photos or []):
            photos_to_check.append(("before_photo", url))
        for url in (jc.after_photos or []):
            photos_to_check.append(("after_photo", url))
        for url in (jc.material_photos or []):
            photos_to_check.append(("material_photo", url))
        if jc.signature_path:
            photos_to_check.append(("signature", jc.signature_path))

        file_results = []
        for kind, url_path in photos_to_check:
            # DB stores paths like /uploads/before/<file>; resolve them under UPLOAD_DIR.
            disk_path = resolve_upload_path(url_path)
            file_results.append({
                "type": kind,
                "db_path": url_path,
                "disk_path": str(disk_path),
                "exists_on_disk": disk_path.exists(),
                "readable": os.access(disk_path, os.R_OK) if disk_path.exists() else False,
            })

        db_checks.append({
            "job_number": jc.job_number,
            "id": jc.id,
            "files": file_results,
        })

    result["db_image_checks"] = db_checks

    # ── 5. Full recursive file tree (capped at 200 entries) ──────────────
    all_files = []
    for f in DATA_ROOT.rglob("*"):
        if f.is_file():
            try:
                f_stat = f.stat()
                all_files.append({
                    "path": str(f.relative_to(DATA_ROOT)),
                    "size_bytes": f_stat.st_size,
                    "modified": datetime.utcfromtimestamp(f_stat.st_mtime).isoformat() + "Z",
                })
            except Exception:
                pass
        if len(all_files) >= 200:
            break

    result["all_files_on_volume"] = all_files
    result["all_files_truncated"] = len(all_files) >= 200

    return result


@router.get("/debug/jobcards")
def debug_jobcards(db: Session = Depends(get_db)):
    jobcards = db.query(JobCard).all()
    return [
        {
            "id": jc.id,
            "job_number": jc.job_number,
            "before_photos": jc.before_photos,
            "after_photos": jc.after_photos,
            "signature_path": jc.signature_path,
        }
        for jc in jobcards
    ]


    return [
        {
            "id": r.id,
            "name": r.name,
            "contact_email": r.contact_email,
            "contact_phone": r.contact_phone,
            "user_count": r.user_count
        }
        for r in results
    ]
@router.get("/super/companies")
def list_companies_with_user_count():
    db = SessionLocal()

    results = (
        db.query(
            Company.id,
            Company.name,
            Company.contact_email,
            Company.contact_phone,
            func.count(User.id).label("user_count")
        )
        .outerjoin(User, User.company_id == Company.id)
        .group_by(Company.id)
        .all()
    )

    db.close()

    return [
        {
            "id": r.id,
            "name": r.name,
            "contact_email": r.contact_email,
            "contact_phone": r.contact_phone,
            "user_count": r.user_count
        }
        for r in results
    ]

    
    
@router.post("/super/companies")
def create_company(
    name: str = Form(...),
    address: str = Form(None),
    contact_email: str = Form(None),
    contact_phone: str = Form(None),
    logo: UploadFile = File(None)
):
    db = SessionLocal()

    logo_path = None

    if logo:
        filename = f"{uuid.uuid4()}_{logo.filename}"
        file_path = UPLOAD_DIR / filename

        with open(file_path, "wb") as f:
            f.write(logo.file.read())

        logo_path = public_upload_path("company", filename)

    company = Company(
        name=name,
        address=address,
        contact_email=contact_email,
        contact_phone=contact_phone,
        logo_path=logo_path
    )

    db.add(company)
    db.commit()
    db.refresh(company)
    db.close()

    return {
        "id": company.id,
        "name": company.name
    }
    #status route
@router.patch("/jobcards/{jobcard_id}/status")
def update_jobcard_status(
    jobcard_id: int,
    status: str,
    db: Session = Depends(get_db)
):
    jobcard = db.query(JobCard).filter(JobCard.id == jobcard_id).first()

    if not jobcard:
        raise HTTPException(status_code=404, detail="Job card not found")

    if status not in ["submitted", "processed", "completed"]:
        raise HTTPException(status_code=422, detail="Invalid status")

    jobcard.status = status
    db.commit()

    return {"success": True, "status": status}

@router.get("/jobcards/{jobcard_id}/pdf")
def admin_get_jobcard_pdf(
    jobcard_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    require_admin(request)

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
