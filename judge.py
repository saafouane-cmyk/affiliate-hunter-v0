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
    if hasattr(products, '__iter__') and not isinstance(products, (list, dict, str)):
        try:
            products = list(products)
        except:
            pass
    if isinstance(products, dict):
        products = list(products.values())
    if not isinstance(products, list):
        try:
            products = list(products)
        except:
            return []
    return products

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
            safe_products.append({
                "name": p.get('name','Unknown'),
                "cost": p.get('cost',0),
                "score": p.get('total_score',0),
                "trend": p.get('trend',{}).get('keyword','') if isinstance(p.get('trend'),dict) else str(p.get('trend','')),
                "orders": p.get('orders',0)
            })
        except:
            continue

    products_json = json.dumps(safe_products, ensure_ascii=False)
    prompt = PROMPT_TEMPLATE.format(final_winners=final_winners, products_json=products_json)

    provider = CONFIG["AI"]["provider"]
    model = CONFIG["AI"]["model"]

    if provider == "groq":
        try:
            from groq import Groq
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY missing")

            # إزالة أي تمرير خاطئ للـ proxies والتأكد من تهيئة العميل بشكل نظيف تماماً
            client = Groq(api_key=api_key)

            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            content = completion.choices[0].message.content
            if "```" in content:
                parts = content.split("```")
                for part in parts:
                    if "{" in part or "[" in part:
                        content = part.replace("json","").strip()
                        break
            parsed = json.loads(content)
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
        return []

    final_winners = CONFIG["AI"].get("final_winners", 3)
    num_winners = min(len(products), final_winners)

    winners = []
    for p in products[:num_winners]:
        try:
            trend = p.get('trend', {})
            if isinstance(trend, dict):
                source_kw = trend.get('source_kw', trend.get('keyword','general'))
                trend_kw = trend.get('keyword','trending')
            else:
                source_kw = str(trend)
                trend_kw = str(trend)

            scores = p.get('scores', {})
            winners.append({
                "name": p.get('name','Unknown Product'),
                "niche": source_kw,
                "trend_keyword": trend_kw,
                "cost": p.get('cost',0),
                "selling_potential": p.get('potential_price', p.get('cost',0)*3.5),
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
            print(f"!! Fallback error: {e}")
            continue

    print(f">> [AI Judge] Selected {len(winners)} winner(s).")
    return winners
