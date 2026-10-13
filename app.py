import os, secrets
from pathlib import Path
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/var/data/uploads" if os.path.isdir("/var/data") else BASE_DIR / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED = {"apk", "exe", "msi", "zip"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["SQLALCHEMY_DATABASE_URI"] = (os.environ.get("DATABASE_URL", "").replace("postgres://", "postgresql://", 1) or "sqlite:///" + str(BASE_DIR / "nexus.db"))
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("RENDER", "") == "true"
db = SQLAlchemy(app)

class AppItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(160), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    platform = db.Column(db.String(20), nullable=False, default="Android")
    version = db.Column(db.String(40), nullable=False, default="1.0.0")
    filename = db.Column(db.String(255), nullable=False)
    downloads = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped

def csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token

@app.before_request
def protect_post_requests():
    if request.method == "POST":
        expected = session.get("_csrf_token", "")
        supplied = request.form.get("_csrf_token", "")
        if not expected or not supplied or not secrets.compare_digest(expected, supplied):
            abort(400, description="Your form session expired. Refresh the page and try again.")

@app.context_processor
def inject_globals():
    return {
        "site_name": "Nexus",
        "admin_logged_in": bool(session.get("is_admin")),
        "csrf_token": csrf_token,
        "supabase_url": os.environ.get("SUPABASE_URL", "").rstrip("/"),
        "supabase_publishable_key": os.environ.get("SUPABASE_PUBLISHABLE_KEY", ""),
    }

@app.route("/")
def index():
    term = request.args.get("q", "").strip()
    platform = request.args.get("platform", "").strip()
    query = AppItem.query
    if term:
        query = query.filter(db.or_(AppItem.name.ilike(f"%{term}%"), AppItem.description.ilike(f"%{term}%")))
    if platform in ("Android", "Windows"):
        query = query.filter_by(platform=platform)
    items = query.order_by(AppItem.created_at.desc()).all()
    return render_template("index.html", items=items, q=term, platform=platform)

@app.route("/app/<int:item_id>")
def detail(item_id):
    item = db.get_or_404(AppItem, item_id)
    return render_template("detail.html", item=item)

@app.route("/download/<int:item_id>")
def download(item_id):
    item = db.get_or_404(AppItem, item_id)
    path = UPLOAD_DIR / item.filename
    if not path.is_file():
        abort(404)
    item.downloads += 1
    db.session.commit()
    return send_from_directory(UPLOAD_DIR, item.filename, as_attachment=True, download_name=secure_filename(item.filename))

@app.route("/login")
def user_login():
    return render_template("auth_login.html")

@app.route("/signup")
def user_signup():
    return render_template("auth_signup.html")

@app.route("/auth/callback")
def auth_callback():
    return render_template("auth_callback.html")

@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        expected = os.environ.get("ADMIN_PASSWORD")
        if not expected:
            flash("Admin password is not configured. Set ADMIN_PASSWORD in Render environment settings.", "error")
        elif secrets.compare_digest(request.form.get("password", ""), expected):
            session["is_admin"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Incorrect password.", "error")
    return render_template("login.html")

@app.route("/admin/dashboard", methods=["GET", "POST"])
@admin_required
def admin_dashboard():
    if request.method == "POST":
        file = request.files.get("file")
        name = request.form.get("name", "").strip()
        ext = (file.filename.rsplit(".", 1)[-1].lower() if file and "." in file.filename else "")
        if not name or not file or not file.filename or ext not in ALLOWED:
            flash("Enter an app name and upload APK, EXE, MSI, or ZIP file.", "error")
            return redirect(url_for("admin_dashboard"))
        safe_name = secure_filename(file.filename)
        stored = secrets.token_hex(8) + "_" + safe_name
        file.save(UPLOAD_DIR / stored)
        slug = secrets.token_hex(5)
        item = AppItem(name=name[:120], slug=slug, description=request.form.get("description", "")[:5000],
                       platform=request.form.get("platform", "Android") if request.form.get("platform") in ("Android", "Windows") else "Android",
                       version=request.form.get("version", "1.0.0")[:40], filename=stored)
        db.session.add(item)
        db.session.commit()
        flash("Upload published.", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("admin.html", items=AppItem.query.order_by(AppItem.created_at.desc()).all())

@app.post("/admin/delete/<int:item_id>")
@admin_required
def delete_item(item_id):
    item = db.get_or_404(AppItem, item_id)
    try:
        (UPLOAD_DIR / item.filename).unlink(missing_ok=True)
    finally:
        db.session.delete(item)
        db.session.commit()
    flash("Listing deleted.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    if not session.get("is_admin"):
        abort(403)
    session.clear()
    return redirect(url_for("index"))

@app.errorhandler(400)
def bad_request(error):
    return (render_template("error.html", code=400, message=getattr(error, "description", "Bad request.")), 400)

@app.errorhandler(403)
def forbidden(_):
    return (render_template("error.html", code=403, message="You do not have permission to access this page."), 403)

@app.errorhandler(404)
def not_found(_):
    return (render_template("error.html", code=404, message="We could not find that page or download."), 404)

@app.errorhandler(413)
def too_large(_):
    return (render_template("error.html", code=413, message="File too large. Maximum upload size is 500 MB."), 413)

@app.route("/health")
def health():
    try:
        db.session.execute(db.text("SELECT 1"))
        database = "ok"
    except Exception:
        db.session.rollback()
        database = "error"
    return {"status": "ok" if database == "ok" else "degraded", "app": "Nexus", "database": database}
