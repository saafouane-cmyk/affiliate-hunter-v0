from trend_hunter import get_trending_keywords
from product_hunter import search_cj_products
from filter import filter_products
from scoring import score_all
from judge import ai_judge
from telegram import send_top_product
import config

def run():
    print("=== Affiliate Hunter V0.1 Started ===")
    trends = get_trending_keywords()
    print(f"Trends found: {trends}")
    if not trends:
        print("No trends today")
        return
    products = search_cj_products(trends)
    print(f"Products found: {len(products)}")
    filtered = filter_products(products)
    print(f"After filter: {len(filtered)}")
    scored = score_all(filtered)
    for item in scored[:10]:
        result = ai_judge(item)
        if result.get("approved"):
            send_top_product(item, result)
            print(f"SENT: {item.get('title')}")
            break
    print("=== Done ===")

if __name__ == "__main__":
    run()
