import os, json, requests, time
from config import CONFIG
from pathlib import Path

CJ_API_URL = "https://developers.cjdropshipping.com/api2.0/v1/product/list"

def load_cache():
    p = Path(CONFIG["CJ"]["cache_file"])
    if p.exists():
        try: return json.loads(p.read_text())
        except: return {}
    return {}

def save_cache(cache):
    Path(CONFIG["CJ"]["cache_file"]).write_text(json.dumps(cache))

def search_cj_products(trends):
    print(">> [Product Hunter] Searching CJ...")
    token = os.getenv("CJ_API_TOKEN")
    if not token:
        print("!! CJ_API_TOKEN missing, using mock data for V0.1 test")
        return get_mock_products(trends)

    cache = load_cache()
    all_products = []
    points_used = 0

    headers = {"CJ-Access-Token": token, "Content-Type": "application/json"}

    for trend in trends:
        keyword = trend['keyword']
        if keyword in cache:
            print(f"   Cache hit for {keyword}")
            all_products.extend(cache[keyword])
            continue

        if points_used + CONFIG["CJ"]["points_per_search"] > CONFIG["CJ"]["daily_points_limit"]:
            print("!! CJ points limit reached (50k), stopping.")
            break

        try:
            payload = {"keyword": keyword, "pageNum": 1, "pageSize": 10}
            resp = requests.post(CJ_API_URL, headers=headers, json=payload, timeout=20)
            points_used += CONFIG["CJ"]["points_per_search"]
            if resp.status_code == 200 and resp.json().get("code") == 200:
                products = []
                for item in resp.json().get("data", {}).get("list", [])[:5]:
                    products.append({
                        "name": item.get("productNameEn"),
                        "cost": float(item.get("sellPrice", 0)),
                        "rating": float(item.get("productScore", 4.5)),
                        "orders": int(item.get("sellCount", 100)),
                        "image": item.get("productImage"),
                        "pid": item.get("pid"),
                        "trend": trend,
                        "source": "CJ"
                    })
                cache[keyword] = products
                all_products.extend(products)
                time.sleep(1) # احترام الحدود
        except Exception as e:
            print(f"!! CJ error for {keyword}: {e}")

    save_cache(cache)
    print(f">> Found {len(all_products)} products, points used ~{points_used}")
    return all_products

def get_mock_products(trends):
    # بيانات وهمية للتجربة بدون CJ Token
    mocks = []
    for t in trends:
        mocks.append({"name": f"Electric Chopper for {t['keyword']}", "cost": 4.8, "rating": 4.7, "orders": 320, "image": "", "pid": "MOCK1", "trend": t, "source": "MOCK"})
        mocks.append({"name": f"Portable Blender {t['keyword']}", "cost": 6.2, "rating": 4.6, "orders": 210, "image": "", "pid": "MOCK2", "trend": t, "source": "MOCK"})
    return mocks
