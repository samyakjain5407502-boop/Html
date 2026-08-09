path = r'jainzee-website/static/css/style.css'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# Add the final targeted button override block at the end of the file
targeted_override = '''

/* ===== FINAL TARGETED GOLD BUTTON FIX - Force specific buttons to Shining Gold ===== */
/* Customer Login, Cart, My Orders, Explore Products, Contact Us - Gold + Black text/icons */

/* Customer Login top bar button */
.customer-panel-btn,
.customer-panel-btn:hover,
a.customer-panel-btn {
    background: linear-gradient(135deg, #FFD700 0%, #D4AC0D 100%) !important;
    color: #000000 !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 15px rgba(255, 215, 0, 0.5) !important;
    border: none !important;
}

/* Cart button */
.admin-panel-btn,
.admin-panel-btn:hover,
a.admin-panel-btn,
#cartLink {
    background: linear-gradient(135deg, #FFD700 0%, #D4AC0D 100%) !important;
    color: #000000 !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 15px rgba(255, 215, 0, 0.5) !important;
    border: none !important;
}

/* My Orders button */
#myOrdersBtn,
.mobile-orders-btn {
    background: linear-gradient(135deg, #FFD700 0%, #D4AC0D 100%) !important;
    color: #000000 !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 15px rgba(255, 215, 0, 0.5) !important;
    border: none !important;
}

/* Explore Products & Contact Us hero buttons */
.btn-primary,
.btn-primary:hover,
.btn-outline,
.btn-outline:hover {
    background: linear-gradient(135deg, #FFD700 0%, #D4AC0D 100%) !important;
    color: #000000 !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 15px rgba(255, 215, 0, 0.5) !important;
    border: none !important;
}

/* WhatsApp Share button */
.whatsapp-share-btn,
.whatsapp-share-btn:hover,
.btn-whatsapp,
.btn-whatsapp:hover {
    background: linear-gradient(135deg, #FFD700 0%, #D4AC0D 100%) !important;
    color: #000000 !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 15px rgba(255, 215, 0, 0.5) !important;
    border: none !important;
}

/* Force ALL icons/text inside these buttons to bold black */
.customer-panel-btn i,
.customer-panel-btn span,
.customer-panel-btn *,
.admin-panel-btn i,
.admin-panel-btn span,
.admin-panel-btn *,
#cartLink i,
#cartLink span,
#cartLink *,
#myOrdersBtn i,
#myOrdersBtn span,
#myOrdersBtn *,
.mobile-orders-btn i,
.mobile-orders-btn span,
.mobile-orders-btn *,
.btn-primary i,
.btn-primary span,
.btn-primary *,
.btn-outline i,
.btn-outline span,
.btn-outline *,
.whatsapp-share-btn i,
.whatsapp-share-btn span,
.whatsapp-share-btn *,
.btn-whatsapp i,
.btn-whatsapp span,
.btn-whatsapp *,
.cart-count-badge {
    color: #000000 !important;
}

/* Override any earlier white icon rules for cart */
.admin-panel-btn .fa-shopping-cart,
.cart-icon {
    color: #000000 !important;
}

/* Override navbar white text on gold buttons */
.navbar .admin-panel-btn,
.navbar .customer-panel-btn,
.navbar .whatsapp-share-btn,
.navbar .admin-panel-btn *,
.navbar .customer-panel-btn *,
.navbar .whatsapp-share-btn * {
    color: #000000 !important;
}

/* Add to Cart buttons - force gold with black text */
button.add-to-cart,
.add-to-cart-btn,
.btn-add-to-cart,
.add-to-cart,
button[onclick*="addToCart"],
.product-card button,
.modal-footer button {
    background: linear-gradient(135deg, #FFD700 0%, #D4AC0D 100%) !important;
    color: #000000 !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 15px rgba(255, 215, 0, 0.5) !important;
    border: none !important;
}

button.add-to-cart *,
.add-to-cart-btn *,
.btn-add-to-cart *,
.add-to-cart *,
button[onclick*="addToCart"] *,
.product-card button *,
.modal-footer button * {
    color: #000000 !important;
}
'''

# Append to end of file
c += targeted_override

with open(path, 'w', encoding='utf-8') as f:
    f.write(c)

print('Done - final targeted gold button fixes applied')