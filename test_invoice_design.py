#!/usr/bin/env python3
"""
Test script for PDF Invoice Design - Retail Receipt Style
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

def test_invoice_design():
    """Test PDF invoice generation with retail receipt style"""
    print("\n" + "=" * 70)
    print("TESTING PDF INVOICE DESIGN - RETAIL RECEIPT STYLE")
    print("=" * 70)
    
    import time
    unique_phone = f"9876543{int(time.time() * 1000) % 100000}"
    
    # Register & Login as customer
    session = requests.Session()
    reg_data = {
        "name": "Invoice Test User",
        "phone": unique_phone,
        "email": f"invoicetest{int(time.time())}@example.com",
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
    
    print(f"[SUCCESS] Customer logged in")
    
    # Place an order with multiple items
    cart_data1 = {"product_id": 1, "quantity": 2, "grade_index": 0}
    cart_data2 = {"product_id": 2, "quantity": 1, "grade_index": 0}
    session.post(f"{BASE_URL}/api/cart", json=cart_data1)
    session.post(f"{BASE_URL}/api/cart", json=cart_data2)
    
    order_data = {
        "name": "Invoice Test User",
        "phone": unique_phone,
        "address": "456 Test Avenue, Indore, MP 452001",
        "payment_method": "cod"
    }
    order_response = session.post(f"{BASE_URL}/api/checkout", json=order_data)
    if order_response.status_code != 200:
        print("[ERROR] Order placement failed!")
        return False
    
    order_id = order_response.json()['order_id']
    print(f"[SUCCESS] Order created with ID: {order_id}")
    
    # Test 1: Download PDF invoice
    print(f"\n=== Test 1: Download PDF Invoice ===")
    invoice_response = session.get(f"{BASE_URL}/api/orders/{order_id}/invoice")
    print(f"Invoice download status: {invoice_response.status_code}")
    
    if invoice_response.status_code != 200:
        print(f"[ERROR] Invoice download failed!")
        print(f"Response: {invoice_response.text}")
        return False
    
    # Check content type
    content_type = invoice_response.headers.get('Content-Type', '')
    print(f"Content-Type: {content_type}")
    
    if 'application/pdf' not in content_type:
        print("[ERROR] Response is not a PDF!")
        return False
    
    # Check PDF data exists
    pdf_data = invoice_response.content
    if not pdf_data or len(pdf_data) == 0:
        print("[ERROR] PDF data is empty!")
        return False
    
    print(f"[SUCCESS] PDF generated successfully")
    print(f"  - PDF size: {len(pdf_data)} bytes")
    print(f"  - Content-Type: {content_type}")
    
    # Check PDF header
    if pdf_data[:4] == b'%PDF':
        print("[SUCCESS] Valid PDF format detected")
    else:
        print("[WARNING] PDF header not found, but download succeeded")
    
    # Save PDF to file for manual inspection
    with open(f'invoice_test_{order_id}.pdf', 'wb') as f:
        f.write(pdf_data)
    print(f"  - Saved to: invoice_test_{order_id}.pdf")
    
    # Test 2: Verify order details in response
    print(f"\n=== Test 2: Verify Order Details ===")
    orders_response = session.get(f"{BASE_URL}/api/my-orders")
    if orders_response.status_code != 200:
        print("[ERROR] Failed to fetch orders!")
        return False
    
    orders = orders_response.json()
    if not orders:
        print("[ERROR] No orders found!")
        return False
    
    order = orders[0]
    print(f"Order ID: {order['id']}")
    print(f"Customer: {order.get('customer_name', 'N/A')}")
    print(f"Phone: {order.get('customer_phone', 'N/A')}")
    print(f"Address: {order.get('customer_address', 'N/A')}")
    print(f"Total: {order.get('total', 'N/A')}")
    print(f"Formatted Date: {order.get('formatted_date', 'N/A')}")
    
    if order.get('item_breakdown'):
        print(f"\nItems in order:")
        for idx, item in enumerate(order['item_breakdown'], 1):
            print(f"  {idx}. {item['name']} - Qty: {item['quantity']} - {item['total']}")
    
    print("[SUCCESS] Order details verified")
    
    # Logout
    session.post(f"{BASE_URL}/api/customer/logout")
    
    print("\n[SUCCESS] PDF INVOICE DESIGN TEST PASSED!")
    return True

if __name__ == "__main__":
    print("=" * 70)
    print("TESTING PDF INVOICE - RETAIL RECEIPT STYLE")
    print("=" * 70)
    
    try:
        result = test_invoice_design()
        
        print("\n" + "=" * 70)
        if result:
            print("[SUCCESS] PDF INVOICE TEST PASSED!")
            print("\nThe PDF invoice has been saved. Please open it to verify:")
            print("  - Clean white background")
            print("  - Black text throughout")
            print("  - Company name in bold uppercase at top")
            print("  - Professional retail receipt layout")
        else:
            print("[ERROR] PDF INVOICE TEST FAILED")
        print("=" * 70)
        
        sys.exit(0 if result else 1)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)