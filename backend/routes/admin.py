import os
import tempfile
import uuid
import zipfile
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from starlette.background import BackgroundTask
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import SessionLocal, get_db
from backend.models import Company, JobCard, User
from backend.routes.auth import get_current_user, require_admin
from backend.storage import (
    UPLOAD_ROOT,
    UPLOAD_VOLUME_ROOT,
    ensure_upload_root,
    ensure_upload_subdir,
    public_upload_path,
    resolve_upload_path,
    upload_relative_path,
)


def _format_utc_timestamp(timestamp: float) -> str:
    return datetime.utcfromtimestamp(timestamp).isoformat() + "Z"


def _safe_upload_file_path(file_path: str) -> tuple[Path, Path]:
    relative = upload_relative_path(f"/uploads/{file_path}")
    upload_root = ensure_upload_root().resolve()
    disk_path = (upload_root / relative).resolve()

    try:
        disk_path.relative_to(upload_root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Upload not found") from exc

    return relative, disk_path


def _upload_public_url(relative_path: Path) -> str:
    return f"/uploads/{relative_path.as_posix()}"


def _upload_inspect_url(relative_path: Path) -> str:
    return f"/admin/debug/upload-file/{quote(relative_path.as_posix(), safe='/')}"


def _build_upload_tree(root_path: Path):
    counters = {
        "total_files": 0,
        "total_directories": 0,
        "total_size_bytes": 0,
    }

    def build_node(path: Path):
        relative_path = path.relative_to(root_path)
        relative_text = (
            "" if relative_path.as_posix() == "." else relative_path.as_posix()
        )

        node = {
            "name": path.name or str(root_path),
            "type": "directory" if path.is_dir() else "file",
            "relative_path": relative_text,
            "disk_path": str(path),
            "permissions": oct(path.stat().st_mode),
            "modified": _format_utc_timestamp(path.stat().st_mtime),
            "readable": os.access(path, os.R_OK),
        }

        if path.is_dir():
            counters["total_directories"] += 1
            children = sorted(
                path.iterdir(),
                key=lambda child: (child.is_file(), child.name.lower()),
            )
            node["children"] = [build_node(child) for child in children]
            return node

        file_size = path.stat().st_size
        counters["total_files"] += 1
        counters["total_size_bytes"] += file_size
        node.update({
            "size_bytes": file_size,
            "public_url": _upload_public_url(relative_path),
            "inspect_url": _upload_inspect_url(relative_path),
        })
        return node

    tree = build_node(root_path)
    return tree, counters


def _render_upload_tree_html(node: dict, is_root: bool = False) -> str:
    if node["type"] == "directory":
        label = escape(node["name"])
        children = "".join(
            _render_upload_tree_html(child) for child in node.get("children", [])
        )
        open_attr = " open" if is_root else ""
        return (
            f"<details{open_attr}><summary>📁 {label}</summary>"
            f"<ul>{children}</ul></details>"
        )

    name = escape(node["name"])
    relative_path = escape(node["relative_path"])
    size_bytes = node.get("size_bytes", 0)
    public_url = escape(node["public_url"], quote=True)
    inspect_url = escape(node["inspect_url"], quote=True)
    lower_name = name.lower()
    preview = ""

    if lower_name.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
        preview = (
            f'<a href="{public_url}" target="_blank">'
            f'<img src="{public_url}" loading="lazy" alt="{name}"></a>'
        )
    elif lower_name.endswith(".pdf"):
        preview = f'<a class="pill" href="{public_url}" target="_blank">Open PDF</a>'

    return (
        "<li>"
        f"<div class=\"file-row\"><span>📄 <strong>{name}</strong></span>"
        f"<span class=\"meta\">{size_bytes:,} bytes · {relative_path}</span>"
        f"<span><a href=\"{public_url}\" target=\"_blank\">public</a> · "
        f"<a href=\"{inspect_url}\" target=\"_blank\">inspect</a></span></div>"
        f"{preview}"
        "</li>"
    )



def _unique_zip_name(filename: str, used_names: set[str]) -> str:
    if filename not in used_names:
        used_names.add(filename)
        return filename

    stem, suffix = os.path.splitext(filename)
    counter = 2
    while True:
        candidate = f"{stem}-{counter}{suffix}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        counter += 1


def _cleanup_temp_file(file_path: str) -> None:
    if os.path.exists(file_path):
        os.remove(file_path)


def _jobcard_pdf_directories() -> list[Path]:
    roots = [ensure_upload_root(), UPLOAD_VOLUME_ROOT, Path("/data/uploads")]
    directories = []
    seen = set()

    for root in roots:
        jobcards_dir = (root / "jobcards").resolve()
        if jobcards_dir in seen:
            continue
        seen.add(jobcards_dir)
        if jobcards_dir.exists():
            directories.append(jobcards_dir)

    return directories


def _write_volume_jobcard_pdf_zip(jobcards_dirs: list[Path], zip_path: str) -> int:
    pdf_entries = []
    for jobcards_dir in jobcards_dirs:
        pdf_entries.extend(
            (jobcards_dir, pdf_path)
            for pdf_path in sorted(jobcards_dir.rglob("*.pdf"))
        )

    used_names: set[str] = set()

    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        manifest_lines = [
            "NORDX jobcard PDF volume export",
            f"Generated at: {datetime.utcnow().isoformat()}Z",
            "Source folders:",
            *(f"- {jobcards_dir}" for jobcards_dir in jobcards_dirs),
            f"Included PDFs: {len(pdf_entries)}",
            "",
            "Included:",
        ]

        for jobcards_dir, pdf_path in pdf_entries:
            archive_name = _unique_zip_name(pdf_path.name, used_names)
            zf.write(pdf_path, arcname=archive_name)
            manifest_lines.append(
                f"- {pdf_path.relative_to(jobcards_dir)} -> {archive_name} "
                f"({pdf_path.stat().st_size} bytes)"
            )

        zf.writestr("README.txt", "\n".join(manifest_lines) + "\n")

    return len(pdf_entries)


def _write_jobcard_pdf_zip(jobcards, zip_path: str) -> dict:
    used_names: set[str] = set()
    included = []
    missing = []

    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for jobcard in jobcards:
            pdf_path = resolve_upload_path(f"/uploads/jobcards/{jobcard.job_number}.pdf")
            if not pdf_path.is_file():
                missing.append({
                    "job_number": jobcard.job_number,
                    "expected_path": str(pdf_path),
                })
                continue

            archive_name = _unique_zip_name(f"{jobcard.job_number}.pdf", used_names)
            zf.write(pdf_path, arcname=archive_name)
            included.append({
                "job_number": jobcard.job_number,
                "archive_name": archive_name,
                "size_bytes": pdf_path.stat().st_size,
            })

        manifest_lines = [
            "NORDX jobcard PDF export",
            f"Generated at: {datetime.utcnow().isoformat()}Z",
            f"Included PDFs: {len(included)}",
            f"Missing PDFs: {len(missing)}",
            "",
            "Included:",
        ]
        manifest_lines.extend(
            f"- {item['job_number']} -> {item['archive_name']} "
            f"({item['size_bytes']} bytes)"
            for item in included
        )

        if missing:
            manifest_lines.extend(["", "Missing:"])
            manifest_lines.extend(
                f"- {item['job_number']} expected at {item['expected_path']}"
                for item in missing
            )

        zf.writestr("README.txt", "\n".join(manifest_lines) + "\n")

    return {
        "included_count": len(included),
        "missing_count": len(missing),
        "included": included,
        "missing": missing,
    }

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
        "upload_dir_env": os.getenv("UPLOAD_DIR", "(not set — defaulting to /data volume, storing files in /data/uploads)"),
        "mounted_upload_root": str(UPLOAD_VOLUME_ROOT),
        "upload_storage_root": str(UPLOAD_ROOT),
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


@router.get("/debug/upload-tree")
def debug_upload_tree(request: Request):
    """Return the complete upload volume as a nested file tree."""
    require_admin(request)

    data_root = ensure_upload_root()
    if not data_root.exists():
        return {
            "data_root_exists": False,
            "data_root": str(data_root),
            "error": (
                f"Configured upload directory {data_root} does not exist "
                "on this container"
            ),
        }

    tree, counters = _build_upload_tree(data_root)
    root_stat = data_root.stat()
    return {
        "data_root_exists": True,
        "data_root": str(data_root),
        "data_root_permissions": oct(root_stat.st_mode),
        "upload_dir_env": os.getenv("UPLOAD_DIR", "(not set — defaulting to /data volume, storing files in /data/uploads)"),
        "mounted_upload_root": str(UPLOAD_VOLUME_ROOT),
        "upload_storage_root": str(UPLOAD_ROOT),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        **counters,
        "tree": tree,
    }


@router.get("/debug/upload-browser", response_class=HTMLResponse)
def debug_upload_browser(request: Request):
    """Render a clickable upload volume browser with image/PDF previews."""
    require_admin(request)

    data_root = ensure_upload_root()
    if not data_root.exists():
        return HTMLResponse(
            (
                "<h1>Upload volume missing</h1>"
                f"<p>{escape(str(data_root))} does not exist.</p>"
            ),
            status_code=404,
        )

    tree, counters = _build_upload_tree(data_root)
    tree_html = _render_upload_tree_html(tree, is_root=True)
    html = f"""
    <!doctype html>
    <html>
      <head>
        <meta charset=\"utf-8\">
        <title>Upload Volume Browser</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 24px; color: #172033; }}
          h1 {{ margin-bottom: 6px; }}
          .summary {{ background: #f4f7fb; border: 1px solid #d8e0ec; border-radius: 8px; padding: 12px; margin-bottom: 18px; }}
          details {{ margin: 6px 0 6px 18px; }}
          summary {{ cursor: pointer; font-weight: 700; }}
          ul {{ list-style: none; padding-left: 18px; }}
          li {{ border-left: 2px solid #e4e9f2; margin: 8px 0; padding: 8px 0 8px 12px; }}
          .file-row {{ display: grid; grid-template-columns: minmax(260px, 1fr) minmax(260px, 1fr) 150px; gap: 12px; align-items: center; }}
          .meta {{ color: #65738a; font-size: 13px; overflow-wrap: anywhere; }}
          img {{ display: block; max-width: 220px; max-height: 160px; object-fit: contain; margin-top: 8px; border: 1px solid #d8e0ec; border-radius: 6px; }}
          a {{ color: #0b63ce; }}
          .pill {{ display: inline-block; margin-top: 8px; padding: 4px 8px; background: #eef5ff; border-radius: 999px; text-decoration: none; }}
        </style>
      </head>
      <body>
        <h1>Upload Volume Browser</h1>
        <div class=\"summary\">
          <div><strong>Root:</strong> {escape(str(data_root))}</div>
          <div><strong>Total files:</strong> {counters['total_files']:,}</div>
          <div><strong>Total directories:</strong> {counters['total_directories']:,}</div>
          <div><strong>Total size:</strong> {counters['total_size_bytes']:,} bytes</div>
          <div><strong>JSON tree:</strong> <a href=\"/admin/debug/upload-tree\">/admin/debug/upload-tree</a></div>
          <div><strong>Download all jobcard PDFs:</strong> <a href=\"/admin/debug/jobcard-pdfs/download\">/admin/debug/jobcard-pdfs/download</a></div>
        </div>
        {tree_html}
      </body>
    </html>
    """
    return HTMLResponse(html)


@router.get("/debug/upload-file/{file_path:path}")
def debug_upload_file(file_path: str, request: Request):
    """Open a single file from the configured upload volume for inspection."""
    require_admin(request)

    try:
        _relative, disk_path = _safe_upload_file_path(file_path)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Upload not found") from exc

    if not disk_path.is_file():
        raise HTTPException(status_code=404, detail="Upload not found")

    return FileResponse(str(disk_path), filename=disk_path.name)


@router.get("/debug/jobcard-pdfs/download")
def debug_download_all_jobcard_pdfs(request: Request):
    """Download every PDF currently stored in the upload volume's jobcards folder."""
    require_admin(request)

    jobcards_dirs = _jobcard_pdf_directories()
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    temp_zip_path = temp_zip.name
    temp_zip.close()

    _write_volume_jobcard_pdf_zip(jobcards_dirs, temp_zip_path)

    today = datetime.utcnow().strftime("%Y%m%d")
    filename = f"nordx-jobcard-pdfs-volume-{today}.zip"
    return FileResponse(
        temp_zip_path,
        media_type="application/zip",
        filename=filename,
        background=BackgroundTask(_cleanup_temp_file, temp_zip_path),
    )


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

@router.get("/jobcards/pdfs/download")
def admin_download_jobcard_pdfs(
    request: Request,
    db: Session = Depends(get_db),
):
    """Download all PDF jobcards for the current admin's company as a zip file."""
    user = require_admin(request)

    jobcards = (
        db.query(JobCard)
        .filter(JobCard.company_id == user["company_id"])
        .order_by(JobCard.created_at.desc())
        .all()
    )

    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    temp_zip_path = temp_zip.name
    temp_zip.close()

    _write_jobcard_pdf_zip(jobcards, temp_zip_path)

    today = datetime.utcnow().strftime("%Y%m%d")
    filename = f"nordx-jobcards-{today}.zip"
    return FileResponse(
        temp_zip_path,
        media_type="application/zip",
        filename=filename,
        background=BackgroundTask(_cleanup_temp_file, temp_zip_path),
    )


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
