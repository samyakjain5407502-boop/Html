#!/usr/bin/env python3
"""
Test script for PDF Invoice & Product Reviews features:
1. Test PDF invoice generation
2. Test product reviews submission
3. Test reviews display
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

def test_pdf_invoice():
    """Test PDF invoice generation"""
    print("\n" + "=" * 70)
    print("TESTING PDF INVOICE GENERATION")
    print("=" * 70)
    
    # Step 1: Login as customer
    print("\n=== Step 1: Customer Login ===")
    import time
    unique_phone = f"9876543{int(time.time()) % 10000}"
    
    # Register
    session = requests.Session()
    reg_data = {
        "name": "Invoice Test User",
        "phone": unique_phone,
        "email": f"invoice{int(time.time())}@example.com",
        "password": "test123"
    }
    reg_response = session.post(f"{BASE_URL}/api/customer/register", json=reg_data)
    print(f"Registration: {reg_response.status_code}")
    
    if reg_response.status_code != 201:
        print("[ERROR] Registration failed!")
        return False
    
    # Login
    login_data = {"phone": unique_phone, "password": "test123"}
    login_response = session.post(f"{BASE_URL}/api/customer/login", json=login_data)
    print(f"Login: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print("[ERROR] Login failed!")
        return False
    
    # Step 2: Place an order
    print("\n=== Step 2: Place Order ===")
    cart_data = {"product_id": 1, "quantity": 1, "grade_index": 0}
    session.post(f"{BASE_URL}/api/cart", json=cart_data)
    
    order_data = {
        "name": "Invoice Test User",
        "phone": unique_phone,
        "address": "123 Invoice Test Street, Indore",
        "payment_method": "cod"
    }
    order_response = session.post(f"{BASE_URL}/api/checkout", json=order_data)
    print(f"Order placement: {order_response.status_code}")
    
    if order_response.status_code != 200:
        print("[ERROR] Order placement failed!")
        return False
    
    order_id = order_response.json()['order_id']
    print(f"[SUCCESS] Order created with ID: {order_id}")
    
    # Step 3: Download PDF invoice
    print("\n=== Step 3: Download PDF Invoice ===")
    invoice_response = session.get(f"{BASE_URL}/api/orders/{order_id}/invoice")
    print(f"Invoice download status: {invoice_response.status_code}")
    print(f"Content-Type: {invoice_response.headers.get('Content-Type')}")
    print(f"Content-Disposition: {invoice_response.headers.get('Content-Disposition')}")
    print(f"PDF size: {len(invoice_response.content)} bytes")
    
    if invoice_response.status_code != 200:
        print("[ERROR] Invoice download failed!")
        return False
    
    if 'application/pdf' not in invoice_response.headers.get('Content-Type', ''):
        print("[ERROR] Response is not a PDF!")
        return False
    
    if len(invoice_response.content) < 1000:
        print("[ERROR] PDF file is too small - likely empty or corrupted!")
        return False
    
    # Save PDF to verify
    with open(f'test_invoice_{order_id}.pdf', 'wb') as f:
        f.write(invoice_response.content)
    print(f"[SUCCESS] PDF invoice saved as test_invoice_{order_id}.pdf")
    
    # Step 4: Logout
    print("\n=== Step 4: Logout ===")
    logout_response = session.post(f"{BASE_URL}/api/customer/logout")
    print(f"Logout: {logout_response.status_code}")
    
    print("\n[SUCCESS] PDF INVOICE TEST PASSED!")
    return True

def test_product_reviews():
    """Test product reviews functionality"""
    print("\n" + "=" * 70)
    print("TESTING PRODUCT REVIEWS & RATINGS")
    print("=" * 70)
    
    # Step 1: Login as customer
    print("\n=== Step 1: Customer Login ===")
    import time
    unique_phone = f"9876543{int(time.time()) % 10000}"
    
    session = requests.Session()
    reg_data = {
        "name": "Review Test User",
        "phone": unique_phone,
        "email": f"review{int(time.time())}@example.com",
        "password": "test123"
    }
    reg_response = session.post(f"{BASE_URL}/api/customer/register", json=reg_data)
    print(f"Registration: {reg_response.status_code}")
    
    if reg_response.status_code != 201:
        print("[ERROR] Registration failed!")
        return False
    
    login_data = {"phone": unique_phone, "password": "test123"}
    login_response = session.post(f"{BASE_URL}/api/customer/login", json=login_data)
    print(f"Login: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print("[ERROR] Login failed!")
        return False
    
    # Step 2: Submit a review
    print("\n=== Step 2: Submit Review ===")
    product_id = 1
    review_data = {
        "rating": 5,
        "review_text": "Excellent quality cashews! Highly recommended."
    }
    review_response = session.post(f"{BASE_URL}/api/products/{product_id}/reviews", json=review_data)
    print(f"Review submission: {review_response.status_code}")
    print(f"Response: {review_response.json()}")
    
    if review_response.status_code != 201:
        print("[ERROR] Review submission failed!")
        return False
    
    print("[SUCCESS] Review submitted")
    
    # Step 3: Submit another review
    print("\n=== Step 3: Submit Another Review ===")
    review_data2 = {
        "rating": 4,
        "review_text": "Good quality but a bit pricey."
    }
    review_response2 = session.post(f"{BASE_URL}/api/products/{product_id}/reviews", json=review_data2)
    print(f"Second review: {review_response2.status_code}")
    
    if review_response2.status_code != 201:
        print("[ERROR] Second review failed!")
        return False
    
    print("[SUCCESS] Second review submitted")
    
    # Step 4: Get reviews
    print("\n=== Step 4: Get Product Reviews ===")
    get_reviews_response = session.get(f"{BASE_URL}/api/products/{product_id}/reviews")
    print(f"Get reviews: {get_reviews_response.status_code}")
    reviews_data = get_reviews_response.json()
    print(f"Total reviews: {reviews_data['total_reviews']}")
    print(f"Average rating: {reviews_data['average_rating']}")
    print(f"Reviews count: {len(reviews_data['reviews'])}")
    
    if reviews_data['total_reviews'] != 2:
        print("[ERROR] Expected 2 reviews!")
        return False
    
    if reviews_data['average_rating'] != 4.5:
        print(f"[ERROR] Expected average rating 4.5, got {reviews_data['average_rating']}")
        return False
    
    print("[SUCCESS] Reviews retrieved correctly")
    
    # Step 5: Test without login (should fail)
    print("\n=== Step 5: Test Review Without Login ===")
    no_login_session = requests.Session()
    no_login_review = no_login_session.post(f"{BASE_URL}/api/products/{product_id}/reviews", 
                                             json={"rating": 3, "review_text": "Should fail"})
    print(f"No login review attempt: {no_login_review.status_code}")
    
    if no_login_review.status_code != 401:
        print("[ERROR] Should require login!")
        return False
    
    print("[SUCCESS] Correctly requires login for reviews")
    
    # Step 6: Logout
    print("\n=== Step 6: Logout ===")
    logout_response = session.post(f"{BASE_URL}/api/customer/logout")
    print(f"Logout: {logout_response.status_code}")
    
    print("\n[SUCCESS] PRODUCT REVIEWS TEST PASSED!")
    return True

if __name__ == "__main__":
    print("=" * 70)
    print("TESTING PDF INVOICE & PRODUCT REVIEWS FEATURES")
    print("=" * 70)
    
    try:
        results = []
        results.append(("PDF Invoice Generation", test_pdf_invoice()))
        results.append(("Product Reviews & Ratings", test_product_reviews()))
        
        print("\n" + "=" * 70)
        print("TEST RESULTS SUMMARY")
        print("=" * 70)
        for test_name, result in results:
            status = "[PASS]" if result else "[FAIL]"
            print(f"{test_name}: {status}")
        
        all_passed = all(result for _, result in results)
        print("\n" + "=" * 70)
        if all_passed:
            print("[SUCCESS] ALL TESTS PASSED!")
        else:
            print("[ERROR] SOME TESTS FAILED")
        print("=" * 70)
        
        sys.exit(0 if all_passed else 1)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)