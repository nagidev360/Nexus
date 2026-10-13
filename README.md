# Nexus

Nexus is a Flask-based download catalog for Android APKs and Windows software.

## Features
- Searchable Android and Windows catalog
- App details and download counters
- Admin login and upload/delete dashboard
- Upload support for APK, EXE, MSI, ZIP (500 MB maximum)
- SQLite by default; PostgreSQL via DATABASE_URL
- Render deployment blueprint and health endpoint

## Run locally
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
set ADMIN_PASSWORD=change-this-password
python -m flask --app app run
```
Open http://127.0.0.1:5000 and visit /admin to manage uploads.

## Render deployment
1. Connect this repository to Render and create a Python web service.
2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn app:app`
4. Set `ADMIN_PASSWORD` to a strong unique secret. Set `SECRET_KEY` to a long random value if not auto-generated.
5. Configure a persistent disk mounted at `/var/data` and keep uploads there. For reliable production use, configure managed PostgreSQL in `DATABASE_URL` and object storage for downloads.

## Security notes
- File extension checks are not malware scanning. Scan uploads before publishing and only distribute files you have rights to share.
- Never commit passwords or API keys.
- SQLite and local uploads are not durable on ephemeral hosting unless stored on a persistent disk.
- For a public production service, add rate limiting, CSRF protection, audit logs, and an actual malware scanning pipeline before accepting public uploads.
