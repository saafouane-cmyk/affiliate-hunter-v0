import os
import json
from typing import Any, Dict, List

from config import CONFIG

PROMPT_TEMPLATE = """
You are a ruthless global affiliate marketing product judge.
Your job is NOT to invent product facts.
You must select the best {final_winners} products from the supplied SHORTLIST.
Judge mainly on marketing potential: WOW, PROBLEM, VIRAL, COMPETITION, PROFIT, GLOBAL, DEMO.
IMPORTANT: Do NOT invent prices/ratings/orders/commissions. Use product_id. Return ONLY valid JSON array, no markdown.
For every selected winner return: {{"product_id": "...", "marketing_score": 0-100, "why": ["WOW: ...","PROBLEM: ...","VIRAL: ...","COMPETITION: ...","MARGIN: ..."], "english_hook": "...", "darija_hook": "...", "recommended_angle": "...", "video_concept": "..."}}
Darija in Arabic script.
Products: {products_json}
"""

def safe_float(v, d=0.0):
    try: return float(v)
    except: return d
def safe_int(v, d=0):
    try: return int(v)
    except: return d
def safe_str(v, d=""):
    return "" if v is None else str(v).strip() or d

def get_product_id(p, i):
    if isinstance(p, dict):
        if p.get("id"): return str(p.get("id"))
        if p.get("product_id"): return str(p.get("product_id"))
        n = safe_str(p.get("name"), f"product-{i}")
        return f"generated-{i}-{n[:50]}"
    return f"generated-{i}"

def extract_trend(p):
    t = p.get("trend") if isinstance(p, dict) else None
    if not isinstance(t, dict): return {"keyword":"", "source_kw":""}
    return {"keyword": safe_str(t.get("keyword")), "source_kw": safe_str(t.get("source_kw"))}

def extract_scores(p):
    s = p.get("scores") if isinstance(p, dict) else None
    if not isinstance(s, dict): s = {}
    return {"wow": safe_float(s.get("wow")), "problem": safe_float(s.get("problem")), "viral": safe_float(s.get("viral")), "competition": safe_float(s.get("competition")), "margin": safe_float(s.get("margin"))}

def normalize_product_for_ai(product, index):
    trend = extract_trend(product)
    scores = extract_scores(product)
    product_id = get_product_id(product, index)
    selling_price = product.get("selling_price", product.get("potential_price", product.get("selling_potential")))
    commission = product.get("commission", product.get("commission_percent"))
    shipping = product.get("shipping_countries", product.get("ships_to", []))
    if not isinstance(shipping, list): shipping = []
    images = product.get("images", [])
    if not isinstance(images, list): images = []
    return {
        "product_id": product_id,
        "name": safe_str(product.get("name")),
        "niche": safe_str(product.get("niche")),
        "cost": safe_float(product.get("cost")),
        "selling_price": safe_float(selling_price) if selling_price is not None else None,
        "commission": safe_float(commission) if commission is not None else None,
        "rating": safe_float(product.get("rating")),
        "orders": safe_int(product.get("orders")),
        "trend_keyword": trend["keyword"],
        "trend_source": trend["source_kw"],
        "total_score": safe_float(product.get("total_score")),
        "scores": scores,
        "shipping_countries": shipping,
        "image_count": len(images),
        "url": safe_str(product.get("affiliate_url", product.get("product_url", ""))),
    }

def build_ai_input(products):
    res=[]
    for i,p in enumerate(products):
        if not isinstance(p, dict): continue
        res.append(normalize_product_for_ai(p,i))
    return res

def sort_products(products):
    return sorted([p for p in products if isinstance(p, dict)], key=lambda p: safe_float(p.get("total_score")), reverse=True)

def extract_json(content):
    if not content: raise ValueError("empty")
    content=content.strip()
    try: return json.loads(content)
    except: pass
    if "```" in content:
        for part in content.split("```"):
            c=part.strip()
            if c.lower().startswith("json"): c=c[4:].strip()
            try: return json.loads(c)
            except: continue
    s=content.find("["); e=content.rfind("]")
    if s!=-1 and e!=-1 and e>s:
        try: return json.loads(content[s:e+1])
        except: pass
    raise ValueError("Could not parse AI JSON")

def validate_ai_winner(w, valid_ids):
    if not isinstance(w, dict): return False
    for k in ["product_id","marketing_score","why","english_hook","darija_hook","recommended_angle","video_concept"]:
        if k not in w: return False
    if safe_str(w.get("product_id")) not in valid_ids: return False
    ms=safe_float(w.get("marketing_score"),-1)
    if not 0 <= ms <= 100: return False
    why=w.get("why")
    if not isinstance(why, list) or len(why)<5: return False
    if not safe_str(w.get("english_hook")): return False
    if not safe_str(w.get("darija_hook")): return False
    return True

def validate_ai_response(data, products):
    if not isinstance(data, list): raise ValueError("not array")
    valid_ids={get_product_id(p,i) for i,p in enumerate(products)}
    clean=[]; seen=set()
    for w in data:
        if not validate_ai_winner(w, valid_ids): continue
        pid=safe_str(w["product_id"])
        if pid in seen: continue
        seen.add(pid); clean.append(w)
    if not clean: raise ValueError("no valid winners")
    max_w=safe_int(CONFIG["AI"].get("final_winners"),3)
    return clean[:max_w]

def merge_winner(ai_winner, original_products):
    target=safe_str(ai_winner["product_id"])
    orig=None
    for i,p in enumerate(original_products):
        if get_product_id(p,i)==target: orig=p; break
    if orig is None: raise ValueError(f"not found {target}")
    r=dict(orig)
    r["product_id"]=target
    r["marketing_score"]=safe_float(ai_winner.get("marketing_score"))
    r["why"]=ai_winner.get("why",[])
    r["english_hook"]=safe_str(ai_winner.get("english_hook"))
    r["darija_hook"]=safe_str(ai_winner.get("darija_hook"))
    r["recommended_angle"]=safe_str(ai_winner.get("recommended_angle"))
    r["video_concept"]=safe_str(ai_winner.get("video_concept"))
    r["original_total_score"]=safe_float(orig.get("total_score"))
    return r

def groq_judge(products):
    from groq import Groq
    api_key=os.getenv("GROQ_API_KEY")
    if not api_key: raise RuntimeError("GROQ_API_KEY missing")
    client=Groq(api_key=api_key)
    model=CONFIG["AI"]["model"]
    products_for_ai=build_ai_input(products)
    products_json=json.dumps(products_for_ai, ensure_ascii=False, indent=2)
    final_winners=safe_int(CONFIG["AI"].get("final_winners"),3)
    final_winners=min(final_winners, len(products_for_ai))
    if final_winners<=0: final_winners=1
    prompt=PROMPT_TEMPLATE.format(final_winners=final_winners, products_json=products_json)
    print(f">> [AI Judge] Sending {len(products_for_ai)} to Groq...")
    comp=client.chat.completions.create(model=model, messages=[{"role":"system","content":"JSON only judge."},{"role":"user","content":prompt}], temperature=0.4)
    if not comp.choices: raise RuntimeError("no choices")
    content=comp.choices[0].message.content
    print(">> [AI Judge] Response received.")
    parsed=extract_json(content)
    validated=validate_ai_response(parsed, products)
    return [merge_winner(w, products) for w in validated]

def fallback_judge(products):
    print(">> [AI Judge] Using deterministic fallback.")
    sorted_p=sort_products(products)
    fw=safe_int(CONFIG["AI"].get("final_winners"),3)
    fw=min(fw, len(sorted_p))
    if fw<=0: fw=min(3, len(sorted_p))
    winners=[]
    for idx, product in enumerate(sorted_p):
        if len(winners)>=fw: break
        pid=get_product_id(product, idx)
        sc=extract_scores(product)
        marketing_score=(sc["wow"]*0.25+sc["problem"]*0.20+sc["viral"]*0.25+sc["competition"]*0.15+sc["margin"]*0.15)*10
        r=dict(product)
        r["product_id"]=pid
        r["marketing_score"]=round(marketing_score,1)
        r["why"]=[f"WOW: {sc['wow']}/10", f"PROBLEM: {sc['problem']}/10", f"VIRAL: {sc['viral']}/10", f"COMPETITION: {sc['competition']}/10", f"MARGIN: {sc['margin']}/10"]
        r["english_hook"]="Stop scrolling — this solves a real problem in seconds."
        r["darija_hook"]="حبس شوية! شوف هاد الحاجة، كتحل مشكل حقيقي فثواني!"
        r["recommended_angle"]="Problem → Demonstration → Result"
        r["video_concept"]="Show problem, then demo product, finish with result."
        r["original_total_score"]=safe_float(product.get("total_score"))
        winners.append(r)
    return winners

def normalize_input_products(products):
    # FIX FOR YOUR BUG: accepts dict, dict_values, list, tuple
    if products is None:
        return []
    if isinstance(products, dict):
        # if dict of id->product, take values
        return list(products.values())
    if not isinstance(products, list):
        try:
            # handles dict_values, tuple, set, etc
            return list(products)
        except Exception:
            print(f"!! [AI Judge] Cannot convert {type(products)} to list")
            return []
    return products

def ai_judge(products):
    products = normalize_input_products(products)
    if not products:
        print("!! [AI Judge] No products received after normalization")
        return []
    # filter only dicts
    products = [p for p in products if isinstance(p, dict)]
    if not products:
        print("!! [AI Judge] No valid dict products")
        return []
    sorted_p=sort_products(products)
    max_p=safe_int(CONFIG["AI"].get("max_products_to_judge"),10)
    max_p=min(max_p, len(sorted_p))
    to_judge=sorted_p[:max_p]
    provider=safe_str(CONFIG["AI"].get("provider","groq"))
    model=safe_str(CONFIG["AI"].get("model",""))
    print(f">> [AI Judge] Provider: {provider} | Model: {model} | Shortlist: {len(to_judge)}")
    if provider.lower()=="groq":
        try:
            winners=groq_judge(to_judge)
            if winners:
                print(f">> [AI Judge] Selected {len(winners)} winner(s).")
                return winners
        except Exception as e:
            print(f"!! [AI Judge] Groq failed: {e}")
            print(">> [AI Judge] Switching to fallback.")
    return fallback_judge(to_judge)

def save_winners(winners, path="winners.json"):
    try:
        d=os.path.dirname(path)
        if d: os.makedirs(d, exist_ok=True)
        tmp=path+".tmp"
        with open(tmp,"w",encoding="utf-8") as f:
            json.dump(winners,f,ensure_ascii=False,indent=2)
        os.replace(tmp,path)
        print(f">> [AI Judge] Winners saved: {path}")
        return True
    except Exception as e:
        print(f"!! [AI Judge] Could not save: {e}")
        return False
