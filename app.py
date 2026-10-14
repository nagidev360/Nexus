import os, secrets, json, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
BASE_DIR=Path(__file__).resolve().parent
UPLOAD_DIR=Path(os.environ.get("UPLOAD_DIR","/var/data/uploads" if os.path.isdir("/var/data") else BASE_DIR/"uploads"));UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
ALLOWED={"apk","exe","msi","zip"}
app=Flask(__name__);app.config["SECRET_KEY"]=os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["SQLALCHEMY_DATABASE_URI"]=(os.environ.get("DATABASE_URL","").replace("postgres://","postgresql://",1) or "sqlite:///"+str(BASE_DIR/"nexus.db"));app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]=False;app.config["MAX_CONTENT_LENGTH"]=500*1024*1024;app.config["SESSION_COOKIE_HTTPONLY"]=True;app.config["SESSION_COOKIE_SAMESITE"]="Lax";app.config["SESSION_COOKIE_SECURE"]=os.environ.get("RENDER","")=="true";app.config["PERMANENT_SESSION_LIFETIME"]=timedelta(days=14);app.config["SESSION_REFRESH_EACH_REQUEST"]=True;db=SQLAlchemy(app)
class AppItem(db.Model):
 id=db.Column(db.Integer,primary_key=True);name=db.Column(db.String(120),nullable=False);slug=db.Column(db.String(160),unique=True,nullable=False);description=db.Column(db.Text,nullable=False,default="");platform=db.Column(db.String(20),nullable=False,default="Android");version=db.Column(db.String(40),nullable=False,default="1.0.0");filename=db.Column(db.String(255),nullable=False);downloads=db.Column(db.Integer,nullable=False,default=0);created_at=db.Column(db.DateTime,default=datetime.utcnow);publisher=db.Column(db.String(160),nullable=True);category=db.Column(db.String(100),nullable=True);icon_url=db.Column(db.String(1000),nullable=True);mod_info=db.Column(db.String(300),nullable=True);play_store_url=db.Column(db.String(1000),nullable=True)
with app.app_context():
 db.create_all()
 # Add optional metadata columns to existing installations without dropping or rewriting records.
 from sqlalchemy import inspect
 existing={col["name"] for col in inspect(db.engine).get_columns("app_item")}
 for column, sql_type in (("publisher","VARCHAR(160)"),("category","VARCHAR(100)"),("icon_url","VARCHAR(1000)"),("mod_info","VARCHAR(300)"),("play_store_url","VARCHAR(1000)")):
  if column not in existing:
   with db.engine.begin() as conn: conn.exec_driver_sql(f"ALTER TABLE app_item ADD COLUMN {column} {sql_type}")
def admin_required(fn):
 @wraps(fn)
 def wrapped(*a,**kw):
  if not session.get("is_admin"): return redirect(url_for("admin_login",next=request.path))
  return fn(*a,**kw)
 return wrapped
def csrf_token():
 token=session.get("_csrf_token")
 if not token: token=secrets.token_urlsafe(32);session["_csrf_token"]=token
 return token
@app.before_request
def protect_post_requests():
 if request.method=="POST":
  expected=session.get("_csrf_token","");supplied=request.form.get("_csrf_token","")
  if not expected or not supplied or not secrets.compare_digest(expected,supplied): abort(400,description="Your form session expired. Refresh the page and try again.")
@app.context_processor
def inject_globals():
 return {"site_name":"Nexus","admin_logged_in":bool(session.get("is_admin")),"csrf_token":csrf_token,"supabase_url":os.environ.get("SUPABASE_URL","").rstrip("/"),"supabase_publishable_key":os.environ.get("SUPABASE_PUBLISHABLE_KEY","")}
@app.route("/")
def index():
 term=request.args.get("q","").strip();platform=request.args.get("platform","").strip();query=AppItem.query
 if term: query=query.filter(db.or_(AppItem.name.ilike(f"%{term}%"),AppItem.description.ilike(f"%{term}%")))
 if platform in ("Android","Windows"): query=query.filter_by(platform=platform)
 return render_template("index.html",items=query.order_by(AppItem.created_at.desc()).all(),q=term,platform=platform)
@app.route("/app/<int:item_id>")
def detail(item_id):
 item=db.get_or_404(AppItem,item_id)
 path=UPLOAD_DIR/item.filename
 return render_template("detail.html",item=item,file_size=path.stat().st_size if path.is_file() else None)
@app.route("/download/<int:item_id>")
def download(item_id):
 item=db.get_or_404(AppItem,item_id);path=UPLOAD_DIR/item.filename
 if not path.is_file(): abort(404)
 item.downloads+=1;db.session.commit();return send_from_directory(UPLOAD_DIR,item.filename,as_attachment=True,download_name=secure_filename(item.filename))
@app.route("/login")
@app.route("/signup")
def user_auth(): return render_template("auth_login.html")
@app.route("/profile")
def profile(): return render_template("profile.html")
@app.route("/auth/callback")
def auth_callback(): return render_template("auth_callback.html")
@app.route("/admin",methods=["GET","POST"])
def admin_login():
 if session.get("is_admin"): return redirect(url_for("admin_dashboard"))
 if request.method=="POST":
  expected=os.environ.get("ADMIN_PASSWORD")
  if not expected: flash("Admin password is not configured. Set ADMIN_PASSWORD in Render environment settings.","error")
  elif secrets.compare_digest(request.form.get("password",""),expected): session["is_admin"]=True;session.permanent=True;return redirect(url_for("admin_dashboard"))
  else: flash("Incorrect password.","error")
 return render_template("login.html")
@app.post("/admin/supabase-login")
def admin_supabase_login():
 token=request.form.get("access_token","").strip()
 supabase_url=os.environ.get("SUPABASE_URL","").rstrip("/")
 supabase_key=os.environ.get("SUPABASE_PUBLISHABLE_KEY","")
 super_admin_email=os.environ.get("SUPER_ADMIN_EMAIL","").strip().casefold()
 if not token or not supabase_url or not supabase_key or not super_admin_email:
  flash("Super-admin login is not configured. Contact the site owner.","error")
  return redirect(url_for("admin_login"))
 try:
  req=urllib.request.Request(supabase_url+"/auth/v1/user",headers={"apikey":supabase_key,"Authorization":"Bearer "+token,"Accept":"application/json"})
  with urllib.request.urlopen(req,timeout=8) as response:
   user=json.loads(response.read().decode("utf-8"))
  verified_email=str(user.get("email","")).casefold()
  if not user.get("id") or verified_email != super_admin_email or not user.get("email_confirmed_at"):
   abort(403)
  session.clear()
  session["is_admin"]=True
  session["admin_role"]="super_admin"
  session["admin_user_id"]=user["id"]
  session["admin_email"]=verified_email
  session.permanent=True
  return redirect(url_for("admin_dashboard"))
 except urllib.error.HTTPError:
  flash("Your Nexus session could not be verified. Please sign in again.","error")
 except (urllib.error.URLError,TimeoutError,ValueError):
  flash("Could not verify your Nexus account right now. Try again.","error")
 return redirect(url_for("admin_login"))
@app.route("/admin/dashboard",methods=["GET","POST"])
@admin_required
def admin_dashboard():
 if request.method=="POST":
  file=request.files.get("file");name=request.form.get("name","").strip();ext=(file.filename.rsplit(".",1)[-1].lower() if file and "." in file.filename else "")
  if not name or not file or not file.filename or ext not in ALLOWED: flash("Enter an app name and upload APK, EXE, MSI, or ZIP file.","error");return redirect(url_for("admin_dashboard"))
  # Use the app title for a readable stored filename instead of a random hash or client filename.
  extension=ext
  base=secure_filename(name)[:100].strip("._-") or "app"
  stored=f"{base}.{extension}"
  suffix=2
  while (UPLOAD_DIR/stored).exists():
   stored=f"{base}-{suffix}.{extension}"
   suffix+=1
  file.save(UPLOAD_DIR/stored)
  item=AppItem(name=name[:120],slug=secrets.token_hex(5),description=request.form.get("description","")[:5000],platform=request.form.get("platform","Android") if request.form.get("platform") in ("Android","Windows") else "Android",version=request.form.get("version","1.0.0")[:40],filename=stored,publisher=request.form.get("publisher","").strip()[:160] or None,category=request.form.get("category","").strip()[:100] or None,icon_url=request.form.get("icon_url","").strip()[:1000] or None,mod_info=request.form.get("mod_info","").strip()[:300] or None,play_store_url=request.form.get("play_store_url","").strip()[:1000] or None)
  db.session.add(item);db.session.commit();flash("Upload published.","success");return redirect(url_for("admin_dashboard"))
 return render_template("admin.html",items=AppItem.query.order_by(AppItem.created_at.desc()).all())
@app.post("/admin/delete/<int:item_id>")
@admin_required
def delete_item(item_id):
 item=db.get_or_404(AppItem,item_id)
 try:(UPLOAD_DIR/item.filename).unlink(missing_ok=True)
 finally: db.session.delete(item);db.session.commit()
 flash("Listing deleted.","success");return redirect(url_for("admin_dashboard"))
@app.route("/admin/logout",methods=["POST"])
def admin_logout():
 if not session.get("is_admin"): abort(403)
 session.clear();return redirect(url_for("index"))
@app.errorhandler(400)
def bad_request(e): return render_template("error.html",code=400,message=getattr(e,"description","Bad request.")),400
@app.errorhandler(403)
def forbidden(_): return render_template("error.html",code=403,message="You do not have permission to access this page."),403
@app.errorhandler(404)
def not_found(_): return render_template("error.html",code=404,message="We could not find that page or download."),404
@app.errorhandler(413)
def too_large(_): return render_template("error.html",code=413,message="File too large. Maximum upload size is 500 MB."),413
@app.route("/health")
def health():
 try: db.session.execute(db.text("SELECT 1"));database="ok"
 except Exception: db.session.rollback();database="error"
 return {"status":"ok" if database=="ok" else "degraded","app":"Nexus","database":database}