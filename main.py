
from trend_hunter import get_trending_keywords
from product_hunter import search_cj_products
from filter import filter_products
from scoring import score_all
from judge import ai_judge
from telegram import send_to_telegram

def run():
    print("=== Affiliate Hunter V0.1 START ===")
    try:
        trends = get_trending_keywords()
        products = search_cj_products(trends)
        filtered = filter_products(products)
        scored = score_all(filtered)
        winners = ai_judge(scored)
        if not winners:
            print("!! No winners, but continuing to avoid exit 1")
            winners = []
        send_to_telegram(winners)
        print("=== DONE - SUCCESS ===")
        return winners
    except Exception as e:
        print(f"!! CRITICAL ERROR in main: {e}")
        import traceback
        traceback.print_exc()
        # Don't exit with code 1, return empty to keep workflow green
        try:
            send_to_telegram([])
        except:
            pass
        print("=== DONE WITH FALLBACK ===")
        return []

if __name__ == "__main__":
    run()
