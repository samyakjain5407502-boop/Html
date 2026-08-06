// ==================== JAINZEE ADMIN JS ====================

let editingProductId = null;
let quickStockProductId = null;
let currentProducts = [];

// ==================== TOAST NOTIFICATIONS ====================

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// ==================== MODAL HELPERS ====================

function openModal(id) {
    document.getElementById(id).classList.add('active');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
}

// Close modal when clicking outside
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('active');
    }
});

// Close modal with Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.active').forEach(m => m.classList.remove('active'));
    }
});

// ==================== IMAGE UPLOAD ====================

async function handleVideoUpload(input, urlFieldId) {
    const file = input.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch('/admin/api/upload', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.error || 'Upload failed');
        }
        document.getElementById(urlFieldId).value = data.url;
        showToast('Video uploaded successfully!');
    } catch (e) {
        showToast(e.message, 'error');
    }
}

function addGradeRow(name = '', price = '') {
    const container = document.getElementById('gradesContainer');
    const row = document.createElement('div');
    row.className = 'grade-row';
    row.style.cssText = 'display: flex; gap: 10px; margin-bottom: 8px;';
    row.innerHTML = `
        <input type="text" class="grade-name" placeholder="Grade name (e.g. Premium)" style="flex: 1;" value="${name}">
        <input type="text" class="grade-price" placeholder="Price (e.g. ₹1,500)" style="flex: 1;" value="${price}">
        <button type="button" class="btn-sm btn-sm-delete" onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>
    `;
    container.appendChild(row);
}

function getGradesFromForm() {
    const grades = [];
    document.querySelectorAll('.grade-row').forEach(row => {
        const name = row.querySelector('.grade-name').value.trim();
        const price = row.querySelector('.grade-price').value.trim();
        if (name) grades.push({ name, price });
    });
    return grades;
}

function setGradesInForm(grades) {
    const container = document.getElementById('gradesContainer');
    container.innerHTML = '';
    if (grades && grades.length) {
        grades.forEach(g => addGradeRow(g.name, g.price));
    } else {
        addGradeRow();
    }
}

async function handleImageUpload(input, urlFieldId, previewId) {
    const file = input.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch('/admin/api/upload', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.error || 'Upload failed');
        }

        // Set the URL field
        document.getElementById(urlFieldId).value = data.url;

        // Show preview
        const preview = document.getElementById(previewId);
        if (preview) {
            const img = preview.querySelector('img');
            img.src = data.url;
            preview.style.display = 'block';
        }

        showToast('Image uploaded successfully!');
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// ==================== PRODUCTS MANAGEMENT ====================

async function loadProducts() {
    try {
        const res = await fetch('/admin/api/products');
        currentProducts = await res.json();
        renderProductsTable();
        updateDashboardStats();
    } catch (e) {
        showToast('Failed to load products', 'error');
    }
}

function getStockStatus(stock) {
    stock = parseInt(stock) || 0;
    if (stock <= 0) return { text: 'Out of Stock', class: 'stock-out' };
    if (stock <= 20) return { text: 'Low Stock', class: 'stock-low' };
    return { text: 'In Stock', class: 'stock-in' };
}

function renderProductsTable() {
    const tbody = document.getElementById('productsTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!currentProducts.length) {
        tbody.innerHTML = '<tr><td colspan="10" style="text-align: center; padding: 40px; color: #8a7362;">No products found. Click "Add Product" to create one.</td></tr>';
        return;
    }

    currentProducts.forEach(p => {
        const status = getStockStatus(p.stock);
        const image = p.image ? `<img src="${p.image}" alt="${p.name_en}" onerror="this.style.display='none'">` : '<span style="font-size: 1.5rem;">📦</span>';

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${image}</td>
            <td><strong>${p.name_en || ''}</strong></td>
            <td>${p.name_hi || ''}</td>
            <td>${p.sku || '-'}</td>
            <td><strong style="color: #b8860b;">${p.price || '-'}</strong></td>
            <td style="text-decoration: line-through; color: #999;">${p.old_price || '-'}</td>
            <td>${p.weight || '-'}</td>
            <td><strong>${p.stock}</strong></td>
            <td><span class="stock-badge ${status.class}">${status.text}</span></td>
            <td>
                <div class="table-actions">
                    <button class="btn-sm btn-sm-stock" onclick="openQuickStock(${p.id})"><i class="fas fa-boxes"></i> Stock</button>
                    <button class="btn-sm btn-sm-edit" onclick="openProductModal(${p.id})"><i class="fas fa-edit"></i> Edit</button>
                    <button class="btn-sm btn-sm-delete" onclick="deleteProduct(${p.id})"><i class="fas fa-trash"></i></button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function openProductModal(id = null) {
    editingProductId = id;
    document.getElementById('modalTitle').textContent = id ? 'Edit Product' : 'Add Product';

    // Reset form
    document.getElementById('pNameEn').value = '';
    document.getElementById('pNameHi').value = '';
    document.getElementById('pPrice').value = '';
    document.getElementById('pOldPrice').value = '';
    document.getElementById('pWeight').value = '';
    document.getElementById('pSku').value = '';
    document.getElementById('pStock').value = '';
    document.getElementById('pStatus').value = 'in_stock';
    document.getElementById('pDescEn').value = '';
    document.getElementById('pDescHi').value = '';
    document.getElementById('pImageUrl').value = '';
    document.getElementById('pImageInput').value = '';
    document.getElementById('pImagePreview').style.display = 'none';
    document.getElementById('pVideoUrl').value = '';
    document.getElementById('pVideoInput').value = '';
    setGradesInForm([]);

    // Load product data if editing
    if (id) {
        const product = currentProducts.find(p => p.id === id);
        if (product) {
            document.getElementById('pNameEn').value = product.name_en || '';
            document.getElementById('pNameHi').value = product.name_hi || '';
            document.getElementById('pPrice').value = product.price || '';
            document.getElementById('pOldPrice').value = product.old_price || '';
            document.getElementById('pWeight').value = product.weight || '';
            document.getElementById('pSku').value = product.sku || '';
            document.getElementById('pStock').value = product.stock || 0;
            document.getElementById('pDescEn').value = product.description_en || '';
            document.getElementById('pDescHi').value = product.description_hi || '';
            document.getElementById('pImageUrl').value = product.image || '';
            document.getElementById('pVideoUrl').value = product.video || '';

            // Load grades
            let grades = [];
            try { grades = JSON.parse(product.grades || '[]'); } catch(e) {}
            setGradesInForm(grades);

            const status = getStockStatus(product.stock);
            document.getElementById('pStatus').value = status.class.replace('stock-', '');

            if (product.image) {
                const preview = document.getElementById('pImagePreview');
                preview.querySelector('img').src = product.image;
                preview.style.display = 'block';
            }
        }
    }

    openModal('productModal');
}

async function saveProduct() {
    const nameEn = document.getElementById('pNameEn').value.trim();
    const nameHi = document.getElementById('pNameHi').value.trim();
    const stock = document.getElementById('pStock').value;
    const statusSel = document.getElementById('pStatus').value;

    if (!nameEn || !nameHi) {
        showToast('Name in both English and Hindi is required!', 'error');
        return;
    }

    // Validate stock
    let stockNum = parseInt(stock) || 0;

    const data = {
        name_en: nameEn,
        name_hi: nameHi,
        price: document.getElementById('pPrice').value.trim(),
        old_price: document.getElementById('pOldPrice').value.trim(),
        weight: document.getElementById('pWeight').value.trim(),
        sku: document.getElementById('pSku').value.trim(),
        stock: stockNum,
        description_en: document.getElementById('pDescEn').value.trim(),
        description_hi: document.getElementById('pDescHi').value.trim(),
        image: document.getElementById('pImageUrl').value.trim(),
        video: document.getElementById('pVideoUrl').value.trim(),
        grades: getGradesFromForm()
    };

    try {
        let res;
        if (editingProductId) {
            res = await fetch(`/admin/api/products/${editingProductId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        } else {
            res = await fetch('/admin/api/products', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        }

        const result = await res.json();
        if (!res.ok) {
            throw new Error(result.error || 'Failed to save product');
        }

        showToast(editingProductId ? 'Product updated successfully!' : 'Product added successfully!');
        closeModal('productModal');
        loadProducts();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function deleteProduct(id) {
    if (!confirm('Are you sure you want to delete this product?')) return;

    try {
        const res = await fetch(`/admin/api/products/${id}`, {
            method: 'DELETE'
        });
        const result = await res.json();
        if (!res.ok) {
            throw new Error(result.error || 'Failed to delete product');
        }
        showToast('Product deleted!');
        loadProducts();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// ==================== QUICK STOCK UPDATE ====================

function openQuickStock(id) {
    quickStockProductId = id;
    const product = currentProducts.find(p => p.id === id);
    if (!product) return;

    document.getElementById('stockModalProductName').textContent = product.name_en || '';
    document.getElementById('stockCurrent').value = product.stock || 0;
    document.getElementById('stockChange').value = '';
    document.getElementById('stockNew').value = '';
    document.getElementById('stockRate').value = product.price || '';

    openModal('stockModal');
}

async function saveQuickStock() {
    if (!quickStockProductId) return;
    const product = currentProducts.find(p => p.id === quickStockProductId);
    if (!product) return;

    const currentStock = parseInt(document.getElementById('stockCurrent').value) || 0;
    const change = parseInt(document.getElementById('stockChange').value) || 0;
    const newVal = document.getElementById('stockNew').value;
    const rate = document.getElementById('stockRate').value;

    // Calculate final stock: if new value provided use it, else current + change
    let finalStock;
    if (newVal !== '') {
        finalStock = parseInt(newVal) || 0;
    } else {
        finalStock = currentStock + change;
    }
    if (finalStock < 0) finalStock = 0;

    const data = {
        name_en: product.name_en || '',
        name_hi: product.name_hi || '',
        price: rate || product.price || '',
        old_price: product.old_price || '',
        weight: product.weight || '',
        sku: product.sku || '',
        stock: finalStock,
        description_en: product.description_en || '',
        description_hi: product.description_hi || '',
        image: product.image || '',
        video: product.video || '',
        grades: product.grades || '[]'
    };

    try {
        const res = await fetch(`/admin/api/products/${quickStockProductId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if (!res.ok) {
            throw new Error(result.error || 'Failed to update stock');
        }
        showToast('Stock updated successfully!');
        closeModal('stockModal');
        loadProducts();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// ==================== DASHBOARD STATS ====================

function updateDashboardStats() {
    const statStock = document.getElementById('statStock');
    const statLowStock = document.getElementById('statLowStock');
    const statProducts = document.getElementById('statProducts');

    if (statProducts) statProducts.textContent = currentProducts.length;

    const totalStock = currentProducts.reduce((sum, p) => sum + (parseInt(p.stock) || 0), 0);
    if (statStock) statStock.textContent = totalStock;

    const lowStockCount = currentProducts.filter(p => (parseInt(p.stock) || 0) <= 20).length;
    if (statLowStock) statLowStock.textContent = lowStockCount;
}

// ==================== SETTINGS MANAGEMENT ====================

async function loadSettings() {
    try {
        const res = await fetch('/admin/api/site');
        const data = await res.json();

        // Shop info
        setVal('sShopNameEn', data.shop_name_en);
        setVal('sShopNameHi', data.shop_name_hi);
        setVal('sTaglineEn', data.tagline_en);
        setVal('sTaglineHi', data.tagline_hi);
        setVal('sAboutEn', data.about_en);
        setVal('sAboutHi', data.about_hi);

        // Contact
        setVal('sAddressEn', data.address_en);
        setVal('sAddressHi', data.address_hi);
        setVal('sPhone', data.phone);
        setVal('sWhatsapp', data.whatsapp);
        setVal('sEmail', data.email);
        setVal('sHoursEn', data.hours_en);
        setVal('sHoursHi', data.hours_hi);

        // Logo
        setVal('sLogoUrl', data.logo || '');
        if (data.logo) {
            const preview = document.getElementById('sLogoPreview');
            preview.querySelector('img').src = data.logo;
            preview.style.display = 'block';
        }

        // Discount & Payment
        setVal('sGlobalDiscount', data.global_discount || '0');
        setVal('sUpiId', data.upi_id || '');
        
        // UPI QR Code preview (Base64 permanent storage)
        if (data.upi_qr_data) {
            const qrPreview = document.getElementById('upiQrPreview');
            if (qrPreview) {
                qrPreview.querySelector('img').src = data.upi_qr_data;
                qrPreview.style.display = 'block';
            }
        }
    } catch (e) {
        showToast('Failed to load settings', 'error');
    }
}

function setVal(id, value) {
    const el = document.getElementById(id);
    if (el) el.value = value || '';
}

async function saveSettings() {
    const data = {
        shop_name_en: document.getElementById('sShopNameEn').value.trim(),
        shop_name_hi: document.getElementById('sShopNameHi').value.trim(),
        tagline_en: document.getElementById('sTaglineEn').value.trim(),
        tagline_hi: document.getElementById('sTaglineHi').value.trim(),
        about_en: document.getElementById('sAboutEn').value.trim(),
        about_hi: document.getElementById('sAboutHi').value.trim(),
        address_en: document.getElementById('sAddressEn').value.trim(),
        address_hi: document.getElementById('sAddressHi').value.trim(),
        phone: document.getElementById('sPhone').value.trim(),
        whatsapp: document.getElementById('sWhatsapp').value.trim(),
        email: document.getElementById('sEmail').value.trim(),
        hours_en: document.getElementById('sHoursEn').value.trim(),
        hours_hi: document.getElementById('sHoursHi').value.trim(),
        logo: document.getElementById('sLogoUrl').value.trim(),
        global_discount: document.getElementById('sGlobalDiscount').value.trim(),
        upi_id: document.getElementById('sUpiId').value.trim()
    };

    const formData = new FormData();
    formData.append('data', JSON.stringify(data));
    
    // Append QR code file if selected
    const qrInput = document.getElementById('upiQrInput');
    if (qrInput.files && qrInput.files[0]) {
        formData.append('upi_qr_code', qrInput.files[0]);
    }

    try {
        const res = await fetch('/admin/api/site', {
            method: 'POST',
            body: formData
        });
        
        // Check if response is OK before parsing JSON
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({ error: 'Unknown error' }));
            throw new Error(errorData.error || `HTTP ${res.status}: ${res.statusText}`);
        }
        
        const result = await res.json();
        if (result.success) {
            showToast('✅ Settings saved successfully!', 'success');
            
            // Clear QR input after successful upload
            if (qrInput.files && qrInput.files[0]) {
                qrInput.value = '';
            }
            
            // Reload settings to show updated preview
            await loadSettings();
        } else {
            throw new Error(result.error || 'Failed to save settings');
        }
    } catch (e) {
        showToast('❌ ' + e.message, 'error');
        console.error('Save settings error:', e);
    }
}

// ==================== CHANGE PASSWORD ====================

async function changePassword() {
    const oldPw = document.getElementById('sOldPassword').value;
    const newPw = document.getElementById('sNewPassword').value;

    if (!oldPw || !newPw) {
        showToast('Please fill both password fields', 'error');
        return;
    }
    if (newPw.length < 6) {
        showToast('New password must be at least 6 characters', 'error');
        return;
    }

    try {
        const res = await fetch('/admin/api/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_password: oldPw, new_password: newPw })
        });
        const result = await res.json();
        if (!res.ok) {
            throw new Error(result.error || 'Failed to change password');
        }
        showToast('Password changed successfully!');
        document.getElementById('sOldPassword').value = '';
        document.getElementById('sNewPassword').value = '';
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// ==================== MAIN PAGE VIDEO UPLOAD ====================

async function uploadMainVideo(file) {
    const btn = document.getElementById('uploadVideoBtn');
    const msg = document.getElementById('videoUploadMsg');
    if (btn) btn.disabled = true;
    if (msg) msg.textContent = 'Uploading video... This may take a few seconds for large files.';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch('/admin/api/upload-main-video', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Upload failed');

        if (msg) {
            msg.innerHTML = '<span style="color: #28a745;"><i class="fas fa-check-circle"></i> Video uploaded successfully! It will now show on the main page.</span>';
        }
        showToast('Main page video updated successfully!');
    } catch (e) {
        if (msg) {
            msg.innerHTML = '<span style="color: #dc3545;"><i class="fas fa-times-circle"></i> Upload failed: ' + e.message + '</span>';
        }
        showToast('Upload failed: ' + e.message, 'error');
    } finally {
        if (btn) btn.disabled = false;
    }
}

// ==================== INIT ====================

document.addEventListener('DOMContentLoaded', () => {
    // Detect current page
    const hasProductsTable = document.getElementById('productsTableBody');
    const hasSettingsForm = document.getElementById('sShopNameEn');

    if (hasProductsTable) {
        loadProducts();
    }

    if (hasSettingsForm) {
        loadSettings();
        loadGeneralMedia();
    }

    // Main video upload form handler
    const mainVideoForm = document.getElementById('mainVideoUploadForm');
    if (mainVideoForm) {
        mainVideoForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const fileInput = document.getElementById('mainVideoInput');
            if (!fileInput.files || !fileInput.files[0]) {
                showToast('Please select a video file first!', 'error');
                return;
            }
            uploadMainVideo(fileInput.files[0]);
        });
    }
});

// ==================== UPI QR CODE UPLOAD ====================

async function handleUpiQrUpload(input) {
    const file = input.files[0];
    if (!file) return;

    const preview = document.getElementById('upiQrPreview');
    const reader = new FileReader();
    
    reader.onload = function(e) {
        preview.querySelector('img').src = e.target.result;
        preview.style.display = 'block';
    };
    
    reader.readAsDataURL(file);
}

// ==================== GENERAL MEDIA (Factory & Company) ====================

async function uploadGeneralMedia() {
    const title = document.getElementById('generalMediaTitle').value;
    const category = document.getElementById('generalMediaCategory').value;
    const fileInput = document.getElementById('generalMediaFileInput');
    const msgDiv = document.getElementById('generalMediaUploadMsg');

    if (!fileInput.files || !fileInput.files[0]) {
        msgDiv.innerHTML = '<span style="color: #dc3545;">Please select a file first.</span>';
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('title', title);
    formData.append('category', category);

    msgDiv.innerHTML = '<span style="color: #007bff;"><i class="fas fa-spinner fa-spin"></i> Uploading...</span>';

    try {
        const res = await fetch('/admin/api/general-media', {
            method: 'POST',
            body: formData,
            credentials: 'same-origin'
        });
        const data = await res.json();
        if (res.ok) {
            msgDiv.innerHTML = '<span style="color: #28a745;">✓ Media uploaded successfully!</span>';
            fileInput.value = '';
            document.getElementById('generalMediaTitle').value = '';
            loadGeneralMedia();
        } else {
            msgDiv.innerHTML = '<span style="color: #dc3545;">❌ ' + (data.error || 'Upload failed') + '</span>';
        }
    } catch(err) {
        msgDiv.innerHTML = '<span style="color: #dc3545;">❌ Upload failed. Server issue.</span>';
    }
}

async function loadGeneralMedia() {
    const mediaList = document.getElementById('generalMediaList');
    if (!mediaList) return;
    
    mediaList.innerHTML = '<p style="color: var(--text-light);">Loading...</p>';
    try {
        const res = await fetch('/admin/api/general-media');
        const media = await res.json();
        if (!media.length) {
            mediaList.innerHTML = '<p style="color: var(--text-light);">No media uploaded yet.</p>';
            return;
        }
        mediaList.innerHTML = '';
        media.forEach(m => {
            const div = document.createElement('div');
            div.style.cssText = 'position: relative; border-radius: 10px; overflow: hidden; border: 1px solid rgba(255,215,0,0.2);';
            if (m.type === 'video') {
                div.innerHTML = '<video controls style="width:100%; height:150px; object-fit:cover;"><source src="' + m.url + '" type="video/mp4"></video>';
            } else {
                div.innerHTML = '<img src="' + m.url + '" style="width:100%; height:150px; object-fit:cover;">';
            }
            const delBtn = document.createElement('button');
            delBtn.innerHTML = '<i class="fas fa-trash"></i>';
            delBtn.onclick = () => deleteGeneralMedia(m.id);
            delBtn.style.cssText = 'position: absolute; top: 5px; right: 5px; background: rgba(220,53,69,0.8); color: white; border: none; width: 25px; height: 25px; border-radius: 50%; cursor: pointer;';
            div.appendChild(delBtn);
            mediaList.appendChild(div);
        });
    } catch(e) {
        mediaList.innerHTML = '<p style="color: #dc3545;">Failed to load media.</p>';
    }
}

async function deleteGeneralMedia(mediaId) {
    if (!confirm('Delete this media?')) return;
    try {
        await fetch('/admin/api/general-media/' + mediaId, { method: 'DELETE' });
        loadGeneralMedia();
    } catch(e) {}
}
