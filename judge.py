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

def ai_judge(products):
    print(f">> [AI Judge] Judging top {len(products)} with {CONFIG['AI']['provider']}/{CONFIG['AI']['model']}")
    provider = CONFIG["AI"]["provider"]
    model = CONFIG["AI"]["model"]
    to_judge = products[:CONFIG["AI"]["max_products_to_judge"]]

    products_json = json.dumps([{"name": p['name'], "cost": p['cost'], "score": p['total_score'], "trend": p['trend']['keyword'], "orders": p['orders']} for p in to_judge], ensure_ascii=False)

    prompt = PROMPT_TEMPLATE.format(final_winners=CONFIG["AI"]["final_winners"], products_json=products_json)

    # Groq path (free)
    if provider == "groq":
        try:
            from groq import Groq
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            content = completion.choices[0].message.content
            # تنظيف الـ JSON
            if "```" in content:
                content = content.split("```")[1].replace("json","").strip()
            return json.loads(content)
        except Exception as e:
            print(f"!! Groq Judge failed: {e}, falling back to scoring only")
            return fallback_judge(to_judge)
    else:
        # هنا يمكن إضافة Gemini 3.7 Flash لاحقا بنفس المتغير
        print(f"Provider {provider} not implemented in V0.1, using fallback")
        return fallback_judge(to_judge)

def fallback_judge(products):
    winners = []
    for p in products[:CONFIG["AI"]["final_winners"]]:
        winners.append({
            "name": p['name'],
            "niche": p['trend']['source_kw'],
            "trend_keyword": p['trend']['keyword'],
            "cost": p['cost'],
            "selling_potential": p['potential_price'],
            "score": p['total_score'],
            "why": [f"Wow: {p['scores']['wow']}/10", f"Problem: {p['scores']['problem']}/10", f"Viral: {p['scores']['viral']}/10", f"Competition: {p['scores']['competition']}/10", f"Margin: {p['scores']['margin']}/10"],
            "english_hook": f"Stop wasting time on {p['trend']['keyword']} - this does it in 10 seconds!",
            "darija_hook": f"تهنيتي من تمارة {p['trend']['keyword']}، هادي كديرها ف 10 ثواني!"
        })
    return winners
