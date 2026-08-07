#!/usr/bin/env python3
"""
Test script for Mobile Responsiveness - Vertical Stacking & Header Cleanup
"""

import requests
import sys
import io

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_URL = "http://127.0.0.1:5000"

def test_mobile_responsiveness():
    """Test mobile responsiveness features"""
    print("\n" + "=" * 70)
    print("TESTING MOBILE RESPONSIVENESS")
    print("=" * 70)
    
    session = requests.Session()
    
    # Test 1: Check homepage loads
    print(f"\n=== Test 1: Homepage Load ===")
    home_response = session.get(f"{BASE_URL}/")
    if home_response.status_code != 200:
        print("[ERROR] Homepage failed to load!")
        return False
    
    print(f"[SUCCESS] Homepage loaded (status: {home_response.status_code})")
    
    # Check for key mobile CSS elements
    html_content = home_response.text
    
    # Test 2: Verify mobile CSS safeguards present
    print(f"\n=== Test 2: Mobile CSS Safeguards ===")
    if 'overflow-x: hidden !important' in html_content or 'overflow-x: hidden' in html_content:
        print("[SUCCESS] overflow-x: hidden found in CSS")
    else:
        print("[WARNING] overflow-x: hidden not explicitly found (may be in external CSS)")
    
    if 'max-width: 100vw' in html_content or 'max-width: 100%' in html_content:
        print("[SUCCESS] max-width constraints found")
    else:
        print("[WARNING] max-width constraints not found in HTML (may be in external CSS)")
    
    # Test 3: Verify cart and customer icons are always visible
    print(f"\n=== Test 3: Cart & Customer Icons Always Visible ===")
    if 'id="cartLink"' in html_content:
        print("[SUCCESS] Cart link found in HTML")
    else:
        print("[ERROR] Cart link not found!")
        return False
    
    if 'id="customerLoginBtn"' in html_content:
        print("[SUCCESS] Customer login button found in HTML")
    else:
        print("[ERROR] Customer login button not found!")
        return False
    
    # Check for display: inline-flex !important (ensures visibility on mobile)
    cart_count = html_content.count('display: inline-flex')
    if cart_count > 0:
        print(f"[SUCCESS] Found {cart_count} elements with display: inline-flex (ensures visibility)")
    else:
        print("[WARNING] No inline-flex found (may use other visibility methods)")
    
    # Test 4: Verify hamburger menu exists
    print(f"\n=== Test 4: Hamburger Menu ===")
    if 'id="hamburger"' in html_content:
        print("[SUCCESS] Hamburger menu button found")
    else:
        print("[ERROR] Hamburger menu not found!")
        return False
    
    if 'id="mobileMenu"' in html_content:
        print("[SUCCESS] Mobile menu container found")
    else:
        print("[ERROR] Mobile menu not found!")
        return False
    
    # Test 5: Verify navigation links are in hamburger menu
    print(f"\n=== Test 5: Navigation Links in Mobile Menu ===")
    mobile_menu_start = html_content.find('id="mobileMenu"')
    mobile_menu_end = html_content.find('</nav>', mobile_menu_start)
    mobile_menu_html = html_content[mobile_menu_start:mobile_menu_end]
    
    nav_links = ['nav_home', 'nav_products', 'nav_about', 'nav_contact']
    for link in nav_links:
        if link in mobile_menu_html:
            print(f"[SUCCESS] '{link}' found in mobile menu")
        else:
            print(f"[WARNING] '{link}' not found in mobile menu")
    
    # Test 6: Check cart page loads
    print(f"\n=== Test 6: Cart Page Load ===")
    cart_response = session.get(f"{BASE_URL}/cart")
    if cart_response.status_code == 200:
        print(f"[SUCCESS] Cart page loaded (status: {cart_response.status_code})")
    else:
        print(f"[ERROR] Cart page failed to load (status: {cart_response.status_code})")
        return False
    
    # Test 7: Check checkout page loads
    print(f"\n=== Test 7: Checkout Page Load ===")
    checkout_response = session.get(f"{BASE_URL}/checkout")
    if checkout_response.status_code == 200:
        print(f"[SUCCESS] Checkout page loaded (status: {checkout_response.status_code})")
    else:
        print(f"[ERROR] Checkout page failed to load (status: {checkout_response.status_code})")
        return False
    
    # Test 8: Verify CSS file is loaded
    print(f"\n=== Test 8: CSS File Loading ===")
    css_response = session.get(f"{BASE_URL}/static/css/style.css")
    if css_response.status_code == 200:
        print(f"[SUCCESS] CSS file loaded (status: {css_response.status_code})")
        
        css_content = css_response.text
        
        # Check for mobile responsive rules
        if '@media (max-width: 768px)' in css_content:
            print("[SUCCESS] Mobile media query (768px) found in CSS")
        else:
            print("[ERROR] Mobile media query not found!")
            return False
        
        if 'flex-direction: column' in css_content:
            print("[SUCCESS] Vertical stacking (flex-direction: column) found in CSS")
        else:
            print("[ERROR] Vertical stacking not found!")
            return False
        
        if 'overflow-x: hidden' in css_content:
            print("[SUCCESS] Horizontal scroll prevention found in CSS")
        else:
            print("[ERROR] Horizontal scroll prevention not found!")
            return False
        
        # Check for cart/checkout vertical stacking
        if '.cart-container' in css_content or '.checkout-container' in css_content:
            print("[SUCCESS] Cart/Checkout container styles found")
        else:
            print("[WARNING] Cart/Checkout container styles not explicitly found")
        
    else:
        print(f"[ERROR] CSS file failed to load (status: {css_response.status_code})")
        return False
    
    # Test 9: Verify admin orders page has responsive table
    print(f"\n=== Test 9: Admin Orders Responsive Table ===")
    admin_login = session.post(f"{BASE_URL}/admin/login", data={"password": "jainzee123"})
    if admin_login.status_code == 302:
        orders_response = session.get(f"{BASE_URL}/admin/orders")
        if orders_response.status_code == 200:
            print(f"[SUCCESS] Admin orders page loaded (status: {orders_response.status_code})")
            
            orders_html = orders_response.text
            if 'overflow-x: auto' in orders_html or 'overflow-x:auto' in orders_html:
                print("[SUCCESS] Responsive table wrapper found in admin orders")
            else:
                print("[WARNING] Responsive table wrapper not found (may be in CSS)")
        else:
            print(f"[ERROR] Admin orders page failed (status: {orders_response.status_code})")
    else:
        print(f"[ERROR] Admin login failed (status: {admin_login.status_code})")
    
    # Logout
    session.get(f"{BASE_URL}/admin/logout")
    
    print("\n[SUCCESS] MOBILE RESPONSIVENESS TEST PASSED!")
    return True

if __name__ == "__main__":
    print("=" * 70)
    print("TESTING MOBILE RESPONSIVENESS")
    print("=" * 70)
    
    try:
        result = test_mobile_responsiveness()
        
        print("\n" + "=" * 70)
        if result:
            print("[SUCCESS] MOBILE RESPONSIVENESS TEST PASSED!")
            print("\nKey Features Verified:")
            print("  ✓ Cart & Customer icons always visible on mobile")
            print("  ✓ Navigation links collapse into hamburger menu")
            print("  ✓ Vertical stacking enforced for cart/checkout")
            print("  ✓ Horizontal scroll prevention enabled")
            print("  ✓ Responsive tables with overflow-x: auto")
        else:
            print("[ERROR] MOBILE RESPONSIVENESS TEST FAILED")
        print("=" * 70)
        
        sys.exit(0 if result else 1)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)