from src.hunters.trend_hunter import get_trending_keywords
from src.hunters.product_hunter import search_cj_products
from src.core.filter import filter_products
from src.core.scoring import score_all
from src.ai.judge import ai_judge
from src.notifier.telegram import send_to_telegram

def run():
    print("=== Affiliate Hunter V0.1 START ===")
    trends = get_trending_keywords()
    products = search_cj_products(trends)
    filtered = filter_products(products)
    scored = score_all(filtered)
    winners = ai_judge(scored)
    send_to_telegram(winners)
    print("=== DONE ===")
    return winners

if __name__ == "__main__":
    run()
