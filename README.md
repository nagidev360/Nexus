# Nexus

A responsive software catalog for Android APKs and Windows software, built with Flask, SQLAlchemy, and a custom responsive frontend.

## Current features
- Responsive storefront and mobile navigation
- Search and Android/Windows filters
- Client-side sorting by newest, name, and download count
- Software details, download counter, and share-listing action
- Admin login, upload, listing management, and delete action
- CSRF checks on POST forms and HTTP-only session cookies
- Health endpoint at `/health`
- APK, EXE, MSI, and ZIP upload allowlist; 500 MB request limit
- SQLite by default or PostgreSQL via `DATABASE_URL`

## Local setup
Requires Python 3.11+.
```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Windows CMD: .venv\Scripts\activate.bat
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```
Set environment variables before starting:
- Windows CMD: `set ADMIN_PASSWORD=choose-a-long-password`
- PowerShell: `$env:ADMIN_PASSWORD="choose-a-long-password"`
- macOS/Linux: `export ADMIN_PASSWORD="choose-a-long-password"`

Run: `python -m flask --app app run`. Open `http://127.0.0.1:5000`; admin portal is at `/admin`.

## Render deployment
The GitHub repository is connected to Render with automatic deploys. Build command: `pip install -r requirements.txt`; start command: `gunicorn app:app`; health check: `/health`.

Set a unique `ADMIN_PASSWORD` and long random `SECRET_KEY` in the Render Environment page. Never commit these secrets.

## Persistence setup still required before production
Render Free web services use ephemeral filesystems. SQLite database files and uploaded binaries can disappear on restart/redeploy. For durable production data:
1. Provision a persistent PostgreSQL database and set its connection URL as `DATABASE_URL`.
2. Store uploaded binaries on persistent storage or object storage and set `UPLOAD_DIR` accordingly.
3. Back up the database and test restore procedures.

## Security / production limitations
Extension checks are not malware scanning and do not prove a file is safe. Only publish software you are authorized to distribute. Before public launch, add automated malware scanning, rate limiting, audit logs, stronger upload validation, backups, and monitoring. This project is a working starter application, not a certified secure download marketplace.
