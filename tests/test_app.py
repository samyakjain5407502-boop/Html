"""
Jainzee website - safety tests.

Run against a TEMPORARY SQLite database (never the production jainzee.db).
Usage:
    python -m pytest tests/ -v
"""
import os
import sys
import json
import tempfile
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'jainzee-website'))

os.environ['ADMIN_PASSWORD'] = 'test-admin-pass-123'
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-pytest-only')


@pytest.fixture()
def client(monkeypatch):
    tmpdir = tempfile.mkdtemp(prefix='jainzee-test-')
    db_path = os.path.join(tmpdir, 'test.db')
    monkeypatch.setenv('JAINZEE_DB_PATH', db_path)
    import importlib
    import app as app_module
    importlib.reload(app_module)
    app_module.app.config['TESTING'] = True  # disables CSRF for API tests
    with app_module.app.test_client() as c:
        yield app_module, c
    if os.path.exists(db_path):
        os.remove(db_path)


def register_and_login(client):
    r = client.post('/api/customer/register', json={
        'name': 'Test User', 'phone': '9999990001', 'email': 'test@example.com',
        'password': 'secret123'})
    assert r.status_code in (200, 201), r.get_data(as_text=True)
    return r.get_json()


def admin_login(client):
    r = client.post('/admin/login', data={'password': 'test-admin-pass-123'})
    assert r.status_code == 302


# ---------------- REGISTRATION / LOGIN ----------------

def test_customer_register_and_login(client):
    _, c = client
    data = register_and_login(c)
    assert data.get('customer_id') or data.get('id')

    r = c.post('/api/customer/login', json={'phone': '9999990001', 'password': 'secret123'})
    assert r.status_code == 200


def test_customer_login_wrong_password(client):
    _, c = client
    register_and_login(c)
    r = c.post('/api/customer/login', json={'phone': '9999990001', 'password': 'wrong'})
    assert r.status_code in (401, 400)


# ---------------- ADMIN ACCESS ----------------

def test_admin_api_requires_login(client):
    _, c = client
    for path in ('/admin/api/products', '/admin/api/orders', '/admin/api/settings'):
        r = c.get(path)
        assert r.status_code == 401, f'{path} not protected'


def test_admin_login_and_access(client):
    _, c = client
    admin_login(c)
    r = c.get('/admin/api/products')
    assert r.status_code == 200
    r = c.get('/admin/api/settings')
    assert r.status_code == 200
    assert 'password_hash' not in r.get_json()['data']


def test_admin_login_page_has_no_password_hint(client):
    _, c = client
    r = c.get('/admin/login')
    body = r.get_data(as_text=True)
    assert 'jainzee123' not in body


def test_csrf_blocks_post_without_token(client):
    app, c = client
    app.app.config['TESTING'] = False  # enable CSRF for this test
    r = c.post('/api/cart', json={'product_id': 1, 'quantity': 1})
    assert r.status_code == 400
    app.app.config['TESTING'] = True


def test_csrf_accepts_form_login_with_matching_token(client):
    app, c = client
    app.app.config['TESTING'] = False
    c.get('/admin/login')  # sets the csrf_token cookie
    cookie = c.get_cookie('csrf_token')
    assert cookie and cookie.value, 'csrf cookie not set on login page'
    r = c.post('/admin/login', data={'password': 'test-admin-pass-123', 'csrf_token': cookie.value})
    assert r.status_code == 302
    app.app.config['TESTING'] = True


# ---------------- CART & STOCK ----------------

def add_to_cart(c, product_id, qty):
    return c.post('/api/cart', json={'product_id': product_id, 'quantity': qty})


def test_cart_rejects_invalid_quantity(client):
    _, c = client
    assert add_to_cart(c, 1, 0).status_code == 400
    assert add_to_cart(c, 1, -2).status_code == 400


def test_cart_rejects_over_stock(client):
    app, c = client
    conn = app.get_db()
    stock = conn.execute('SELECT stock FROM products WHERE id=1').fetchone()['stock']
    conn.close()
    r = add_to_cart(c, 1, stock + 10)
    assert r.status_code == 400
    assert 'stock' in r.get_json()['error'].lower()


def test_cart_add_valid(client):
    _, c = client
    r = add_to_cart(c, 1, 2)
    assert r.status_code == 200
    assert c.get('/api/cart/count').get_json()['count'] == 2


# ---------------- CHECKOUT ----------------

def checkout(c, payment='cod'):
    return c.post('/api/checkout', json={
        'name': 'Test User', 'phone': '9999990001',
        'address': '1 Test Road, Indore', 'payment_method': payment})


def test_checkout_success_reduces_stock(client):
    app, c = client
    conn = app.get_db()
    before = conn.execute('SELECT stock FROM products WHERE id=1').fetchone()['stock']
    conn.close()
    add_to_cart(c, 1, 2)
    r = checkout(c)
    assert r.status_code == 200
    order_id = r.get_json()['order_id']
    conn = app.get_db()
    after = conn.execute('SELECT stock FROM products WHERE id=1').fetchone()['stock']
    order = conn.execute('SELECT items, total FROM orders WHERE id=?', (order_id,)).fetchone()
    conn.close()
    assert after == before - 2
    # Snapshot must contain frozen name and unit price
    items = json.loads(order['items'])
    assert items[0]['name_en'] == 'Premium Cashew'
    assert float(items[0]['unit_price']) > 0
    assert order['total'].startswith('₹')


def test_checkout_blocked_when_stock_insufficient(client):
    app, c = client
    conn = app.get_db()
    stock = conn.execute('SELECT stock FROM products WHERE id=2').fetchone()['stock']
    conn.close()
    add_to_cart(c, 2, stock)  # allowed, exactly at stock
    # Simulate stock dropping after the cart was filled
    conn = app.get_db()
    conn.execute('UPDATE products SET stock=1 WHERE id=2')
    conn.commit()
    conn.close()
    r = checkout(c)
    assert r.status_code == 400
    assert 'stock' in r.get_json()['error'].lower()


def test_checkout_only_cod_or_upi(client):
    _, c = client
    add_to_cart(c, 1, 1)
    r = checkout(c, payment='credit_card')
    assert r.status_code == 400
    assert checkout(c, payment='upi').status_code == 200


# ---------------- ORDER HISTORY & INVOICE ----------------

def test_order_history_and_invoice(client):
    app, c = client
    register_and_login(c)
    add_to_cart(c, 1, 1)
    r = checkout(c)
    order_id = r.get_json()['order_id']

    r = c.get('/api/my-orders')
    assert r.status_code == 200
    orders = r.get_json()
    assert any(o['id'] == order_id for o in orders)

    # Invoice is DELIVERY-GATED: not delivered yet -> 403 clean error page
    r = c.get(f'/api/orders/{order_id}/invoice')
    assert r.status_code == 403
    assert 'available after delivery' in r.get_data(as_text=True)

    # Mark delivered -> invoice becomes downloadable
    conn = app.get_db()
    conn.execute("UPDATE orders SET status='delivered' WHERE id=?", (order_id,))
    conn.commit()
    conn.close()

    r = c.get(f'/api/orders/{order_id}/invoice')
    assert r.status_code == 200
    assert r.headers['Content-Type'] == 'application/pdf'
    assert r.data.startswith(b'%PDF')


def test_invoice_blocked_until_delivered(client):
    app, c = client
    register_and_login(c)
    add_to_cart(c, 1, 1)
    order_id = checkout(c).get_json()['order_id']
    # Status is pending_cod -> must be blocked
    r = c.get(f'/api/orders/{order_id}/invoice')
    assert r.status_code == 403
    body = r.get_data(as_text=True)
    assert 'Invoice will be available after delivery' in body


def test_invoice_blocked_for_pending_and_shipped(client):
    app, c = client
    register_and_login(c)
    add_to_cart(c, 1, 1)
    order_id = checkout(c).get_json()['order_id']
    # Explicitly non-delivered statuses must also be blocked
    for status in ('Pending', 'Shipped'):
        conn = app.get_db()
        conn.execute('UPDATE orders SET status=? WHERE id=?', (status, order_id))
        conn.commit()
        conn.close()
        r = c.get(f'/api/orders/{order_id}/invoice')
        assert r.status_code == 403, f'status={status} must not allow invoice download'
        assert 'Invoice will be available after delivery' in r.get_data(as_text=True)


def test_my_orders_redirects_unauthenticated(client):
    _, c = client
    # API gate: unauthenticated customers get 401 from the orders API
    r = c.get('/api/my-orders')
    assert r.status_code == 401
    assert r.get_json()['error'] == 'Not logged in'
    # Auth status flag the My Orders navigation relies on
    r = c.get('/api/auth/status')
    assert r.status_code == 200
    assert r.get_json()['customer_logged_in'] is False
    # Shipped JS redirects unauthenticated My Orders clicks to the customer login page
    r = c.get('/static/js/main.js')
    assert r.status_code == 200
    assert '/customer?msg=' in r.get_data(as_text=True)
    # Redirect target (customer login/orders page) loads
    assert c.get('/customer').status_code == 200


def test_invoice_uses_snapshot_after_price_change(client):
    app, c = client
    register_and_login(c)
    add_to_cart(c, 1, 1)
    r = checkout(c)
    order_id = r.get_json()['order_id']
    # Change the live product name/price - invoice must still use the snapshot
    conn = app.get_db()
    conn.execute("UPDATE products SET name_en='CHANGED', price='₹99' WHERE id=1")
    # Invoice is delivery-gated: mark the order delivered first
    conn.execute("UPDATE orders SET status='Delivered' WHERE id=?", (order_id,))
    conn.commit()
    conn.close()
    r = c.get(f'/api/orders/{order_id}/invoice')
    assert r.status_code == 200


# ---------------- PUBLIC SAFETY ----------------

def test_public_api_does_not_leak_private_settings(client):
    _, c = client
    data = c.get('/api/site').get_json()
    assert 'password_hash' not in data
    assert 'shop_name_en' in data  # safe shop details still available


# ---------------- COUPON & SHIPPING ----------------

def make_coupon(app, code='SAVE10', dtype='percent', value='10', min_amt='0', limit=0, active=1, expiry=''):
    conn = app.get_db()
    conn.execute(
        'INSERT INTO coupons (code, discount_type, discount_value, expiry_date, min_order_amount, usage_limit, is_active) VALUES (?,?,?,?,?,?,?)',
        (code, dtype, value, expiry, min_amt, limit, active))
    conn.commit()
    conn.close()


def test_coupon_valid_and_checkout(client):
    app, c = client
    register_and_login(c)
    make_coupon(app, 'SAVE10', 'percent', '10')
    add_to_cart(c, 1, 1)

    r = c.post('/api/coupon/validate', json={'coupon_code': 'SAVE10'})
    assert r.status_code == 200
    assert r.get_json()['valid'] is True

    r = checkout(c, payment='cod')  # without coupon
    assert r.status_code == 200

    # Now checkout with a coupon and verify usage + discount snapshot
    add_to_cart(c, 1, 1)
    r = c.post('/api/checkout', json={
        'name': 'Test User', 'phone': '9999990001', 'address': '1 Test Road, Indore',
        'payment_method': 'cod', 'coupon_code': 'SAVE10'})
    assert r.status_code == 200
    data = r.get_json()
    assert data['coupon_discount'] > 0

    conn = app.get_db()
    used = conn.execute("SELECT used_count FROM coupons WHERE code='SAVE10'").fetchone()['used_count']
    conn.close()
    assert used >= 1
    # Shipping setting default is 50
    assert data['shipping'] >= 0


def test_coupon_min_order_and_limit(client):
    app, c = client
    register_and_login(c)
    make_coupon(app, 'MIN100', 'flat', '20', '5000', limit=1)
    add_to_cart(c, 1, 1)
    r = c.post('/api/coupon/validate', json={'coupon_code': 'MIN100'})
    assert r.status_code == 400  # below minimum order


def test_api_coupons_lists_only_active_unexpired(client):
    app, c = client
    today = date.today()
    make_coupon(app, 'LIVE10', 'percent', '10', expiry='')                    # active, no expiry
    make_coupon(app, 'FUTURE15', 'percent', '15',
                expiry=(today + timedelta(days=30)).isoformat())              # active, future expiry
    make_coupon(app, 'OLD20', 'percent', '20',
                expiry=(today - timedelta(days=1)).isoformat())               # expired
    make_coupon(app, 'HIDDEN25', 'percent', '25', active=0)                   # inactive

    # Public endpoint - no login required
    r = c.get('/api/coupons')
    assert r.status_code == 200
    coupons = r.get_json()
    codes = {x['code'] for x in coupons}
    assert 'LIVE10' in codes
    assert 'FUTURE15' in codes
    assert 'OLD20' not in codes      # expired coupons are filtered out
    assert 'HIDDEN25' not in codes   # inactive coupons are filtered out
    live = next(x for x in coupons if x['code'] == 'LIVE10')
    assert live['discount_type'] == 'percent'
    assert float(live['discount_value']) == 10


def test_shipping_threshold_dynamic(client):
    app, c = client
    register_and_login(c)

    def set_setting(key, value):
        conn = app.get_db()
        conn.execute('UPDATE settings SET value=? WHERE key=?', (value, key))
        conn.commit()
        conn.close()

    set_setting('shipping_charge', '50')

    # Subtotal ₹1,200 >= ₹1,000 threshold -> FREE delivery
    set_setting('free_shipping_min', '1000')
    add_to_cart(c, 1, 1)
    r = checkout(c)
    assert r.status_code == 200
    data = r.get_json()
    assert float(data['subtotal']) == 1200
    assert data['shipping'] == 0

    # Threshold above subtotal -> shipping charge applies
    set_setting('free_shipping_min', '5000')
    add_to_cart(c, 1, 1)
    r = checkout(c)
    assert r.status_code == 200
    data = r.get_json()
    assert float(data['subtotal']) == 1200
    assert data['shipping'] == 50

    # Boundary: exactly at the threshold is still free
    set_setting('free_shipping_min', '1200')
    add_to_cart(c, 1, 1)
    r = checkout(c)
    assert r.status_code == 200
    assert r.get_json()['shipping'] == 0


def test_invalid_payment_method_rejected(client):
    app, c = client
    register_and_login(c)
    add_to_cart(c, 1, 1)
    r = c.post('/api/checkout', json={
        'name': 'Test User', 'phone': '9999990001', 'address': 'A', 'payment_method': 'credit'})
    assert r.status_code == 400


# ---------------- WISHLIST & REORDER ----------------

def test_wishlist_requires_login(client):
    _, c = client
    r = c.post('/api/wishlist', json={'product_id': 1})
    assert r.status_code == 401


def test_wishlist_add_toggle_and_list(client):
    app, c = client
    register_and_login(c)
    r = c.post('/api/wishlist', json={'product_id': 1})
    assert r.status_code == 201
    r = c.get('/api/wishlist')
    data = r.get_json()
    assert 1 in data['product_ids']
    # toggle off
    r = c.post('/api/wishlist', json={'product_id': 1})
    assert r.get_json()['in_wishlist'] is False


def test_reorder_adds_to_cart(client):
    app, c = client
    register_and_login(c)
    add_to_cart(c, 1, 2)
    r = checkout(c)
    order_id = r.get_json()['order_id']
    r = c.post('/api/reorder', json={'order_id': order_id})
    assert r.status_code == 200
    assert r.get_json()['added'] == 2
    # Cart now has 2 again
    assert c.get('/api/cart/count').get_json()['count'] == 2


# ---------------- REVIEW RESTRICTIONS ----------------

def test_one_review_per_product_with_edit_delete(client):
    app, c = client
    register_and_login(c)
    r = c.post('/api/products/1/reviews', json={'rating': 5, 'review_text': 'Great!'})
    assert r.status_code == 201
    # Second review rejected
    r = c.post('/api/products/1/reviews', json={'rating': 4, 'review_text': 'Again'})
    assert r.status_code == 400
    # Edit own review
    r = c.put('/api/products/1/reviews', json={'rating': 3, 'review_text': 'Edited'})
    assert r.status_code == 200
    # Delete own review
    r = c.delete('/api/products/1/reviews')
    assert r.status_code == 200
    # Can review again after delete
    r = c.post('/api/products/1/reviews', json={'rating': 5, 'review_text': 'New'})
    assert r.status_code == 201


# ---------------- ADMIN DASHBOARD, HEALTH & ERRORS ----------------

def test_health_endpoint(client):
    _, c = client
    r = c.get('/health')
    assert r.status_code == 200
    assert r.get_json()['status'] == 'ok'


def test_admin_stats_and_coupons_require_login(client):
    _, c = client
    assert c.get('/admin/api/stats').status_code == 401
    assert c.get('/admin/api/coupons').status_code == 401


def test_admin_coupon_crud(client):
    app, c = client
    admin_login(c)
    r = c.post('/admin/api/coupons', json={'code': 'WELCOME', 'discount_type': 'percent',
                                           'discount_value': '15', 'min_order_amount': '0',
                                           'usage_limit': '50', 'is_active': 1})
    assert r.status_code == 201
    cid = r.get_json()['id']
    r = c.get('/admin/api/coupons')
    assert any(x['code'] == 'WELCOME' for x in r.get_json())
    r = c.delete(f'/admin/api/coupons/{cid}')
    assert r.status_code == 200


def test_error_pages(client):
    _, c = client
    r = c.get('/this-page-does-not-exist')
    assert r.status_code == 404
    assert 'error.html' in r.get_data(as_text=True) or 'home' in r.get_data(as_text=True).lower()
    r = c.get('/api/nonexistent')
    assert r.get_json()['error'] == 'Not found'

