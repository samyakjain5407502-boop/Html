"""Build the admin dashboard from the persisted catalogue and order records."""
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import re


SHOP_TIME = timezone(timedelta(hours=5, minutes=30))
PERIODS = {'all': 'All time', 'today': 'Today', '7d': 'Last 7 days', '30d': 'Last 30 days'}
PERIOD_DAYS = {'today': 1, '7d': 7, '30d': 30}
FULFILMENT_STATES = ('pending', 'confirmed', 'processing', 'shipped')
ORDER_STATES = (*FULFILMENT_STATES, 'delivered', 'cancelled', 'other')
STATE_LABELS = {
    'pending': 'Pending', 'confirmed': 'Confirmed', 'processing': 'Processing',
    'shipped': 'Shipped', 'delivered': 'Delivered', 'cancelled': 'Cancelled', 'other': 'Other',
}


def order_state(value):
    status = str(value or 'pending').strip().lower().replace(' ', '_')
    if status == 'pending' or status.startswith('pending_'):
        return 'pending'
    if status.startswith('paid_') or status == 'paid':
        return 'confirmed'
    if status in ('dispatched', 'out_for_delivery'):
        return 'shipped'
    if status in ('canceled', 'refunded'):
        return 'cancelled'
    return status if status in ORDER_STATES else 'other'


def shop_timestamp(value):
    try:
        stamp = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(SHOP_TIME)


def order_amount(value):
    try:
        amount = Decimal(re.sub(r'[₹,\s]', '', str(value)))
    except InvalidOperation:
        return None
    return amount if amount.is_finite() and 0 <= amount <= Decimal('9999999999999999.99') else None


def format_inr(amount):
    whole, fraction = f'{amount:.2f}'.split('.')
    last_three = whole[-3:]
    leading = whole[:-3]
    pairs = [leading[max(0, end - 2):end] for end in range(len(leading), 0, -2)]
    return '₹' + ','.join([*reversed(pairs), last_three]) + (f'.{fraction}' if fraction != '00' else '')


def collect_dashboard(conn, period, now=None):
    now = now or datetime.now(SHOP_TIME)
    today = now.date()
    period_start = today - timedelta(days=PERIOD_DAYS[period] - 1) if period in PERIOD_DAYS else None
    week = {today - timedelta(days=offset): 0 for offset in range(6, -1, -1)}
    statuses = Counter()
    recent_orders = []
    total_sales = Decimal(0)
    order_value = Decimal(0)
    fulfilment = invalid_totals = 0

    orders = conn.execute('''
        SELECT id, customer_name, total, status, is_hidden, created_at
        FROM orders ORDER BY id DESC
    ''')
    for order in orders:
        stamp = shop_timestamp(order['created_at'])
        day = stamp.date() if stamp else None
        if day in week:
            week[day] += 1
        if period_start and (day is None or not period_start <= day <= today):
            continue

        state = order_state(order['status'])
        archived = bool(order['is_hidden'])
        amount = order_amount(order['total'])
        statuses[state] += 1
        if not archived and state in FULFILMENT_STATES:
            fulfilment += 1
        if state != 'cancelled':
            if amount is None:
                invalid_totals += 1
            else:
                order_value += amount
                if state == 'delivered':
                    total_sales += amount
        if not archived and len(recent_orders) < 8:
            recent_orders.append({
                'id': order['id'], 'customer_name': order['customer_name'] or 'Customer',
                'total': format_inr(amount) if amount is not None else 'Unavailable',
                'status': order['status'] or 'pending', 'state': state,
                'status_label': STATE_LABELS[state],
                'created_at': stamp.strftime('%d %b %Y, %I:%M %p') if stamp else 'Date unavailable',
            })

    products = conn.execute('''
        SELECT id, name_en, name_hi, COALESCE(stock, 0) AS stock
        FROM products ORDER BY COALESCE(stock, 0), id
    ''').fetchall()
    low_stock = [dict(product) for product in products if product['stock'] <= 10]
    chart_peak = max(1, *week.values())
    return {
        'total_sales': round(total_sales, 2), 'sales_display': format_inr(total_sales),
        'order_value': round(order_value, 2), 'order_value_display': format_inr(order_value),
        'total_orders': sum(statuses.values()), 'pending_orders': statuses['pending'],
        'delivered_orders': statuses['delivered'], 'needs_fulfilment': fulfilment,
        'total_products': len(products), 'stock_units': sum(max(0, p['stock']) for p in products),
        'out_of_stock': sum(p['stock'] <= 0 for p in low_stock),
        'low_stock_count': len(low_stock), 'low_stock': low_stock, 'recent_orders': recent_orders,
        'statuses': [{'label': STATE_LABELS[s], 'state': s, 'count': statuses[s]} for s in ORDER_STATES],
        'trend': [{'label': day.strftime('%a'), 'date': day.strftime('%d %b'), 'orders': count,
                   'height': round(100 * count / chart_peak)} for day, count in week.items()],
        'invalid_totals': invalid_totals, 'updated_at': now.strftime('%I:%M %p IST'),
    }
