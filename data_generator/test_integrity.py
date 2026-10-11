"""
Data integrity tests. Run after generate.py to verify
all constraints, volumes, and relationships are correct.
"""

import psycopg2
from config import PG_CONFIG, SEED_CONFIG, PAYMENT_METHODS, ORDER_CHANNELS, ORDER_STATUSES, TIERS, STATUSES

def get_conn():
    return psycopg2.connect(**PG_CONFIG)


def test(name, passed):
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}")
    return passed


def main():
    conn = get_conn()
    cur = conn.cursor()
    all_passed = True

    print("\n=== ROW COUNTS ===")
    for table, expected in [
        ("customers", SEED_CONFIG["num_customers"]),
        ("retailers", SEED_CONFIG["num_retailers"]),
        ("products", SEED_CONFIG["num_products"]),
        ("orders", SEED_CONFIG["num_orders"]),
    ]:
        cur.execute(f"SELECT count(*) FROM {table}")
        actual = cur.fetchone()[0]
        all_passed &= test(f"{table}: expected {expected}, got {actual}", actual == expected)

    cur.execute("SELECT count(*) FROM order_items")
    item_count = cur.fetchone()[0]
    min_items = SEED_CONFIG["num_orders"]
    max_items = SEED_CONFIG["num_orders"] * SEED_CONFIG["max_items_per_order"]
    all_passed &= test(f"order_items: {item_count} rows (expected {min_items}-{max_items})", min_items <= item_count <= max_items)

    print("\n=== REFERENTIAL INTEGRITY ===")
    cur.execute("SELECT count(*) FROM orders o LEFT JOIN customers c ON o.customer_id = c.customer_id WHERE c.customer_id IS NULL")
    orphans = cur.fetchone()[0]
    all_passed &= test(f"Orders with invalid customer_id: {orphans}", orphans == 0)

    cur.execute("SELECT count(*) FROM orders o LEFT JOIN retailers r ON o.retailer_id = r.retailer_id WHERE r.retailer_id IS NULL")
    orphans = cur.fetchone()[0]
    all_passed &= test(f"Orders with invalid retailer_id: {orphans}", orphans == 0)

    cur.execute("SELECT count(*) FROM order_items i LEFT JOIN orders o ON i.order_id = o.order_id WHERE o.order_id IS NULL")
    orphans = cur.fetchone()[0]
    all_passed &= test(f"Order items with invalid order_id: {orphans}", orphans == 0)

    cur.execute("SELECT count(*) FROM order_items i LEFT JOIN products p ON i.product_id = p.product_id WHERE p.product_id IS NULL")
    orphans = cur.fetchone()[0]
    all_passed &= test(f"Order items with invalid product_id: {orphans}", orphans == 0)

    cur.execute("SELECT count(*) FROM orders o LEFT JOIN order_items i ON o.order_id = i.order_id WHERE i.item_id IS NULL")
    orphans = cur.fetchone()[0]
    all_passed &= test(f"Orders with zero items: {orphans}", orphans == 0)

    print("\n=== VALUE CONSTRAINTS ===")
    cur.execute("SELECT DISTINCT payment_method FROM orders")
    methods = {r[0] for r in cur.fetchall()}
    all_passed &= test(f"Payment methods: {methods}", methods.issubset(set(PAYMENT_METHODS)))

    cur.execute("SELECT DISTINCT order_channel FROM orders")
    channels = {r[0] for r in cur.fetchall()}
    all_passed &= test(f"Order channels: {channels}", channels.issubset(set(ORDER_CHANNELS)))

    cur.execute("SELECT DISTINCT status FROM orders")
    statuses = {r[0] for r in cur.fetchall()}
    all_passed &= test(f"Order statuses: {statuses}", statuses.issubset(set(ORDER_STATUSES)))

    cur.execute("SELECT DISTINCT tier FROM customers")
    tiers = {r[0] for r in cur.fetchall()}
    all_passed &= test(f"Customer tiers: {tiers}", tiers.issubset(set(TIERS)))

    cur.execute("SELECT DISTINCT status FROM retailers")
    r_statuses = {r[0] for r in cur.fetchall()}
    all_passed &= test(f"Retailer statuses: {r_statuses}", r_statuses.issubset(set(STATUSES)))

    print("\n=== FINANCIAL INTEGRITY ===")
    cur.execute("SELECT count(*) FROM orders WHERE subtotal < 0 OR delivery_fee < 0 OR discount_amount < 0 OR total_amount < 0")
    negatives = cur.fetchone()[0]
    all_passed &= test(f"Negative financial values: {negatives}", negatives == 0)

    cur.execute("""
        SELECT count(*) FROM orders
        WHERE ABS(total_amount - (subtotal - discount_amount + delivery_fee)) > 0.02
    """)
    mismatches = cur.fetchone()[0]
    all_passed &= test(f"Total amount calculation mismatches: {mismatches}", mismatches == 0)

    print("\n=== DELIVERY & RATING LOGIC ===")
    cur.execute("SELECT count(*) FROM orders WHERE status = 'delivered' AND actual_delivery_minutes IS NULL")
    missing = cur.fetchone()[0]
    all_passed &= test(f"Delivered orders missing actual_delivery_minutes: {missing}", missing == 0)

    cur.execute("SELECT count(*) FROM orders WHERE status = 'delivered' AND rating IS NULL")
    missing = cur.fetchone()[0]
    all_passed &= test(f"Delivered orders missing rating: {missing}", missing == 0)

    cur.execute("SELECT count(*) FROM orders WHERE status != 'delivered' AND actual_delivery_minutes IS NOT NULL")
    unexpected = cur.fetchone()[0]
    all_passed &= test(f"Non-delivered orders with actual_delivery_minutes: {unexpected}", unexpected == 0)

    cur.execute("SELECT count(*) FROM orders WHERE status != 'delivered' AND rating IS NOT NULL")
    unexpected = cur.fetchone()[0]
    all_passed &= test(f"Non-delivered orders with rating: {unexpected}", unexpected == 0)

    cur.execute("SELECT count(*) FROM orders WHERE rating IS NOT NULL AND (rating < 1 OR rating > 5)")
    invalid = cur.fetchone()[0]
    all_passed &= test(f"Ratings outside 1-5 range: {invalid}", invalid == 0)

    print(f"\n{'='*40}")
    if all_passed:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED - check above")
    print(f"{'='*40}\n")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
