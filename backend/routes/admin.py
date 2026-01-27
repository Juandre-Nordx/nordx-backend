#from fastapi import APIRouter, Depends, HTTPException
#from fastapi.responses import FileResponse
#from sqlalchemy.orm import Session
#from sqlalchemy import func
#from backend.database import get_db
#from backend.models import JobCard
#from backend.models import Company, User
#from pathlib import Path
#from fastapi import UploadFile, File, Form
#from backend.models import Company
#import os
#import uuid
#from fastapi import APIRouter, Request, Depends
#from backend.auth import require_admin
#from backend.database import SessionLocal
#from backend.routes.auth import get_current_user, require_admin
#
#router = APIRouter(prefix="/admin", tags=["Admin"])
##router = APIRouter()
#UPLOAD_BASE = "/uploads"
#
#UPLOAD_DIR = Path("/data/uploads/company")
#UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
#
#
## ===============================
## Company
## ===============================
#@router.get("/company")
#def get_company(db: Session = Depends(get_db)):
#    company = db.query(Company).first()
#    if not company:
#        company = Company(name="New Company")
#        db.add(company)
#        db.commit()
#        db.refresh(company)
#    return company
#
#@router.post("/company")
#def update_company(
#    name: str = Form(...),
#    address: str = Form(""),
#    contact_email: str = Form(""),
#    contact_phone: str = Form(""),
#    logo: UploadFile = File(None),
#    db: Session = Depends(get_db)
#):
#    company = db.query(Company).first()
#
#    if not company:
#        company = Company(name=name)
#        db.add(company)
#
#    company.name = name
#    company.address = address
#    company.contact_email = contact_email
#    company.contact_phone = contact_phone
#
#    if logo:
#    ext = Path(logo.filename).suffix or ".png"
#    filename = f"{uuid.uuid4().hex}{ext}"
#    file_path = UPLOAD_DIR / filename
#
#    with file_path.open("wb") as f:
#        import shutil
#        shutil.copyfileobj(logo.file, f)
#
#    company.logo_path = f"/uploads/company/{filename}"
#
#    db.commit()
#    return {"success": True}
#
## ===============================
## LIST ALL JOBCARDS
## ===============================
#@router.get("/jobcards")
#def list_jobcards(
#    request: Request,
#    db: Session = Depends(get_db),
#    current_user: dict = Depends(get_current_user),
#):
#    require_admin(request)
#
#    jobcards = (
#        db.query(JobCard)
#        .filter(JobCard.company_id == current_user["company_id"])
#        .order_by(JobCard.created_at.desc())
#        .all()
#    )
#
#    return [
#        {
#            "id": jc.id,
#            "job_number": jc.job_number,
#            "client_name": jc.client_name,
#            "technician_name": jc.technician_name,
#            "hours_worked": jc.hours_worked,
#            "created_at": jc.created_at,
#            "status": jc.status,
#            "pdf": f"/admin/jobcards/{jc.id}/pdf",
#        }
#        for jc in jobcards
#    ]
#
## GET SINGLE JOBCARD
## ===============================
#@router.get("/jobcards/{jobcard_id}")
#def get_jobcard(
#    jobcard_id: int,
#    request: Request,
#    db: Session = Depends(get_db),
#    current_user: dict = Depends(get_current_user),
#):
#    require_admin(request)
#
#    jc = (
#        db.query(JobCard)
#        .filter(
#            JobCard.id == jobcard_id,
#            JobCard.company_id == current_user["company_id"],
#        )
#        .first()
#    )
#
#    if not jc:
#        raise HTTPException(status_code=404, detail="Jobcard not found")
#
#    return {
#        "id": jc.id,
#        "job_number": jc.job_number,
#        "client_name": jc.client_name,
#        "customer_email": jc.customer_email,
#        "site_address": jc.site_address,
#        "contact_person": jc.contact_person,
#        "contact_number": jc.contact_number,
#        "technician_name": jc.technician_name,
#        "arrival_time": jc.arrival_time,
#        "departure_time": jc.departure_time,
#        "hours_worked": jc.hours_worked,
#        "instruction_given_by": jc.instruction_given_by,
#        "job_description": jc.job_description,
#        "materials_used": jc.materials_used,
#        "material_photos": jc.material_photos or [],
#        "before_photos": jc.before_photos or [],
#        "after_photos": jc.after_photos or [],
#        "status": jc.status,
#        "signature_path": jc.signature_path,
#        "created_at": jc.created_at.isoformat(),
#        "pdf": f"/admin/jobcards/{jc.id}/pdf",
#    }
#
#@router.get("/debug/jobcards")
#def debug_jobcards(db: Session = Depends(get_db)):
#    jobcards = db.query(JobCard).all()
#    return [
#        {
#            "id": jc.id,
#            "job_number": jc.job_number,
#            "before_photos": jc.before_photos,
#            "after_photos": jc.after_photos,
#            "signature_path": jc.signature_path,
#        }
#        for jc in jobcards
#    ]
#
#
#    return [
#        {
#            "id": r.id,
#            "name": r.name,
#            "contact_email": r.contact_email,
#            "contact_phone": r.contact_phone,
#            "user_count": r.user_count
#        }
#        for r in results
#    ]
#@router.get("/super/companies")
#def list_companies_with_user_count():
#    db = SessionLocal()
#
#    results = (
#        db.query(
#            Company.id,
#            Company.name,
#            Company.contact_email,
#            Company.contact_phone,
#            func.count(User.id).label("user_count")
#        )
#        .outerjoin(User, User.company_id == Company.id)
#        .group_by(Company.id)
#        .all()
#    )
#
#    db.close()
#
#    return [
#        {
#            "id": r.id,
#            "name": r.name,
#            "contact_email": r.contact_email,
#            "contact_phone": r.contact_phone,
#            "user_count": r.user_count
#        }
#        for r in results
#    ]
#
#    
#    
#@router.post("/super/companies")
#def create_company(
#    name: str = Form(...),
#    address: str = Form(None),
#    contact_email: str = Form(None),
#    contact_phone: str = Form(None),
#    logo: UploadFile = File(None)
#):
#    db = SessionLocal()
#
#    logo_path = None
#
#    if logo:
#        filename = f"{uuid.uuid4()}_{logo.filename}"
#        file_path = UPLOAD_DIR / filename
#
#        with open(file_path, "wb") as f:
#            f.write(logo.file.read())
#
#        logo_path = f"/uploads/company/{filename}"
#
#    company = Company(
#        name=name,
#        address=address,
#        contact_email=contact_email,
#        contact_phone=contact_phone,
#        logo_path=logo_path
#    )
#
#    db.add(company)
#    db.commit()
#    db.refresh(company)
#    db.close()
#
#    return {
#        "id": company.id,
#        "name": company.name
#    }
#    #status route
#@router.patch("/jobcards/{jobcard_id}/status")
#def update_jobcard_status(
#    jobcard_id: int,
#    status: str,
#    db: Session = Depends(get_db)
#):
#    jobcard = db.query(JobCard).filter(JobCard.id == jobcard_id).first()
#
#    if not jobcard:
#        raise HTTPException(status_code=404, detail="Job card not found")
#
#    if status not in ["submitted", "processed", "completed"]:
#        raise HTTPException(status_code=422, detail="Invalid status")
#
#    jobcard.status = status
#    db.commit()
#
#    return {"success": True, "status": status}
#
#@router.get("/jobcards/{jobcard_id}/pdf")
#def admin_get_jobcard_pdf(
#    jobcard_id: int,
#    request: Request,
#    db: Session = Depends(get_db),
#):
#    require_admin(request)
#
#    jobcard = db.query(JobCard).filter(JobCard.id == jobcard_id).first()
#    if not jobcard:
#        raise HTTPException(status_code=404, detail="Job card not found")
#
#    pdf_path = os.path.join(
#        "/data/uploads",
#        "jobcards",
#        f"{jobcard.job_number}.pdf"
#    )
#
#    if not os.path.exists(pdf_path):
#        raise HTTPException(status_code=404, detail="PDF missing")
#
#    return FileResponse(
#        pdf_path,
#        media_type="application/pdf",
#        filename=f"{jobcard.job_number}.pdf",
#    )


from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pathlib import Path
import os
import uuid

from backend.database import get_db, SessionLocal
from backend.models import JobCard, Company, User
from backend.auth import require_admin
from backend.routes.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"])

UPLOAD_DIR = Path("/data/uploads/company")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

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
    db: Session = Depends(get_db),
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
        ext = Path(logo.filename).suffix or ".png"
        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = UPLOAD_DIR / filename

        with file_path.open("wb") as f:
            import shutil
            shutil.copyfileobj(logo.file, f)

        company.logo_path = f"/uploads/company/{filename}"

    db.commit()
    return {"success": True}


# ===============================
## LIST ALL JOBCARDS
## ===============================
@router.get("/jobcards")
def list_jobcards(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_admin(request)

    jobcards = (
        db.query(JobCard)
        .filter(JobCard.company_id == current_user["company_id"])
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


# ===============================
# GET SINGLE JOBCARD
# ===============================
@router.get("/jobcards/{jobcard_id}")
def get_jobcard(
    jobcard_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_admin(request)

    jc = (
        db.query(JobCard)
        .filter(
            JobCard.id == jobcard_id,
            JobCard.company_id == current_user["company_id"],
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
        "pdf": f"/admin/jobcards/{jc.id}/pdf",
    }


# ===============================
# SUPER ADMIN
# ===============================
@router.get("/super/companies")
def list_companies_with_user_count():
    db = SessionLocal()

    results = (
        db.query(
            Company.id,
            Company.name,
            Company.contact_email,
            Company.contact_phone,
            func.count(User.id).label("user_count"),
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
            "user_count": r.user_count,
        }
        for r in results
    ]


# ===============================
# STATUS UPDATE
# ===============================
@router.patch("/jobcards/{jobcard_id}/status")
def update_jobcard_status(
    jobcard_id: int,
    status: str,
    db: Session = Depends(get_db),
):
    jobcard = db.query(JobCard).filter(JobCard.id == jobcard_id).first()

    if not jobcard:
        raise HTTPException(status_code=404, detail="Job card not found")

    if status not in ["submitted", "processed", "completed"]:
        raise HTTPException(status_code=422, detail="Invalid status")

    jobcard.status = status
    db.commit()

    return {"success": True, "status": status}


# ===============================
# PDF DOWNLOAD
# ===============================
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

    pdf_path = f"/data/uploads/jobcards/{jobcard.job_number}.pdf"

    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF missing")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"{jobcard.job_number}.pdf",
    )
