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
- **Default Password:** `jainzee123`
- ⚠️ **Change the password after first login** (Settings page)

## ☁️ Deploy to Render (Free)

1. Push this folder to a GitHub repository:
```bash
git init
git add .
git commit -m "Jainzee website"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/jainzee-website.git
git push -u origin main
```

2. Go to [render.com](https://render.com) and sign up

3. Click **"New +"** → **"Web Service"**

4. Connect your GitHub repository

5. Settings:
   - **Name:** `jainzee-website`
   - **Environment:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`

6. Add environment variable:
   - `SECRET_KEY` = any random string (e.g. `jainzee-super-secret-key`)

7. Click **"Create Web Service"**

8. Wait 2-3 minutes, then your website is LIVE! 🎉

## ☁️ Deploy to Railway (Alternative)

1. Push to GitHub (same as above)
2. Go to [railway.app](https://railway.app)
3. Click **"New Project"** → **"Deploy from GitHub repo"**
4. Select your repository
5. Railway auto-detects the Python app

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
- **Deployment:** Gunicorn + Render/Railway

---

© Jainzee Food Processing Industries. All Rights Reserved.