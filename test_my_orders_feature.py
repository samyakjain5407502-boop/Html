#!/usr/bin/env python3
"""
Test script for Customer Order History & Status Tracking feature:
1. Register/Login as customer
2. Place an order
3. View order in "My Orders"
4. Admin updates order status
5. Verify status change reflects in customer view
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

def test_complete_order_flow():
    """Test the complete order flow with status tracking"""
    print("\n" + "=" * 70)
    print("TESTING CUSTOMER ORDER HISTORY & STATUS TRACKING")
    print("=" * 70)
    
    # Step 1: Register customer
    print("\n=== Step 1: Register Customer ===")
    import time
    unique_phone = f"9876543{int(time.time()) % 10000}"
    customer_data = {
        "name": "Order Test User",
        "phone": unique_phone,
        "email": f"ordertest{int(time.time())}@example.com",
        "password": "test123"
    }
    response = requests.post(f"{BASE_URL}/api/customer/register", json=customer_data)
    print(f"Registration Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code != 201:
        print("[ERROR] Registration failed!")
        return False
    
    customer_id = response.json()['id']
    print(f"[SUCCESS] Customer registered with ID: {customer_id}")
    
    # Step 2: Login
    print("\n=== Step 2: Customer Login ===")
    session = requests.Session()
    login_data = {
        "phone": unique_phone,
        "password": "test123"
    }
    response = session.post(f"{BASE_URL}/api/customer/login", json=login_data)
    print(f"Login Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code != 200:
        print("[ERROR] Login failed!")
        return False
    
    print("[SUCCESS] Customer logged in")
    
    # Step 3: Add item to cart and place order
    print("\n=== Step 3: Place Order ===")
    cart_data = {
        "product_id": 1,
        "quantity": 2,
        "grade_index": 0
    }
    cart_response = session.post(f"{BASE_URL}/api/cart", json=cart_data)
    print(f"Add to cart status: {cart_response.status_code}")
    
    order_data = {
        "name": "Order Test User",
        "phone": unique_phone,
        "address": "123 Test Street, Indore",
        "payment_method": "cod"
    }
    order_response = session.post(f"{BASE_URL}/api/checkout", json=order_data)
    print(f"Order placement status: {order_response.status_code}")
    print(f"Order response: {order_response.json()}")
    
    if order_response.status_code != 200:
        print("[ERROR] Order placement failed!")
        return False
    
    order_id = order_response.json()['order_id']
    print(f"[SUCCESS] Order placed with ID: {order_id}")
    
    # Step 4: View order in "My Orders"
    print("\n=== Step 4: View My Orders ===")
    my_orders_response = session.get(f"{BASE_URL}/api/my-orders")
    print(f"My Orders API status: {my_orders_response.status_code}")
    orders = my_orders_response.json()
    print(f"Total orders found: {len(orders)}")
    
    if not orders:
        print("[ERROR] No orders found in My Orders!")
        return False
    
    print(f"Latest order details:")
    latest_order = orders[0]
    print(f"  - Order ID: {latest_order['id']}")
    print(f"  - Status: {latest_order['status_display']}")
    print(f"  - Total: {latest_order['total']}")
    print(f"  - Items: {latest_order['item_summary']}")
    print(f"  - Created: {latest_order['created_at']}")
    print("[SUCCESS] Order visible in My Orders")
    
    # Step 5: Admin updates order status
    print("\n=== Step 5: Admin Updates Order Status ===")
    admin_session = requests.Session()
    admin_login = admin_session.post(f"{BASE_URL}/admin/login", data={"password": "jainzee123"})
    print(f"Admin login status: {admin_login.status_code}")
    
    if admin_login.status_code != 200:
        print("[ERROR] Admin login failed!")
        return False
    
    # Update status to 'confirmed'
    update_data = {"status": "confirmed"}
    update_response = admin_session.put(
        f"{BASE_URL}/admin/api/orders/{order_id}",
        json=update_data
    )
    print(f"Status update response: {update_response.status_code}")
    print(f"Update response: {update_response.json()}")
    
    if update_response.status_code != 200:
        print("[ERROR] Status update failed!")
        return False
    
    print("[SUCCESS] Order status updated to 'confirmed' by admin")
    
    # Step 6: Verify status change in customer view
    print("\n=== Step 6: Verify Status Change in Customer View ===")
    time.sleep(1)  # Small delay to ensure DB update
    
    my_orders_after = session.get(f"{BASE_URL}/api/my-orders")
    orders_after = my_orders_after.json()
    
    if not orders_after:
        print("[ERROR] No orders found after status update!")
        return False
    
    updated_order = orders_after[0]
    print(f"Updated order status: {updated_order['status_display']}")
    
    if updated_order['status_display'] != 'Processing':
        print(f"[ERROR] Status not updated! Expected 'Processing', got '{updated_order['status_display']}'")
        return False
    
    print("[SUCCESS] Status change reflected in customer view")
    
    # Step 7: Update to 'shipped'
    print("\n=== Step 7: Admin Updates to Shipped ===")
    update_shipped = admin_session.put(
        f"{BASE_URL}/admin/api/orders/{order_id}",
        json={"status": "shipped"}
    )
    print(f"Shipped update status: {update_shipped.status_code}")
    
    time.sleep(1)
    my_orders_shipped = session.get(f"{BASE_URL}/api/my-orders").json()
    shipped_status = my_orders_shipped[0]['status_display']
    print(f"Customer sees status: {shipped_status}")
    
    if shipped_status != 'Dispatched':
        print(f"[ERROR] Expected 'Dispatched', got '{shipped_status}'")
        return False
    
    print("[SUCCESS] Status updated to 'Dispatched' correctly")
    
    # Step 8: Customer logout
    print("\n=== Step 8: Customer Logout ===")
    logout_response = session.post(f"{BASE_URL}/api/customer/logout")
    print(f"Logout status: {logout_response.status_code}")
    print(f"Logout response: {logout_response.json()}")
    
    if logout_response.status_code != 200:
        print("[ERROR] Logout failed!")
        return False
    
    print("[SUCCESS] Customer logged out")
    
    print("\n" + "=" * 70)
    print("[SUCCESS] ALL TESTS PASSED!")
    print("=" * 70)
    print("\nFeature Summary:")
    print("✓ Customer can view order history via 'My Orders'")
    print("✓ Order status updates are reflected in real-time")
    print("✓ Status badges display correctly (Pending → Processing → Dispatched)")
    print("✓ Admin can update order status from admin panel")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    try:
        success = test_complete_order_flow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)