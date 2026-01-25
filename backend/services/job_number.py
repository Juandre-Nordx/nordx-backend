from datetime import datetime
from sqlalchemy.orm import Session
from backend.models import JobCard


def generate_job_number(db: Session) -> str:
    """
    Generates a job number like:
    DC-20260104-001
    """

    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"DC-{today}-"

    last_job = (
        db.query(JobCard)
        .filter(JobCard.job_number.like(f"{prefix}%"))
        .order_by(JobCard.job_number.desc())
        .first()
    )

    if last_job:
        last_seq = int(last_job.job_number.split("-")[-1])
        next_seq = last_seq + 1
    else:
        next_seq = 1

    return f"{prefix}{next_seq:03d}"
