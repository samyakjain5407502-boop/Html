import os
import re
import json
import time
import secrets
import sqlite3
from datetime import timedelta, datetime, date
from functools import wraps
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash, send_from_directory, g
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import jwt
from dotenv import load_dotenv

# Load environment variables from .env file if present (local development).
# In production, set real environment variables in the hosting dashboard.
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Allow tests / deployments to override the database location via environment.
DB_PATH = os.environ.get('JAINZEE_DB_PATH', os.path.join(BASE_DIR, 'jainzee.db'))
# PostgreSQL-ready configuration: set DATABASE_URL in production to use
# Postgres; leave unset (or use JAINZEE_DB_PATH) for local SQLite development.
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
USE_POSTGRES = DATABASE_URL.startswith(('postgres://', 'postgresql://'))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'mp4', 'webm', 'mov', 'avi'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'mov', 'avi'}

app = Flask(__name__)
# SECURITY: SECRET_KEY must come from the environment. In development (no
# SECRET_KEY set) a random key is generated for the current process; set
# SECRET_KEY in production so sessions survive restarts.
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
if not os.environ.get('SECRET_KEY'):
    print('[WARNING] SECRET_KEY environment variable is not set. '
          'Using a random temporary key - sessions will not survive restarts. '
          'Set SECRET_KEY before deploying to production.')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
# Keep customer & admin logged in for 30 days (persistent sessions)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- DATABASE HELPERS ----------------
# Supports SQLite locally (default) and PostgreSQL via DATABASE_URL.
# The wrapper below translates the small amount of SQLite-specific SQL used
# by the app (PRAGMA table_info, INSERT OR IGNORE/REPLACE, ? placeholders)
# so the same code runs on both engines.

class PostgresConnection:
    """Thin compatibility wrapper over psycopg2 mimicking the sqlite3 API."""

    def __init__(self, conn):
        self._conn = conn

    @staticmethod
    def _translate(sql):
        s = sql.strip()
        if s.upper().startswith('PRAGMA TABLE_INFO'):
            table = s.split('(')[1].rstrip(') ').strip()
            return ('__COLUMNS__', table)
        s = s.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
        s = s.replace('MAX(stock - ?, 0)', 'GREATEST(stock - ?, 0)')
        s = s.replace(
            'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
            'INSERT INTO settings (key, value) VALUES (?, ?) '
            'ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value')
        if s.upper().startswith('INSERT OR IGNORE'):
            s = s.replace('INSERT OR IGNORE', 'INSERT', 1) + ' ON CONFLICT DO NOTHING'
        elif s.upper().startswith('INSERT') and 'RETURNING' not in s.upper():
            s += ' RETURNING id'
        return (s.replace('?', '%s'), None)

    def _columns(self, table):
        cur = self._conn.cursor()
        cur.execute(
            "SELECT column_name AS name FROM information_schema.columns "
            "WHERE table_name = %s", (table,))
        return [dict(r) for r in cur.fetchall()]

    def execute(self, sql, params=()):
        translated, special = self._translate(sql)
        cur = self._conn.cursor()
        if special == '__COLUMNS__' or special:
            self._last_columns = self._columns(special) if special else []
            return _CursorStub(self._last_columns)
        cur.execute(translated, params)
        if translated.upper().startswith('INSERT'):
            row = cur.fetchone()
            if row:
                cur.lastrowid = list(row.values())[0]
        return cur

    def executescript(self, script):
        for statement in script.split(';'):
            if statement.strip():
                self.execute(statement)

    def executemany(self, sql, seq):
        for params in seq:
            self.execute(sql, params)

    def commit(self): self._conn.commit()
    def rollback(self): self._conn.rollback()
    def close(self): self._conn.close()

    # Context-manager compatibility (not used, but harmless)
    def __enter__(self): return self
    def __exit__(self, *a): self.close()


class _CursorStub:
    def __init__(self, rows): self._rows = rows

    def fetchone(self): return self._rows[0] if self._rows else None
    def fetchall(self): return self._rows
    def __iter__(self): return iter(self._rows)


def get_db():
    if USE_POSTGRES:
        import psycopg2
        import psycopg2.extras
        url = DATABASE_URL
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
        conn = psycopg2.connect(url)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return PostgresConnection(conn)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_en TEXT NOT NULL UNIQUE,
            name_hi TEXT NOT NULL,
            price TEXT,
            weight TEXT,
            description_en TEXT,
            description_hi TEXT,
            image TEXT DEFAULT '',
            stock INTEGER DEFAULT 0,
            old_price TEXT DEFAULT '',
            sku TEXT DEFAULT '',
            video TEXT DEFAULT '',
            grades TEXT DEFAULT '[]'
        );
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            email TEXT DEFAULT '',
            address TEXT DEFAULT '',
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            customer_name TEXT,
            customer_phone TEXT,
            customer_address TEXT,
            items TEXT,
            total TEXT,
            status TEXT DEFAULT 'pending',
            is_hidden INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
    ''')

    # Create product_media table for admin product photo/video uploads
    cur.execute('''CREATE TABLE IF NOT EXISTS product_media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        url TEXT,
        type TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(id)
    )''')

    # Create general_media table for factory/company media
    cur.execute('''CREATE TABLE IF NOT EXISTS general_media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        category TEXT,
        type TEXT,
        url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Create product_reviews table for customer reviews and ratings
    cur.execute('''CREATE TABLE IF NOT EXISTS product_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        customer_name TEXT NOT NULL,
        customer_phone TEXT NOT NULL,
        rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
        review_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    )''')

    # Migration: Add missing columns to existing products table (older DB versions)
    cur.execute("PRAGMA table_info(products)")
    existing_cols = [(row['name'] if isinstance(row, dict) else row[1]) for row in cur.fetchall()]
    migration_cols = {
        'stock': 'INTEGER DEFAULT 0',
        'old_price': "TEXT DEFAULT ''",
        'sku': "TEXT DEFAULT ''",
        'image': "TEXT DEFAULT ''",
        'video': "TEXT DEFAULT ''",
        'grades': "TEXT DEFAULT '[]'",
    }
    for col, col_def in migration_cols.items():
        if col not in existing_cols:
            try:
                cur.execute(f"ALTER TABLE products ADD COLUMN {col} {col_def}")
            except sqlite3.OperationalError:
                pass  # Column already exists
    
    # Migration: Add is_hidden column to orders table if it doesn't exist
    cur.execute("PRAGMA table_info(orders)")
    order_cols = [(row['name'] if isinstance(row, dict) else row[1]) for row in cur.fetchall()]
    order_migration_cols = {
        'is_hidden': 'INTEGER DEFAULT 0',
        'subtotal': "TEXT DEFAULT ''",
        'discount_amount': "TEXT DEFAULT ''",
        'shipping_charge': "TEXT DEFAULT '0'",
        'coupon_code': "TEXT DEFAULT ''",
    }
    for col, col_def in order_migration_cols.items():
        if col not in order_cols:
            try:
                cur.execute(f"ALTER TABLE orders ADD COLUMN {col} {col_def}")
            except Exception:
                pass  # Column already exists

    # Coupon management table
    cur.execute('''CREATE TABLE IF NOT EXISTS coupons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        discount_type TEXT NOT NULL DEFAULT 'percent',
        discount_value TEXT NOT NULL DEFAULT '0',
        expiry_date TEXT DEFAULT '',
        min_order_amount TEXT DEFAULT '0',
        is_active INTEGER DEFAULT 1,
        usage_limit INTEGER DEFAULT 0,
        used_count INTEGER DEFAULT 0
    )''')

    # Wishlist table (one row per customer+product)
    cur.execute('''CREATE TABLE IF NOT EXISTS wishlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (product_id) REFERENCES products(id),
        UNIQUE (customer_id, product_id)
    )''')

    # One review per customer per product
    try:
        cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_reviews_unique '
                    'ON product_reviews (product_id, customer_phone)')
    except Exception:
        pass  # Index already exists (or duplicates remain, handled below)

    # SECURITY: the admin password is set via the ADMIN_PASSWORD environment
    # variable. If not configured, a strong random password is generated and
    # printed ONCE to the server console - no hard-coded default exists.
    admin_password = os.environ.get('ADMIN_PASSWORD')
    pw_row = cur.execute("SELECT value FROM settings WHERE key='password_hash'").fetchone()
    needs_new_hash = False
    if pw_row is None:
        needs_new_hash = True
    elif not admin_password and check_password_hash(pw_row['value'], 'jainzee123'):
        # Migrate away from the legacy hard-coded default password
        needs_new_hash = True
    if needs_new_hash:
        if not admin_password:
            admin_password = secrets.token_urlsafe(12)
            print('=' * 60)
            print('ADMIN PASSWORD (generated, shown once - change it after login):')
            print(f'  {admin_password}')
            print('Set the ADMIN_PASSWORD environment variable to choose your own.')
            print('=' * 60)
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('password_hash', ?)",
                    (generate_password_hash(admin_password),))

    default_settings = {
        'shop_name_en': 'Jainzee Food Processing Industries',
        'shop_name_hi': 'जैनज़ी फूड प्रोसेसिंग इंडस्ट्रीज़',
        'tagline_en': 'Pure & Premium Dry Fruits',
        'tagline_hi': 'शुद्ध और प्रीमियम ड्राई फ्रूट्स',
        'address_en': 'Siyaganj, Indore, Madhya Pradesh 452001',
        'address_hi': 'सियागंज, इंदौर, मध्य प्रदेश 452001',
        'phone': '+91 98260 00000',
        'whatsapp': '919826000000',
        'email': 'info@jainzee.in',
        'hours_en': 'Mon - Sun: 10:00 AM - 9:00 PM',
        'hours_hi': 'सोम - रवि: सुबह 10:00 - रात 9:00',
        'about_en': 'Jainzee Food Processing Industries is a trusted name for pure, hygienic and premium quality dry fruits. We source the finest cashews, pistachios, almonds, walnuts and raisins so you can enjoy nature\'s best, every single day.',
        'about_hi': 'जैनज़ी फूड प्रोसेसिंग इंडस्ट्रीज़ शुद्ध, स्वच्छ और प्रीमियम गुणवत्ता वाले ड्राई फ्रूट्स के लिए एक विश्वसनीय नाम है। हम सबसे बेहतरीन काजू, पिस्ता, बादाम, अखरोट और किशमिश लाते हैं ताकि आप हर दिन प्रकृति का सर्वश्रेष्ठ आनंद ले सकें।',
        'logo': '',
        'global_discount': '0',
        'upi_id': '',
        'upi_qr_code': '',
        'homepage_video_url': '',
        'global_discount_percent': '0',
        'shipping_charge': '50',
        'free_shipping_min': '1000'
    }
    for k, v in default_settings.items():
        cur.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (k, v))

    cur.executemany(
        '''INSERT OR IGNORE INTO products (name_en, name_hi, price, weight, description_en, description_hi, image, stock, old_price, sku)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        [
            ('Premium Cashew', 'प्रीमियम काजू', '₹1,200', '500g / 1kg',
             'Large, creamy and perfectly roasted premium cashews. Rich in healthy fats and essential minerals.',
             'बड़े, क्रीमी और बेहतरीन रोस्टेड प्रीमियम काजू। स्वस्थ वसा और आवश्यक खनिजों से भरपूर।', '', 100, '₹1,500', 'CAS-001'),
            ('Pistachio', 'पिस्ता', '₹1,800', '250g / 500g',
             'Premium Iranian pistachios - crunchy, flavorful and naturally salted. A great source of protein and fiber.',
             'प्रीमियम ईरानी पिस्ता - कुरकुरे, स्वादिष्ट और प्राकृतिक नमकीन। प्रोटीन और फाइबर का बेहतरीन स्रोत।', '', 75, '₹2,000', 'PIS-001'),
            ('Almonds', 'बादाम', '₹900', '500g / 1kg',
             'California almonds, hand-sorted for uniform size. Perfect for daily nutrition and healthy snacking.',
             'हैंड-सॉर्टेड कैलिफोर्निया बादाम, एक समान आकार के। दैनिक पोषण और स्वस्थ नाश्ते के लिए उत्तम।', '', 150, '₹1,100', 'ALM-001'),
            ('Walnuts', 'अखरोट', '₹1,400', '250g / 500g',
             'Whole walnuts with light-colored kernels, rich in Omega-3 fatty acids and antioxidants.',
             'हल्के रंग की गिरी वाले साबुत अखरोट, ओमेगा-3 फैटी एसिड और एंटीऑक्सीडेंट से भरपूर।', '', 60, '₹1,600', 'WAL-001'),
            ('Raisins (Kishmish)', 'किशमिश', '₹350', '500g / 1kg',
             'Golden and black raisins, naturally sun-dried. Sweet, juicy and full of natural energy.',
             'गोल्डन और ब्लैक किशमिश, प्राकृतिक रूप से धूप में सुखाई गई। मीठी, रसीली और प्राकृतिक ऊर्जा से भरपूर।', '', 200, '₹400', 'RAI-001'),
        ]
    )
    conn.commit()
    conn.close()

# ---------------- AUTH ----------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ---------------- GLOBAL ADMIN ACCESS GUARD ----------------
# Every /admin/* route (including all /admin/api/* endpoints) requires an
# authenticated admin session. API routes get a JSON 401, pages redirect.

PUBLIC_ADMIN_ENDPOINTS = {'admin_login', 'admin_logout', 'static'}

@app.before_request
def admin_access_guard():
    if request.path.startswith('/admin'):
        endpoint = (request.endpoint or '').split('.')[0]
        if endpoint not in PUBLIC_ADMIN_ENDPOINTS and not session.get('admin_logged_in'):
            if request.path.startswith('/admin/api'):
                return jsonify({'error': 'Admin authentication required'}), 401
            return redirect(url_for('admin_login'))
    return None

# ---------------- CSRF PROTECTION ----------------
# Double-submit cookie pattern: a random token is stored in a cookie and must
# be echoed back (header X-CSRF-TOKEN or form field csrf_token) on every
# state-changing request (POST / PUT / DELETE). Disabled while TESTING.

@app.before_request
def csrf_protect():
    if app.config.get('TESTING'):
        return None
    if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
        token = request.headers.get('X-CSRF-TOKEN') or request.form.get('csrf_token') or ''
        cookie_token = request.cookies.get('csrf_token', '')
        if not token or not cookie_token or not secrets.compare_digest(token, cookie_token):
            return jsonify({'error': 'CSRF validation failed. Please refresh the page and try again.'}), 400
    return None

@app.after_request
def csrf_set_cookie(response):
    token = request.cookies.get('csrf_token') or getattr(g, 'csrf_token', None)
    if token:
        response.set_cookie('csrf_token', token, samesite='Lax', httponly=False)
    return response

def _csrf_token():
    """Return the CSRF token for the current request, creating one (via g)
    if the browser has not been issued a cookie yet."""
    token = request.cookies.get('csrf_token') or getattr(g, 'csrf_token', None)
    if not token:
        token = secrets.token_hex(32)
        g.csrf_token = token
    return token

@app.context_processor
def inject_csrf_token():
    # For plain HTML forms (e.g. admin login). JS fetches send the header via
    # static/js/csrf.js instead.
    return {'csrf_token': _csrf_token()}

# ---------------- LOGIN RATE LIMITING ----------------
# Simple in-memory sliding-window limiter: max 5 login attempts per IP per
# 5 minutes (applies to admin and customer logins/registration).

LOGIN_ATTEMPTS = {}
RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW = 300  # seconds


def _client_ip():
    return (request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
            or request.remote_addr or 'unknown')


def rate_limit_ok(scope):
    """Record an attempt for scope+IP; return False when over the limit."""
    key = f'{scope}:{_client_ip()}'
    now = time.time()
    attempts = [t for t in LOGIN_ATTEMPTS.get(key, []) if now - t < RATE_LIMIT_WINDOW]
    if len(attempts) >= RATE_LIMIT_MAX:
        LOGIN_ATTEMPTS[key] = attempts
        return False
    attempts.append(now)
    LOGIN_ATTEMPTS[key] = attempts
    return True


def rate_limit_clear(scope):
    LOGIN_ATTEMPTS.pop(f'{scope}:{_client_ip()}', None)



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------- JWT HELPERS ----------------

def _get_jwt_secret():
    """Return the JWT signing secret as clean UTF-8 text.

    Prefers the SECRET_KEY environment variable; falls back to the app
    secret key, then a default. Guarantees a non-empty str with no
    encoding artifacts, so PyJWT HMAC signing/verification is stable
    across restarts and environments.
    """
    raw = os.environ.get('SECRET_KEY') or app.secret_key
    if isinstance(raw, bytes):
        try:
            raw = raw.decode('utf-8')
        except UnicodeDecodeError:
            raw = raw.decode('utf-8', errors='replace')
    secret = str(raw).strip()
    if not secret:
        # Last resort: random per-process key (still never a hard-coded value)
        secret = secrets.token_hex(32)
    return secret


def generate_jwt_token(customer_id, customer_name):
    payload = {
        'customer_id': customer_id,
        'customer_name': customer_name,
        'exp': datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm='HS256')

def get_jwt_customer():
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:].strip()
        if not token:
            return None, None
        try:
            payload = jwt.decode(token, _get_jwt_secret(), algorithms=['HS256'])
            return payload['customer_id'], payload['customer_name']
        except Exception:
            return None, None
    return None, None

# ---------------- LEGAL / POLICY PAGES ----------------

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy.html')

@app.route('/terms')
@app.route('/terms-and-conditions')
def terms_conditions():
    return render_template('terms.html')

@app.route('/shipping')
@app.route('/shipping-policy')
def shipping_policy():
    return render_template('shipping.html')

@app.route('/refund')
@app.route('/refund-policy')
def refund_policy():
    return render_template('refund.html')

# ---------------- PUBLIC ROUTES ----------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/auth/status')
def api_auth_status():
    admin_logged_in = bool(session.get('admin_logged_in'))
    customer_logged_in = bool(session.get('customer_id'))
    if not customer_logged_in:
        jwt_customer_id, _ = get_jwt_customer()
        customer_logged_in = bool(jwt_customer_id)
    return jsonify({
        'admin_logged_in': admin_logged_in,
        'customer_logged_in': customer_logged_in
    })

# Keys that are safe to expose through PUBLIC APIs (shop details only).
# Never include password hashes, admin-only configuration, etc.
PUBLIC_SETTINGS_KEYS = {
    'shop_name_en', 'shop_name_hi', 'tagline_en', 'tagline_hi',
    'address_en', 'address_hi', 'phone', 'whatsapp', 'email',
    'hours_en', 'hours_hi', 'about_en', 'about_hi', 'logo',
    'upi_id', 'upi_qr_data', 'homepage_video_url',
    'shipping_charge', 'free_shipping_min',
}

@app.route('/api/site')
def api_site():
    """Public shop-details endpoint - returns only safe, whitelisted keys."""
    conn = get_db()
    rows = conn.execute('SELECT key, value FROM settings').fetchall()
    conn.close()
    data = {}
    for r in rows:
        if r['key'] in PUBLIC_SETTINGS_KEYS:
            data[r['key']] = r['value']
    return jsonify(data)

@app.route('/admin/api/settings')
@login_required
def admin_api_settings():
    """Admin-only settings endpoint (full settings, minus credentials)."""
    try:
        conn = get_db()
        rows = conn.execute('SELECT key, value FROM settings').fetchall()
        conn.close()
        data = {}
        for r in rows:
            data[r['key']] = r['value']
        data.pop('password_hash', None)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/products')
def api_products():
    conn = get_db()
    rows = conn.execute('SELECT * FROM products ORDER BY id').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/static/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ---------------- CUSTOMER ROUTES ----------------

@app.route('/customer')
def customer_page():
    return render_template('customer.html')

@app.route('/cart')
def cart_page():
    return render_template('cart.html')

@app.route('/checkout')
def checkout_page():
    return render_template('checkout.html')

@app.route('/api/customer/register', methods=['POST'])
def api_customer_register():
    if not rate_limit_ok('register'):
        return jsonify({'error': 'Too many attempts. Please wait 5 minutes and try again.'}), 429
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    # Accept either phone OR email as the login identifier (simplified 3-field form)
    if not name or (not phone and not email) or not password:
        return jsonify({'error': 'Name, email/phone and password are required'}), 400
    if len(password) < 4:
        return jsonify({'error': 'Password must be at least 4 characters'}), 400
    conn = get_db()
    try:
        cur = conn.execute(
            'INSERT INTO customers (name, phone, email, address, password_hash) VALUES (?, ?, ?, ?, ?)',
            (name, phone, email, data.get('address', ''), generate_password_hash(password))
        )
        conn.commit()
        customer_id = cur.lastrowid
        session.permanent = True  # Keep logged in for 30 days
        session['customer_id'] = customer_id
        session['customer_name'] = name
        token = generate_jwt_token(customer_id, name)
        conn.close()
        return jsonify({'id': customer_id, 'name': name, 'message': 'Registration successful', 'token': token}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Phone number already registered. Please login.'}), 400

@app.route('/api/customer/login', methods=['POST'])
def api_customer_login():
    if not rate_limit_ok('customer_login'):
        return jsonify({'error': 'Too many login attempts. Please wait 5 minutes and try again.'}), 429
    data = request.get_json() or {}
    identifier = data.get('phone', '') or data.get('email', '') or data.get('identifier', '')
    identifier = identifier.strip()
    password = data.get('password', '')
    if not identifier or not password:
        return jsonify({'error': 'Email/phone and password are required'}), 400
    conn = get_db()
    # Login by phone OR email
    row = conn.execute('SELECT * FROM customers WHERE phone=? OR email=?', (identifier, identifier)).fetchone()
    conn.close()
    if not row or not check_password_hash(row['password_hash'], password):
        return jsonify({'error': 'Invalid email/phone or password'}), 400
    rate_limit_clear('customer_login')
    session.permanent = True  # Keep logged in for 30 days
    session['customer_id'] = row['id']
    session['customer_name'] = row['name']
    token = generate_jwt_token(row['id'], row['name'])
    return jsonify({'id': row['id'], 'name': row['name'], 'message': 'Login successful', 'token': token})

# Alias endpoint: POST /api/login (same as customer login, for frontend convenience)
@app.route('/api/login', methods=['POST'])
def api_login():
    return api_customer_login()

@app.route('/api/customer/logout', methods=['POST'])
def api_customer_logout():
    session.pop('customer_id', None)
    session.pop('customer_name', None)
    return jsonify({'message': 'Logged out'})

# ---------------- GOOGLE OAUTH =================

@app.route('/api/auth/google')
def api_auth_google():
    """Google OAuth endpoint - redirects to Google OAuth consent screen"""
    # Google OAuth 2.0 configuration
    # Get client ID from environment variable or use placeholder
    client_id = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
    
    # Validate client ID
    if not client_id or client_id == 'YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com' or 'YOUR_' in client_id:
        # Return a user-friendly error page instead of redirecting to Google with invalid credentials
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Google Sign In - Configuration Required</title>
            <style>
                body {
                    font-family: 'Poppins', sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: #f5f5f5;
                }
                .message {
                    text-align: center;
                    padding: 40px;
                    background: white;
                    border-radius: 16px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                    max-width: 500px;
                }
                .error { color: #dc3545; }
                .info { color: #17a2b8; }
            </style>
        </head>
        <body>
            <div class="message">
                <h2 class="error">⚠️ Google Sign In Not Configured</h2>
                <p>Google OAuth is not yet configured for this website.</p>
                <p class="info">To enable Google Sign In:</p>
                <ol style="text-align: left; margin: 20px auto; max-width: 300px;">
                    <li>Go to <a href="https://console.cloud.google.com" target="_blank">Google Cloud Console</a></li>
                    <li>Create OAuth 2.0 credentials</li>
                    <li>Set the GOOGLE_CLIENT_ID environment variable</li>
                </ol>
                <p>Please use phone/email login instead, or contact the administrator.</p>
                <button onclick="window.close()" style="padding: 10px 20px; background: #b8860b; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 1rem; margin-top: 20px;">Close</button>
            </div>
            <script>
                // Notify parent window of the error
                if (window.opener) {
                    window.opener.postMessage({
                        type: 'google-auth-error',
                        error: 'Google Sign In is not configured. Please use phone/email login.'
                    }, window.location.origin);
                }
            </script>
        </body>
        </html>
        ''', 400
    
    # Build the redirect URI dynamically - force https (required by Google and to match the registered redirect URI)
    redirect_uri = url_for('api_auth_google_callback', _external=True, _scheme='https')
    # Fallback if behind a proxy that injects http
    if redirect_uri.startswith('http://'):
        redirect_uri = redirect_uri.replace('http://', 'https://', 1)
    
    # Properly encode the redirect URI for the OAuth URL
    from urllib.parse import quote
    encoded_redirect_uri = quote(redirect_uri, safe='')
    
    # Google OAuth URL with required scopes
    # Using response_type=code for authorization code flow (more secure)
    scope = 'openid email profile'
    encoded_scope = quote(scope, safe='')
    
    # Construct OAuth URL with properly encoded parameters
    google_auth_url = (
        f'https://accounts.google.com/o/oauth2/v2/auth?'
        f'client_id={client_id}&'
        f'redirect_uri={encoded_redirect_uri}&'
        f'response_type=code&'
        f'scope={encoded_scope}&'
        f'access_type=offline&'
        f'prompt=consent'
    )
    
    return redirect(google_auth_url)

@app.route('/api/auth/google/token', methods=['POST'])
def api_auth_google_token():
    """Exchange Google OAuth authorization code (or access_token) for user info and create/login customer"""
    data = request.get_json() or {}
    code = data.get('code', '')
    access_token = data.get('access_token', '')
    
    import urllib.request
    import urllib.parse
    import json as json_mod
    
    try:
        # If an authorization code was provided, exchange it for an access token
        if code and not access_token:
            client_id = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
            client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '').strip()
            redirect_uri = url_for('api_auth_google_callback', _external=True, _scheme='https')
            # Fallback if behind a proxy that injects http
            if redirect_uri.startswith('http://'):
                redirect_uri = redirect_uri.replace('http://', 'https://', 1)
            
            if not client_id or not client_secret:
                return jsonify({'error': 'Google OAuth is not configured'}), 400
            
            token_req = urllib.parse.urlencode({
                'code': code,
                'client_id': os.environ.get('GOOGLE_CLIENT_ID', '').strip(),
                'client_secret': os.environ.get('GOOGLE_CLIENT_SECRET', '').strip(),
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code'
            }).encode('utf-8')
            
            token_req_obj = urllib.request.Request(
                'https://oauth2.googleapis.com/token',
                data=token_req,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            try:
                with urllib.request.urlopen(token_req_obj, timeout=10) as response:
                    token_data = json_mod.loads(response.read().decode('utf-8'))
            except urllib.error.HTTPError as e:
                # Print the exact error response from Google for easy debugging
                print(f"Google Token Exchange Error: {e.read().decode('utf-8')}")
                return jsonify({'error': 'Failed to exchange authorization code with Google'}), 400
            
            access_token = token_data.get('access_token', '')
            if not access_token:
                return jsonify({'error': 'Failed to exchange authorization code with Google'}), 400
        
        if not access_token:
            return jsonify({'error': 'No authorization code or access token provided'}), 400
        
        # Fetch user info from Google
        userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f'Bearer {access_token}'}
        
        req_obj = urllib.request.Request(userinfo_url, headers=headers)
        with urllib.request.urlopen(req_obj, timeout=10) as response:
            user_info = json_mod.loads(response.read().decode('utf-8'))
        
        # Extract user details
        google_id = user_info.get('id', '')
        email = user_info.get('email', '')
        name = user_info.get('name', '')
        picture = user_info.get('picture', '')
        
        if not email or not name:
            return jsonify({'error': 'Could not retrieve user information from Google'}), 400
        
        # Check if customer exists with this email or create new one
        conn = get_db()
        customer = conn.execute(
            'SELECT * FROM customers WHERE email=? OR phone=?',
            (email, email)
        ).fetchone()
        
        if customer:
            # Existing customer - log them in
            customer_id = customer['id']
            session.permanent = True
            session['customer_id'] = customer_id
            session['customer_name'] = customer['name']
            token = generate_jwt_token(customer_id, customer['name'])
            conn.close()
            return jsonify({
                'logged_in': True,
                'token': token,
                'customer': {
                    'id': customer_id,
                    'name': customer['name'],
                    'email': customer['email']
                }
            })
        else:
            # New customer - create account
            # Generate a random password (user will login via Google in future)
            import secrets
            random_password = secrets.token_urlsafe(32)
            
            cur = conn.execute(
                'INSERT INTO customers (name, email, phone, password_hash) VALUES (?, ?, ?, ?)',
                (name, email, email, generate_password_hash(random_password))
            )
            conn.commit()
            customer_id = cur.lastrowid
            
            # Log them in
            session.permanent = True
            session['customer_id'] = customer_id
            session['customer_name'] = name
            conn.close()
            
            token = generate_jwt_token(customer_id, name)
            return jsonify({
                'logged_in': True,
                'token': token,
                'customer': {
                    'id': customer_id,
                    'name': name,
                    'email': email
                }
            })
    
    except Exception as e:
        print(f"Google OAuth error: {e}")
        return jsonify({'error': 'Failed to authenticate with Google. Please try again.'}), 500

@app.route('/api/auth/google/callback')
def api_auth_google_callback():
    """Google OAuth callback endpoint - handles the popup window"""
    # This page receives the OAuth token from Google via URL fragment
    # It extracts the token and sends it to the parent window via postMessage
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Google Sign In - Processing</title>
        <style>
            body {
                font-family: 'Poppins', sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background: #f5f5f5;
            }
            .message {
                text-align: center;
                padding: 40px;
                background: white;
                border-radius: 16px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            .success { color: #28a745; }
            .error { color: #dc3545; }
            .spinner {
                border: 3px solid #f3f3f3;
                border-top: 3px solid #4285F4;
                border-radius: 50%;
                width: 30px;
                height: 30px;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div class="message">
            <h2 id="status">Signing in with Google...</h2>
            <div class="spinner"></div>
            <p>Please wait while we complete your sign-in.</p>
        </div>
        <script>
            // Read authorization code from URL query parameters
            // Google is configured with response_type=code (authorization code flow),
            // so the callback receives ?code=... (or ?error=...) in the query string,
            // NOT an access_token in the URL hash fragment.
            const urlParams = new URLSearchParams(window.location.search);
            const code = urlParams.get('code');
            const error = urlParams.get('error');
            
            if (code) {
                // Send the authorization code to the parent window for server-side exchange
                if (window.opener) {
                    window.opener.postMessage({
                        type: 'google-auth-code',
                        code: code
                    }, window.location.origin);
                }
                
                document.getElementById('status').textContent = 'Sign in successful!';
                document.getElementById('status').className = 'success';
                document.querySelector('.spinner').style.display = 'none';
                document.querySelector('p').textContent = 'You can close this window.';
                
                // Auto-close after 1.5 seconds
                setTimeout(() => window.close(), 1500);
            } else if (error) {
                document.getElementById('status').textContent = 'Sign in failed: ' + error;
                document.getElementById('status').className = 'error';
                document.querySelector('.spinner').style.display = 'none';
                document.querySelector('p').textContent = 'Please try again or close this window.';
                
                // Send error message to parent window
                if (window.opener) {
                    window.opener.postMessage({
                        type: 'google-auth-error',
                        error: error
                    }, window.location.origin);
                }
                
                setTimeout(() => window.close(), 2000);
            } else {
                document.getElementById('status').textContent = 'No token received';
                document.getElementById('status').className = 'error';
                document.querySelector('.spinner').style.display = 'none';
                document.querySelector('p').textContent = 'Authentication failed. Please close and try again.';
                
                setTimeout(() => window.close(), 2000);
            }
        </script>
    </body>
    </html>
    '''

@app.route('/api/customer/me')
def api_customer_me():
    customer_id = session.get('customer_id')
    if not customer_id:
        customer_id, _ = get_jwt_customer()
    if not customer_id:
        return jsonify({'logged_in': False})
    conn = get_db()
    row = conn.execute('SELECT id, name, phone, email, address FROM customers WHERE id=?', (customer_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'logged_in': False})
    return jsonify({'logged_in': True, 'customer': dict(row)})

@app.route('/api/customer/orders', methods=['GET', 'POST'])
def api_customer_orders():
    if request.method == 'GET':
        customer_id = session.get('customer_id')
        if not customer_id:
            customer_id, _ = get_jwt_customer()
        if not customer_id:
            return jsonify({'error': 'Not logged in'}), 401
        conn = get_db()
        rows = conn.execute('SELECT * FROM orders WHERE customer_id=? ORDER BY id DESC', (customer_id,)).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    else:
        data = request.get_json() or {}
        items = data.get('items', [])
        total = data.get('total', '')
        if not items:
            return jsonify({'error': 'No items in order'}), 400
        import json as json_mod
        items_json = json_mod.dumps(items)
        name = data.get('name', session.get('customer_name', ''))
        phone = data.get('phone', '')
        address = data.get('address', '')
        customer_id = session.get('customer_id')
        if not customer_id:
            customer_id, customer_name_jwt = get_jwt_customer()
            if customer_id and not name:
                name = customer_name_jwt or name
        conn = get_db()
        cur = conn.execute(
            'INSERT INTO orders (customer_id, customer_name, customer_phone, customer_address, items, total) VALUES (?, ?, ?, ?, ?, ?)',
            (customer_id, name, phone, address, items_json, total)
        )
        conn.commit()
        order_id = cur.lastrowid
        conn.close()
        return jsonify({'id': order_id, 'message': 'Order placed successfully!'}), 201

@app.route('/api/my-orders', methods=['GET'])
def api_my_orders():
    """Get orders for the currently logged-in customer"""
    customer_id = session.get('customer_id')
    if not customer_id:
        customer_id, _ = get_jwt_customer()
    if not customer_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    conn = get_db()
    rows = conn.execute(
        'SELECT id, items, total, status, created_at FROM orders WHERE customer_id=? ORDER BY id DESC',
        (customer_id,)
    ).fetchall()
    conn.close()
    
    orders = []
    for row in rows:
        order = dict(row)
        
        # Format date/time as DD Mon YYYY, HH:MM AM/PM
        try:
            dt = datetime.strptime(order.get('created_at', ''), '%Y-%m-%d %H:%M:%S')
            order['formatted_date'] = dt.strftime('%d %b %Y, %I:%M %p')
        except:
            order['formatted_date'] = order.get('created_at', 'N/A')
        
        # Parse items to get structured breakdown
        try:
            import json as json_mod
            items = json_mod.loads(order.get('items', '[]'))
            # Create structured item breakdown
            item_breakdown = []
            for item in items:
                product_id = item.get('product_id')
                qty = item.get('quantity', 1)
                grade_index = item.get('grade_index', 0)
                
                # Get product details
                conn = get_db()
                product = conn.execute('SELECT name_en, price, weight, grades FROM products WHERE id=?', (product_id,)).fetchone()
                conn.close()
                
                if product:
                    name = product['name_en']
                    price_str = product['price'] or '₹0'
                    price = float(re.sub(r'[₹,\s]', '', price_str) or 0)
                    
                    # Get weight/variant
                    weight = product['weight'] or ''
                    variant = ''
                    try:
                        grades = json_mod.loads(product['grades'] or '[]')
                        if grades and grade_index < len(grades):
                            variant = grades[grade_index].get('name', '')
                    except:
                        pass
                    
                    item_total = price * qty
                    
                    item_breakdown.append({
                        'name': name,
                        'variant': variant or weight,
                        'quantity': qty,
                        'unit_price': f"₹{price:.2f}",
                        'total': f"₹{item_total:.2f}"
                    })
                else:
                    item_breakdown.append({
                        'name': f"Product #{product_id}",
                        'variant': '',
                        'quantity': qty,
                        'unit_price': '₹0.00',
                        'total': '₹0.00'
                    })
            
            order['item_breakdown'] = item_breakdown
            order['item_summary'] = f"{len(item_breakdown)} item(s)" if item_breakdown else 'No items'
        except:
            order['item_breakdown'] = []
            order['item_summary'] = 'Order details unavailable'
        
        # Format status for display
        status = order.get('status', 'pending')
        if status.startswith('pending_'):
            status = 'Pending'
        elif status == 'confirmed':
            status = 'Processing'
        elif status == 'shipped':
            status = 'Dispatched'
        elif status == 'delivered':
            status = 'Delivered'
        elif status == 'cancelled':
            status = 'Cancelled'
        else:
            status = status.replace('_', ' ').title()
        order['status_display'] = status
        
        orders.append(order)
    
    return jsonify(orders)

# ---------------- ADMIN ORDERS ----------------

@app.route('/admin/orders')
@login_required
def admin_orders_page():
    return render_template('admin/orders.html')

@app.route('/admin/api/orders', methods=['GET'])
@login_required
def admin_api_orders():
    conn = get_db()
    
    # Check if show_hidden parameter is present
    show_hidden = request.args.get('show_hidden', 'false').lower() == 'true'
    
    # Filter orders based on is_hidden status
    if show_hidden:
        rows = conn.execute('SELECT * FROM orders WHERE is_hidden=1 ORDER BY id DESC').fetchall()
    else:
        rows = conn.execute('SELECT * FROM orders WHERE is_hidden=0 ORDER BY id DESC').fetchall()
    
    conn.close()
    
    # Enrich orders with product details
    import json as json_mod
    enriched_orders = []
    for order in rows:
        order_dict = dict(order)
        
        # Parse items and enrich with product details
        try:
            items = json_mod.loads(order_dict.get('items', '[]'))
            enriched_items = []
            for item in items:
                product_id = item.get('product_id')
                quantity = item.get('quantity', 1)
                grade_index = item.get('grade_index', 0)
                
                # Prefer the order snapshot so history stays correct after
                # product/price changes; fall back to live data for legacy orders.
                if item.get('name_en'):
                    price = float(item.get('unit_price', 0) or 0)
                    item_total = price * quantity
                    enriched_items.append({
                        'name': item.get('name_en'),
                        'variant': item.get('variant', ''),
                        'quantity': quantity,
                        'unit_price': f"₹{price:.2f}",
                        'total': f"₹{item_total:.2f}"
                    })
                    continue
                
                # Get product details
                conn = get_db()
                product = conn.execute('SELECT name_en, price, weight, grades FROM products WHERE id=?', (product_id,)).fetchone()
                conn.close()
                
                if product:
                    name = product['name_en']
                    price_str = product['price'] or '₹0'
                    price = float(re.sub(r'[₹,\s]', '', price_str) or 0)
                    
                    # Get variant/weight
                    variant = product['weight'] or ''
                    try:
                        grades = json_mod.loads(product['grades'] or '[]')
                        if grades and grade_index < len(grades):
                            variant = grades[grade_index].get('name', variant)
                    except:
                        pass
                    
                    item_total = price * quantity
                    
                    enriched_items.append({
                        'name': name,
                        'variant': variant,
                        'quantity': quantity,
                        'unit_price': f"₹{price:.2f}",
                        'total': f"₹{item_total:.2f}"
                    })
                else:
                    enriched_items.append({
                        'name': f"Product #{product_id}",
                        'variant': '',
                        'quantity': quantity,
                        'unit_price': '₹0.00',
                        'total': '₹0.00'
                    })
            
            order_dict['items_parsed'] = enriched_items
        except:
            order_dict['items_parsed'] = []
        
        # Format date/time
        try:
            dt = datetime.strptime(order_dict.get('created_at', ''), '%Y-%m-%d %H:%M:%S')
            order_dict['formatted_date'] = dt.strftime('%d %b %Y, %I:%M %p')
        except:
            order_dict['formatted_date'] = order_dict.get('created_at', 'N/A')
        
        enriched_orders.append(order_dict)
    
    return jsonify(enriched_orders)

@app.route('/admin/api/orders/<int:oid>', methods=['PUT'])
@login_required
def admin_api_order_update(oid):
    data = request.get_json() or {}
    status = data.get('status', 'pending')
    conn = get_db()
    conn.execute('UPDATE orders SET status=? WHERE id=?', (status, oid))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Order status updated'})

@app.route('/admin/api/orders/<int:oid>/hide', methods=['POST'])
@login_required
def admin_api_order_hide(oid):
    """Toggle hide/archive status of an order"""
    conn = get_db()
    order = conn.execute('SELECT is_hidden FROM orders WHERE id=?', (oid,)).fetchone()
    if not order:
        conn.close()
        return jsonify({'error': 'Order not found'}), 404
    
    new_status = 1 if order['is_hidden'] == 0 else 0
    conn.execute('UPDATE orders SET is_hidden=? WHERE id=?', (new_status, oid))
    conn.commit()
    conn.close()
    
    action = 'hidden' if new_status == 1 else 'restored'
    return jsonify({'message': f'Order {action} successfully', 'is_hidden': new_status})

@app.route('/admin/api/orders/<int:oid>', methods=['DELETE'])
@login_required
def admin_api_order_delete(oid):
    """Permanently delete an order"""
    conn = get_db()
    result = conn.execute('DELETE FROM orders WHERE id=?', (oid,))
    conn.commit()
    conn.close()
    
    if result.rowcount > 0:
        return jsonify({'message': 'Order deleted permanently'})
    else:
        return jsonify({'error': 'Order not found'}), 404

# ---------------- ADMIN ROUTES ----------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if not rate_limit_ok('admin'):
            flash('Too many login attempts. Please wait 5 minutes and try again.', 'error')
            return render_template('admin/login.html'), 429
        password = request.form.get('password', '')
        conn = get_db()
        row = conn.execute("SELECT value FROM settings WHERE key='password_hash'").fetchone()
        conn.close()
        if row and check_password_hash(row['value'], password):
            rate_limit_clear('admin')
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Incorrect password. Please try again.', 'error')
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
def admin_dashboard():
    conn = get_db()
    product_count = conn.execute('SELECT COUNT(*) as c FROM products').fetchone()['c']
    conn.close()
    return render_template('admin/dashboard.html', product_count=product_count)

@app.route('/admin/products')
@login_required
def admin_products_page():
    return render_template('admin/products.html')

@app.route('/admin/settings')
@login_required
def admin_settings_page():
    return render_template('admin/settings.html')

@app.route('/admin/coupons')
@login_required
def admin_coupons_page():
    return render_template('admin/coupons.html')

# ---------------- ADMIN API ----------------

@app.route('/admin/api/products', methods=['GET', 'POST'])
@login_required
def admin_api_products():
    conn = get_db()
    if request.method == 'GET':
        rows = conn.execute('SELECT * FROM products ORDER BY id').fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    else:
        data = request.get_json() or {}
        name_en = data.get('name_en', '').strip()
        name_hi = data.get('name_hi', '').strip()
        if not name_en or not name_hi:
            return jsonify({'error': 'Name in both English and Hindi is required'}), 400
        try:
            stock = int(data.get('stock', 0))
        except (ValueError, TypeError):
            stock = 0
        grades_json = data.get('grades', '[]')
        if isinstance(grades_json, list):
            import json as json_mod
            grades_json = json_mod.dumps(grades_json)
        cur = conn.execute(
            'INSERT INTO products (name_en, name_hi, price, weight, description_en, description_hi, image, stock, old_price, sku, video, grades) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (name_en, name_hi, data.get('price', ''), data.get('weight', ''),
             data.get('description_en', ''), data.get('description_hi', ''), data.get('image', ''),
             stock, data.get('old_price', ''), data.get('sku', ''), data.get('video', ''), grades_json)
        )
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return jsonify({'id': new_id, 'message': 'Product added successfully'}), 201

@app.route('/admin/api/products/<int:pid>', methods=['PUT', 'DELETE'])
@login_required
def admin_api_product(pid):
    conn = get_db()
    if request.method == 'PUT':
        data = request.get_json() or {}
        try:
            stock = int(data.get('stock', 0))
        except (ValueError, TypeError):
            stock = 0
        grades_json = data.get('grades', '[]')
        if isinstance(grades_json, list):
            import json as json_mod
            grades_json = json_mod.dumps(grades_json)
        conn.execute(
            'UPDATE products SET name_en=?, name_hi=?, price=?, weight=?, description_en=?, description_hi=?, image=?, stock=?, old_price=?, sku=?, video=?, grades=? WHERE id=?',
            (data.get('name_en', ''), data.get('name_hi', ''), data.get('price', ''),
             data.get('weight', ''), data.get('description_en', ''), data.get('description_hi', ''),
             data.get('image', ''), stock, data.get('old_price', ''), data.get('sku', ''),
             data.get('video', ''), grades_json, pid)
        )
        conn.commit()
        conn.close()
        return jsonify({'message': 'Product updated successfully'})
    else:
        conn.execute('DELETE FROM products WHERE id=?', (pid,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Product deleted successfully'})

@app.route('/admin/api/site', methods=['GET', 'POST'])
@login_required
def admin_api_site():
    try:
        conn = get_db()
        if request.method == 'GET':
            try:
                rows = conn.execute('SELECT key, value FROM settings').fetchall()
                data = {r['key']: r['value'] for r in rows}
                data.pop('password_hash', None)
                conn.close()
                return jsonify({'success': True, 'data': data})
            except Exception as e:
                conn.close()
                return jsonify({'success': False, 'error': str(e)}), 500
        else:
            try:
                # Handle both FormData (multipart/form-data) and JSON
                data = {}
                
                # Try to get JSON data first
                json_data = request.get_json(silent=True)
                if json_data:
                    data = json_data
                else:
                    # Fall back to form data
                    data = request.form.to_dict()
                    # Parse the 'data' field if it exists (JSON string in FormData)
                    if 'data' in data:
                        import json as json_mod
                        try:
                            data = json_mod.loads(data['data'])
                        except:
                            pass
                
                editable_keys = ['shop_name_en', 'shop_name_hi', 'tagline_en', 'tagline_hi',
                                 'address_en', 'address_hi', 'phone', 'whatsapp', 'email',
                                 'hours_en', 'hours_hi', 'about_en', 'about_hi', 'logo',
                                 'global_discount', 'global_discount_percent', 'upi_id',
                                 'homepage_video_url', 'gstin', 'tax_percent',
                                 'shipping_charge', 'free_shipping_min']
                for key in editable_keys:
                    if key in data:
                        # Use INSERT OR REPLACE to ensure persistence even for new keys
                        conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(data[key])))
                
                # Handle UPI QR code upload - convert to Base64 for permanent storage
                qr_file = request.files.get('upi_qr_code')
                if qr_file and qr_file.filename:
                    import base64
                    # Read file and convert to base64
                    file_data = qr_file.read()
                    base64_data = base64.b64encode(file_data).decode('utf-8')
                    mime_type = qr_file.content_type or 'image/png'
                    data_url = f'data:{mime_type};base64,{base64_data}'
                    
                    # Store Base64 string in database (permanent, never lost)
                    conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', ('upi_qr_data', data_url))
                
                conn.commit()
                conn.close()
                return jsonify({'success': True, 'message': 'Settings saved successfully'})
            except Exception as e:
                conn.rollback()
                conn.close()
                return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': 'Server error: ' + str(e)}), 500

@app.route('/admin/api/upload', methods=['POST'])
@login_required
def admin_api_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # avoid name collisions
        name, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
            filename = f"{name}_{counter}{ext}"
            counter += 1
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({'url': f'/static/uploads/{filename}', 'message': 'Image uploaded successfully'})
    return jsonify({'error': 'File type not allowed. Use PNG, JPG, JPEG, GIF, WEBP or SVG.'}), 400

@app.route('/admin/api/change-password', methods=['POST'])
@login_required
def admin_api_change_password():
    data = request.get_json() or {}
    old_pw = data.get('old_password', '')
    new_pw = data.get('new_password', '')
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key='password_hash'").fetchone()
    if not row or not check_password_hash(row['value'], old_pw):
        conn.close()
        return jsonify({'error': 'Old password is incorrect'}), 400
    if len(new_pw) < 6:
        conn.close()
        return jsonify({'error': 'New password must be at least 6 characters'}), 400
    conn.execute("UPDATE settings SET value=? WHERE key='password_hash'", (generate_password_hash(new_pw),))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Password changed successfully'})

@app.route('/admin/api/upload-main-video', methods=['POST'])
@login_required
def admin_api_upload_main_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No video file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No video selected'}), 400
    
    # Validate it's a video file
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        return jsonify({'error': 'Only video files are allowed (MP4, WEBM, MOV, AVI)'}), 400
    
    # Save always as main_banner_video.mp4 (browser compatible)
    filename = 'main_banner_video.mp4'
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    return jsonify({'message': 'Main video updated successfully', 'url': '/static/uploads/main_banner_video.mp4'})

# ---------------- PDF INVOICE GENERATION ----------------

@app.route('/api/orders/<int:order_id>/invoice')
def api_order_invoice(order_id):
    """Generate and download PDF invoice for an order"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    import io
    # Unicode font so the Rupee symbol renders correctly on all devices
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    font_dir = os.path.join(BASE_DIR, 'static', 'fonts')
    try:
        pdfmetrics.registerFont(TTFont('JainzeeSans', os.path.join(font_dir, 'DejaVuSans.ttf')))
        pdfmetrics.registerFont(TTFont('JainzeeSans-Bold', os.path.join(font_dir, 'DejaVuSans-Bold.ttf')))
        BASE_FONT, BASE_FONT_BOLD = 'JainzeeSans', 'JainzeeSans-Bold'
    except Exception:
        BASE_FONT, BASE_FONT_BOLD = 'Helvetica', 'Helvetica-Bold'
    
    # Check if customer is logged in
    customer_id = session.get('customer_id')
    if not customer_id:
        customer_id, _ = get_jwt_customer()
    if not customer_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    conn = get_db()
    order = conn.execute('SELECT * FROM orders WHERE id=? AND customer_id=?', 
                        (order_id, customer_id)).fetchone()
    
    if not order:
        conn.close()
        return jsonify({'error': 'Order not found'}), 404

    # DELIVERY-GATED INVOICE: invoices are only available once the order has
    # been delivered. Prevent premature downloads with a clean error page.
    raw_status = str(order['status'] or '').strip().lower()
    if not raw_status.startswith('deliver'):
        conn.close()
        return render_template(
            'error.html', code=403,
            title='Invoice Not Available',
            message='Invoice will be available after delivery.'
        ), 403

    # Get shop settings
    settings = {}
    for row in conn.execute('SELECT key, value FROM settings'):
        settings[row['key']] = row['value']
    
    # Parse order items
    import json as json_mod
    items = json_mod.loads(order['items'] or '[]')
    
    conn.close()
    
    # Create PDF buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                          rightMargin=72, leftMargin=72,
                          topMargin=72, bottomMargin=18)
    
    # Container for the 'flowables'
    elements = []
    
    # Custom styles
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#b8860b'),
        alignment=TA_CENTER,
        spaceAfter=30,
        fontName=BASE_FONT_BOLD
    )
    
    # Header style
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#2c1810'),
        alignment=TA_LEFT,
        spaceAfter=6,
        fontName=BASE_FONT_BOLD
    )
    
    # Normal style
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#4a3728'),
        alignment=TA_LEFT,
        spaceAfter=4
    )
    
    # ===== RETAIL RECEIPT STYLE INVOICE =====
    
    # Company Header - Bold, Uppercase, Black
    company_header_style = ParagraphStyle(
        'CompanyHeader',
        parent=styles['Normal'],
        fontSize=20,
        textColor=colors.black,
        alignment=TA_CENTER,
        spaceAfter=6,
        fontName=BASE_FONT_BOLD
    )
    
    shop_name = settings.get('shop_name_en', 'JAINZEE FOOD PROCESSING INDUSTRIES').upper()
    elements.append(Paragraph(shop_name, company_header_style))
    elements.append(Spacer(1, 4))
    
    # Tagline
    tagline_style = ParagraphStyle(
        'Tagline',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        alignment=TA_CENTER,
        spaceAfter=8,
        fontName=BASE_FONT
    )
    tagline = settings.get('tagline_en', 'Pure & Premium Dry Fruits')
    elements.append(Paragraph(f"Tax Invoice / Cash Memo", tagline_style))
    elements.append(Spacer(1, 6))
    
    # Company Contact Info
    contact_style = ParagraphStyle(
        'ContactInfo',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.black,
        alignment=TA_CENTER,
        spaceAfter=3,
        fontName=BASE_FONT
    )
    
    address = settings.get('address_en', 'Siyaganj, Indore, Madhya Pradesh 452001')
    phone = settings.get('phone', '+91 98260 00000')
    email = settings.get('email', 'info@jainzee.in')
    
    elements.append(Paragraph(f"Address: {address}", contact_style))
    elements.append(Paragraph(f"Phone: {phone} | Email: {email}", contact_style))
    # Show GSTIN only if configured in admin settings
    gstin = (settings.get('gstin') or '').strip()
    if gstin:
        elements.append(Paragraph(f"GSTIN: {gstin}", contact_style))
    elements.append(Spacer(1, 10))
    
    # Dashed horizontal line
    line_data = [['', '', '']]
    line_table = Table(line_data, colWidths=[2.5*inch, 2*inch, 2.5*inch])
    line_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 2, colors.black),
        ('TOPPADDING', (0, 0), (-1, 0), 0),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
    ]))
    elements.append(line_table)
    elements.append(Spacer(1, 12))
    
    # Invoice Details Section - Two columns
    invoice_info_style = ParagraphStyle(
        'InvoiceInfo',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        alignment=TA_LEFT,
        spaceAfter=4,
        fontName=BASE_FONT
    )
    
    invoice_info_bold_style = ParagraphStyle(
        'InvoiceInfoBold',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        alignment=TA_LEFT,
        spaceAfter=4,
        fontName=BASE_FONT_BOLD
    )
    
    # Format date
    try:
        dt = datetime.strptime(order['created_at'], '%Y-%m-%d %H:%M:%S')
        formatted_date = dt.strftime('%d %b %Y, %I:%M %p')
    except:
        formatted_date = order['created_at']
    
    # Left side - Invoice details
    left_data = [
        [Paragraph("<b>Invoice No:</b>", invoice_info_bold_style), Paragraph(f"INV-{order['id']:06d}", invoice_info_style)],
        [Paragraph("<b>Order No:</b>", invoice_info_bold_style), Paragraph(f"#{order['id']}", invoice_info_style)],
        [Paragraph("<b>Date & Time:</b>", invoice_info_bold_style), Paragraph(formatted_date, invoice_info_style)],
    ]
    
    left_table = Table(left_data, colWidths=[1.5*inch, 2.5*inch])
    left_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    # Right side - Customer details
    right_data = [
        [Paragraph("<b>Customer Name:</b>", invoice_info_bold_style), Paragraph(order['customer_name'], invoice_info_style)],
        [Paragraph("<b>Phone:</b>", invoice_info_bold_style), Paragraph(order['customer_phone'], invoice_info_style)],
        [Paragraph("<b>Address:</b>", invoice_info_bold_style), Paragraph(order['customer_address'], invoice_info_style)],
    ]
    
    right_table = Table(right_data, colWidths=[1.3*inch, 2.7*inch])
    right_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    # Combine left and right
    combined_data = [[left_table, right_table]]
    combined_table = Table(combined_data, colWidths=[4*inch, 4*inch])
    combined_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(combined_table)
    elements.append(Spacer(1, 15))
    
    # Items table header with black borders
    items_data = [['Item Name', 'Qty', 'Unit Price (₹)', 'Total (₹)']]
    
    # Calculate subtotal
    subtotal = 0
    for item in items:
        product_id = item.get('product_id')
        qty = item.get('quantity', 1)
        
        # Prefer the order SNAPSHOT (name/variant/price frozen at purchase time)
        # so old invoices remain correct even if the product changes later.
        # Fall back to the live product record only for legacy orders.
        if item.get('name_en'):
            name = item.get('name_en')
            variant = item.get('variant', '')
            if variant:
                name = f"{name} ({variant})"
            price = float(item.get('unit_price', 0) or 0)
        else:
            # Legacy order: fall back to live product data
            conn = get_db()
            product = conn.execute('SELECT name_en, price FROM products WHERE id=?', (product_id,)).fetchone()
            conn.close()
            
            if product:
                name = product['name_en']
                price_str = product['price'] or '₹0'
                price = float(re.sub(r'[₹,\s]', '', price_str) or 0)
            else:
                name = f"Product #{product_id}"
                price = 0
        
        item_total = price * qty
        subtotal += item_total
        
        items_data.append([
            name,
            str(qty),
            f"₹{price:.2f}",
            f"₹{item_total:.2f}"
        ])
    
    # Check for discount
    discount_percent = 0
    try:
        discount_val = settings.get('global_discount_percent') or settings.get('global_discount', '0')
        discount_percent = float(str(discount_val).replace('%', '').strip()) or 0
    except:
        discount_percent = 0
    
    discount_amount = (subtotal * discount_percent) / 100
    
    # Prefer the IMMUTABLE order totals saved at purchase time (coupon,
    # shipping etc.); fall back to recomputation for legacy orders.
    def _num(v):
        try:
            return float(re.sub(r'[₹,\s]', '', str(v or '')) or 0)
        except (ValueError, TypeError):
            return 0.0
    stored_subtotal = _num(order['subtotal']) if 'subtotal' in order.keys() else 0.0
    stored_discount = _num(order['discount_amount']) if 'discount_amount' in order.keys() else 0.0
    stored_shipping = _num(order['shipping_charge']) if 'shipping_charge' in order.keys() else 0.0
    stored_coupon_code = (order['coupon_code'] or '') if 'coupon_code' in order.keys() else ''
    has_stored_totals = stored_subtotal > 0
    if has_stored_totals:
        invoice_subtotal = stored_subtotal
        invoice_discount = stored_discount
        invoice_shipping = stored_shipping
    else:
        invoice_subtotal = subtotal
        invoice_discount = discount_amount
        invoice_shipping = 0.0
    invoice_total = invoice_subtotal - invoice_discount + invoice_shipping
    if invoice_total < 0:
        invoice_total = 0
    
    # Tax breakup: shown ONLY when GSTIN and tax_percent are configured in
    # admin settings (inclusive pricing - tax is a component of the total).
    tax_percent = 0
    try:
        tax_percent = float(str(settings.get('tax_percent', '') or '').strip()) or 0
    except (ValueError, TypeError):
        tax_percent = 0
    show_tax = bool(gstin) and tax_percent > 0
    taxable_value = 0
    tax_amount = 0
    if show_tax:
        taxable_value = invoice_total / (1 + tax_percent / 100)
        tax_amount = invoice_total - taxable_value
    
    # Items table with black borders
    items_table = Table(items_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
    items_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), BASE_FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('LINEABOVE', (0, 0), (-1, 0), 1.5, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        
        # Data rows
        ('FONTNAME', (0, 1), (-1, -4), BASE_FONT),
        ('FONTSIZE', (0, 1), (-1, -4), 10),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),
        ('TEXTCOLOR', (0, 1), (-1, -4), colors.black),
        ('BOTTOMPADDING', (0, 1), (-1, -4), 8),
        ('TOPPADDING', (0, 1), (-1, -4), 8),
        ('LINEBELOW', (0, -4), (-1, -4), 0.5, colors.lightgrey),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 12))
    
    # Totals section - Right aligned
    totals_data = [
        ['', '', 'Subtotal:', f"₹{invoice_subtotal:.2f}"],
    ]
    
    if invoice_discount > 0:
        label = 'Discount:'
        if stored_coupon_code:
            label = f'Discount (Coupon {stored_coupon_code}):'
        elif discount_percent > 0:
            label = f'Discount ({discount_percent}%):'
        totals_data.append(['', '', label, f"-₹{invoice_discount:.2f}"])
    
    if invoice_shipping > 0:
        totals_data.append(['', '', 'Shipping Charge:', f"₹{invoice_shipping:.2f}"])
    
    if show_tax:
        half_tax = tax_amount / 2
        totals_data.append(['', '', f'Taxable Value:', f"₹{taxable_value:.2f}"])
        totals_data.append(['', '', f'CGST ({tax_percent/2:.2f}%):', f"₹{half_tax:.2f}"])
        totals_data.append(['', '', f'SGST ({tax_percent/2:.2f}%):', f"₹{half_tax:.2f}"])
    
    totals_data.append(['', '', 'Grand Total:', f"₹{invoice_total:.2f}"])
    
    totals_table = Table(totals_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
    totals_table.setStyle(TableStyle([
        ('FONTNAME', (2, 0), (2, -2), BASE_FONT_BOLD),
        ('FONTNAME', (3, 0), (3, -2), BASE_FONT_BOLD),
        ('FONTSIZE', (2, 0), (3, -2), 11),
        ('TEXTCOLOR', (2, 0), (3, -2), colors.black),
        ('ALIGN', (2, 0), (3, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -2), 6),
        ('TOPPADDING', (0, 0), (-1, -2), 6),
        ('LINEABOVE', (2, 0), (3, 0), 1, colors.black),
        ('LINEBELOW', (2, -1), (3, -1), 2, colors.black),
        ('FONTNAME', (2, -1), (3, -1), BASE_FONT_BOLD),
        ('FONTSIZE', (2, -1), (3, -1), 13),
        ('TEXTCOLOR', (2, -1), (3, -1), colors.black),
        ('BOTTOMPADDING', (2, -1), (3, -1), 10),
        ('TOPPADDING', (2, -1), (3, -1), 10),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 25))
    
    # Footer
    footer_line_data = [['', '', '']]
    footer_line_table = Table(footer_line_data, colWidths=[2.5*inch, 2*inch, 2.5*inch])
    footer_line_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 1.5, colors.black),
        ('TOPPADDING', (0, 0), (-1, 0), 0),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
    ]))
    elements.append(footer_line_table)
    elements.append(Spacer(1, 8))
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.black,
        alignment=TA_CENTER,
        spaceAfter=4,
        fontName=BASE_FONT
    )
    elements.append(Paragraph("Thank you for shopping with Jainzee Food Processing Industries!", footer_style))
    elements.append(Paragraph("For any queries, contact us at " + phone + " | " + email, footer_style))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    # Return PDF as download
    from flask import make_response
    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=invoice_{order_id}.pdf'
    
    return response

# ---------------- CART & CHECKOUT API ----------------

@app.route('/api/cart', methods=['GET', 'POST'])
def api_cart():
    if request.method == 'GET':
        cart = session.get('cart', [])
        # Enrich with product details
        if not cart:
            return jsonify([])
        conn = get_db()
        enriched = []
        for item in cart:
            row = conn.execute('SELECT * FROM products WHERE id=?', (item['product_id'],)).fetchone()
            if row:
                p = dict(row)
                grades = []
                try: grades = json.loads(p.get('grades', '[]'))
                except: pass
                selectedGrade = grades[item.get('grade_index', 0)] if grades else None
                enriched.append({
                    'product_id': item['product_id'],
                    'name_en': p['name_en'],
                    'name_hi': p['name_hi'],
                    'image': p.get('image', ''),
                    'quantity': item['quantity'],
                    'grade_index': item.get('grade_index', 0),
                    'grade_name': selectedGrade['name'] if selectedGrade else item.get('weight', ''),
                    'grade_price': selectedGrade['price'] if selectedGrade else p.get('price', ''),
                    'base_price': p.get('price', ''),
                    'old_price': p.get('old_price', ''),
                    'weight': item.get('weight', p.get('weight', '')),
                    'stock': p.get('stock', 0)
                })
        conn.close()
        return jsonify(enriched)
    else:
        try:
            data = request.get_json() or {}
            product_id = int(data.get('product_id', 0))
            quantity = int(data.get('quantity', 1))
            grade_index = int(data.get('grade_index', 0))
            
            if not product_id or product_id <= 0:
                return jsonify({'error': 'Valid Product ID required'}), 400
            # Validate quantity: must be a positive integer
            if quantity <= 0:
                return jsonify({'error': 'Quantity must be at least 1'}), 400
            
            # Validate against available stock
            conn = get_db()
            row = conn.execute('SELECT stock FROM products WHERE id=?', (product_id,)).fetchone()
            conn.close()
            if not row:
                return jsonify({'error': 'Product not found'}), 404
            available_stock = row['stock'] or 0
            
            cart = session.get('cart', [])
            
            # Check if same product+grade already in cart
            existing = None
            for i, item in enumerate(cart):
                if item['product_id'] == product_id and item.get('grade_index', 0) == grade_index:
                    existing = i
                    break
            
            new_quantity = quantity + (cart[existing]['quantity'] if existing is not None else 0)
            if new_quantity > available_stock:
                return jsonify({'error': f'Only {available_stock} unit(s) available in stock'}), 400
            
            if existing is not None:
                cart[existing]['quantity'] += quantity
            else:
                cart.append({
                    'product_id': product_id, 
                    'quantity': quantity, 
                    'grade_index': grade_index
                })
            
            session['cart'] = cart
            session.modified = True
            cart_count = sum(i['quantity'] for i in cart)
            return jsonify({'message': 'Added to cart', 'cart_count': cart_count}), 200
            
        except (ValueError, TypeError) as e:
            return jsonify({'error': 'Invalid data format: ' + str(e)}), 400
        except Exception as e:
            return jsonify({'error': 'Server error: ' + str(e)}), 500

@app.route('/api/cart/<int:item_index>', methods=['PUT', 'DELETE'])
def api_cart_item(item_index):
    cart = session.get('cart', [])
    if item_index < 0 or item_index >= len(cart):
        return jsonify({'error': 'Item not found'}), 404
    if request.method == 'DELETE':
        removed = cart.pop(item_index)
        session['cart'] = cart
        session.modified = True
        return jsonify({'message': 'Item removed', 'cart_count': sum(i['quantity'] for i in cart)})
    else:
        data = request.get_json() or {}
        try:
            quantity = int(data.get('quantity', cart[item_index]['quantity']))
        except (ValueError, TypeError):
            return jsonify({'error': 'Quantity must be a whole number'}), 400
        if quantity < 0:
            return jsonify({'error': 'Quantity cannot be negative'}), 400
        if quantity == 0:
            cart.pop(item_index)
        else:
            # Validate against available stock
            conn = get_db()
            row = conn.execute('SELECT stock FROM products WHERE id=?', (cart[item_index]['product_id'],)).fetchone()
            conn.close()
            available_stock = row['stock'] if row else 0
            if quantity > (available_stock or 0):
                return jsonify({'error': f'Only {available_stock} unit(s) available in stock'}), 400
            cart[item_index]['quantity'] = quantity
        session['cart'] = cart
        session.modified = True
        return jsonify({'message': 'Cart updated', 'cart_count': sum(i['quantity'] for i in cart)})

@app.route('/api/cart/count')
def api_cart_count():
    cart = session.get('cart', [])
    return jsonify({'count': sum(i['quantity'] for i in cart)})

@app.route('/api/checkout', methods=['POST'])
def api_checkout():
    data = request.get_json() or {}
    payment_method = str(data.get('payment_method', 'cod')).lower().strip()
    # SECURITY/BUSINESS RULE: only COD and UPI payments are accepted
    if payment_method not in ('cod', 'upi'):
        return jsonify({'error': 'Invalid payment method. Only COD and UPI are accepted.'}), 400
    customer_name = data.get('name', '')
    customer_phone = data.get('phone', '')
    customer_address = data.get('address', '')
    cart = session.get('cart', [])
    if not cart:
        return jsonify({'error': 'Cart is empty'}), 400
    if not customer_name or not customer_phone or not customer_address:
        return jsonify({'error': 'Name, phone and address are required'}), 400
    
    conn = get_db()
    import json as json_mod
    
    # Fetch global discount from settings (use global_discount_percent, fallback to global_discount for legacy)
    global_discount_percent = 0
    try:
        global_discount_row = conn.execute("SELECT value FROM settings WHERE key='global_discount_percent'").fetchone()
        if global_discount_row is None or not str(global_discount_row['value'] or '').strip():
            global_discount_row = conn.execute("SELECT value FROM settings WHERE key='global_discount'").fetchone()
        if global_discount_row and str(global_discount_row['value'] or '').strip():
            global_discount_percent = float(str(global_discount_row['value']).replace('%', '').strip()) or 0
    except (ValueError, TypeError):
        global_discount_percent = 0
    
    # Validate every cart item: quantity must be a positive integer within
    # available stock. Checkout is blocked if stock is insufficient.
    for item in cart:
        try:
            qty = int(item.get('quantity', 0))
        except (ValueError, TypeError):
            conn.close()
            return jsonify({'error': 'Invalid quantity in cart'}), 400
        if qty <= 0:
            conn.close()
            return jsonify({'error': 'Invalid quantity in cart'}), 400
        row = conn.execute('SELECT stock FROM products WHERE id=?', (item['product_id'],)).fetchone()
        if not row:
            conn.close()
            return jsonify({'error': 'A product in your cart is no longer available'}), 400
        if qty > (row['stock'] or 0):
            conn.close()
            return jsonify({'error': f'Insufficient stock for an item in your cart. Only {row["stock"]} unit(s) available.'}), 400
    
    # Calculate total with only admin-set global discount
    # NOTE: item prices in cart are ALREADY the final discounted prices - do NOT double-deduct MRP savings
    subtotal = 0
    order_items_snapshot = []
    for item in cart:
        row = conn.execute('SELECT * FROM products WHERE id=?', (item['product_id'],)).fetchone()
        if row:
            grades = []
            try: grades = json_mod.loads(row['grades'] or '[]')
            except: pass
            grade_idx = item.get('grade_index', 0)
            grade_price_str = grades[grade_idx]['price'] if grades and grade_idx < len(grades) else row['price']
            grade_name = grades[grade_idx].get('name', '') if grades and grade_idx < len(grades) else ''
            base_price_str = row['price']
            
            grade_price = float(re.sub(r'[₹,\s]', '', str(grade_price_str)) or 0)
            base_price = float(re.sub(r'[₹,\s]', '', str(base_price_str)) or 0)
            
            item_price = grade_price if grade_price > 0 else base_price
            qty = int(item.get('quantity', 1))
            subtotal += item_price * qty
            
            # SNAPSHOT: freeze name, weight/grade, price and quantity at order
            # time so old invoices stay correct even if the product changes later.
            order_items_snapshot.append({
                'product_id': item['product_id'],
                'grade_index': grade_idx,
                'quantity': qty,
                'name_en': row['name_en'],
                'name_hi': row['name_hi'],
                'variant': grade_name or row['weight'] or '',
                'unit_price': item_price,
            })
    
    # Apply ONLY global admin discount
    global_discount_amount = (subtotal * global_discount_percent) / 100
    
    # ---- Coupon validation & discount ----
    coupon_code = str(data.get('coupon_code', '') or '').strip().upper()
    coupon_discount = 0.0
    coupon_row = None
    if coupon_code:
        coupon_row = conn.execute(
            'SELECT * FROM coupons WHERE code=?', (coupon_code,)).fetchone()
        if not coupon_row or not coupon_row['is_active']:
            conn.close()
            return jsonify({'error': 'Invalid or inactive coupon code'}), 400
        try:
            if coupon_row['expiry_date'] and str(coupon_row['expiry_date']).strip():
                if date.today().isoformat() > str(coupon_row['expiry_date']).strip():
                    conn.close()
                    return jsonify({'error': 'This coupon has expired'}), 400
        except (ValueError, TypeError):
            pass
        min_amount = float(re.sub(r'[₹,\s]', '', str(coupon_row['min_order_amount'] or '0')) or 0)
        if subtotal < min_amount:
            conn.close()
            return jsonify({'error': f'This coupon requires a minimum order of ₹{min_amount:g}'}), 400
        usage_limit = int(coupon_row['usage_limit'] or 0)
        if usage_limit > 0 and int(coupon_row['used_count'] or 0) >= usage_limit:
            conn.close()
            return jsonify({'error': 'This coupon has reached its usage limit'}), 400
        if coupon_row['discount_type'] == 'flat':
            coupon_discount = min(float(re.sub(r'[₹,\s]', '', str(coupon_row['discount_value'])) or 0), subtotal)
        else:
            coupon_discount = subtotal * (float(str(coupon_row['discount_value']).replace('%', '').strip() or 0) / 100)
            coupon_discount = min(coupon_discount, subtotal)
    
    # ---- Shipping charge ----
    shipping_charge = 0.0
    free_shipping_min = 0.0
    try:
        ship_row = conn.execute("SELECT value FROM settings WHERE key='shipping_charge'").fetchone()
        shipping_charge = float(re.sub(r'[₹,\s]', '', str(ship_row['value'] or '0')) or 0) if ship_row else 0.0
    except (ValueError, TypeError):
        shipping_charge = 0.0
    try:
        free_min_row = conn.execute("SELECT value FROM settings WHERE key='free_shipping_min'").fetchone()
        free_shipping_min = float(re.sub(r'[₹,\s]', '', str(free_min_row['value'] or '0')) or 0) if free_min_row else 0.0
    except (ValueError, TypeError):
        free_shipping_min = 0.0
    amount_before_shipping = subtotal - global_discount_amount - coupon_discount
    if shipping_charge > 0 and free_shipping_min > 0 and amount_before_shipping >= free_shipping_min:
        shipping_charge = 0.0  # free shipping threshold reached
    
    total_discount = global_discount_amount + coupon_discount
    final_total = subtotal - total_discount + shipping_charge
    if final_total < 0:
        final_total = 0
    
    cur = conn.execute(
        'INSERT INTO orders (customer_id, customer_name, customer_phone, customer_address, items, total, status, subtotal, discount_amount, shipping_charge, coupon_code) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            session.get('customer_id') or (get_jwt_customer()[0]),
            customer_name, customer_phone, customer_address,
            json_mod.dumps(order_items_snapshot),
            '₹' + str(round(final_total, 2)), 'pending_' + payment_method,
            str(round(subtotal, 2)), str(round(total_discount, 2)),
            str(round(shipping_charge, 2)), coupon_code
        )
    )
    
    # Reduce stock after successful order placement
    for item in order_items_snapshot:
        conn.execute('UPDATE products SET stock = MAX(stock - ?, 0) WHERE id=?',
                     (item['quantity'], item['product_id']))
    
    # Increment coupon usage
    if coupon_row is not None:
        conn.execute('UPDATE coupons SET used_count = used_count + 1 WHERE id=?', (coupon_row['id'],))
    
    conn.commit()
    order_id = cur.lastrowid
    conn.close()
    
    # Clear cart
    session.pop('cart', None)
    session.modified = True
    
    return jsonify({
        'order_id': order_id,
        'total': '₹' + str(round(final_total, 2)),
        'subtotal': round(subtotal, 2),
        'discount': round(total_discount, 2),
        'coupon_discount': round(coupon_discount, 2),
        'shipping': round(shipping_charge, 2),
        'payment_method': payment_method,
        'message': 'Order placed successfully!'
    })

# ---------------- ADMIN PRODUCT MEDIA ----------------

@app.route('/admin/api/product-media/<int:pid>', methods=['POST'])
@login_required
def admin_api_product_media(pid):
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    filename = secure_filename(file.filename)
    name, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
        filename = f"{name}_{counter}{ext}"
        counter += 1
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    url = f'/static/uploads/{filename}'
    # Store in product_media table
    conn = get_db()
    conn.execute('INSERT INTO product_media (product_id, url, type) VALUES (?, ?, ?)',
                 (pid, url, 'video' if ext.lower() in ALLOWED_VIDEO_EXTENSIONS else 'image'))
    conn.commit()
    conn.close()
    return jsonify({'url': url, 'message': 'Media uploaded successfully'})

@app.route('/admin/api/product-media/<int:pid>', methods=['GET'])
@login_required
def admin_api_product_media_list(pid):
    conn = get_db()
    rows = conn.execute('SELECT * FROM product_media WHERE product_id=? ORDER BY id DESC', (pid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/admin/api/product-media/<int:mid>', methods=['DELETE'])
@login_required
def admin_api_product_media_delete(mid):
    conn = get_db()
    row = conn.execute('SELECT url FROM product_media WHERE id=?', (mid,)).fetchone()
    if row:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(row['url']))
        if os.path.exists(filepath):
            os.remove(filepath)
        conn.execute('DELETE FROM product_media WHERE id=?', (mid,))
        conn.commit()
    conn.close()
    return jsonify({'message': 'Media deleted'})

# ---------------- GENERAL MEDIA (Factory & Company) ----------------

@app.route('/admin/api/general-media', methods=['GET', 'POST'])
@login_required
def admin_api_general_media():
    conn = get_db()
    if request.method == 'GET':
        rows = conn.execute('SELECT * FROM general_media ORDER BY id DESC').fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    else:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        title = request.form.get('title', '')
        category = request.form.get('category', 'factory')
        
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
            filename = f"{name}_{counter}{ext}"
            counter += 1
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        url = f'/static/uploads/{filename}'
        
        conn.execute('INSERT INTO general_media (title, category, type, url) VALUES (?, ?, ?, ?)',
                     (title, category, 'video' if ext.lower() in ALLOWED_VIDEO_EXTENSIONS else 'image', url))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Media uploaded successfully', 'url': url}), 201

@app.route('/admin/api/general-media/<int:mid>', methods=['DELETE'])
@login_required
def admin_api_general_media_delete(mid):
    conn = get_db()
    row = conn.execute('SELECT url FROM general_media WHERE id=?', (mid,)).fetchone()
    if row:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(row['url']))
        if os.path.exists(filepath):
            os.remove(filepath)
        conn.execute('DELETE FROM general_media WHERE id=?', (mid,))
        conn.commit()
    conn.close()
    return jsonify({'message': 'Media deleted'})

@app.route('/api/general-media')
def api_general_media():
    conn = get_db()
    rows = conn.execute('SELECT * FROM general_media ORDER BY id DESC').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ---------------- PRODUCT REVIEWS API ----------------

@app.route('/api/products/<int:product_id>/reviews', methods=['GET', 'POST'])
def api_product_reviews(product_id):
    """Get or submit reviews for a product"""
    conn = get_db()
    
    if request.method == 'GET':
        # Get all reviews for this product
        reviews = conn.execute(
            'SELECT * FROM product_reviews WHERE product_id=? ORDER BY created_at DESC',
            (product_id,)
        ).fetchall()
        
        # Calculate average rating
        avg_rating = conn.execute(
            'SELECT AVG(rating) as avg FROM product_reviews WHERE product_id=?',
            (product_id,)
        ).fetchone()
        
        conn.close()
        
        return jsonify({
            'reviews': [dict(r) for r in reviews],
            'average_rating': round(avg_rating['avg'], 1) if avg_rating and avg_rating['avg'] else 0,
            'total_reviews': len(reviews)
        })
    
    else:  # POST - submit a review
        # Check if customer is logged in
        customer_id = session.get('customer_id')
        if not customer_id:
            customer_id, _ = get_jwt_customer()
        if not customer_id:
            return jsonify({'error': 'Please login to submit a review'}), 401
        
        data = request.get_json() or {}
        rating = data.get('rating')
        review_text = data.get('review_text', '').strip()
        
        # Validate rating
        if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
        
        # Get customer details
        customer = conn.execute(
            'SELECT name, phone FROM customers WHERE id=?',
            (customer_id,)
        ).fetchone()
        
        if not customer:
            conn.close()
            return jsonify({'error': 'Customer not found'}), 404
        
        # Enforce ONE review per customer per product
        existing = conn.execute(
            'SELECT id FROM product_reviews WHERE product_id=? AND customer_phone=?',
            (product_id, customer['phone'])).fetchone()
        if existing:
            conn.close()
            return jsonify({'error': 'You have already reviewed this product. You can edit or delete your review.'}), 400
        
        # Insert review
        conn.execute(
            'INSERT INTO product_reviews (product_id, customer_name, customer_phone, rating, review_text) VALUES (?, ?, ?, ?, ?)',
            (product_id, customer['name'], customer['phone'], rating, review_text)
        )
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Review submitted successfully!'}), 201

@app.route('/api/products/<int:product_id>/reviews', methods=['PUT'])
def api_review_update(product_id):
    """Edit the logged-in customer's own review for a product."""
    customer_id = _get_customer_id()
    if not customer_id:
        return jsonify({'error': 'Please login to edit a review'}), 401
    data = request.get_json() or {}
    rating = data.get('rating')
    review_text = (data.get('review_text', '') or '').strip()
    if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({'error': 'Rating must be between 1 and 5'}), 400
    conn = get_db()
    customer = conn.execute('SELECT name, phone FROM customers WHERE id=?', (customer_id,)).fetchone()
    if not customer:
        conn.close()
        return jsonify({'error': 'Customer not found'}), 404
    cur = conn.execute(
        'UPDATE product_reviews SET rating=?, review_text=? '
        'WHERE product_id=? AND customer_phone=?',
        (rating, review_text, product_id, customer['phone']))
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    if not updated:
        return jsonify({'error': 'Review not found'}), 404
    return jsonify({'message': 'Review updated successfully!'})

@app.route('/api/products/<int:product_id>/reviews', methods=['DELETE'])
def api_review_delete(product_id):
    """Delete the logged-in customer's own review for a product."""
    customer_id = _get_customer_id()
    if not customer_id:
        return jsonify({'error': 'Please login to delete a review'}), 401
    conn = get_db()
    customer = conn.execute('SELECT name, phone FROM customers WHERE id=?', (customer_id,)).fetchone()
    if not customer:
        conn.close()
        return jsonify({'error': 'Customer not found'}), 404
    cur = conn.execute(
        'DELETE FROM product_reviews WHERE product_id=? AND customer_phone=?',
        (product_id, customer['phone']))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    if not deleted:
        return jsonify({'error': 'Review not found'}), 404
    return jsonify({'message': 'Review deleted successfully!'})

@app.route('/api/my-reviews', methods=['GET'])
def api_my_reviews():
    """Get all reviews by the currently logged-in customer"""
    customer_id = session.get('customer_id')
    if not customer_id:
        customer_id, _ = get_jwt_customer()
    if not customer_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    conn = get_db()
    reviews = conn.execute(
        'SELECT pr.*, p.name_en as product_name FROM product_reviews pr JOIN products p ON pr.product_id = p.id WHERE pr.customer_phone = (SELECT phone FROM customers WHERE id=?) ORDER BY pr.created_at DESC',
        (customer_id,)
    ).fetchall()
    conn.close()
    
    return jsonify([dict(r) for r in reviews])

# ---------------- PUBLIC COUPON LISTING & VALIDATION ----------------

@app.route('/api/coupons', methods=['GET'])
def api_coupons_list():
    """Public listing of all ACTIVE, UNEXPIRED coupons.

    Used by the cart/checkout 'View & Apply Coupon' modal so customers can
    browse available offers without knowing the code in advance.
    """
    conn = get_db()
    rows = conn.execute('SELECT id, code, discount_type, discount_value, '
                        'expiry_date, min_order_amount, is_active, '
                        'usage_limit, used_count FROM coupons '
                        'ORDER BY id DESC').fetchall()
    conn.close()
    today = date.today().isoformat()
    coupons = []
    for r in rows:
        if not r['is_active']:
            continue  # skip inactive coupons
        expiry = (r['expiry_date'] or '').strip()
        if expiry:
            try:
                if today > expiry:
                    continue  # skip expired coupons
            except (ValueError, TypeError):
                pass
        coupons.append({
            'id': r['id'],
            'code': r['code'],
            'discount_type': r['discount_type'],
            'discount_value': r['discount_value'],
            'min_order_amount': r['min_order_amount'],
            'expiry_date': expiry,
            'used_count': int(r['used_count'] or 0),
            'usage_limit': int(r['usage_limit'] or 0),
        })
    return jsonify(coupons)


@app.route('/api/coupon/validate', methods=['POST'])
def api_coupon_validate():
    """Validate a coupon code against the current cart (nothing is stored)."""
    data = request.get_json() or {}
    coupon_code = str(data.get('coupon_code', '') or '').strip().upper()
    if not coupon_code:
        return jsonify({'valid': False, 'error': 'Enter a coupon code'}), 400
    cart = session.get('cart', [])
    conn = get_db()
    subtotal = 0
    for item in cart:
        row = conn.execute('SELECT price, grades FROM products WHERE id=?', (item['product_id'],)).fetchone()
        if row:
            grades = []
            try: grades = json.loads(row['grades'] or '[]')
            except: pass
            g_idx = item.get('grade_index', 0)
            price_str = grades[g_idx]['price'] if grades and g_idx < len(grades) else row['price']
            price = float(re.sub(r'[₹,\s]', '', str(price_str)) or 0)
            subtotal += price * int(item.get('quantity', 1))
    coupon = conn.execute('SELECT * FROM coupons WHERE code=?', (coupon_code,)).fetchone()
    conn.close()
    if not coupon or not coupon['is_active']:
        return jsonify({'valid': False, 'error': 'Invalid or inactive coupon code'}), 400
    if coupon['expiry_date'] and str(coupon['expiry_date']).strip():
        try:
            if date.today().isoformat() > str(coupon['expiry_date']).strip():
                return jsonify({'valid': False, 'error': 'This coupon has expired'}), 400
        except (ValueError, TypeError):
            pass
    min_amount = float(re.sub(r'[₹,\s]', '', str(coupon['min_order_amount'] or '0')) or 0)
    if subtotal < min_amount:
        return jsonify({'valid': False, 'error': f'This coupon requires a minimum order of ₹{min_amount:g}'}), 400
    usage_limit = int(coupon['usage_limit'] or 0)
    if usage_limit > 0 and int(coupon['used_count'] or 0) >= usage_limit:
        return jsonify({'valid': False, 'error': 'This coupon has reached its usage limit'}), 400
    if coupon['discount_type'] == 'flat':
        discount = min(float(re.sub(r'[₹,\s]', '', str(coupon['discount_value'])) or 0), subtotal)
    else:
        discount = subtotal * (float(str(coupon['discount_value']).replace('%', '').strip() or 0) / 100)
        discount = min(discount, subtotal)
    return jsonify({
        'valid': True,
        'code': coupon['code'],
        'discount': round(discount, 2),
        'discount_type': coupon['discount_type'],
        'description': (f"₹{float(re.sub(r'[₹,\\s]', '', str(coupon['discount_value'])) or 0):g} off"
                        if coupon['discount_type'] == 'flat'
                        else f"{float(str(coupon['discount_value']).replace('%', '').strip() or 0):g}% off")
    })

# ---------------- ADMIN COUPON MANAGEMENT ----------------

@app.route('/admin/api/coupons', methods=['GET', 'POST'])
@login_required
def admin_api_coupons():
    conn = get_db()
    if request.method == 'GET':
        rows = conn.execute('SELECT * FROM coupons ORDER BY id DESC').fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    data = request.get_json() or {}
    code = str(data.get('code', '') or '').strip().upper()
    if not code:
        conn.close()
        return jsonify({'error': 'Coupon code is required'}), 400
    discount_type = data.get('discount_type', 'percent')
    if discount_type not in ('percent', 'flat'):
        discount_type = 'percent'
    try:
        cur = conn.execute(
            'INSERT INTO coupons (code, discount_type, discount_value, expiry_date, min_order_amount, is_active, usage_limit) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            (code, discount_type, str(data.get('discount_value', '0') or '0'),
             str(data.get('expiry_date', '') or ''), str(data.get('min_order_amount', '0') or '0'),
             1 if data.get('is_active', 1) else 0, int(data.get('usage_limit', 0) or 0)))
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return jsonify({'id': new_id, 'message': 'Coupon created'}), 201
    except Exception:
        conn.rollback()
        conn.close()
        return jsonify({'error': 'Coupon code already exists or data invalid'}), 400

@app.route('/admin/api/coupons/<int:cid>', methods=['PUT', 'DELETE'])
@login_required
def admin_api_coupon(cid):
    conn = get_db()
    if request.method == 'DELETE':
        conn.execute('DELETE FROM coupons WHERE id=?', (cid,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Coupon deleted'})
    data = request.get_json() or {}
    discount_type = data.get('discount_type', 'percent')
    if discount_type not in ('percent', 'flat'):
        discount_type = 'percent'
    conn.execute(
        'UPDATE coupons SET code=?, discount_type=?, discount_value=?, expiry_date=?, min_order_amount=?, is_active=?, usage_limit=? WHERE id=?',
        (str(data.get('code', '') or '').strip().upper(), discount_type,
         str(data.get('discount_value', '0') or '0'), str(data.get('expiry_date', '') or ''),
         str(data.get('min_order_amount', '0') or '0'), 1 if data.get('is_active', 1) else 0,
         int(data.get('usage_limit', 0) or 0), cid))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Coupon updated'})

# ---------------- WISHLIST API ----------------

def _get_customer_id():
    cid = session.get('customer_id')
    if not cid:
        cid, _ = get_jwt_customer()
    return cid

@app.route('/api/wishlist', methods=['GET', 'POST'])
def api_wishlist():
    customer_id = _get_customer_id()
    if not customer_id:
        return jsonify({'error': 'Please login to use the wishlist'}), 401
    conn = get_db()
    if request.method == 'GET':
        rows = conn.execute(
            'SELECT p.* FROM wishlist w JOIN products p ON w.product_id = p.id '
            'WHERE w.customer_id=? ORDER BY w.created_at DESC', (customer_id,)).fetchall()
        ids = [r['id'] for r in conn.execute(
            'SELECT product_id AS id FROM wishlist WHERE customer_id=?', (customer_id,)).fetchall()]
        conn.close()
        return jsonify({'products': [dict(r) for r in rows], 'product_ids': ids})
    data = request.get_json() or {}
    try:
        product_id = int(data.get('product_id', 0))
    except (ValueError, TypeError):
        product_id = 0
    if not product_id:
        conn.close()
        return jsonify({'error': 'Valid product ID required'}), 400
    exists = conn.execute('SELECT id FROM products WHERE id=?', (product_id,)).fetchone()
    if not exists:
        conn.close()
        return jsonify({'error': 'Product not found'}), 404
    already = conn.execute('SELECT id FROM wishlist WHERE customer_id=? AND product_id=?',
                           (customer_id, product_id)).fetchone()
    if already:
        conn.execute('DELETE FROM wishlist WHERE id=?', (already['id'],))
        conn.commit()
        conn.close()
        return jsonify({'in_wishlist': False, 'message': 'Removed from wishlist'})
    conn.execute('INSERT INTO wishlist (customer_id, product_id) VALUES (?, ?)',
                 (customer_id, product_id))
    conn.commit()
    conn.close()
    return jsonify({'in_wishlist': True, 'message': 'Added to wishlist'}), 201

@app.route('/api/wishlist/<int:product_id>', methods=['DELETE'])
def api_wishlist_remove(product_id):
    customer_id = _get_customer_id()
    if not customer_id:
        return jsonify({'error': 'Please login to use the wishlist'}), 401
    conn = get_db()
    conn.execute('DELETE FROM wishlist WHERE customer_id=? AND product_id=?', (customer_id, product_id))
    conn.commit()
    conn.close()
    return jsonify({'in_wishlist': False, 'message': 'Removed from wishlist'})

# ---------------- REORDER (ADD AGAIN) ----------------

@app.route('/api/reorder', methods=['POST'])
def api_reorder():
    """Add items from a previous order back into the cart (stock validated)."""
    customer_id = _get_customer_id()
    if not customer_id:
        return jsonify({'error': 'Please login to reorder'}), 401
    data = request.get_json() or {}
    try:
        order_id = int(data.get('order_id', 0))
    except (ValueError, TypeError):
        order_id = 0
    if not order_id:
        return jsonify({'error': 'Valid order ID required'}), 400
    conn = get_db()
    order = conn.execute('SELECT * FROM orders WHERE id=? AND customer_id=?',
                         (order_id, customer_id)).fetchone()
    if not order:
        conn.close()
        return jsonify({'error': 'Order not found'}), 404
    try:
        items = json.loads(order['items'] or '[]')
    except (ValueError, TypeError):
        items = []
    cart = session.get('cart', [])
    added, skipped = 0, []
    for item in items:
        product_id = item.get('product_id')
        qty = int(item.get('quantity', 1) or 1)
        if not product_id or qty <= 0:
            continue
        row = conn.execute('SELECT stock FROM products WHERE id=?', (product_id,)).fetchone()
        if not row:
            skipped.append(f'Product #{product_id} no longer available')
            continue
        grade_idx = item.get('grade_index', 0)
        in_cart = next((c for c in cart
                        if c['product_id'] == product_id and c.get('grade_index', 0) == grade_idx), None)
        current_qty = in_cart['quantity'] if in_cart else 0
        room = (row['stock'] or 0) - current_qty
        if room <= 0:
            if 'Not enough stock for one or more items' not in skipped:
                skipped.append('Not enough stock for one or more items')
            continue
        add_qty = min(qty, room)
        if in_cart:
            in_cart['quantity'] += add_qty
        else:
            cart.append({'product_id': product_id, 'quantity': add_qty, 'grade_index': grade_idx})
        added += add_qty
    session['cart'] = cart
    session.modified = True
    conn.close()
    return jsonify({
        'message': f'{added} item(s) added to cart',
        'added': added,
        'skipped': skipped,
        'cart_count': sum(i['quantity'] for i in cart)
    })

# ---------------- ADMIN DASHBOARD STATS ----------------

@app.route('/admin/api/stats')
@login_required
def admin_api_stats():
    conn = get_db()
    total_orders = conn.execute('SELECT COUNT(*) AS c FROM orders').fetchone()['c']
    pending_orders = conn.execute("SELECT COUNT(*) AS c FROM orders WHERE status LIKE 'pending%'").fetchone()['c']
    delivered_orders = conn.execute("SELECT COUNT(*) AS c FROM orders WHERE status LIKE '%deliver%'").fetchone()['c']
    total_sales = 0.0
    for row in conn.execute('SELECT total FROM orders WHERE is_hidden=0'):
        try:
            total_sales += float(re.sub(r'[₹,\s]', '', str(row['total'] or '0')) or 0)
        except (ValueError, TypeError):
            pass
    low_stock_items = conn.execute(
        'SELECT id, name_en, name_hi, stock FROM products WHERE stock <= 10 ORDER BY stock ASC').fetchall()
    total_products = conn.execute('SELECT COUNT(*) AS c FROM products').fetchone()['c']
    recent_orders = conn.execute(
        'SELECT id, customer_name, customer_phone, total, status, created_at '
        'FROM orders ORDER BY id DESC LIMIT 10').fetchall()
    conn.close()
    return jsonify({
        'total_sales': round(total_sales, 2),
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'delivered_orders': delivered_orders,
        'total_products': total_products,
        'low_stock_count': len(low_stock_items),
        'low_stock': [dict(r) for r in low_stock_items],
        'recent_orders': [dict(r) for r in recent_orders],
    })

# ---------------- HEALTH & ERROR PAGES ----------------

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.errorhandler(404)
def handle_404(e):
    if request.path.startswith('/api') or request.path.startswith('/admin/api'):
        return jsonify({'error': 'Not found'}), 404
    return render_template('error.html', code=404,
                           title='Page Not Found',
                           message='Sorry, the page you are looking for does not exist.'), 404

@app.errorhandler(500)
def handle_500(e):
    if request.path.startswith('/api') or request.path.startswith('/admin/api'):
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('error.html', code=500,
                           title='Something Went Wrong',
                           message='An unexpected error occurred. Please try again later.'), 500

# ---------------- STARTUP ----------------

# Initialize database on module load (required for Gunicorn deployment)
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # SECURITY: never run with debug enabled in production
    app.run(host='0.0.0.0', port=port, debug=False)
