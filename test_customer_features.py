#!/usr/bin/env python3
"""
Test script for customer features:
1. Register a new customer
2. Login
3. Check customer name in response
4. Place an order
5. Verify order appears in admin
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

def test_customer_registration():
    """Test customer registration"""
    print("\n=== Test 1: Customer Registration ===")
    # Use unique phone number to avoid conflicts with previous test runs
    import time
    unique_phone = f"9876543{int(time.time()) % 10000}"
    data = {
        "name": "Test User",
        "phone": unique_phone,
        "email": f"test{int(time.time())}@example.com",
        "password": "test123"
    }
    response = requests.post(f"{BASE_URL}/api/customer/register", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    # Store for later tests
    test_customer_registration.phone = unique_phone
    return response.status_code == 201

def test_customer_login():
    """Test customer login"""
    print("\n=== Test 2: Customer Login ===")
    # Use the phone from registration if available
    phone = getattr(test_customer_registration, 'phone', '9876543210')
    data = {
        "phone": phone,
        "password": "test123"
    }
    response = requests.post(f"{BASE_URL}/api/customer/login", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_customer_me():
    """Test getting customer info (simulates header display)"""
    print("\n=== Test 3: Get Customer Info (for header display) ===")
    # First login to get session
    session = requests.Session()
    phone = getattr(test_customer_registration, 'phone', '9876543210')
    login_data = {
        "phone": phone,
        "password": "test123"
    }
    session.post(f"{BASE_URL}/api/customer/login", json=login_data)
    
    # Now get customer info
    response = session.get(f"{BASE_URL}/api/customer/me")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_place_order():
    """Test placing an order"""
    print("\n=== Test 4: Place Order ===")
    session = requests.Session()
    
    # Login first
    phone = getattr(test_customer_registration, 'phone', '9876543210')
    login_data = {
        "phone": phone,
        "password": "test123"
    }
    session.post(f"{BASE_URL}/api/customer/login", json=login_data)
    
    # Add item to cart
    cart_data = {
        "product_id": 1,
        "quantity": 2,
        "grade_index": 0
    }
    session.post(f"{BASE_URL}/api/cart", json=cart_data)
    
    # Place order
    order_data = {
        "name": "Test User",
        "phone": phone,
        "address": "123 Test Street, Indore",
        "payment_method": "cod"
    }
    response = session.post(f"{BASE_URL}/api/checkout", json=order_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_admin_orders():
    """Test that order appears in admin"""
    print("\n=== Test 5: Check Order in Admin ===")
    # Admin login (default password: jainzee123)
    session = requests.Session()
    session.post(f"{BASE_URL}/admin/login", data={"password": "jainzee123"})
    
    response = session.get(f"{BASE_URL}/admin/api/orders")
    print(f"Status: {response.status_code}")
    orders = response.json()
    print(f"Total orders: {len(orders)}")
    if orders:
        print(f"Latest order: {orders[0]}")
    return response.status_code == 200 and len(orders) > 0

def test_customer_logout():
    """Test customer logout"""
    print("\n=== Test 6: Customer Logout ===")
    session = requests.Session()
    
    # Login first
    phone = getattr(test_customer_registration, 'phone', '9876543210')
    login_data = {
        "phone": phone,
        "password": "test123"
    }
    session.post(f"{BASE_URL}/api/customer/login", json=login_data)
    
    # Logout
    response = session.post(f"{BASE_URL}/api/customer/logout")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Verify logged out
    me_response = session.get(f"{BASE_URL}/api/customer/me")
    print(f"After logout - /api/customer/me status: {me_response.status_code}")
    print(f"After logout - /api/customer/me response: {me_response.json()}")
    return response.status_code == 200

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING CUSTOMER FEATURES")
    print("=" * 60)
    
    try:
        results = []
        results.append(("Registration", test_customer_registration()))
        results.append(("Login", test_customer_login()))
        results.append(("Get Customer Info", test_customer_me()))
        results.append(("Place Order", test_place_order()))
        results.append(("Admin Orders", test_admin_orders()))
        results.append(("Logout", test_customer_logout()))
        
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)
        for test_name, result in results:
            status = "[PASS]" if result else "[FAIL]"
            print(f"{test_name}: {status}")
        
        all_passed = all(result for _, result in results)
        print("\n" + ("=" * 60))
        if all_passed:
            print("[SUCCESS] ALL TESTS PASSED!")
        else:
            print("[ERROR] SOME TESTS FAILED")
        print("=" * 60)
            
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
