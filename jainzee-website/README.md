# 🌰 Jainzee Food Processing Industries - Website

A complete bilingual (Hindi/English) website for **Jainzee Food Processing Industries** - a dry fruits business located at **Siyaganj, Indore**.

## ✨ Features

### Public Website
- 🌐 **Bilingual** - Full Hindi/English language toggle (साथ ही हिंदी भी)
- 🥜 **Products Showcase** - Cashew, Pistachio, Almonds, Walnuts, Raisins
- 💰 **Price Display** - Shows current rate, old price (strikethrough) and OFF badge
- 📦 **Stock Status** - Shows "In Stock" / "Out of Stock" on each product
- 📍 **Address** - Siyaganj, Indore with Google Maps link
- 📱 **Fully Responsive** - Works on mobile, tablet, and desktop
- 🏪 **Store Information** - Address, phone, WhatsApp, email, opening hours

### Admin Panel (`/admin`)
- 🔐 **Secure Login** with password protection
- 📦 **Product Management**:
  - Add / Edit / Delete products
  - Update **stock quantity** (add/remove stock quickly)
  - Update **rates/prices** (current price + old price for discounts)
  - Upload product images
  - English + Hindi product names & descriptions
- 🏪 **Website Settings**:
  - Edit shop name (EN/HI), tagline, about us
  - Edit address, phone, WhatsApp, email, opening hours
  - Upload company logo
  - Change admin password
- 📊 **Dashboard** - Total products, total stock, low stock alerts

## 🚀 Quick Start (Local)

```bash
# 1. Go to project folder
cd jainzee-website

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py

# 4. Open in browser
# Website:  http://localhost:5000
# Admin:    http://localhost:5000/admin
```

## 🔑 Admin Login

- **URL:** `http://localhost:5000/admin`
- **Password:** set the `ADMIN_PASSWORD` environment variable before starting the app.
- If `ADMIN_PASSWORD` is not set, a strong random password is generated and printed **once** to the server console on first start.
- ⚠️ **Change the password after first login** (Settings page)

## 🔐 Environment Variables (required before deployment)

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Session/JWT signing key. **Required in production** (e.g. `python -c "import secrets; print(secrets.token_hex(32))"`). |
| `ADMIN_PASSWORD` | Admin panel password. Generated randomly (printed once to console) if not set. |
| `DATABASE_URL` | **PostgreSQL connection string** (e.g. `postgresql://user:pass@host:5432/db`). If set, the app uses Postgres. Omit for local SQLite. |
| `JAINZEE_DB_PATH` | Optional override of the SQLite database location (used by the test suite). Ignored when PostgreSQL is in use. |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Optional - enables Google Sign-In for customers. |
| `PORT` | Optional - server port (default 5000). |

Example (PowerShell):
```powershell
$env:SECRET_KEY="..."; $env:ADMIN_PASSWORD="..."; $env:DATABASE_URL="postgresql://..."; python app.py
```

## 🧪 Tests

Tests run against a **temporary SQLite database** (never the production DB):

```bash
python -m pytest tests/ -v
```

## 💾 Backups

SQLite backup (safe, online, keeps last 30 copies in `backups/`):
```bash
python scripts/backup_db.py
```
For PostgreSQL, use `pg_dump "$DATABASE_URL" > backups/jainzee_$(date +%F_%H%M%S).sql`.

## ❤️ Customer features
- Product **search** by name + filters (price range, in-stock, wishlist).
- **Wishlist** for logged-in customers.
- **Coupons** (managed in Admin → Coupons) with percentage/flat discount, expiry, min order, usage limits.
- **Reorder** / "Add Again" in My Orders.
- **One review per customer per product**, with edit/delete.
- **Shipping** charges with a free-shipping threshold (Admin → Settings).

## Admin dashboard
Shows total sales, total/pending/delivered orders, low-stock count, a recent-orders list, and a low-stock warning list.

## ☁️ Deploy to Vercel (Production)

**Live site:** https://html-jainzee.vercel.app

1. Push this folder to a GitHub repository:
```bash
git init
git add .
git commit -m "Jainzee website"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/jainzee-website.git
git push -u origin main
```

2. Go to [vercel.com](https://vercel.com) and sign up / log in with GitHub.

3. Click **"Add New..."** → **"Project"**, then import your GitHub repository.

4. Configure the project (Python / Flask):
   - **Framework Preset:** Other
   - **Install Command:** `pip install -r requirements.txt`
   - **Build Command:** leave empty
   - **Output Directory:** leave empty

5. Add environment variables (Project → **Settings** → **Environment Variables**):
   - `SECRET_KEY` – long random string, e.g. `python -c "import secrets; print(secrets.token_hex(32))"`
   - `ADMIN_PASSWORD` – your admin panel password
   - `DATABASE_URL` – PostgreSQL connection string (**recommended**; Vercel's filesystem is ephemeral, so a local SQLite file is not persisted)
   - `BLOB_READ_WRITE_TOKEN` – added automatically when you link a **Vercel Blob** store to the project. Required for media uploads (logo, product images/videos) in production.
   - `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` – only if Google Sign-In is enabled

6. Click **"Deploy"**. The first build takes roughly 1–3 minutes.

7. Your website is LIVE at **https://html-jainzee.vercel.app** 🎉

> **Google Sign-In:** add `https://html-jainzee.vercel.app/api/auth/google/callback`
> to the **Authorized redirect URIs** in the Google Cloud Console.

> **Media uploads:** Vercel's filesystem is read-only/ephemeral, so files cannot be saved
> to `static/uploads` there. When `BLOB_READ_WRITE_TOKEN` is set the app uploads logos,
> product images/videos and other media to **Vercel Blob** (via the `vercel_blob` Python
> SDK) and stores the returned CDN URL in the database. Without the token (local
> development) uploads still go to `static/uploads`.
>
> **Note:** a local SQLite database is not persisted between deployments - use an external
> database via `DATABASE_URL`.
> **If an upload fails:** the app prints a warning at boot when it detects it is running on
> Vercel without `BLOB_READ_WRITE_TOKEN`, and the upload then returns a readable `502` JSON
> error that names the variable - never a bare `500 Internal Server Error`. Fix it with
> `vercel env add BLOB_READ_WRITE_TOKEN production` (or Project Settings > Environment
> Variables in the Vercel dashboard) and redeploy.


> **Upload size limits:** Vercel Functions cap the request body at ~4.5 MB, and that limit is
> enforced *before* the app runs, so anything larger returns `413 FUNCTION_PAYLOAD_TOO_LARGE`.
> To make large photos work anyway, the admin panel (`static/js/admin.js`) resizes/compresses
> images **in the browser** before sending them (longest side capped at 2000 px, re-encoded as
> WebP with a JPEG fallback, skipped when the result would not be smaller). SVGs and GIFs are
> never rasterised. Videos are never re-encoded, so on Vercel they must stay under ~4.5 MB -
> for larger videos paste a hosted URL instead. Anything over the limit now fails with a readable
> JSON error instead of a bare 413 page. The effective limits are exposed to the admin UI via
> `GET /admin/api/upload-config`.
>
> **Accepted image types:** `png`, `jpg`, `jpeg`, `gif`, `webp`, `svg`, `avif`, `bmp`, `tiff`,
> `tif`, `heic`, `heif`. Video types: `mp4`, `webm`, `mov`, `avi`.
> (Note: browsers cannot display `heic`/`heif` on most platforms - those are accepted for
> upload, but exporting to WebP/JPEG is preferable for anything shown on the site.)

## ☁️ Deploy to other hosts (Railway / Heroku-style)

The app also runs on any Gunicorn-compatible host (the included `Procfile` starts `gunicorn app:app`):

1. Push to GitHub (same as above)
2. Go to [railway.app](https://railway.app)
3. Click **"New Project"** → **"Deploy from GitHub repo"**
4. Select your repository — Railway auto-detects the Python app

## 📁 Project Structure

```
jainzee-website/
├── app.py                  # Flask backend (API + Admin)
├── requirements.txt        # Python dependencies
├── Procfile                # For deployment (gunicorn)
├── README.md               # This file
├── jainzee.db              # SQLite database (auto-created)
├── static/
│   ├── css/
│   │   ├── style.css       # Public website styles
│   │   └── admin.css       # Admin panel styles
│   ├── js/
│   │   ├── main.js         # Public website JS (language toggle)
│   │   └── admin.js        # Admin panel JS
│   └── uploads/            # Uploaded images (logo, products)
└── templates/
    ├── index.html          # Public homepage
    └── admin/
        ├── login.html      # Admin login
        ├── dashboard.html  # Admin dashboard
        ├── products.html   # Product & stock management
        └── settings.html   # Website settings
```

## 📝 How to Use Admin Panel

### Updating Stock
1. Login to `/admin`
2. Go to **Products & Stock**
3. Click **"Stock"** button on any product
4. Either:
   - Enter **+/-** value to add/remove stock, OR
   - Enter new stock quantity directly
5. Optionally update rate in the same popup
6. Click **Update**

### Adding Products
1. Login to `/admin`
2. Go to **Products & Stock**
3. Click **"Add Product"**
4. Fill in English + Hindi details
5. Upload product image (or paste image URL)
6. Click **Save Product**

### Uploading Logo
1. Login to `/admin`
2. Go to **Settings**
3. Scroll to **Company Logo**
4. Click to upload your logo image
5. Click **Save All Settings**

## 🛠️ Technology

- **Backend:** Flask (Python)
- **Database:** SQLite (no setup needed)
- **Frontend:** HTML, CSS, JavaScript
- **Deployment:** Vercel (Python/Flask) · Gunicorn-compatible (Procfile)

---

© Jainzee Food Processing Industries. All Rights Reserved.