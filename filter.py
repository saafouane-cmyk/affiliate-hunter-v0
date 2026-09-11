from config import CONFIG

def filter_products(products):
    print(f">> [Filter] Filtering {len(products)} products...")
    filtered = []
    for p in products:
        if p.get("rating", 0) < CONFIG["CJ"]["min_rating"]: continue
        if p.get("orders", 0) < CONFIG["CJ"]["min_orders"]: continue
        if p.get("cost", 999) > 15: continue # نريد منتجات رخيصة بهامش عالي
        if p.get("cost", 0) < 1: continue
        filtered.append(p)
    print(f">> After filter: {len(filtered)}")
    return filtered
