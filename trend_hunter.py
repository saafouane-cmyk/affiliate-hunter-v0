import time
from pytrends.request import TrendReq
from config import CONFIG

def get_trending_keywords():
    print(">> [Trend Hunter] Fetching trends...")
    try:
        pytrends = TrendReq(hl='en-US', tz=0)
        seed = CONFIG["TRENDS"]["keywords_seed"]
        pytrends.build_payload(seed, timeframe='now 7-d', geo=CONFIG["TRENDS"]["geo"])
        related = pytrends.related_queries()

        trends = []
        for kw in seed[:CONFIG["TRENDS"]["max_trends"]]:
            if kw in related and related[kw]['rising'] is not None:
                rising = related[kw]['rising'].head(2)
                for _, row in rising.iterrows():
                    trends.append({"keyword": row['query'], "source_kw": kw, "growth": row['value']})
            trends.append({"keyword": kw, "source_kw": kw, "growth": "stable"})

        # إزالة التكرار
        uniq = {t['keyword']: t for t in trends}.values()
        result = list(uniq)[:CONFIG["TRENDS"]["max_trends"]]
        print(f">> Found {len(result)} trends: {[t['keyword'] for t in result]}")
        return result
    except Exception as e:
        print(f"!! Trend Hunter failed: {e}, using seed keywords")
        return [{"keyword": k, "source_kw": k, "growth": "seed"} for k in CONFIG["TRENDS"]["keywords_seed"][:3]]
