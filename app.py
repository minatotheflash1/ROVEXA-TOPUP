import os
import time
import random
import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__, template_folder='.')

# --- Database Config ---
db_url = os.getenv("DATABASE_URL")
if db_url:
    # Force pure-Python pg8000 driver to prevent libpq.so.5 crash on Railway
    if db_url.startswith("postgres://"): 
        db_url = db_url.replace("postgres://", "postgresql+pg8000://", 1)
    elif db_url.startswith("postgresql://") and "pg8000" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+pg8000://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url or "sqlite:///rovexa_pro_final.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "rovexa_ultimate_99")

# EI LINE TA MISSING CHILO!
db = SQLAlchemy(app) 

# --- Database Models (With Custom Tablenames to bypass Old DB Conflicts) ---
class User(db.Model):
    __tablename__ = 'users_premium_v1'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    membership = db.Column(db.String(20), default='BRONZE') 
    is_verified = db.Column(db.Boolean, default=False)
    verify_code = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class OrderV4(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False)
    game_type = db.Column(db.String(50), nullable=False)
    player_id = db.Column(db.String(100), nullable=False)
    player_name = db.Column(db.String(100), nullable=False)
    package_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.String(20), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    sender_number = db.Column(db.String(20), nullable=False)
    trx_id = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='Pending') 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FundHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(50))
    status = db.Column(db.String(20), default='Completed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context(): 
    db.create_all()

# --- Configurations ---
MEMBERSHIP_DATA = {
    'BRONZE': {'discount': 0.01, 'price': 50, 'badge': '🥉'},
    'SILVER': {'discount': 0.02, 'price': 100, 'badge': '🥈'},
    'GOLD': {'discount': 0.04, 'price': 200, 'badge': '🥇'},
    'ELITE': {'discount': 0.10, 'price': 300, 'badge': '💎'},
    'OWNER': {'discount': 0.15, 'price': 0, 'badge': '👑'}
}

PACKAGES = {
    "freefire": [
        {"id": "ff_115", "name": "115 Diamonds", "price": 84, "icon": "💎"},
        {"id": "ff_240", "name": "240 Diamonds", "price": 169, "icon": "💎"},
        {"id": "ff_mo", "name": "Monthly Pass", "price": 799, "icon": "👑"}
    ],
    "pubg": [
        {"id": "pubg_60", "name": "60 UC", "price": 90, "icon": "🪙"},
        {"id": "pubg_325", "name": "325 UC", "price": 450, "icon": "🪙"}
    ]
}

def get_package_by_id(pkg_id):
    for game, pkgs in PACKAGES.items():
        for p in pkgs:
            if p['id'] == pkg_id: return p, game
    return None, None

def send_otp_email(receiver_email, code):
    sender = os.getenv("SMTP_EMAIL", "your_email@gmail.com") 
    password = os.getenv("SMTP_PASSWORD", "your_app_password")
    if sender == "your_email@gmail.com":
        print(f"\n[MOCK EMAIL] To: {receiver_email} | OTP CODE: {code}\n")
        return True 
    try:
        msg = MIMEText(f"Welcome to ROVEXA! Your code is: {code}")
        msg['Subject'] = 'ROVEXA - Verify Your Email'
        msg['From'] = f"ROVEXA ESPORTS <{sender}>"
        msg['To'] = receiver_email
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        return False

# --- Routes ---
@app.route('/')
def index():
    user = User.query.filter_by(email=session.get('user_email')).first() if 'user_email' in session else None
    return render_template('index.html', packages=PACKAGES, user=user, m_data=MEMBERSHIP_DATA)

@app.route('/check_uid', methods=['POST'])
def check_uid():
    uid = request.json.get('uid')
    if not uid: return jsonify({"success": False, "msg": "Invalid Game UID!"})
    time.sleep(1)
    return jsonify({"success": True, "name": f"ROVEXA_{uid[-4:]} 亗"})

# --- Authentication ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email').lower()
        if email == "mdananto01@gmail.com": return render_template('register.html', error="Admin must login directly!")
        if User.query.filter_by(email=email).first() or User.query.filter_by(username=request.form.get('username')).first():
            return render_template('register.html', error="Email or Username already exists!")
        
        otp = str(random.randint(100000, 999999))
        new_user = User(name=request.form.get('name'), username=request.form.get('username'), email=email, password=generate_password_hash(request.form.get('password')), verify_code=otp)
        db.session.add(new_user)
        db.session.commit()
        send_otp_email(email, otp)
        session['temp_email'] = email
        return redirect(url_for('verify'))
    return render_template('register.html')

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    email = session.get('temp_email')
    if not email: return redirect(url_for('register'))
    if request.method == 'POST':
        user = User.query.filter_by(email=email).first()
        if user and user.verify_code == request.form.get('code'):
            user.is_verified = True
            user.verify_code = None
            db.session.commit()
            session.pop('temp_email', None)
            session['user_email'] = user.email
            return redirect(url_for('index'))
        return render_template('verify.html', email=email, error="Invalid OTP Code!")
    return render_template('verify.html', email=email)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, pw = request.form.get('email').lower(), request.form.get('password')
        
        # Hardcoded Admin Logic
        if email == "mdananto01@gmail.com" and pw == "Ananto01@$":
            u = User.query.filter_by(email=email).first()
            if not u:
                u = User(name="Ananto", username="owner", email=email, password=generate_password_hash(pw), membership='OWNER', is_verified=True)
                db.session.add(u)
                db.session.commit()
            session['user_email'] = u.email
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))

        u = User.query.filter_by(email=email).first()
        if u and check_password_hash(u.password, pw):
            if not u.is_verified:
                session['temp_email'] = u.email
                otp = str(random.randint(100000, 999999))
                u.verify_code = otp
                db.session.commit()
                send_otp_email(u.email, otp)
                return redirect(url_for('verify'))
            session['user_email'] = u.email
            return redirect(url_for('index'))
        return render_template('login.html', error="Incorrect Email or Password!")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/profile')
def profile():
    if 'user_email' not in session: return redirect(url_for('login'))
    user = User.query.filter_by(email=session['user_email']).first()
    orders = OrderV4.query.filter_by(user_email=user.email).order_by(OrderV4.created_at.desc()).all()
    funds = FundHistory.query.filter_by(user_email=user.email).order_by(FundHistory.created_at.desc()).all()
    return render_template('profile.html', user=user, orders=orders, funds=funds, badge=MEMBERSHIP_DATA[user.membership]['badge'])

# --- Checkout & Orders ---
@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_email' not in session: return redirect(url_for('login'))
    user = User.query.filter_by(email=session['user_email']).first()
    pkg, game = get_package_by_id(request.form.get('package_id'))
    if not pkg: return redirect(url_for('index'))
    discount_pct = MEMBERSHIP_DATA[user.membership]['discount'] * 100
    return render_template('checkout.html', pkg=pkg, game=game, uid=request.form.get('player_id'), uname=request.form.get('player_name'), discount=discount_pct)

@app.route('/submit_order', methods=['POST'])
def submit_order():
    if 'user_email' not in session: return redirect(url_for('login'))
    db.session.add(OrderV4(
        user_email=session['user_email'], game_type=request.form.get('game_type'), player_id=request.form.get('player_id'), 
        player_name=request.form.get('player_name'), package_name=request.form.get('package_name'), 
        price=request.form.get('final_price'), payment_method=request.form.get('payment_method'),
        sender_number=request.form.get('sender_number'), trx_id=request.form.get('trx_id')
    ))
    db.session.commit()
    return redirect(url_for('profile'))

# --- Admin Panel ---
@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'): return redirect(url_for('login'))
    orders = OrderV4.query.order_by(OrderV4.created_at.desc()).all()
    revenue = sum([int(float(''.join(c for c in o.price if c.isdigit() or c == '.'))) for o in orders if o.status == 'Completed' and any(c.isdigit() for c in o.price)])
    return render_template('admin.html', orders=orders, total=len(orders), pending=sum(1 for o in orders if o.status == 'Pending'), revenue=revenue)

@app.route('/order-action/<int:id>/<action>')
def order_action(id, action):
    if session.get('admin_logged_in'):
        order = OrderV4.query.get(id)
        if order: 
            order.status = "Completed" if action == "complete" else "Rejected"
            db.session.commit()
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__': app.run(debug=True)
