from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from backend.models import Company
from backend.database import SessionLocal

from pathlib import Path
from PIL import Image
from io import BytesIO
from datetime import datetime
import json

# ---------------------------------
# Helpers
# ---------------------------------
def get_company():
    db = SessionLocal()
    company = db.query(Company).first()
    db.close()
    return company


def normalize_photo_paths(photo_field, base_dir: Path):
    if not photo_field:
        return []

    # Normalize input to list of strings
    if isinstance(photo_field, list):
        raw_paths = photo_field

    elif isinstance(photo_field, str):
        try:
            raw_paths = json.loads(photo_field)
            if not isinstance(raw_paths, list):
                raw_paths = [photo_field]
        except Exception:
            raw_paths = [p.strip() for p in photo_field.split(",") if p.strip()]

    else:
        return []

    resolved = []

    for p in raw_paths:
        p = p.replace("\\", "/").strip()

        if not p:
            continue

        # Expecting /uploads/...
        full_path = base_dir / p.lstrip("/")

        if full_path.exists():
            resolved.append(full_path)
        else:
            print(f"[PDF] Missing image:", full_path)

    return resolved


def draw_photo_grid(c, image_paths, start_x, start_y, max_width=500):
    thumb_w = 120
    thumb_h = 80
    padding = 10

    x = start_x
    y = start_y

    for path in image_paths:
        try:
            img = Image.open(path).convert("RGB")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            reader = ImageReader(buffer)
            c.drawImage(reader, x, y - thumb_h, thumb_w, thumb_h)

            x += thumb_w + padding
            if x + thumb_w > start_x + max_width:
                x = start_x
                y -= thumb_h + padding

        except Exception as e:
            print(f"[PDF] Failed to draw image {path}: {e}")

    return y - thumb_h - 20

# ---------------------------------
# Main PDF Generator
# ---------------------------------
def generate_jobcard_pdf(jobcard, output_path: str):
    company = get_company()
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    BASE_DIR = Path("/data")

    margin_x = 40
    y = height - 40

    # =====================================================
    # HEADER
    # =====================================================
    if company and company.logo_path:
        logo_path = BASE_DIR / company.logo_path.lstrip("/")
        if logo_path.exists():
            img = Image.open(logo_path).convert("RGB")
            buf = BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            c.drawImage(ImageReader(buf), margin_x, y - 70, 160, 60)

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
    # JOB META (2 COLUMN)
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

    c.setFont("Helvetica", 10)
    text = c.beginText(margin_x, y)
    for line in (jobcard.job_description or "").split("\n"):
        text.textLine(line)
    c.drawText(text)
    y = text.getY() - 20

    # =====================================================
    # MATERIALS USED
    # =====================================================
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin_x, y, "Materials Used")
    y -= 15

    c.setFont("Helvetica", 10)
    mtext = c.beginText(margin_x, y)
    if jobcard.materials_used:
        for line in jobcard.materials_used.split("\n"):
            mtext.textLine(line)
    else:
        mtext.textLine("None recorded.")
    c.drawText(mtext)
    y = mtext.getY() - 20

    # =====================================================
    # MATERIAL RECEIPT PHOTOS
    # =====================================================
    material_paths = normalize_photo_paths(jobcard.material_photos, BASE_DIR)
    if material_paths:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin_x, y, "Material Receipt Photos")
        y -= 15
        y = draw_photo_grid(c, material_paths, margin_x, y)

    # =====================================================
    # BEFORE / AFTER PHOTOS
    # =====================================================
    before_paths = normalize_photo_paths(jobcard.before_photos, BASE_DIR)
    after_paths = normalize_photo_paths(jobcard.after_photos, BASE_DIR)

    if before_paths:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin_x, y, "Before Photos")
        y -= 15
        y = draw_photo_grid(c, before_paths, margin_x, y)

    if after_paths:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin_x, y, "After Photos")
        y -= 15
        y = draw_photo_grid(c, after_paths, margin_x, y)

    # =====================================================
    # SIGNATURE
    # =====================================================
    if jobcard.signature_path:
        sig_path = BASE_DIR / jobcard.signature_path.lstrip("/")
        if sig_path.exists():
            c.setFont("Helvetica-Bold", 11)
            c.drawString(margin_x, y, "Customer Signature")
            y -= 10

            img = Image.open(sig_path).convert("RGBA")
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
    c.drawString(
        margin_x,
        20,
        f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    c.drawRightString(width - margin_x, 20, "Page 1 of 1")

    c.showPage()
    c.save()

