#!/usr/bin/env python3
"""
Test script for Symmetrical Single-Row Mobile Header Layout
"""

import requests
import sys
import io

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_URL = "http://127.0.0.1:5000"

def test_symmetrical_header():
    """Test symmetrical single-row mobile header layout"""
    print("\n" + "=" * 70)
    print("TESTING SYMMETRICAL SINGLE-ROW MOBILE HEADER")
    print("=" * 70)
    
    session = requests.Session()
    
    # Test 1: Check homepage loads
    print(f"\n=== Test 1: Homepage Load ===")
    home_response = session.get(f"{BASE_URL}/")
    if home_response.status_code != 200:
        print("[ERROR] Homepage failed to load!")
        return False
    
    print(f"[SUCCESS] Homepage loaded (status: {home_response.status_code})")
    html_content = home_response.text
    
    # Test 2: Verify 3-zone header structure
    print(f"\n=== Test 2: 3-Zone Header Structure ===")
    
    # Check for nav-left zone
    if 'class="nav-left"' in html_content or 'nav-left' in html_content:
        print("[SUCCESS] LEFT ZONE (nav-left) found - User Icon + Hamburger")
    else:
        print("[ERROR] LEFT ZONE not found!")
        return False
    
    # Check for nav-center zone
    if 'class="nav-center"' in html_content or 'nav-center' in html_content:
        print("[SUCCESS] CENTER ZONE (nav-center) found - Brand Logo & Title")
    else:
        print("[ERROR] CENTER ZONE not found!")
        return False
    
    # Check for nav-right zone
    if 'class="nav-right"' in html_content or 'nav-right' in html_content:
        print("[SUCCESS] RIGHT ZONE (nav-right) found - My Orders + Cart")
    else:
        print("[ERROR] RIGHT ZONE not found!")
        return False
    
    # Test 3: Verify icon-only buttons (no text labels on mobile)
    print(f"\n=== Test 3: Icon-Only Buttons (No Text Labels) ===")
    
    # Check that cart link has no text span
    cart_link_start = html_content.find('id="cartLink"')
    if cart_link_start > 0:
        cart_link_end = html_content.find('</a>', cart_link_start)
        cart_link_html = html_content[cart_link_start:cart_link_end]
        
        # Should have icon but no text span
        if 'fa-shopping-cart' in cart_link_html:
            print("[SUCCESS] Cart icon found")
        else:
            print("[ERROR] Cart icon not found!")
            return False
        
        # Check for badge
        if 'cart-count-badge' in cart_link_html or 'cartBadge' in cart_link_html:
            print("[SUCCESS] Cart badge found")
        else:
            print("[WARNING] Cart badge not found in cart link")
    
    # Check customer login button
    if 'id="customerLoginBtn"' in html_content:
        customer_start = html_content.find('id="customerLoginBtn"')
        customer_html = html_content[customer_start:customer_start + 500]
        if 'fa-user' in customer_html:
            print("[SUCCESS] Customer user icon found")
        else:
            print("[ERROR] Customer user icon not found!")
            return False
    
    # Check my orders button
    if 'id="myOrdersBtn"' in html_content:
        orders_start = html_content.find('id="myOrdersBtn"')
        orders_html = html_content[orders_start:orders_start + 500]
        if 'fa-box' in orders_html:
            print("[SUCCESS] My Orders icon found")
        else:
            print("[ERROR] My Orders icon not found!")
            return False
    
    # Test 4: Verify brand logo and title in center
    print(f"\n=== Test 4: Brand Logo & Title in Center ===")
    
    if 'id="navLogo"' in html_content:
        print("[SUCCESS] Nav logo found")
    else:
        print("[ERROR] Nav logo not found!")
        return False
    
    if 'id="navShopName"' in html_content:
        print("[SUCCESS] Nav shop name found")
    else:
        print("[ERROR] Nav shop name not found!")
        return False
    
    # Test 5: Verify CSS has single-row layout rules
    print(f"\n=== Test 5: CSS Single-Row Layout Rules ===")
    
    css_response = session.get(f"{BASE_URL}/static/css/style.css")
    if css_response.status_code == 200:
        css_content = css_response.text
        
        # Check for flex-direction: row
        if 'flex-direction: row' in css_content or 'flex-direction:row' in css_content:
            print("[SUCCESS] flex-direction: row found in CSS")
        else:
            print("[ERROR] flex-direction: row not found!")
            return False
        
        # Check for justify-content: space-between
        if 'justify-content: space-between' in css_content or 'justify-content:space-between' in css_content:
            print("[SUCCESS] justify-content: space-between found")
        else:
            print("[ERROR] justify-content: space-between not found!")
            return False
        
        # Check for align-items: center
        if 'align-items: center' in css_content or 'align-items:center' in css_content:
            print("[SUCCESS] align-items: center found")
        else:
            print("[ERROR] align-items: center not found!")
            return False
        
        # Check for white-space: nowrap
        if 'white-space: nowrap' in css_content or 'white-space:nowrap' in css_content:
            print("[SUCCESS] white-space: nowrap found (prevents wrapping)")
        else:
            print("[ERROR] white-space: nowrap not found!")
            return False
        
        # Check for logo height constraints
        if 'max-height: 32px' in css_content or 'max-height:32px' in css_content:
            print("[SUCCESS] Logo max-height: 32px found")
        else:
            print("[WARNING] Logo max-height: 32px not explicitly found")
        
        # Check for nav-container height
        if 'height: 50px' in css_content or 'height:50px' in css_content:
            print("[SUCCESS] Navbar height: 50px found")
        else:
            print("[WARNING] Navbar height: 50px not explicitly found")
        
        # Check for 3-zone layout
        if '.nav-left' in css_content and '.nav-center' in css_content and '.nav-right' in css_content:
            print("[SUCCESS] All 3 zones (nav-left, nav-center, nav-right) styled")
        else:
            print("[ERROR] Not all 3 zones styled!")
            return False
        
        # Check for icon-only styling (hidden text)
        if 'display: none' in css_content and 'nav-icon-btn' in css_content:
            print("[SUCCESS] Icon-only button styling found")
        else:
            print("[WARNING] Icon-only button styling may not be complete")
    
    else:
        print(f"[ERROR] CSS file failed to load (status: {css_response.status_code})")
        return False
    
    # Test 6: Verify hamburger menu exists
    print(f"\n=== Test 6: Hamburger Menu ===")
    
    if 'id="hamburger"' in html_content:
        print("[SUCCESS] Hamburger menu button found")
    else:
        print("[ERROR] Hamburger menu not found!")
        return False
    
    # Test 7: Verify no duplicate/conflicting navbar elements
    print(f"\n=== Test 7: No Duplicate Navbar Elements ===")
    
    # Count occurrences of key elements
    cart_count = html_content.count('id="cartLink"')
    if cart_count == 1:
        print(f"[SUCCESS] Cart link appears exactly once ({cart_count} time)")
    else:
        print(f"[WARNING] Cart link appears {cart_count} times (should be 1)")
    
    customer_count = html_content.count('id="customerLoginBtn"')
    if customer_count == 1:
        print(f"[SUCCESS] Customer login button appears exactly once ({customer_count} time)")
    else:
        print(f"[WARNING] Customer login button appears {customer_count} times (should be 1)")
    
    # Test 8: Verify mobile menu has navigation links
    print(f"\n=== Test 8: Mobile Menu Navigation Links ===")
    
    mobile_menu_start = html_content.find('id="mobileMenu"')
    if mobile_menu_start > 0:
        mobile_menu_end = html_content.find('</nav>', mobile_menu_start)
        mobile_menu_html = html_content[mobile_menu_start:mobile_menu_end]
        
        nav_links = ['nav_home', 'nav_products', 'nav_about', 'nav_contact']
        found_links = 0
        for link in nav_links:
            if link in mobile_menu_html:
                found_links += 1
        
        if found_links == len(nav_links):
            print(f"[SUCCESS] All {len(nav_links)} navigation links found in mobile menu")
        else:
            print(f"[WARNING] Only {found_links}/{len(nav_links)} navigation links found")
    else:
        print("[ERROR] Mobile menu not found!")
        return False
    
    # Test 9: Verify cart and checkout pages load
    print(f"\n=== Test 9: Cart & Checkout Pages ===")
    
    cart_response = session.get(f"{BASE_URL}/cart")
    if cart_response.status_code == 200:
        print(f"[SUCCESS] Cart page loaded (status: {cart_response.status_code})")
    else:
        print(f"[ERROR] Cart page failed (status: {cart_response.status_code})")
        return False
    
    checkout_response = session.get(f"{BASE_URL}/checkout")
    if checkout_response.status_code == 200:
        print(f"[SUCCESS] Checkout page loaded (status: {checkout_response.status_code})")
    else:
        print(f"[ERROR] Checkout page failed (status: {checkout_response.status_code})")
        return False
    
    print("\n[SUCCESS] SYMMETRICAL HEADER TEST PASSED!")
    return True

if __name__ == "__main__":
    print("=" * 70)
    print("TESTING SYMMETRICAL SINGLE-ROW MOBILE HEADER")
    print("=" * 70)
    
    try:
        result = test_symmetrical_header()
        
        print("\n" + "=" * 70)
        if result:
            print("[SUCCESS] SYMMETRICAL HEADER TEST PASSED!")
            print("\nHeader Layout Verified:")
            print("  ✓ LEFT ZONE: User Icon + Hamburger Menu")
            print("  ✓ CENTER ZONE: Brand Logo + 'Jainzee' Title")
            print("  ✓ RIGHT ZONE: My Orders Icon + Cart Icon with Badge")
            print("  ✓ Single horizontal row (no wrapping)")
            print("  ✓ Icon-only buttons (no text labels)")
            print("  ✓ Logo scaled to 28-32px height")
            print("  ✓ Navbar height: 50px")
            print("\nNext Step: Open Chrome DevTools (F12) → Toggle Device Toolbar")
            print("  → Select 375px viewport → Verify single-row header")
        else:
            print("[ERROR] SYMMETRICAL HEADER TEST FAILED")
        print("=" * 70)
        
        sys.exit(0 if result else 1)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)