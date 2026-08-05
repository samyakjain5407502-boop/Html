import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'jainzee.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'mp4', 'webm', 'mov', 'avi'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'mov', 'avi'}

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'jainzee-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- DATABASE HELPERS ----------------

def get_db():
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
    ''')

    # Migration: Add missing columns to existing products table (older DB versions)
    cur.execute("PRAGMA table_info(products)")
    existing_cols = [row[1] for row in cur.fetchall()]
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
        'password_hash': generate_password_hash('jainzee123'),
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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------- PUBLIC ROUTES ----------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/auth/status')
def api_auth_status():
    return jsonify({
        'admin_logged_in': bool(session.get('admin_logged_in')),
        'customer_logged_in': bool(session.get('customer_id'))
    })

@app.route('/api/site')
def api_site():
    conn = get_db()
    rows = conn.execute('SELECT key, value FROM settings').fetchall()
    conn.close()
    data = {}
    for r in rows:
        data[r['key']] = r['value']
    data.pop('password_hash', None)
    return jsonify(data)

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

@app.route('/api/customer/register', methods=['POST'])
def api_customer_register():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    password = data.get('password', '')
    if not name or not phone or not password:
        return jsonify({'error': 'Name, phone and password are required'}), 400
    if len(password) < 4:
        return jsonify({'error': 'Password must be at least 4 characters'}), 400
    conn = get_db()
    try:
        cur = conn.execute(
            'INSERT INTO customers (name, phone, email, address, password_hash) VALUES (?, ?, ?, ?, ?)',
            (name, phone, data.get('email', ''), data.get('address', ''), generate_password_hash(password))
        )
        conn.commit()
        customer_id = cur.lastrowid
        session['customer_id'] = customer_id
        session['customer_name'] = name
        conn.close()
        return jsonify({'id': customer_id, 'name': name, 'message': 'Registration successful'}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Phone number already registered. Please login.'}), 400

@app.route('/api/customer/login', methods=['POST'])
def api_customer_login():
    data = request.get_json() or {}
    phone = data.get('phone', '').strip()
    password = data.get('password', '')
    conn = get_db()
    row = conn.execute('SELECT * FROM customers WHERE phone=?', (phone,)).fetchone()
    conn.close()
    if not row or not check_password_hash(row['password_hash'], password):
        return jsonify({'error': 'Invalid phone or password'}), 400
    session['customer_id'] = row['id']
    session['customer_name'] = row['name']
    return jsonify({'id': row['id'], 'name': row['name'], 'message': 'Login successful'})

@app.route('/api/customer/logout', methods=['POST'])
def api_customer_logout():
    session.pop('customer_id', None)
    session.pop('customer_name', None)
    return jsonify({'message': 'Logged out'})

@app.route('/api/customer/me')
def api_customer_me():
    if not session.get('customer_id'):
        return jsonify({'logged_in': False})
    conn = get_db()
    row = conn.execute('SELECT id, name, phone, email, address FROM customers WHERE id=?', (session['customer_id'],)).fetchone()
    conn.close()
    if not row:
        return jsonify({'logged_in': False})
    return jsonify({'logged_in': True, 'customer': dict(row)})

@app.route('/api/customer/orders', methods=['GET', 'POST'])
def api_customer_orders():
    if request.method == 'GET':
        if not session.get('customer_id'):
            return jsonify({'error': 'Not logged in'}), 401
        conn = get_db()
        rows = conn.execute('SELECT * FROM orders WHERE customer_id=? ORDER BY id DESC', (session['customer_id'],)).fetchall()
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
        conn = get_db()
        cur = conn.execute(
            'INSERT INTO orders (customer_id, customer_name, customer_phone, customer_address, items, total) VALUES (?, ?, ?, ?, ?, ?)',
            (customer_id, name, phone, address, items_json, total)
        )
        conn.commit()
        order_id = cur.lastrowid
        conn.close()
        return jsonify({'id': order_id, 'message': 'Order placed successfully!'}), 201

# ---------------- ADMIN ORDERS ----------------

@app.route('/admin/orders')
@login_required
def admin_orders_page():
    return render_template('admin/orders.html')

@app.route('/admin/api/orders', methods=['GET'])
@login_required
def admin_api_orders():
    conn = get_db()
    rows = conn.execute('SELECT * FROM orders ORDER BY id DESC').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

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

# ---------------- ADMIN ROUTES ----------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        conn = get_db()
        row = conn.execute("SELECT value FROM settings WHERE key='password_hash'").fetchone()
        conn.close()
        if row and check_password_hash(row['value'], password):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Incorrect password! (Default: jainzee123)', 'error')
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
    conn = get_db()
    if request.method == 'GET':
        rows = conn.execute('SELECT key, value FROM settings').fetchall()
        conn.close()
        data = {r['key']: r['value'] for r in rows}
        data.pop('password_hash', None)
        return jsonify(data)
    else:
        data = request.get_json() or {}
        editable_keys = ['shop_name_en', 'shop_name_hi', 'tagline_en', 'tagline_hi',
                         'address_en', 'address_hi', 'phone', 'whatsapp', 'email',
                         'hours_en', 'hours_hi', 'about_en', 'about_hi', 'logo']
        for key in editable_keys:
            if key in data:
                conn.execute('UPDATE settings SET value=? WHERE key=?', (str(data[key]), key))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Settings saved successfully'})

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
    
    # Direct static/uploads/main_banner_video.mp4 me save hoga
    filename = 'main_banner_video.mp4'
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    return jsonify({'message': 'Main video updated successfully', 'url': '/static/uploads/main_banner_video.mp4'})

# ---------------- STARTUP ----------------

# Initialize database on module load (required for Gunicorn deployment)
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
