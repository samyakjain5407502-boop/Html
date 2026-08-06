#!/usr/bin/env python3
"""Test script to verify POST /api/cart functionality"""
import urllib.request
import urllib.parse
import json

BASE_URL = "http://127.0.0.1:5000"

def test_add_to_cart():
    """Test adding item to cart"""
    print("Testing POST /api/cart...")
    
    # Test data
    payload = {
        "product_id": 1,
        "quantity": 2,
        "grade_index": 0
    }
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            f"{BASE_URL}/api/cart",
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req) as response:
            status_code = response.status
            response_data = json.loads(response.read().decode('utf-8'))
            
            print(f"Status Code: {status_code}")
            print(f"Response: {response_data}")
            
            if status_code == 200:
                print("✅ POST /api/cart - SUCCESS")
                return True
            else:
                print("❌ POST /api/cart - FAILED")
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_cart():
    """Test getting cart items"""
    print("\nTesting GET /api/cart...")
    
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/cart") as response:
            status_code = response.status
            cart_items = json.loads(response.read().decode('utf-8'))
            
            print(f"Status Code: {status_code}")
            print(f"Cart Items: {json.dumps(cart_items, indent=2)}")
            
            if status_code == 200:
                print("✅ GET /api/cart - SUCCESS")
                return True
            else:
                print("❌ GET /api/cart - FAILED")
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_cart_count():
    """Test getting cart count"""
    print("\nTesting GET /api/cart/count...")
    
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/cart/count") as response:
            status_code = response.status
            response_data = json.loads(response.read().decode('utf-8'))
            
            print(f"Status Code: {status_code}")
            print(f"Response: {response_data}")
            
            if status_code == 200:
                print("✅ GET /api/cart/count - SUCCESS")
                return True
            else:
                print("❌ GET /api/cart/count - FAILED")
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("CART API TEST")
    print("=" * 50)
    
    # Run tests
    test1 = test_add_to_cart()
    test2 = test_get_cart()
    test3 = test_cart_count()
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"POST /api/cart: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"GET /api/cart: {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"GET /api/cart/count: {'✅ PASS' if test3 else '❌ FAIL'}")
    
    if all([test1, test2, test3]):
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed!")