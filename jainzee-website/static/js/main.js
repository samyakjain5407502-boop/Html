// ==================== JAINZEE WEBSITE - MAIN JS ====================

let siteData = {};
let products = [];
let currentLang = localStorage.getItem('jainzee_lang') || 'en';

// Translation dictionary for static UI elements
const translations = {
    en: {
        'nav_home': 'Home',
        'nav_products': 'Products',
        'nav_about': 'About Us',
        'nav_contact': 'Contact',
        'explore_products': 'Explore Products',
        'contact_us': 'Contact Us',
        'our_products': 'Our Premium Products',
        'products_subtitle': 'Handpicked, hygienically processed & premium quality dry fruits',
        'why_choose': 'Why Choose Jainzee?',
        'feature_pure': '100% Pure',
        'feature_pure_desc': 'No adulteration, only pure & natural dry fruits',
        'feature_hygienic': 'Hygienic Processing',
        'feature_hygienic_desc': 'Modern food-grade processing facility',
        'feature_price': 'Best Prices',
        'feature_price_desc': 'Direct from processor, no middlemen',
        'feature_delivery': 'Bulk & Retail',
        'feature_delivery_desc': 'Available for home, business & bulk orders',
        'about_us': 'About Jainzee',
        'about_li1': 'Premium quality dry fruits',
        'about_li2': 'Hygienic food processing',
        'about_li3': 'Trusted by thousands of customers',
        'about_li4': 'Wholesale & retail available',
        'contact_us_title': 'Contact Us',
        'contact_subtitle': 'Visit our store or get in touch with us',
        'our_address': 'Our Address',
        'view_map': 'View on Map',
        'call_us': 'Call Us',
        'whatsapp_us': 'WhatsApp Us',
        'opening_hours': 'Opening Hours',
        'email_us': 'Email Us',
        'quick_links': 'Quick Links',
        'contact_info': 'Contact Info',
        'all_rights': 'All Rights Reserved.',
        'admin_login': 'Admin',
        'edit_website': 'Edit Website',
        'customer_login': 'Customer Login',
        'share_whatsapp': 'Share',
        'cart_title': 'Cart'
    },
    hi: {
        'nav_home': 'होम',
        'nav_products': 'उत्पाद',
        'nav_about': 'हमारे बारे में',
        'nav_contact': 'संपर्क',
        'explore_products': 'उत्पाद देखें',
        'contact_us': 'संपर्क करें',
        'our_products': 'हमारे प्रीमियम उत्पाद',
        'products_subtitle': 'चुने हुए, स्वच्छ प्रोसेस्ड और प्रीमियम गुणवत्ता वाले ड्राई फ्रूट्स',
        'why_choose': 'जैनज़ी ही क्यों?',
        'feature_pure': '100% शुद्ध',
        'feature_pure_desc': 'कोई मिलावट नहीं, केवल शुद्ध और प्राकृतिक ड्राई फ्रूट्स',
        'feature_hygienic': 'स्वच्छ प्रोसेसिंग',
        'feature_hygienic_desc': 'आधुनिक फूड-ग्रेड प्रोसेसिंग सुविधा',
        'feature_price': 'सबसे अच्छी कीमतें',
        'feature_price_desc': 'सीधे प्रोसेसर से, बिना बिचौलियों के',
        'feature_delivery': 'थोक और रिटेल',
        'feature_delivery_desc': 'घर, व्यापार और थोक ऑर्डर के लिए उपलब्ध',
        'about_us': 'जैनज़ी के बारे में',
        'about_li1': 'प्रीमियम गुणवत्ता वाले ड्राई फ्रूट्स',
        'about_li2': 'स्वच्छ खाद्य प्रोसेसिंग',
        'about_li3': 'हजारों ग्राहकों का विश्वास',
        'about_li4': 'थोक और रिटेल उपलब्ध',
        'contact_us_title': 'संपर्क करें',
        'contact_subtitle': 'हमारी दुकान पर आएं या हमसे जुड़ें',
        'our_address': 'हमारा पता',
        'view_map': 'मानचित्र देखें',
        'call_us': 'कॉल करें',
        'whatsapp_us': 'व्हाट्सएप करें',
        'opening_hours': 'खुलने का समय',
        'email_us': 'ईमेल करें',
        'quick_links': 'त्वरित लिंक',
        'contact_info': 'संपर्क जानकारी',
        'all_rights': 'सर्वाधिकार सुरक्षित।',
        'admin_login': 'एडमिन',
        'edit_website': 'वेबसाइट एडिट करें',
        'customer_login': 'ग्राहक लॉगिन',
        'share_whatsapp': 'शेयर करें',
        'cart_title': 'कार्ट'
    }
};

// ==================== WHATSAPP SHARE ====================

function shareOnWhatsApp(event) {
    event.preventDefault();
    const url = window.location.href;
    const text = encodeURIComponent('Check out Jainzee Food Processing Industries - Premium Dry Fruits! 🥜🌰\n\n' + url);
    window.open('https://wa.me/?text=' + text, '_blank');
}

// ==================== CART ====================

let cartCount = 0;

async function updateCartCount() {
    try {
        const res = await fetch('/api/cart/count');
        const data = await res.json();
        cartCount = data.count;
        const cartLink = document.getElementById('cartLink');
        if (cartLink) {
            let badge = cartLink.querySelector('.cart-count-badge');
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'cart-count-badge';
                cartLink.appendChild(badge);
            }
            badge.textContent = data.count;
            badge.style.display = data.count > 0 ? '' : 'none';
        }
    } catch(e) {}
}

// Universal Add to Cart function for Product Cards
async function addToCart(productId, gradeIndex = 0, quantity = 1) {
    try {
        const res = await fetch('/api/cart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                product_id: parseInt(productId),
                quantity: parseInt(quantity) || 1,
                grade_index: parseInt(gradeIndex) || 0
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to add to cart');

        // Update cart badge immediately
        await updateCartCount();
        
        // Show success alert/toast
        alert(currentLang === 'hi' ? 'कार्ट में जोड़ दिया गया!' : 'Added to cart!');
    } catch(e) {
        alert('Error: ' + e.message);
        console.error('Add to cart error:', e);
    }
}

// Expose globally for inline onclick handlers
window.addToCart = addToCart;

function openProductModal(product) {
    const modal = document.getElementById('productModal');
    if (!modal) return;
    
    // Populate product info
    const name = currentLang === 'hi' ? (product.name_hi || product.name_en) : product.name_en;
    const desc = currentLang === 'hi' ? (product.description_hi || product.description_en) : product.description_en;
    
    document.getElementById('modalProductName').textContent = name;
    document.getElementById('modalProductDesc').textContent = desc || '';
    document.getElementById('modalProductId').value = product.id;
    document.getElementById('modalQuantity').value = 1;
    
    // Populate grade/weight options
    const gradeSelect = document.getElementById('modalGradeSelect');
    gradeSelect.innerHTML = '';
    
    // Parse available weights from product.weight field (e.g., "500g / 1kg")
    const weightField = product.weight || '';
    const availableWeights = [];
    
    if (weightField.includes('500g') || weightField.includes('500')) {
        availableWeights.push('500g');
    }
    if (weightField.includes('1kg') || weightField.includes('1000g') || weightField.includes('1 kg')) {
        availableWeights.push('1kg');
    }
    
    // If no weights found in product, default to 500g and 1kg
    if (availableWeights.length === 0) {
        availableWeights.push('500g', '1kg');
    }
    
    // Create grades array with prices
    const grades = availableWeights.map((w, index) => {
        let price = product.price || '₹0';
        // Adjust price based on weight (1kg is typically 1.8x 500g price)
        if (w === '1kg') {
            const basePrice = parseFloat(String(price).replace(/[₹,\s]/g, '')) || 0;
            price = '₹' + Math.round(basePrice * 1.8);
        }
        return { name: w, price: price, index: index };
    });
    
    // Store grades on product for later use
    product._grades = grades;
    
    // Populate dropdown
    grades.forEach(g => {
        const opt = document.createElement('option');
        opt.value = g.index;
        opt.textContent = g.name + ' - ' + g.price;
        gradeSelect.appendChild(opt);
    });
    
    // Set max quantity based on stock
    document.getElementById('modalQuantity').max = product.stock || 999;
    
    // Show image
    const img = document.getElementById('modalProductImage');
    if (product.image) {
        img.src = product.image;
        img.style.display = '';
    } else {
        img.style.display = 'none';
    }
    
    modal.classList.add('active');
}

function updateModalPrice() {
    // This function can be used to update price display when grade changes
    // For now, the price is shown in the dropdown itself
}

function closeProductModal() {
    const modal = document.getElementById('productModal');
    if (modal) modal.classList.remove('active');
}

async function addToCartFromModal() {
    const productId = document.getElementById('modalProductId').value;
    const quantity = parseInt(document.getElementById('modalQuantity').value) || 1;
    const gradeIndex = parseInt(document.getElementById('modalGradeSelect').value) || 0;
    
    if (quantity < 1) {
        alert(currentLang === 'hi' ? 'कम से कम 1 चुनें' : 'Please select at least 1 item');
        return;
    }
    
    try {
        const res = await fetch('/api/cart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                product_id: parseInt(productId),
                quantity: quantity,
                grade_index: gradeIndex
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to add to cart');
        
        // Update cart count immediately
        await updateCartCount();
        
        // Close modal and show success
        closeProductModal();
        alert(currentLang === 'hi' ? 'कार्ट में जोड़ दिया गया!' : 'Added to cart!');
    } catch(e) {
        alert('Error: ' + e.message);
        console.error('Add to cart error:', e);
    }
}

// ==================== AUTH STATUS CHECK ====================

async function checkAuthStatus() {
    try {
        const res = await fetch('/api/auth/status');
        const data = await res.json();
        
        // Handle admin login
        if (data.admin_logged_in) {
            // Show admin edit buttons
            const adminBtn = document.getElementById('adminPanelBtn');
            const mobileAdmin = document.getElementById('mobileAdminLink');
            const floatingBtn = document.getElementById('floatingEditBtn');
            const footerAdmin = document.getElementById('footerAdminLink');
            if (adminBtn) adminBtn.style.display = '';
            if (mobileAdmin) mobileAdmin.style.display = '';
            if (floatingBtn) floatingBtn.style.display = '';
            if (footerAdmin) footerAdmin.style.display = '';
        }
        
        // Handle customer login - show customer name in header
        if (data.customer_logged_in) {
            // Fetch customer details
            const customerRes = await fetch('/api/customer/me');
            const customerData = await customerRes.json();
            if (customerData.logged_in && customerData.customer) {
                const customerName = customerData.customer.name;
                const loginBtn = document.getElementById('customerLoginBtn');
                const nameDisplay = document.getElementById('customerNameDisplay');
                const nameText = document.getElementById('customerNameText');
                const myOrdersBtn = document.getElementById('myOrdersBtn');
                
                if (loginBtn) loginBtn.style.display = 'none';
                if (nameDisplay) {
                    nameDisplay.style.display = 'inline-flex';
                    nameDisplay.style.alignItems = 'center';
                    nameDisplay.style.gap = '8px';
                }
                if (nameText) nameText.textContent = customerName;
                if (myOrdersBtn) myOrdersBtn.style.display = 'inline-flex';
                
                // Show My Orders in mobile menu
                const mobileMyOrders = document.getElementById('mobileMyOrdersLink');
                if (mobileMyOrders) mobileMyOrders.style.display = 'flex';
            }
        }
    } catch (e) {
        console.error('Failed to check auth status:', e);
    }
}

// ==================== MY ORDERS MODAL ====================

async function openMyOrdersModal() {
    const modal = document.getElementById('myOrdersModal');
    const ordersList = document.getElementById('myOrdersList');
    
    if (!modal) return;
    
    // Show modal with loading state
    modal.classList.add('active');
    ordersList.innerHTML = '<p style="text-align: center; padding: 40px; color: var(--text-light);">Loading orders...</p>';
    
    try {
        const res = await fetch('/api/my-orders');
        if (!res.ok) {
            if (res.status === 401) {
                ordersList.innerHTML = '<p style="text-align: center; padding: 40px; color: var(--text-light);">Please login to view your orders</p>';
                return;
            }
            throw new Error('Failed to load orders');
        }
        
        const orders = await res.json();
        
        if (!orders.length) {
            ordersList.innerHTML = '<p style="text-align: center; padding: 40px; color: var(--text-light);">No past orders found</p>';
            return;
        }
        
        // Display orders
        let html = '<div style="display: flex; flex-direction: column; gap: 15px;">';
        
        orders.forEach(order => {
            const statusClass = getStatusClass(order.status_display);
            
            // Build item breakdown HTML
            let itemsHtml = '';
            if (order.item_breakdown && order.item_breakdown.length > 0) {
                itemsHtml = '<div style="margin-bottom: 10px;">';
                order.item_breakdown.forEach(item => {
                    itemsHtml += `
                        <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(184,134,11,0.05); font-size: 0.9rem;">
                            <div style="flex: 1;">
                                <span style="color: var(--text); font-weight: 500;">${item.name}</span>
                                ${item.variant ? `<span style="color: var(--text-light); font-size: 0.85rem;"> (${item.variant})</span>` : ''}
                                <span style="color: var(--text-light);"> x${item.quantity}</span>
                            </div>
                            <span style="color: var(--text); font-weight: 600; margin-left: 10px;">${item.total}</span>
                        </div>
                    `;
                });
                itemsHtml += '</div>';
            }
            
            html += `
                <div style="background: white; border-radius: 12px; padding: 20px; border: 1px solid rgba(184,134,11,0.1); box-shadow: 0 2px 10px rgba(0,0,0,0.05);">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
                        <div>
                            <strong style="color: var(--dark); font-size: 1.1rem;">Order #${order.id}</strong>
                            <p style="color: var(--text-light); font-size: 0.85rem; margin-top: 4px;">
                                <i class="far fa-clock"></i> ${order.formatted_date || order.created_at}
                            </p>
                        </div>
                        <span class="order-status-badge ${statusClass}" style="padding: 6px 14px; border-radius: 20px; font-size: 0.8rem; font-weight: 600;">
                            ${order.status_display}
                        </span>
                    </div>
                    ${itemsHtml}
                    <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 10px; border-top: 1px solid rgba(184,134,11,0.1); margin-bottom: 10px;">
                        <span style="color: var(--text-light); font-size: 0.9rem;">Total Amount</span>
                        <strong style="color: var(--primary-dark); font-size: 1.2rem;">${order.total}</strong>
                    </div>
                    <button class="btn btn-primary" style="width: 100%; padding: 10px; font-size: 0.85rem;" onclick="downloadInvoice(${order.id})">
                        <i class="fas fa-download"></i> Download Invoice (PDF)
                    </button>
                </div>
            `;
        });
        
        html += '</div>';
        ordersList.innerHTML = html;
        
    } catch (e) {
        console.error('Error loading orders:', e);
        ordersList.innerHTML = '<p style="text-align: center; padding: 40px; color: #dc3545;">Failed to load orders. Please try again.</p>';
    }
}

function closeMyOrdersModal() {
    const modal = document.getElementById('myOrdersModal');
    if (modal) modal.classList.remove('active');
}

function getStatusClass(status) {
    switch(status) {
        case 'Pending':
            return 'status-pending';
        case 'Processing':
            return 'status-processing';
        case 'Dispatched':
            return 'status-dispatched';
        case 'Delivered':
            return 'status-delivered';
        case 'Cancelled':
            return 'status-cancelled';
        default:
            return 'status-pending';
    }
}

// ==================== PDF INVOICE DOWNLOAD ====================

function downloadInvoice(orderId) {
    // Open invoice in new tab for download
    const url = `/api/orders/${orderId}/invoice`;
    window.open(url, '_blank');
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

// ==================== MAIN BANNER VIDEO ====================

async function loadMainBannerVideo() {
    try {
        // Check if main_banner_video.mp4 exists by making a HEAD-like request
        const res = await fetch('/static/uploads/main_banner_video.mp4', { method: 'HEAD' });
        if (res.ok) {
            const card = document.getElementById('videoBannerCard');
            const video = document.getElementById('mainBannerVideo');
            const source = document.getElementById('mainBannerVideoSource');
            if (card && video && source) {
                // Add cache-busting timestamp so new uploads show immediately
                const url = '/static/uploads/main_banner_video.mp4?t=' + Date.now();
                source.src = url;
                video.load();
                card.style.display = '';
            }
        }
    } catch (e) {
        // Video doesn't exist yet - keep banner hidden
        console.log('No banner video uploaded yet');
    }
}

// ==================== API HELPERS ====================

async function fetchSiteData() {
    try {
        const res = await fetch('/api/site');
        siteData = await res.json();
        applySiteData();
    } catch (e) {
        console.error('Failed to load site data:', e);
    }
}

// Load saved settings on page init - ensures persistence after refresh
async function loadSiteSettings() {
    try {
        const res = await fetch('/admin/api/settings');
        const result = await res.json();
        if (!result.success) return;
        const settings = result.data || {};

        // Apply homepage video URL
        if (settings.homepage_video_url) {
            const videoSource = document.getElementById('mainBannerVideoSource');
            const videoEl = document.getElementById('mainBannerVideo');
            const videoCard = document.getElementById('videoBannerCard');
            if (videoSource) {
                videoSource.src = settings.homepage_video_url;
                if (videoEl) videoEl.load();
                if (videoCard) videoCard.style.display = '';
            }
        }

        // Apply global discount percent (used by cart/checkout calculations)
        if (settings.global_discount_percent) {
            window.globalDiscountPercent = parseFloat(settings.global_discount_percent) || 0;
        }

        // Apply UPI QR data (Base64) for checkout
        if (settings.upi_qr_data) {
            window.upiQrData = settings.upi_qr_data;
            const qrImage = document.getElementById('upiQrCodeImage');
            if (qrImage) {
                qrImage.src = settings.upi_qr_data;
                qrImage.style.display = '';
            }
        }

        // Apply UPI ID
        if (settings.upi_id) {
            window.upiId = settings.upi_id;
        }
    } catch (e) {
        console.error('Failed to load site settings:', e);
    }
}

async function fetchProducts() {
    try {
        const res = await fetch('/api/products');
        products = await res.json();
        renderProducts();
    } catch (e) {
        console.error('Failed to load products:', e);
    }
}

// ==================== APPLY SITE DATA ====================

function applySiteData() {
    // Shop name
    setText('heroShopName', currentLang === 'hi' ? siteData.shop_name_hi : siteData.shop_name_en);
    setText('navShopName', currentLang === 'hi' ? siteData.shop_name_hi : siteData.shop_name_en);
    setText('footerShopName', currentLang === 'hi' ? siteData.shop_name_hi : siteData.shop_name_en);
    setText('footerName', currentLang === 'hi' ? siteData.shop_name_hi : siteData.shop_name_en);
    document.title = (currentLang === 'hi' ? siteData.shop_name_hi : siteData.shop_name_en) + ' - Dry Fruits';

    // Tagline
    setText('heroTagline', currentLang === 'hi' ? siteData.tagline_hi : siteData.tagline_en);
    setText('footerAbout', currentLang === 'hi' ? siteData.tagline_hi : siteData.tagline_en);

    // About text
    setText('aboutText', currentLang === 'hi' ? siteData.about_hi : siteData.about_en);

    // Contact info
    setText('contactAddress', currentLang === 'hi' ? siteData.address_hi : siteData.address_en);
    setText('footerAddress', currentLang === 'hi' ? siteData.address_hi : siteData.address_en);
    setText('contactPhone', siteData.phone || '');
    setText('footerPhone', siteData.phone || '');
    setText('contactHours', currentLang === 'hi' ? siteData.hours_hi : siteData.hours_en);
    setText('contactEmail', siteData.email || '');

    // WhatsApp link
    const waLink = document.getElementById('whatsappLink');
    if (waLink && siteData.whatsapp) {
        waLink.href = 'https://wa.me/' + siteData.whatsapp;
    }

    // Logo - ALWAYS keep visible, NEVER hide it
    const logo = siteData.logo || '';
    const navLogo = document.getElementById('navLogo');
    const heroLogo = document.getElementById('heroLogo');
    
    // Nav logo: always visible, never hidden
    if (navLogo) {
        navLogo.style.display = 'inline-block';
        navLogo.style.visibility = 'visible';
        navLogo.style.opacity = '1';
        if (logo) {
            navLogo.src = logo;
        }
        // Remove any onerror that hides the logo
        navLogo.onerror = null;
    }
    
    // Hero logo: ALWAYS keep visible - use admin logo if set, otherwise keep the default logo.svg from HTML
    if (heroLogo) {
        if (logo) {
            heroLogo.src = logo;
        }
        heroLogo.style.display = 'inline-block';
        heroLogo.style.visibility = 'visible';
        heroLogo.style.opacity = '1';
    }
}

// ==================== PRODUCT REVIEWS ====================

let currentReviewProductId = null;
let currentReviewRating = 0;

async function loadProductReviews(productId) {
    try {
        const res = await fetch(`/api/products/${productId}/reviews`);
        const data = await res.json();
        
        const reviewsContainer = document.getElementById(`reviews-${productId}`);
        if (!reviewsContainer) return;
        
        // Update average rating display
        const ratingDisplay = document.getElementById(`rating-${productId}`);
        if (ratingDisplay && data.average_rating) {
            ratingDisplay.innerHTML = `
                <div class="stars">
                    ${generateStars(data.average_rating)}
                </div>
                <span class="rating-text">${data.average_rating} (${data.total_reviews} reviews)</span>
            `;
        }
        
        // Display reviews list
        if (!data.reviews.length) {
            reviewsContainer.innerHTML = '<p class="no-reviews">No reviews yet. Be the first to review!</p>';
            return;
        }
        
        let html = '<div class="reviews-list">';
        data.reviews.forEach(review => {
            html += `
                <div class="review-item">
                    <div class="review-header">
                        <span class="review-author">${review.customer_name}</span>
                        <span class="review-date">${new Date(review.created_at).toLocaleDateString()}</span>
                    </div>
                    <div class="review-rating">${generateStars(review.rating)}</div>
                    ${review.review_text ? `<p class="review-text">${review.review_text}</p>` : ''}
                </div>
            `;
        });
        html += '</div>';
        reviewsContainer.innerHTML = html;
        
    } catch (e) {
        console.error('Error loading reviews:', e);
    }
}

function generateStars(rating) {
    let stars = '';
    for (let i = 1; i <= 5; i++) {
        if (i <= rating) {
            stars += '<i class="fas fa-star"></i>';
        } else {
            stars += '<i class="fas fa-star star-empty"></i>';
        }
    }
    return stars;
}

function openReviewsModal(productId) {
    currentReviewProductId = productId;
    
    const modal = document.getElementById('reviewsModal');
    if (!modal) return;
    
    // Set product ID for review form
    document.getElementById('reviewProductId').value = productId;
    document.getElementById('reviewRating').value = 0;
    document.getElementById('reviewText').value = '';
    updateStarDisplay(0);
    
    // Show modal
    modal.classList.add('active');
    
    // Load reviews into modal
    loadReviewsIntoModal(productId);
}

function closeReviewsModal() {
    const modal = document.getElementById('reviewsModal');
    if (modal) modal.classList.remove('active');
}

async function loadReviewsIntoModal(productId) {
    const reviewsContent = document.getElementById('reviewsModalContent');
    if (!reviewsContent) return;
    
    reviewsContent.innerHTML = '<p style="text-align: center; padding: 20px; color: var(--text-light);">Loading reviews...</p>';
    
    try {
        const res = await fetch(`/api/products/${productId}/reviews`);
        const data = await res.json();
        
        if (!data.reviews || !data.reviews.length) {
            reviewsContent.innerHTML = '<p class="no-reviews">No reviews yet. Be the first to review!</p>';
            return;
        }
        
        let html = '<div class="reviews-list">';
        data.reviews.forEach(review => {
            html += `
                <div class="review-item">
                    <div class="review-header">
                        <span class="review-author">${review.customer_name}</span>
                        <span class="review-date">${new Date(review.created_at).toLocaleDateString()}</span>
                    </div>
                    <div class="review-rating">${generateStars(review.rating)}</div>
                    ${review.review_text ? `<p class="review-text">${review.review_text}</p>` : ''}
                </div>
            `;
        });
        html += '</div>';
        reviewsContent.innerHTML = html;
        
    } catch (e) {
        reviewsContent.innerHTML = '<p style="text-align: center; padding: 20px; color: #dc3545;">Failed to load reviews.</p>';
        console.error('Error loading reviews into modal:', e);
    }
}

// Alias for backward compatibility
function openReviewForm(productId) {
    openReviewsModal(productId);
}

function closeReviewModal() {
    closeReviewsModal();
}

function setRating(rating) {
    currentReviewRating = rating;
    document.getElementById('reviewRating').value = rating;
    updateStarDisplay(rating);
}

function updateStarDisplay(rating) {
    const stars = document.querySelectorAll('.star-rating-input .star');
    stars.forEach((star, index) => {
        if (index < rating) {
            star.classList.add('active');
        } else {
            star.classList.remove('active');
        }
    });
}

async function submitReview() {
    const rating = currentReviewRating;
    const reviewText = document.getElementById('reviewText').value.trim();
    
    if (rating === 0) {
        alert('Please select a rating');
        return;
    }
    
    try {
        const res = await fetch(`/api/products/${currentReviewProductId}/reviews`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rating, review_text: reviewText })
        });
        
        const data = await res.json();
        if (!res.ok) {
            if (res.status === 401) {
                alert('Please login to submit a review');
                return;
            }
            throw new Error(data.error || 'Failed to submit review');
        }
        
        alert('Review submitted successfully!');
        closeReviewModal();
        
        // Reload reviews
        loadProductReviews(currentReviewProductId);
        
    } catch (e) {
        alert('Error: ' + e.message);
        console.error('Submit review error:', e);
    }
}

// ==================== PRODUCTS RENDERING ====================

const productIcons = {
    'cashew': '🥜',
    'pistachio': '🌰',
    'almond': '🌰',
    'walnut': '🥥',
    'raisin': '🍇',
    'kishmish': '🍇'
};

function getProductIcon(name) {
    const lower = (name || '').toLowerCase();
    for (const key in productIcons) {
        if (lower.includes(key)) return productIcons[key];
    }
    return '🥜';
}

function formatPriceDisplay(price) {
    if (!price) return '';
    const clean = String(price).replace(/[₹,\s]/g, '');
    const num = parseFloat(clean);
    if (isNaN(num)) return price;
    return '₹' + num.toLocaleString('en-IN');
}

function renderProducts() {
    const grid = document.getElementById('productsGrid');
    if (!grid) return;
    grid.innerHTML = '';

    if (!products.length) {
        grid.innerHTML = '<p class="no-products">' + (currentLang === 'hi' ? 'कोई उत्पाद नहीं मिला' : 'No products found') + '</p>';
        return;
    }

    products.forEach((p, index) => {
        const card = document.createElement('div');
        card.className = 'product-card';
        card.style.animationDelay = (index * 0.1) + 's';

        const name = currentLang === 'hi' ? (p.name_hi || p.name_en) : p.name_en;
        const desc = currentLang === 'hi' ? (p.description_hi || p.description_en) : p.description_en;

        let imageHtml = '';
        if (p.image) {
            imageHtml = '<img src="' + p.image + '" alt="' + name + '" loading="lazy">';
        } else {
            imageHtml = '<div class="product-image-placeholder">' + getProductIcon(name) + '</div>';
        }

        // Video
        let videoHtml = '';
        if (p.video) {
            videoHtml = `
                <div class="product-video">
                    <video controls preload="metadata" style="width:100%; border-radius:8px; margin-bottom:10px;">
                        <source src="${p.video}" type="video/mp4">
                        ${currentLang === 'hi' ? 'आपका ब्राउज़र वीडियो सपोर्ट नहीं करता' : 'Your browser does not support video'}
                    </video>
                </div>`;
        }

        // Stock badge
        let stockHtml = '';
        const stockNum = parseInt(p.stock) || 0;
        if (stockNum > 0) {
            const stockText = currentLang === 'hi' ? 'स्टॉक में' : 'In Stock';
            stockHtml = '<span class="stock-badge stock-in" style="display:inline-flex;align-items:center;gap:5px;margin-top:10px;"><i class="fas fa-check-circle"></i> ' + stockText + '</span>';
        } else {
            const outText = currentLang === 'hi' ? 'स्टॉक खत्म' : 'Out of Stock';
            stockHtml = '<span class="stock-badge stock-out" style="display:inline-flex;align-items:center;gap:5px;margin-top:10px;"><i class="fas fa-times-circle"></i> ' + outText + '</span>';
        }

        // Rating display (compact - just average and count)
        const ratingHtml = `
            <div class="rating-display" id="rating-${p.id}" style="cursor: pointer;" onclick="event.stopPropagation(); openReviewsModal(${p.id})">
                <div class="stars">
                    <i class="fas fa-star star-empty"></i>
                    <i class="fas fa-star star-empty"></i>
                    <i class="fas fa-star star-empty"></i>
                    <i class="fas fa-star star-empty"></i>
                    <i class="fas fa-star star-empty"></i>
                </div>
                <span class="rating-text">No reviews</span>
            </div>
            <button class="btn btn-outline" style="width: 100%; margin-top: 8px; padding: 6px; font-size: 0.8rem; border: 1px solid var(--primary); color: var(--primary);" onclick="event.stopPropagation(); openReviewsModal(${p.id})">
                <i class="fas fa-comments"></i> Read Reviews
            </button>
        `;

        // Grades
        let grades = [];
        try { grades = JSON.parse(p.grades || '[]'); } catch(e) {}
        let gradeHtml = '';
        if (grades.length) {
            const gradeLabel = currentLang === 'hi' ? 'ग्रेड चुनें:' : 'Choose Grade:';
            gradeHtml = `
                <div class="grade-selector">
                    <label>${gradeLabel}</label>
                    <select class="grade-select" onchange="updateGradePrice(this, ${p.id})">
                        ${grades.map((g, i) => `<option value="${i}" ${i === 0 ? 'selected' : ''}>${g.name} - ${g.price}</option>`).join('')}
                    </select>
                </div>`;
        }

        // Price display with old price + discount
        let priceHtml = '<div class="product-price" id="price-' + p.id + '">' + formatPriceDisplay(p.price) + '</div>';
        if (p.old_price && p.price) {
            priceHtml = `
                <div class="product-price-row">
                    <div class="product-price" id="price-${p.id}">${formatPriceDisplay(p.price)}</div>
                    <div class="product-old-price">${formatPriceDisplay(p.old_price)}</div>
                    <span class="discount-badge">${currentLang === 'hi' ? 'छूट' : 'OFF'}</span>
                </div>`;
        }

        const addDisabled = stockNum <= 0 ? 'disabled' : '';
        const addBtnText = currentLang === 'hi' ? 'कार्ट में जोड़ें' : 'Add to Cart';
        
        // Create inline quantity and weight selector for direct add to cart
        const qtyId = 'qty-' + p.id;
        const weightId = 'weight-' + p.id;
        
        // Parse weights for inline selector
        const weightField = p.weight || '';
        const availableWeights = [];
        if (weightField.includes('500g') || weightField.includes('500')) availableWeights.push('500g');
        if (weightField.includes('1kg') || weightField.includes('1000g') || weightField.includes('1 kg')) availableWeights.push('1kg');
        if (availableWeights.length === 0) availableWeights.push('500g', '1kg');
        
        const weightOptions = availableWeights.map((w, i) => `<option value="${i}">${w}</option>`).join('');
        
        card.innerHTML = `
            <div class="product-image" onclick="openProductModal(${JSON.stringify(p).replace(/"/g, '"')})">
                ${imageHtml}
                <span class="product-badge">${currentLang === 'hi' ? 'प्रीमियम' : 'Premium'}</span>
            </div>
            <div class="product-info">
                <h3 onclick="openProductModal(${JSON.stringify(p).replace(/"/g, '"')})" style="cursor: pointer;">${name}</h3>
                ${priceHtml}
                <div class="product-weight"><i class="fas fa-box"></i> ${p.weight || ''}</div>
                ${gradeHtml}
                ${videoHtml}
                <p class="product-desc">${desc || ''}</p>
                ${stockHtml}
                
                <!-- Compact Rating Box -->
                <div class="rating-box" style="background: white; border: 1px solid rgba(184,134,11,0.15); border-radius: 10px; padding: 12px; margin-top: 10px; cursor: pointer;" onclick="event.stopPropagation(); openReviewsModal(${p.id})">
                    <div class="rating-display" id="rating-${p.id}" style="margin-bottom: 8px;">
                        <div class="stars">
                            <i class="fas fa-star star-empty"></i>
                            <i class="fas fa-star star-empty"></i>
                            <i class="fas fa-star star-empty"></i>
                            <i class="fas fa-star star-empty"></i>
                            <i class="fas fa-star star-empty"></i>
                        </div>
                        <span class="rating-text">No reviews</span>
                    </div>
                    <button class="btn btn-outline" style="width: 100%; padding: 6px; font-size: 0.8rem; border: 1px solid var(--primary); color: var(--primary); background: transparent;" onclick="event.stopPropagation(); openReviewsModal(${p.id})">
                        <i class="fas fa-comments"></i> Read Reviews
                    </button>
                </div>
                
                <!-- Inline Quantity & Weight Selector -->
                <div style="display: flex; gap: 10px; margin-top: 15px; align-items: center;">
                    <input type="number" id="${qtyId}" min="1" max="${stockNum || 999}" value="1" style="width: 70px; padding: 8px; text-align: center; border: 2px solid #e8e0d5; border-radius: 8px; background: white; color: var(--text); font-size: 0.9rem;" onclick="event.stopPropagation();">
                    <select id="${weightId}" class="grade-select" style="flex: 1; padding: 8px; font-size: 0.9rem;" onclick="event.stopPropagation();">
                        ${weightOptions}
                    </select>
                </div>
                
                <button class="btn btn-primary" style="width: 100%; margin-top: 10px; font-size: 0.9rem; padding: 12px;" onclick="event.stopPropagation(); addToCart(${p.id}, document.getElementById('${weightId}').value, document.getElementById('${qtyId}').value)" ${addDisabled}>
                    <i class="fas fa-shopping-cart"></i> ${addBtnText}
                </button>
            </div>
        `;
        grid.appendChild(card);
        
        // Load reviews for this product
        loadProductReviews(p.id);
    });
    
    // Ensure all cards are visible after rendering
    document.querySelectorAll('.product-card').forEach(card => {
        card.style.opacity = '1';
        card.style.transform = 'translateY(0)';
    });
}

function updateGradePrice(select, productId) {
    const product = products.find(p => p.id === productId);
    if (!product) return;
    let grades = [];
    try { grades = JSON.parse(product.grades || '[]'); } catch(e) {}
    const idx = parseInt(select.value) || 0;
    if (grades[idx]) {
        const priceEl = document.getElementById('price-' + productId);
        if (priceEl) priceEl.textContent = formatPriceDisplay(grades[idx].price);
    }
}

// ==================== LANGUAGE TOGGLE ====================

function setLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('jainzee_lang', lang);

    // Update toggle buttons
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.lang === lang);
    });

    // Update document lang attribute
    document.documentElement.lang = lang;
    document.documentElement.classList.toggle('lang-hi', lang === 'hi');

    // Apply translations to static elements
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.dataset.i18n;
        if (translations[lang] && translations[lang][key]) {
            el.textContent = translations[lang][key];
        }
    });

    // Apply dynamic site data
    applySiteData();

    // Re-render products with new language
    renderProducts();
}

function setText(id, text) {
    const el = document.getElementById(id);
    // Only update if text is a non-empty value - never wipe default HTML content
    if (el && text !== undefined && text !== null && String(text).trim() !== '') {
        el.textContent = text;
    }
}

// ==================== NAVBAR & MOBILE MENU ====================

function setupNavbar() {
    const hamburger = document.getElementById('hamburger');
    const mobileMenu = document.getElementById('mobileMenu');

    if (hamburger) {
        hamburger.addEventListener('click', () => {
            mobileMenu.classList.toggle('active');
        });
    }

    // Close menu when clicking a link
    mobileMenu.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            mobileMenu.classList.remove('active');
        });
    });

    // Navbar scroll effect
    window.addEventListener('scroll', () => {
        const navbar = document.querySelector('.navbar');
        if (window.scrollY > 50) {
            navbar.style.boxShadow = '0 4px 20px rgba(0,0,0,0.2)';
        } else {
            navbar.style.boxShadow = '0 2px 20px rgba(0,0,0,0.1)';
        }
    });
}

// ==================== INIT ====================

function init() {
    // Language toggle event listeners
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.addEventListener('click', () => setLanguage(btn.dataset.lang));
    });

    // Set current year in footer
    document.getElementById('currentYear').textContent = new Date().getFullYear();

    setupNavbar();

    // Check auth status first (admin edit buttons)
    checkAuthStatus();

    // Load cart count
    updateCartCount();

    // Load main banner video (if uploaded)
    loadMainBannerVideo();

    // Load factory & company media
    loadGeneralMedia();

    // Load saved settings (video, discount, QR) - ensures persistence after refresh
    loadSiteSettings();

    // Load data
    fetchSiteData().then(() => fetchProducts());

    // My Orders button click handler
    const myOrdersBtn = document.getElementById('myOrdersBtn');
    if (myOrdersBtn) {
        myOrdersBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openMyOrdersModal();
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    setLanguage(currentLang); // Apply saved language first
    init();
});

// ==================== GENERAL MEDIA (Factory & Company) ====================

async function loadGeneralMedia() {
    const mediaContainer = document.getElementById('generalMediaPlayer');
    if (!mediaContainer) return;
    
    try {
        const res = await fetch('/api/general-media');
        const media = await res.json();
        
        if (!media.length) {
            mediaContainer.innerHTML = '<p style="text-align: center; padding: 40px; color: var(--text-light); grid-column: 1 / -1;">No media uploaded yet. Check back soon!</p>';
            return;
        }
        
        mediaContainer.innerHTML = '';
        media.forEach(m => {
            const card = document.createElement('div');
            card.className = 'media-card';
            
            let mediaHtml = '';
            if (m.type === 'video') {
                mediaHtml = '<video controls preload="metadata" style="width:100%; height:300px; object-fit:cover;"><source src="' + m.url + '" type="video/mp4">Your browser does not support video.</video>';
            } else {
                mediaHtml = '<img src="' + m.url + '" alt="' + (m.title || 'Company Photo') + '" style="width:100%; height:300px; object-fit:cover;">';
            }
            
            card.innerHTML = mediaHtml + '<div class="media-card-caption"><h4>' + (m.title || 'Untitled') + '</h4><p>' + (m.category === 'factory' ? 'Factory Video' : 'Company Photo') + '</p></div>';
            mediaContainer.appendChild(card);
        });
    } catch(e) {
        mediaContainer.innerHTML = '<p style="text-align: center; padding: 40px; color: var(--text-light); grid-column: 1 / -1;">Failed to load media.</p>';
        console.error('Failed to load general media:', e);
    }
}

// Remove IntersectionObserver - it was hiding elements with opacity:0 that never became visible
document.addEventListener('DOMContentLoaded', function() {
    // Ensure ALL cards are always fully visible
    document.querySelectorAll('.product-card, .feature-card, .contact-card').forEach(card => {
        card.style.opacity = '1';
        card.style.transform = 'translateY(0)';
    });

    // Re-apply when products are rendered dynamically
    const grid = document.getElementById('productsGrid');
    if (grid) {
        const mutationObserver = new MutationObserver(() => {
            document.querySelectorAll('.product-card, .feature-card, .contact-card').forEach(card => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            });
        });
        mutationObserver.observe(grid, { childList: true });
    }
});
