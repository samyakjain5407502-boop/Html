"""Safe automated database backup.

Backs up the SQLite database (the file pointed to by JAINZEE_DB_PATH or the
default jainzee.db) into backups/ with a timestamp. Keeps the last 30 backups.
The production database is NEVER modified by this script.

Usage:
    python scripts/backup_db.py
For PostgreSQL deployments use pg_dump instead:
    pg_dump "$DATABASE_URL" > backups/jainzee_$(date +%F_%H%M%S).sql
"""
import os
import sys
import shutil
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get('JAINZEE_DB_PATH', os.path.join(BASE_DIR, 'jainzee.db'))
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
KEEP = 30


def main():
    if not os.path.exists(DB_PATH):
        print(f'Database not found: {DB_PATH}')
        sys.exit(1)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = os.path.join(BACKUP_DIR, f'jainzee_{stamp}.db')
    # Use sqlite3's online backup API so the DB can be copied safely while running.
    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(dest)
    src.backup(dst)
    dst.close()
    src.close()
    print(f'Backup written: {dest}')
    backups = sorted(f for f in os.listdir(BACKUP_DIR) if f.startswith('jainzee_') and f.endswith('.db'))
    for old in backups[:-KEEP]:
        os.remove(os.path.join(BACKUP_DIR, old))
        print(f'Pruned old backup: {old}')


if __name__ == '__main__':
    main()
