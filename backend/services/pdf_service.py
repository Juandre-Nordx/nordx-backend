from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from backend.models import Company
from backend.database import SessionLocal

from pathlib import Path
from PIL import Image
from io import BytesIO
from datetime import datetime


# ---------------------------------
# Helpers
# ---------------------------------
def get_company_by_id(company_id: int):
    db = SessionLocal()
    company = db.query(Company).filter(Company.id == company_id).first()
    db.close()
    return company


def normalize_photo_paths(photo_field, base_dir):
    paths = []

    if not photo_field:
        return paths

    raw_paths = photo_field if isinstance(photo_field, list) else [p.strip() for p in str(photo_field).split(",")]

    for p in raw_paths:
        p = p.replace("\\", "/")
        path = Path(p) if ":" in p else base_dir / p.lstrip("/")
        if path.exists():
            paths.append(path)

    return paths


def draw_photo_grid(c, image_paths, start_x, start_y, max_width=500):
    thumb_w = 120
    thumb_h = 80
    padding = 10

    x = start_x
    y = start_y

    for path in image_paths:
        try:
            img = Image.open(path).convert("RGB")
            buf = BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)

            c.drawImage(ImageReader(buf), x, y - thumb_h, thumb_w, thumb_h)

            x += thumb_w + padding
            if x + thumb_w > start_x + max_width:
                x = start_x
                y -= thumb_h + padding

        except Exception:
            pass

    return y - thumb_h - 20


# ---------------------------------
# Main PDF Generator
# ---------------------------------
def generate_jobcard_pdf(jobcard, output_path: str):
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    BASE_DIR = Path("/data")

    margin_x = 40
    y = height - 40

    # =====================================================
    # HEADER
    # =====================================================
    company = get_company_by_id(jobcard.company_id)
    
    print("=== PDF LOGO DEBUG ===")
    print("Company ID:", jobcard.company_id)

    if company:
        print("Company name:", company.name)
        print("Logo path (DB):", company.logo_path)
    else:
        print("Company NOT FOUND")


    if company and company.logo_path:
    logo_path = Path("/data") / company.logo_path.lstrip("/")
    print("Resolved logo path:", logo_path)
    print("Logo exists:", logo_path.exists())

    if logo_path.exists():
        c.drawImage(
            ImageReader(str(logo_path)),
            x=40,
            y=height - 100,
            width=120,
            height=60,
            preserveAspectRatio=True,
            mask="auto",
        )
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(width - margin_x, y - 20, "JOB CARD")

    c.setFont("Helvetica", 9)
    if company:
        c.drawRightString(width - margin_x, y - 40, company.name)
        if company.contact_phone:
            c.drawRightString(width - margin_x, y - 55, f"Tel: {company.contact_phone}")
        if company.contact_email:
            c.drawRightString(width - margin_x, y - 70, f"Email: {company.contact_email}")

    y -= 100
    c.line(margin_x, y, width - margin_x, y)
    y -= 20

    # =====================================================
    # JOB META
    # =====================================================
    c.setFont("Helvetica", 10)
    left_x = margin_x
    right_x = width / 2 + 10

    meta = [
        ("Job Number", jobcard.job_number),
        ("Client", jobcard.client_name),
        ("Site Address", jobcard.site_address),
        ("Contact Person", jobcard.contact_person),
        ("Contact Number", jobcard.contact_number),
        ("Technician", jobcard.technician_name),
        ("Arrival Time", jobcard.arrival_time),
        ("Departure Time", jobcard.departure_time),
        ("Hours Worked", jobcard.hours_worked),
        ("Instructions Given By", jobcard.instruction_given_by),
    ]

    for i, (label, value) in enumerate(meta):
        x = left_x if i % 2 == 0 else right_x
        if i % 2 == 0 and i > 0:
            y -= 14

        c.setFont("Helvetica-Bold", 9)
        c.drawString(x, y, f"{label}:")
        c.setFont("Helvetica", 9)
        c.drawString(x + 110, y, str(value or ""))

    y -= 30
    c.line(margin_x, y, width - margin_x, y)
    y -= 20

    # =====================================================
    # JOB DESCRIPTION
    # =====================================================
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin_x, y, "Job Description")
    y -= 15

    text = c.beginText(margin_x, y)
    for line in (jobcard.job_description or "").split("\n"):
        text.textLine(line)
    c.drawText(text)
    y = text.getY() - 20

    # =====================================================
    # MATERIALS
    # =====================================================
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin_x, y, "Materials Used")
    y -= 15

    text = c.beginText(margin_x, y)
    for line in (jobcard.materials_used or "None").split("\n"):
        text.textLine(line)
    c.drawText(text)
    y = text.getY() - 20

    # =====================================================
    # PHOTOS
    # =====================================================
    for title, photos in [
        ("Material Receipt Photos", jobcard.material_photos),
        ("Before Photos", jobcard.before_photos),
        ("After Photos", jobcard.after_photos),
    ]:
        paths = normalize_photo_paths(photos, BASE_DIR)
        if paths:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(margin_x, y, title)
            y -= 15
            y = draw_photo_grid(c, paths, margin_x, y)

    # =====================================================
    # SIGNATURE
    # =====================================================
    if jobcard.signature_path:
        sig = BASE_DIR / jobcard.signature_path.lstrip("/")
        if sig.exists():
            c.setFont("Helvetica-Bold", 11)
            c.drawString(margin_x, y, "Customer Signature")
            y -= 10

            img = Image.open(sig).convert("RGBA")
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])

            buf = BytesIO()
            bg.save(buf, format="PNG")
            buf.seek(0)

            c.drawImage(ImageReader(buf), margin_x, y - 60, 220, 60)
            y -= 80

    # =====================================================
    # FOOTER
    # =====================================================
    c.setFont("Helvetica", 8)
    c.drawString(margin_x, 20, f"Generated on {datetime.now():%Y-%m-%d %H:%M}")
    c.drawRightString(width - margin_x, 20, "Page 1 of 1")

    c.showPage()
    c.save()
