"""Smoke test: premium UX layer wiring.

Verifies that every page renders, that premium.js / premium.css are served,
and that the templates reference them (plus the new skeleton markup).
Run: python smoke_premium.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jainzee-website'))

os.environ['ADMIN_PASSWORD'] = 'smoke-admin-pass'
os.environ.setdefault('SECRET_KEY', 'smoke-secret-key')
tmpdir = tempfile.mkdtemp()
os.environ['JAINZEE_DB_PATH'] = os.path.join(tmpdir, 'smoke.db')

import app as app_module

app_module.app.config['TESTING'] = True
client = app_module.app.test_client()

failures = []

def check(name, cond, detail=''):
    status = 'PASS' if cond else 'FAIL'
    print(f'[{status}] {name}' + (f' - {detail}' if detail and not cond else ''))
    if not cond:
        failures.append(name)

# Static assets are served
for path in ('/static/js/premium.js', '/static/css/premium.css'):
    r = client.get(path)
    check(f'{path} served', r.status_code == 200 and len(r.data) > 1000)

# Public pages render and include the premium layer
r = client.get('/')
html = r.get_data(as_text=True)
check('GET /', r.status_code == 200)
check('/ includes premium.js', 'premium.js' in html)
check('/ includes premium.css', 'premium.css' in html)
check('/ has product skeleton cards', 'skeleton-card' in html)
check('/ removed old spinner block', 'productsLoading' not in html)

for path in ('/cart', '/checkout', '/customer'):
    r = client.get(path)
    html = r.get_data(as_text=True)
    check(f'GET {path}', r.status_code == 200)
    check(f'{path} includes premium layer', 'premium.js' in html and 'premium.css' in html)

# Admin pages (login first)
r = client.post('/admin/login', data={'password': 'smoke-admin-pass'})
check('admin login', r.status_code == 302)

for path in ('/admin', '/admin/products', '/admin/settings', '/admin/orders', '/admin/coupons'):
    r = client.get(path)
    html = r.get_data(as_text=True)
    check(f'GET {path}', r.status_code == 200)
    check(f'{path} includes premium layer', 'premium.js' in html and 'premium.css' in html)

# Admin specifics
r = client.get('/admin/products')
html = r.get_data(as_text=True)
check('products table has skeleton rows', 'skeleton-row' in html)
check('save buttons pass "this" for busy state', 'saveProduct(this)' in html and 'saveQuickStock(this)' in html)

r = client.get('/admin/settings')
html = r.get_data(as_text=True)
check('settings skeleton overlay present', 'settingsSkeleton' in html)
check('save settings passes "this"', 'saveSettings(this)' in html)

r = client.get('/admin')
html = r.get_data(as_text=True)
check('dashboard stat skeletons', 'sk-num' in html)
check('dashboard list skeletons', 'sk-list' in html)

print()
if failures:
    print(f'{len(failures)} FAILURE(S):')
    for f in failures:
        print(' -', f)
    sys.exit(1)
print('ALL SMOKE CHECKS PASSED')
