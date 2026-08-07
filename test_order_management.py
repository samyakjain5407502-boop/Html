#!/usr/bin/env python3
"""
Test script for Order Management (Hide/Archive/Delete) functionality
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

def test_order_management():
    """Test order hide/archive and delete functionality"""
    print("\n" + "=" * 70)
    print("TESTING ORDER MANAGEMENT (HIDE/DELETE)")
    print("=" * 70)
    
    import time
    unique_phone = f"9876543{int(time.time() * 1000) % 100000}"
    
    # Register & Login as customer
    session = requests.Session()
    reg_data = {
        "name": "Order Management Test User",
        "phone": unique_phone,
        "email": f"ordermgmt{int(time.time())}@example.com",
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
    
    # Place an order
    cart_data = {"product_id": 1, "quantity": 1, "grade_index": 0}
    session.post(f"{BASE_URL}/api/cart", json=cart_data)
    
    order_data = {
        "name": "Order Management Test User",
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
    
    # Login as admin
    admin_session = requests.Session()
    admin_login = admin_session.post(f"{BASE_URL}/admin/login", data={"password": "jainzee123"})
    if admin_login.status_code != 200:
        print("[ERROR] Admin login failed!")
        return False
    
    print(f"[SUCCESS] Admin logged in")
    
    # Test 1: Get active orders (should include our order)
    print(f"\n=== Test 1: Get Active Orders ===")
    active_orders_resp = admin_session.get(f"{BASE_URL}/admin/api/orders")
    if active_orders_resp.status_code != 200:
        print("[ERROR] Failed to get active orders!")
        return False
    
    active_orders = active_orders_resp.json()
    our_order = next((o for o in active_orders if o['id'] == order_id), None)
    if not our_order:
        print("[ERROR] Our order not found in active orders!")
        return False
    
    print(f"[SUCCESS] Order found in active orders")
    print(f"  - Order ID: {our_order['id']}")
    print(f"  - Customer: {our_order['customer_name']}")
    print(f"  - Total: {our_order['total']}")
    print(f"  - is_hidden: {our_order.get('is_hidden', 'N/A')}")
    
    # Test 2: Hide/Archive the order
    print(f"\n=== Test 2: Hide/Archive Order ===")
    hide_resp = admin_session.post(f"{BASE_URL}/admin/api/orders/{order_id}/hide")
    if hide_resp.status_code != 200:
        print(f"[ERROR] Hide failed! Status: {hide_resp.status_code}")
        print(f"Response: {hide_resp.text}")
        return False
    
    hide_result = hide_resp.json()
    print(f"[SUCCESS] Order hidden: {hide_result['message']}")
    print(f"  - is_hidden: {hide_result['is_hidden']}")
    
    # Test 3: Verify order is hidden from active view
    print(f"\n=== Test 3: Verify Order Hidden from Active View ===")
    active_orders_resp2 = admin_session.get(f"{BASE_URL}/admin/api/orders")
    active_orders2 = active_orders_resp2.json()
    hidden_order = next((o for o in active_orders2 if o['id'] == order_id), None)
    if hidden_order:
        print("[ERROR] Order should not be in active orders list!")
        return False
    
    print("[SUCCESS] Order correctly hidden from active view")
    
    # Test 4: Get archived orders (should include our order)
    print(f"\n=== Test 4: Get Archived Orders ===")
    archived_resp = admin_session.get(f"{BASE_URL}/admin/api/orders?show_hidden=true")
    if archived_resp.status_code != 200:
        print("[ERROR] Failed to get archived orders!")
        return False
    
    archived_orders = archived_resp.json()
    archived_order = next((o for o in archived_orders if o['id'] == order_id), None)
    if not archived_order:
        print("[ERROR] Our order not found in archived orders!")
        return False
    
    print(f"[SUCCESS] Order found in archived orders")
    print(f"  - Order ID: {archived_order['id']}")
    print(f"  - is_hidden: {archived_order.get('is_hidden', 'N/A')}")
    
    # Test 5: Restore the order
    print(f"\n=== Test 5: Restore Order ===")
    restore_resp = admin_session.post(f"{BASE_URL}/admin/api/orders/{order_id}/hide")
    if restore_resp.status_code != 200:
        print(f"[ERROR] Restore failed! Status: {restore_resp.status_code}")
        return False
    
    restore_result = restore_resp.json()
    print(f"[SUCCESS] Order restored: {restore_result['message']}")
    print(f"  - is_hidden: {restore_result['is_hidden']}")
    
    # Test 6: Verify order is back in active view
    print(f"\n=== Test 6: Verify Order Restored to Active View ===")
    active_orders_resp3 = admin_session.get(f"{BASE_URL}/admin/api/orders")
    active_orders3 = active_orders_resp3.json()
    restored_order = next((o for o in active_orders3 if o['id'] == order_id), None)
    if not restored_order:
        print("[ERROR] Order should be in active orders list after restore!")
        return False
    
    print("[SUCCESS] Order correctly restored to active view")
    
    # Test 7: Delete the order permanently
    print(f"\n=== Test 7: Delete Order Permanently ===")
    delete_resp = admin_session.delete(f"{BASE_URL}/admin/api/orders/{order_id}")
    if delete_resp.status_code != 200:
        print(f"[ERROR] Delete failed! Status: {delete_resp.status_code}")
        print(f"Response: {delete_resp.text}")
        return False
    
    delete_result = delete_resp.json()
    print(f"[SUCCESS] Order deleted: {delete_result['message']}")
    
    # Test 8: Verify order is deleted
    print(f"\n=== Test 8: Verify Order Deleted ===")
    active_orders_resp4 = admin_session.get(f"{BASE_URL}/admin/api/orders")
    active_orders4 = active_orders_resp4.json()
    deleted_order = next((o for o in active_orders4 if o['id'] == order_id), None)
    if deleted_order:
        print("[ERROR] Order should not exist after deletion!")
        return False
    
    print("[SUCCESS] Order correctly deleted from database")
    
    # Logout
    session.post(f"{BASE_URL}/api/customer/logout")
    admin_session.get(f"{BASE_URL}/admin/logout")
    
    print("\n[SUCCESS] ORDER MANAGEMENT TEST PASSED!")
    return True

if __name__ == "__main__":
    print("=" * 70)
    print("TESTING ORDER MANAGEMENT FUNCTIONALITY")
    print("=" * 70)
    
    try:
        result = test_order_management()
        
        print("\n" + "=" * 70)
        if result:
            print("[SUCCESS] ALL ORDER MANAGEMENT TESTS PASSED!")
        else:
            print("[ERROR] SOME TESTS FAILED")
        print("=" * 70)
        
        sys.exit(0 if result else 1)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)