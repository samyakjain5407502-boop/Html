# -*- coding: utf-8 -*-
"""Restore wiped settings in jainzee.db (only fills empty values, preserves user data)."""
import sqlite3

DB = 'jainzee-website/jainzee.db'

# Values captured from the API before the wipe - only applied to keys that are currently empty
RESTORE = {
    'shop_name_en': 'Jainzee Food Processing Industries',
    'shop_name_hi': 'जैनज़ी फूड प्रोसेसिंग इंडस्ट्रीज़',
    'tagline_en': 'Pure & Premium Dry Fruits',
    'tagline_hi': 'शुद्ध और प्रीमियम ड्राई फ्रूट्स',
    'address_en': 'Siyaganj, Indore, Madhya Pradesh 452001',
    'address_hi': 'सियागंज, इंदौर, मध्य प्रदेश 452001',
    'phone': '+91 9752937733',
    'whatsapp': '+91 9752937733',
    'email': 'info@jainzee.in',
    'hours_en': 'Mon - Sun: 10:00 AM - 9:00 PM',
    'hours_hi': 'सोम - रवि: सुबह 10:00 - रात 9:00',
    'about_en': 'Jainzee Food Processing Industries is a trusted name for pure, hygienic and premium quality dry fruits. We source the finest cashews, pistachios, almonds, walnuts and raisins so you can enjoy nature\'s best, every single day.',
    'about_hi': 'जैनज़ी फूड प्रोसेसिंग इंडस्ट्रीज़ शुद्ध, स्वच्छ और प्रीमियम गुणवत्ता वाले ड्राई फ्रूट्स के लिए एक विश्वसनीय नाम है। हम सबसे बेहतरीन काजू, पिस्ता, बादाम, अखरोट और किशमिश लाते हैं ताकि आप हर दिन प्रकृति का सर्वश्रेष्ठ आनंद ले सकें।',
    'logo': '/static/uploads/WhatsApp_Image_2026-08-04_at_9.31.10_PM_3.jpeg',
    'upi_id': '',
}

conn = sqlite3.connect(DB)
cur = conn.cursor()

updated = []
skipped = []
for key, value in RESTORE.items():
    row = cur.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
    if row is None:
        # Key missing entirely - insert it
        cur.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
        updated.append((key, '<missing>', value))
    elif (row[0] or '').strip() == '' and key != 'upi_id' and value != '':
        # Empty value - restore it (but never restore empty upi_id)
        cur.execute('UPDATE settings SET value=? WHERE key=?', (value, key))
        updated.append((key, row[0], value))
    else:
        skipped.append((key, row[0]))

conn.commit()
conn.close()

print('=' * 60)
print('RESTORE SUMMARY (only empty keys filled)')
print('=' * 60)
for k, old, new in updated:
    print(f'RESTORED: {k} = {new[:60]}')
for k, v in skipped:
    print(f'LEFT: {k} = {v[:60]}')
print('=' * 60)
print(f'Restored {len(updated)} key(s) | Untouched {len(skipped)} key(s)')