# JobCard Pro API

A FastAPI backend service for managing digital job cards, tracking technician activities, materials, client information, and supporting signatures and photo uploads.

## Architecture

- **Framework**: FastAPI (Python 3.12)
- **Database**: PostgreSQL (Replit built-in)
- **ORM**: SQLAlchemy
- **Auth**: Session-based (Starlette SessionMiddleware) + bcrypt password hashing
- **PDF Generation**: ReportLab
- **Email**: Resend

## Project Structure

```
backend/
  main.py          - FastAPI app setup, middleware, routes, DB init
  database.py      - SQLAlchemy engine & session setup
  models.py        - DB models: Company, User, JobCard, JobCardItem, Admin
  schemas.py       - Pydantic schemas
  routes/
    auth.py        - Login, logout, password reset
    admin.py       - Admin/company management, jobcard listing
    jobcards.py    - Job card creation, photo upload, PDF generation
    users.py       - User management
  services/
    pdf_service.py  - PDF report generation via ReportLab
    email_service.py - Email sending via Resend
    job_number.py   - Job number generation
```

## Environment Variables

- `DATABASE_URL` - PostgreSQL connection string (auto-set by Replit)
- `SESSION_SECRET` - Secret key for session cookies (default: "dev-secret" in dev)
- `ENVIRONMENT` - "development" | "production" | "beta" | "static" (default: "development")
- `UPLOAD_DIR` - Directory for uploaded files (default: /home/runner/workspace/uploads)
- `RESEND_API_KEY` - API key for sending emails via Resend

## Development

The app runs on port 5000 via uvicorn with `--reload` for hot reloading.

- Dev: sessions use `lax` same_site and no HTTPS-only
- Production: sessions use `none` same_site, HTTPS-only, domain `.nordx.co.za`

## API Endpoints

- `GET /health` - Health check
- `POST /auth/login` - Login
- `POST /auth/logout` - Logout
- `GET /auth/me` - Current user
- `POST /auth/forgot-password` / `POST /auth/reset-password`
- `GET /admin/company` / `POST /admin/company`
- `GET /admin/jobcards` / `GET /admin/jobcards/{id}`
- `POST /jobcards/` - Create job card (with file upload)
- `GET /jobcards/{id}/pdf` - Download PDF

## Deployment

Configured as autoscale deployment using Gunicorn with UvicornWorker on port 5000.
