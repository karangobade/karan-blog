from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
import cloudinary
import cloudinary.uploader
from datetime import datetime

import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "connect_args": {
        "ssl": {"ssl_mode": "REQUIRED"}
    }
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = os.getenv("EMAIL_USER")
app.config['MAIL_PASSWORD'] = os.getenv("EMAIL_PASS")

app.secret_key = os.getenv("SECRET_KEY")
mail = Mail(app)

class Contact(db.Model):
    __tablename__ = "contact"
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(120), nullable=False)
    email=db.Column(db.Text(20), nullable=False)
    msg=db.Column(db.Text(500), nullable=False)
    

class Post(db.Model):
    __tablename__ = "post"
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    slug = db.Column(db.String(500), nullable=False, unique=True)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    excerpt = db.Column(db.String(500), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    



# ---------- ROUTES ----------

@app.route("/")
def home():
    posts = Post.query.all()
    return render_template("home.html", posts=posts)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        msg = request.form.get("msg")
        new_c=Contact(name=name,email=email,msg=msg)
        db.session.add(new_c)
        db.session.commit()
        flash("Thanks for reaching out! I'll get back to you soon.", "success")
        mail.send_message(f"New message from {name}",
                              sender=email,
                              recipients=[os.getenv("EMAIL_USER")],
                              body=msg + "\n\nSent by: " + name + "\nEmail: " + email + "\msg: "+msg
                              )
        return redirect(url_for("contact"))
    
    return render_template("contact.html")

@app.route("/post")
def posts():
    posts = Post.query.all()
    return render_template("posts.html", posts=posts)

@app.route("/post/<string:post_slug>", methods=["GET"])
def post(post_slug):
    found = Post.query.filter_by(slug=post_slug).first()
    return render_template("post.html", post=found)


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" in session:
        posts = Post.query.all()
        return render_template("dashboard.html", posts=posts)
    else:
        return redirect(url_for("login"))
@app.route("/edit/<int:sno>", methods=["GET", "POST"])
def edit(sno):
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        slug = request.form.get("slug")
        date_str = request.form.get("date")
        excerpt = request.form.get("excerpt")
        image_file = request.files.get("image")
        image_url = None
        if image_file and image_file.filename != "":
            upload_result = cloudinary.uploader.upload(image_file, folder="karan_blog")
            image_url = upload_result["secure_url"]

        if date_str:
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    date = datetime.utcnow()
        else:
            date = datetime.utcnow()

        if sno == 0:
            post = Post(
                title=title, content=content, slug=slug,
                date=date,excerpt=excerpt, image_url=image_url
            )
            db.session.add(post)
            db.session.commit()
            return redirect(url_for("dashboard"))
        else:
            post = Post.query.filter_by(sno=sno).first()
            post.title = title
            post.content = content
            post.slug = slug
            post.date = date
            post.excerpt = excerpt
            if image_url:
                post.image_url = image_url
            db.session.commit()
            return redirect(url_for("dashboard"))

    post = Post.query.filter_by(sno=sno).first() if sno != 0 else None
    return render_template('edit.html', post=post, sno=sno)

@app.route("/delete/<int:sno>")
def delete(sno):
    if "user" not in session:
        return redirect(url_for("login"))

    post = Post.query.filter_by(sno=sno).first()
    if post:
        db.session.delete(post)
        db.session.commit()
        flash("Post deleted successfully.", "success")
    else:
        flash("Post not found.", "error")

    return redirect(url_for("dashboard"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form.get("name")
        passa = request.form.get("passa")
        
        
        if name ==os.getenv("ADMIN_USERNAME") and passa==os.getenv("ADMIN_PASSWORD"):
            flash("Logged in successfully!", "success")
            session["user"]="admin"
            return redirect(url_for("dashboard"))
        else:
            flash("don't try to login its only admin access", "error")
            return redirect(url_for("login"))   
         
    return render_template("login.html")



@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out.", "info")
    return redirect(url_for("home"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)