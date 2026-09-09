"""Re-sync the admin password hash in the SQLite DB with ADMIN_PASSWORD.

Reads ADMIN_PASSWORD from jainzee-website/.env (or the environment) and makes
sure the stored hash in the settings table (key 'password_hash') matches it.
Safe to run repeatedly: it only writes when the stored hash does not already
match the configured password.
"""
import os
import sys
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'jainzee-website'))

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, 'jainzee-website', '.env'), override=True)

from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.environ.get('JAINZEE_DB_PATH', os.path.join(BASE_DIR, 'jainzee-website', 'jainzee.db'))
password = (os.environ.get('ADMIN_PASSWORD') or '').strip()
if not password:
    sys.exit('ADMIN_PASSWORD is not set (.env or environment). Nothing to do.')
if not os.path.exists(DB_PATH):
    sys.exit(f'Database not found: {DB_PATH}')

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT value FROM settings WHERE key='password_hash'").fetchone()
if row and check_password_hash(row['value'], password):
    print('Admin password hash already in sync with ADMIN_PASSWORD. No change needed.')
else:
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('password_hash', ?)",
                 (generate_password_hash(password),))
    conn.commit()
    print('Admin password hash re-synced from ADMIN_PASSWORD.')
conn.close()