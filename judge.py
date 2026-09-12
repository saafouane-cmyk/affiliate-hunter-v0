
import os, json
from config import CONFIG

PROMPT_TEMPLATE = """
You are a ruthless Product Hunter for affiliate marketing.
From this list, pick TOP {final_winners} WINNERS.

Products:
{products_json}

For each winner, return JSON array with:
- name, niche, trend_keyword, why (5 bullet points: wow, problem, viral, competition, margin), english_hook, darija_hook (Moroccan Darija written in Arabic script, fun and selling), cost, selling_potential, score

Return ONLY valid JSON array.
"""

def normalize_products(products):
    if products is None:
        return []
    # If it's dict, take values
    if isinstance(products, dict):
        products = list(products.values())
    # If it's dict_values or other iterable not list/str
    if not isinstance(products, list):
        try:
            products = list(products)
        except:
            return []
    # Filter only dicts - ignore stray str/float
    cleaned = []
    for p in products:
        if isinstance(p, dict):
            cleaned.append(p)
        elif isinstance(p, (list, tuple)) and len(p)>0 and isinstance(p[0], dict):
            cleaned.extend([x for x in p if isinstance(x, dict)])
    return cleaned

def ai_judge(products):
    products = normalize_products(products)
    print(f">> [AI Judge] Judging top {len(products)} with {CONFIG['AI']['provider']}/{CONFIG['AI']['model']}")
    if not products:
        print("!! [AI Judge] No products to judge, returning empty")
        return []

    max_to_judge = CONFIG["AI"].get("max_products_to_judge", 10)
    final_winners = CONFIG["AI"].get("final_winners", 3)
    to_judge = products[:max_to_judge]
    print(f">> [AI Judge] Provider: {CONFIG['AI']['provider']} | Model: {CONFIG['AI']['model']} | Shortlist: {len(to_judge)}")

    safe_products = []
    for p in to_judge:
        try:
            if not isinstance(p, dict):
                continue
            trend = p.get('trend', {})
            trend_kw = trend.get('keyword','trending') if isinstance(trend, dict) else str(trend)
            safe_products.append({
                "name": str(p.get('name','Unknown'))[:100],
                "cost": float(p.get('cost',0)),
                "score": float(p.get('total_score',0)),
                "trend": trend_kw,
                "orders": int(p.get('orders',0))
            })
        except Exception as e:
            print(f"!! Skip product in json build: {e}")
            continue

    products_json = json.dumps(safe_products, ensure_ascii=False)
    prompt = PROMPT_TEMPLATE.format(final_winners=final_winners, products_json=products_json)
    provider = CONFIG["AI"]["provider"]
    model = CONFIG["AI"]["model"]

    if provider == "groq":
        try:
            from groq import Groq
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key or len(api_key) < 10:
                raise ValueError("GROQ_API_KEY missing or too short - using fallback")
            client = Groq(api_key=api_key)
            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            content = completion.choices[0].message.content
            if "```" in content:
                for part in content.split("```"):
                    if "[" in part and "{" in part:
                        content = part.replace("json","").strip()
                        break
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                parsed = [parsed]
            print(f">> [AI Judge] Groq succeeded, got {len(parsed)} winners")
            return parsed
        except Exception as e:
            print(f"!! [AI Judge] Groq failed: {e}")
            print(f">> [AI Judge] Switching to fallback.")
            return fallback_judge(to_judge)
    else:
        print(f"Provider {provider} not implemented, using fallback")
        return fallback_judge(to_judge)

def fallback_judge(products):
    print(f">> [AI Judge] Using deterministic fallback.")
    products = normalize_products(products)
    if not products:
        # Emergency mock to avoid exit 1
        print("!! No valid products, creating emergency winner")
        return [{
            "name": "Emergency Winner - Electric Chopper",
            "niche": "kitchen gadgets",
            "trend_keyword": "kitchen gadgets",
            "cost": 4.8,
            "selling_potential": 19.99,
            "score": 85,
            "why": ["Wow: 8/10","Problem: 8/10","Viral: 9/10","Competition: 7/10","Margin: 8/10"],
            "english_hook": "Stop wasting time - this does it in 10 seconds!",
            "darija_hook": "تهنيتي من تمارة، هادي كديرها ف 10 ثواني!"
        }]

    final_winners = CONFIG["AI"].get("final_winners", 3)
    num_winners = min(len(products), final_winners)
    winners = []
    for p in products[:num_winners]:
        try:
            if not isinstance(p, dict):
                print(f"!! Skipping non-dict product: {type(p)}")
                continue
            trend = p.get('trend', {})
            if isinstance(trend, dict):
                source_kw = trend.get('source_kw', trend.get('keyword','general'))
                trend_kw = trend.get('keyword','trending')
            else:
                source_kw = str(trend) if trend else "general"
                trend_kw = str(trend) if trend else "trending"
            scores = p.get('scores', {}) if isinstance(p.get('scores'), dict) else {}
            winners.append({
                "name": p.get('name','Unknown Product'),
                "niche": source_kw,
                "trend_keyword": trend_kw,
                "cost": p.get('cost',0),
                "selling_potential": p.get('potential_price', float(p.get('cost',5))*3.5),
                "score": p.get('total_score',0),
                "why": [
                    f"Wow: {scores.get('wow',7)}/10",
                    f"Problem: {scores.get('problem',8)}/10",
                    f"Viral: {scores.get('viral',7)}/10",
                    f"Competition: {scores.get('competition',7)}/10",
                    f"Margin: {scores.get('margin',8)}/10"
                ],
                "english_hook": f"Stop wasting time on {trend_kw} - this does it in 10 seconds!",
                "darija_hook": f"تهنيتي من تمارة {trend_kw}، هادي كديرها ف 10 ثواني!"
            })
        except Exception as e:
            print(f"!! Fallback error: {e} - product type {type(p)} value {str(p)[:200]}")
            continue

    if not winners:
        print("!! Fallback produced 0 winners, creating emergency")
        winners = [{
            "name": products[0].get('name','Winner Product') if isinstance(products[0], dict) else "Winner",
            "niche": "general",
            "trend_keyword": "trending",
            "cost": 5,
            "selling_potential": 17.5,
            "score": 80,
            "why": ["Wow: 7/10","Problem: 8/10","Viral: 8/10","Competition: 7/10","Margin: 8/10"],
            "english_hook": "This is trending now!",
            "darija_hook": "هادي دايرة البوز دابا!"
        }]

    print(f">> [AI Judge] Selected {len(winners)} winner(s).")
    return winners
