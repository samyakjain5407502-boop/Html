import os
import re
import json
import sqlite3
from datetime import timedelta
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
app.secret_key = os.environ.get('SECRET_KEY', 'jainzee_permanent_secret_key_2026')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
# Keep customer & admin logged in for 30 days (persistent sessions)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

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
        'global_discount': '0',
        'upi_id': '',
        'upi_qr_code': '',
        'homepage_video_url': '',
        'global_discount_percent': '0'
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

@app.route('/admin/api/settings')
def admin_api_settings():
    """Public endpoint to fetch all settings (no login required for frontend)"""
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
        conn.close()
        return jsonify({'id': customer_id, 'name': name, 'message': 'Registration successful'}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Phone number already registered. Please login.'}), 400

@app.route('/api/customer/login', methods=['POST'])
def api_customer_login():
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
    session.permanent = True  # Keep logged in for 30 days
    session['customer_id'] = row['id']
    session['customer_name'] = row['name']
    return jsonify({'id': row['id'], 'name': row['name'], 'message': 'Login successful'})

# Alias endpoint: POST /api/login (same as customer login, for frontend convenience)
@app.route('/api/login', methods=['POST'])
def api_login():
    return api_customer_login()

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

@app.route('/api/my-orders', methods=['GET'])
def api_my_orders():
    """Get orders for the currently logged-in customer"""
    if not session.get('customer_id'):
        return jsonify({'error': 'Not logged in'}), 401
    
    conn = get_db()
    rows = conn.execute(
        'SELECT id, items, total, status, created_at FROM orders WHERE customer_id=? ORDER BY id DESC',
        (session['customer_id'],)
    ).fetchall()
    conn.close()
    
    orders = []
    for row in rows:
        order = dict(row)
        # Parse items to get summary
        try:
            import json as json_mod
            items = json_mod.loads(order.get('items', '[]'))
            # Create a summary of items
            item_summary = []
            for item in items:
                product_id = item.get('product_id')
                qty = item.get('quantity', 1)
                # Get product name
                conn = get_db()
                product = conn.execute('SELECT name_en, name_hi FROM products WHERE id=?', (product_id,)).fetchone()
                conn.close()
                if product:
                    name = product['name_en']
                    item_summary.append(f"{name} x{qty}")
                else:
                    item_summary.append(f"Product #{product_id} x{qty}")
            order['item_summary'] = ', '.join(item_summary) if item_summary else 'No items'
        except:
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
                                 'homepage_video_url']
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
    
    # Check if customer is logged in
    if not session.get('customer_id'):
        return jsonify({'error': 'Not logged in'}), 401
    
    conn = get_db()
    order = conn.execute('SELECT * FROM orders WHERE id=? AND customer_id=?', 
                        (order_id, session['customer_id'])).fetchone()
    
    if not order:
        conn.close()
        return jsonify({'error': 'Order not found'}), 404
    
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
        fontName='Helvetica-Bold'
    )
    
    # Header style
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#2c1810'),
        alignment=TA_LEFT,
        spaceAfter=6,
        fontName='Helvetica-Bold'
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
    
    # Company name
    shop_name = settings.get('shop_name_en', 'Jainzee Food Processing Industries')
    elements.append(Paragraph(shop_name, title_style))
    elements.append(Spacer(1, 12))
    
    # Company details
    address = settings.get('address_en', 'Siyaganj, Indore, Madhya Pradesh 452001')
    phone = settings.get('phone', '+91 98260 00000')
    email = settings.get('email', 'info@jainzee.in')
    
    elements.append(Paragraph(f"Address: {address}", normal_style))
    elements.append(Paragraph(f"Phone: {phone}", normal_style))
    elements.append(Paragraph(f"Email: {email}", normal_style))
    elements.append(Spacer(1, 20))
    
    # Invoice title
    invoice_title = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#b8860b'),
        alignment=TA_CENTER,
        spaceAfter=20,
        fontName='Helvetica-Bold'
    )
    elements.append(Paragraph("INVOICE", invoice_title))
    elements.append(Spacer(1, 12))
    
    # Order details table
    order_data = [
        ['Invoice #:', f"INV-{order['id']:06d}"],
        ['Order #:', str(order['id'])],
        ['Date:', order['created_at']],
        ['Customer Name:', order['customer_name']],
        ['Phone:', order['customer_phone']],
        ['Address:', order['customer_address']]
    ]
    
    order_table = Table(order_data, colWidths=[2.5*inch, 4*inch])
    order_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#b8860b')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#2c1810')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(order_table)
    elements.append(Spacer(1, 20))
    
    # Items table
    elements.append(Paragraph("Order Items:", header_style))
    elements.append(Spacer(1, 8))
    
    # Calculate subtotal
    subtotal = 0
    items_data = [['Item', 'Qty', 'Price', 'Total']]
    
    for item in items:
        product_id = item.get('product_id')
        qty = item.get('quantity', 1)
        
        # Get product details
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
    
    # Add subtotal, discount, and total rows
    items_data.append(['', '', '', ''])
    items_data.append(['', '', 'Subtotal:', f"₹{subtotal:.2f}"])
    
    # Check for discount
    discount_percent = 0
    try:
        discount_val = settings.get('global_discount_percent') or settings.get('global_discount', '0')
        discount_percent = float(str(discount_val).replace('%', '').strip()) or 0
    except:
        discount_percent = 0
    
    discount_amount = (subtotal * discount_percent) / 100
    final_total = subtotal - discount_amount
    
    if discount_percent > 0:
        items_data.append(['', '', f'Discount ({discount_percent}%):', f"-₹{discount_amount:.2f}"])
    
    items_data.append(['', '', 'Grand Total:', f"₹{final_total:.2f}"])
    
    items_table = Table(items_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
    items_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#b8860b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        
        # Data rows
        ('FONTNAME', (0, 1), (-1, -4), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -4), 10),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),
        ('TEXTCOLOR', (0, 1), (-1, -4), colors.HexColor('#2c1810')),
        ('BOTTOMPADDING', (0, 1), (-1, -4), 8),
        ('TOPPADDING', (0, 1), (-1, -4), 8),
        
        # Total rows
        ('FONTNAME', (2, -3), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (2, -3), (-1, -1), 11),
        ('TEXTCOLOR', (2, -3), (-1, -1), colors.HexColor('#b8860b')),
        ('LINEABOVE', (2, -3), (-1, -3), 1, colors.HexColor('#e8e0d5')),
        ('LINEABOVE', (2, -1), (-1, -1), 2, colors.HexColor('#b8860b')),
        ('BOTTOMPADDING', (2, -1), (-1, -1), 12),
        ('TOPPADDING', (2, -1), (-1, -1), 12),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 30))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#8a7362'),
        alignment=TA_CENTER,
        spaceAfter=6
    )
    elements.append(Paragraph("Thank you for your business!", footer_style))
    elements.append(Paragraph("For any queries, contact us at " + email, footer_style))
    
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
            
            cart = session.get('cart', [])
            
            # Check if same product+grade already in cart
            existing = None
            for i, item in enumerate(cart):
                if item['product_id'] == product_id and item.get('grade_index', 0) == grade_index:
                    existing = i
                    break
            
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
        quantity = int(data.get('quantity', cart[item_index]['quantity']))
        if quantity <= 0:
            cart.pop(item_index)
        else:
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
    payment_method = data.get('payment_method', 'cod')
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
    items_json = json_mod.dumps(cart)
    
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
    
    # Calculate total with only admin-set global discount
    # NOTE: item prices in cart are ALREADY the final discounted prices - do NOT double-deduct MRP savings
    subtotal = 0
    for item in cart:
        row = conn.execute('SELECT * FROM products WHERE id=?', (item['product_id'],)).fetchone()
        if row:
            grades = []
            try: grades = json_mod.loads(row['grades'] or '[]')
            except: pass
            grade_price_str = grades[item.get('grade_index', 0)]['price'] if grades and item.get('grade_index', 0) < len(grades) else row['price']
            base_price_str = row['price']
            
            grade_price = float(re.sub(r'[₹,\s]', '', str(grade_price_str)) or 0)
            base_price = float(re.sub(r'[₹,\s]', '', str(base_price_str)) or 0)
            
            item_price = grade_price if grade_price > 0 else base_price
            subtotal += item_price * item['quantity']
    
    # Apply ONLY global admin discount
    global_discount_amount = (subtotal * global_discount_percent) / 100
    final_total = subtotal - global_discount_amount
    
    cur = conn.execute(
        'INSERT INTO orders (customer_id, customer_name, customer_phone, customer_address, items, total, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (session.get('customer_id'), customer_name, customer_phone, customer_address, items_json, '₹' + str(round(final_total, 2)), 'pending_' + payment_method)
    )
    conn.commit()
    order_id = cur.lastrowid
    conn.close()
    
    # Clear cart
    session.pop('cart', None)
    session.modified = True
    
    return jsonify({
        'order_id': order_id, 
        'total': '₹' + str(round(final_total, 2)), 
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
        if not session.get('customer_id'):
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
            (session['customer_id'],)
        ).fetchone()
        
        if not customer:
            conn.close()
            return jsonify({'error': 'Customer not found'}), 404
        
        # Insert review
        conn.execute(
            'INSERT INTO product_reviews (product_id, customer_name, customer_phone, rating, review_text) VALUES (?, ?, ?, ?, ?)',
            (product_id, customer['name'], customer['phone'], rating, review_text)
        )
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Review submitted successfully!'}), 201

@app.route('/api/my-reviews', methods=['GET'])
def api_my_reviews():
    """Get all reviews by the currently logged-in customer"""
    if not session.get('customer_id'):
        return jsonify({'error': 'Not logged in'}), 401
    
    conn = get_db()
    reviews = conn.execute(
        'SELECT pr.*, p.name_en as product_name FROM product_reviews pr JOIN products p ON pr.product_id = p.id WHERE pr.customer_phone = (SELECT phone FROM customers WHERE id=?) ORDER BY pr.created_at DESC',
        (session['customer_id'],)
    ).fetchall()
    conn.close()
    
    return jsonify([dict(r) for r in reviews])

# ---------------- STARTUP ----------------

# Initialize database on module load (required for Gunicorn deployment)
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
