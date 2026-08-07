#!/usr/bin/env python3
"""
Test script for Mobile Responsiveness, Order Breakdown, and Review UI improvements
"""

import requests
import json
import sys
import io

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_URL = "http://127.0.0.1:5000"

def test_order_breakdown_and_formatting():
    """Test order item breakdown and date/time formatting"""
    print("\n" + "=" * 70)
    print("TESTING ORDER BREAKDOWN & DATE/TIME FORMATTING")
    print("=" * 70)
    
    import time
    unique_phone = f"9876543{int(time.time()) % 10000}"
    
    # Register & Login
    session = requests.Session()
    reg_data = {
        "name": "Order Test User",
        "phone": unique_phone,
        "email": f"ordertest{int(time.time())}@example.com",
        "password": "test123"
    }
    reg_response = session.post(f"{BASE_URL}/api/customer/register", json=reg_data)
    if reg_response.status_code != 201:
        print("[ERROR] Registration failed!")
        return False
    
    login_data = {"phone": unique_phone, "password": "test123"}
    login_response = session.post(f"{BASE_URL}/api/customer/login", json=login_data)
    if login_response.status_code != 200:
        print("[ERROR] Login failed!")
        return False
    
    # Place order
    cart_data = {"product_id": 1, "quantity": 2, "grade_index": 0}
    session.post(f"{BASE_URL}/api/cart", json=cart_data)
    
    order_data = {
        "name": "Order Test User",
        "phone": unique_phone,
        "address": "123 Test Street, Indore",
        "payment_method": "cod"
    }
    order_response = session.post(f"{BASE_URL}/api/checkout", json=order_data)
    if order_response.status_code != 200:
        print("[ERROR] Order placement failed!")
        return False
    
    order_id = order_response.json()['order_id']
    print(f"[SUCCESS] Order created with ID: {order_id}")
    
    # Get order details
    orders_response = session.get(f"{BASE_URL}/api/my-orders")
    if orders_response.status_code != 200:
        print("[ERROR] Failed to fetch orders!")
        return False
    
    orders = orders_response.json()
    if not orders:
        print("[ERROR] No orders found!")
        return False
    
    order = orders[0]
    
    # Test 1: Check formatted date exists
    print(f"\n=== Test 1: Date Formatting ===")
    if 'formatted_date' not in order:
        print("[ERROR] formatted_date field missing!")
        return False
    
    print(f"Formatted Date: {order['formatted_date']}")
    # Should be in format "DD Mon YYYY, HH:MM AM/PM"
    if ',' not in order['formatted_date'] or 'AM' not in order['formatted_date'] and 'PM' not in order['formatted_date']:
        print(f"[ERROR] Date format incorrect! Expected 'DD Mon YYYY, HH:MM AM/PM', got: {order['formatted_date']}")
        return False
    
    print("[SUCCESS] Date formatted correctly")
    
    # Test 2: Check item breakdown exists
    print(f"\n=== Test 2: Item Breakdown ===")
    if 'item_breakdown' not in order:
        print("[ERROR] item_breakdown field missing!")
        return False
    
    if not order['item_breakdown']:
        print("[ERROR] item_breakdown is empty!")
        return False
    
    print(f"Items in order: {len(order['item_breakdown'])}")
    for idx, item in enumerate(order['item_breakdown'], 1):
        print(f"\nItem {idx}:")
        print(f"  - Name: {item.get('name', 'N/A')}")
        print(f"  - Variant: {item.get('variant', 'N/A')}")
        print(f"  - Quantity: {item.get('quantity', 'N/A')}")
        print(f"  - Unit Price: {item.get('unit_price', 'N/A')}")
        print(f"  - Total: {item.get('total', 'N/A')}")
        
        # Verify all required fields exist
        if not all([item.get('name'), item.get('variant') is not None, item.get('quantity'), item.get('unit_price'), item.get('total')]):
            print("[ERROR] Item breakdown missing required fields!")
            return False
    
    print("[SUCCESS] Item breakdown structured correctly")
    
    # Test 3: Check item_summary
    print(f"\n=== Test 3: Item Summary ===")
    if 'item_summary' not in order:
        print("[ERROR] item_summary field missing!")
        return False
    
    print(f"Item Summary: {order['item_summary']}")
    print("[SUCCESS] Item summary present")
    
    # Logout
    session.post(f"{BASE_URL}/api/customer/logout")
    
    print("\n[SUCCESS] ORDER BREAKDOWN & FORMATTING TEST PASSED!")
    return True

def test_reviews_api():
    """Test reviews API endpoints"""
    print("\n" + "=" * 70)
    print("TESTING REVIEWS API")
    print("=" * 70)
    
    import time
    unique_phone = f"9876543{int(time.time() * 1000) % 100000}"
    
    # Register & Login
    session = requests.Session()
    reg_data = {
        "name": "Review Test User",
        "phone": unique_phone,
        "email": f"reviewtest{int(time.time())}@example.com",
        "password": "test123"
    }
    reg_response = session.post(f"{BASE_URL}/api/customer/register", json=reg_data)
    if reg_response.status_code != 201:
        print("[ERROR] Registration failed!")
        return False
    
    login_data = {"phone": unique_phone, "password": "test123"}
    login_response = session.post(f"{BASE_URL}/api/customer/login", json=login_data)
    if login_response.status_code != 200:
        print("[ERROR] Login failed!")
        return False
    
    # Test 1: Submit review
    print(f"\n=== Test 1: Submit Review ===")
    product_id = 2  # Use product ID 2 to avoid conflicts with previous tests
    review_data = {
        "rating": 5,
        "review_text": "Excellent quality! Highly recommended."
    }
    review_response = session.post(f"{BASE_URL}/api/products/{product_id}/reviews", json=review_data)
    print(f"Review submission: {review_response.status_code}")
    
    if review_response.status_code != 201:
        print(f"[ERROR] Review submission failed! Response: {review_response.text}")
        return False
    
    print("[SUCCESS] Review submitted")
    
    # Test 2: Get reviews
    print(f"\n=== Test 2: Get Reviews ===")
    get_reviews = session.get(f"{BASE_URL}/api/products/{product_id}/reviews")
    print(f"Get reviews: {get_reviews.status_code}")
    
    if get_reviews.status_code != 200:
        print("[ERROR] Failed to get reviews!")
        return False
    
    reviews_data = get_reviews.json()
    initial_count = reviews_data['total_reviews']
    print(f"Total reviews: {initial_count}")
    print(f"Average rating: {reviews_data['average_rating']}")
    
    # Check that we have at least 1 review (may have existing reviews from other tests)
    if initial_count < 1:
        print("[ERROR] Expected at least 1 review!")
        return False
    
    # Verify our review is in the list
    our_review = next((r for r in reviews_data['reviews'] if r['customer_name'] == 'Review Test User'), None)
    if not our_review:
        print("[ERROR] Our review not found in reviews list!")
        return False
    
    if our_review['rating'] != 5:
        print(f"[ERROR] Expected rating 5, got {our_review['rating']}")
        return False
    
    print("[SUCCESS] Reviews retrieved correctly")
    print(f"  - Found our review with rating: {our_review['rating']}")
    
    # Test 3: Verify review count increased (each submission adds a new review)
    print(f"\n=== Test 3: Submit Second Review ===")
    review_data2 = {
        "rating": 4,
        "review_text": "Good quality product."
    }
    review_response2 = session.post(f"{BASE_URL}/api/products/{product_id}/reviews", json=review_data2)
    print(f"Second review: {review_response2.status_code}")
    
    if review_response2.status_code != 201:
        print("[ERROR] Second review failed!")
        return False
    
    # Check updated count
    get_reviews2 = session.get(f"{BASE_URL}/api/products/{product_id}/reviews").json()
    print(f"Total reviews after second: {get_reviews2['total_reviews']}")
    print(f"Average rating: {get_reviews2['average_rating']}")
    
    # Verify we have more reviews now
    if get_reviews2['total_reviews'] <= initial_count:
        print("[ERROR] Review count should have increased!")
        return False
    
    # Verify both our reviews are in the list
    our_reviews = [r for r in get_reviews2['reviews'] if r['customer_name'] == 'Review Test User']
    if len(our_reviews) < 2:
        print(f"[ERROR] Expected at least 2 reviews from us, found {len(our_reviews)}")
        return False
    
    print("[SUCCESS] Multiple reviews working correctly")
    
    # Logout
    session.post(f"{BASE_URL}/api/customer/logout")
    
    print("\n[SUCCESS] REVIEWS API TEST PASSED!")
    return True

def test_mobile_responsive_css():
    """Test that mobile responsive CSS exists"""
    print("\n" + "=" * 70)
    print("TESTING MOBILE RESPONSIVE CSS")
    print("=" * 70)
    
    try:
        with open('jainzee-website/static/css/style.css', 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        # Check for media queries
        print(f"\n=== Test 1: Media Queries ===")
        if '@media (max-width: 768px)' not in css_content:
            print("[ERROR] Mobile media query (768px) not found!")
            return False
        
        print("[SUCCESS] Mobile media query (768px) found")
        
        if '@media (max-width: 480px)' not in css_content:
            print("[ERROR] Small mobile media query (480px) not found!")
            return False
        
        print("[SUCCESS] Small mobile media query (480px) found")
        
        # Check for key responsive elements
        print(f"\n=== Test 2: Responsive Elements ===")
        key_elements = [
            'modal-content',
            'products-grid',
            'cart-item',
            'checkout-grid',
            'admin-table'
        ]
        
        for element in key_elements:
            if element not in css_content:
                print(f"[WARNING] Element '{element}' not found in CSS")
            else:
                print(f"[SUCCESS] Element '{element}' found")
        
        print("\n[SUCCESS] MOBILE RESPONSIVE CSS TEST PASSED!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to read CSS file: {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("TESTING ALL IMPROVEMENTS")
    print("=" * 70)
    
    try:
        results = []
        results.append(("Mobile Responsive CSS", test_mobile_responsive_css()))
        results.append(("Order Breakdown & Date Formatting", test_order_breakdown_and_formatting()))
        results.append(("Reviews API", test_reviews_api()))
        
        print("\n" + "=" * 70)
        print("TEST RESULTS SUMMARY")
        print("=" * 70)
        for test_name, result in results:
            status = "[PASS]" if result else "[FAIL]"
            print(f"{test_name}: {status}")
        
        all_passed = all(result for _, result in results)
        print("\n" + "=" * 70)
        if all_passed:
            print("[SUCCESS] ALL IMPROVEMENT TESTS PASSED!")
        else:
            print("[ERROR] SOME TESTS FAILED")
        print("=" * 70)
        
        sys.exit(0 if all_passed else 1)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)