from config import CONFIG

def calculate_score(product):
    # تقدير أولي، سيحسنه الـ AI Judge لاحقا
    cost = product.get("cost", 5)
    # هامش تقديري
    potential_price = cost * 3.5
    margin_score = min(10, (potential_price - cost) / potential_price * 15)

    # تقديرات بناء على الترند
    wow = 8 if "electric" in product['name'].lower() or "portable" in product['name'].lower() else 6
    problem = 8
    viral = 9 if product['trend']['growth'] != 'seed' else 6
    competition = 7 # نفترض متوسط حتى نضيف أداة SEO لاحقا

    weights = CONFIG["SCORING"]["weights"]
    score = (wow*weights['wow'] + problem*weights['problem'] + viral*weights['viral'] + margin_score*weights['margin'] + competition*weights['competition']) * 10

    product['scores'] = {"wow": wow, "problem": problem, "viral": viral, "margin": round(margin_score,1), "competition": competition}
    product['potential_price'] = round(potential_price, 2)
    product['total_score'] = round(score, 1)
    return product

def score_all(products):
    print(f">> [Scoring] Scoring {len(products)}...")
    for p in products:
        calculate_score(p)
    return sorted(products, key=lambda x: x['total_score'], reverse=True)
