import os
import json
from typing import Any, Dict, List

from config import CONFIG


# ============================================================
# AI JUDGE V0.2
# ============================================================
# وظيفته:
# 1. يأخذ المنتجات التي اجتازت الـ Hard Validator
# 2. يرتبها حسب total_score
# 3. يرسل بيانات كافية للـ AI
# 4. يختار أفضل المنتجات تسويقياً
# 5. يتحقق من JSON الناتج
# 6. لا يسمح للـ AI بتغيير البيانات المالية/الفعلية
# 7. إذا فشل AI يرجع إلى fallback آمن
#
# Pipeline:
#
# HUNTER
#    ↓
# NORMALIZER
#    ↓
# HARD VALIDATOR
#    ↓
# AI JUDGE  ← هذا الملف
#    ↓
# WINNERS
#    ↓
# VIDEO ENGINE V3.6.1
#
# ============================================================


# ------------------------------------------------------------
# PROMPT
# ------------------------------------------------------------

PROMPT_TEMPLATE = """
You are a ruthless global affiliate marketing product judge.

Your job is NOT to invent product facts.

You must select the best {final_winners} products from the supplied
SHORTLIST.

Judge mainly on marketing potential:

1. WOW FACTOR
2. SOLVES A REAL PROBLEM
3. VIRAL / SHORT-FORM VIDEO POTENTIAL
4. LOW COMPETITION / DIFFERENTIATION
5. PROFIT / COMMISSION POTENTIAL
6. GLOBAL MARKETABILITY
7. DEMONSTRATION POTENTIAL IN A 15-20 SECOND VIDEO

IMPORTANT RULES:

- Do NOT invent prices.
- Do NOT invent ratings.
- Do NOT invent orders.
- Do NOT invent commissions.
- Do NOT invent shipping countries.
- Do NOT change total_score.
- Do NOT create facts that are not present in the input.
- Use the supplied product_id to identify products.
- Return ONLY valid JSON.
- No Markdown.
- No ```json.
- No explanations outside the JSON.

For every selected winner return:

{
  "product_id": "...",
  "marketing_score": 0-100,
  "why": [
    "WOW: ...",
    "PROBLEM: ...",
    "VIRAL: ...",
    "COMPETITION: ...",
    "MARGIN: ..."
  ],
  "english_hook": "...",
  "darija_hook": "...",
  "recommended_angle": "...",
  "video_concept": "..."
}

The hooks must be short and suitable for a 15-20 second
affiliate video.

Moroccan Darija must be written in Arabic script.

Products:

{products_json}
"""


# ------------------------------------------------------------
# SAFE HELPERS
# ------------------------------------------------------------

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def get_product_id(product: Dict[str, Any], index: int) -> str:
    """
    نحاول استعمال ID الحقيقي.
    إذا لم يوجد، ننشئ ID ثابتاً نسبياً.
    """

    product_id = product.get("id")

    if product_id:
        return str(product_id)

    # بعض الـ hunters قد تستعمل product_id
    product_id = product.get("product_id")

    if product_id:
        return str(product_id)

    # fallback
    name = safe_str(product.get("name"), f"product-{index}")
    return f"generated-{index}-{name[:50]}"


# ------------------------------------------------------------
# EXTRACT TREND
# ------------------------------------------------------------

def extract_trend(product: Dict[str, Any]) -> Dict[str, str]:

    trend = product.get("trend")

    if not isinstance(trend, dict):
        return {
            "keyword": "",
            "source_kw": "",
        }

    return {
        "keyword": safe_str(trend.get("keyword")),
        "source_kw": safe_str(trend.get("source_kw")),
    }


# ------------------------------------------------------------
# EXTRACT SCORES
# ------------------------------------------------------------

def extract_scores(product: Dict[str, Any]) -> Dict[str, float]:

    scores = product.get("scores")

    if not isinstance(scores, dict):
        scores = {}

    return {
        "wow": safe_float(scores.get("wow")),
        "problem": safe_float(scores.get("problem")),
        "viral": safe_float(scores.get("viral")),
        "competition": safe_float(scores.get("competition")),
        "margin": safe_float(scores.get("margin")),
    }


# ------------------------------------------------------------
# NORMALIZE PRODUCT FOR AI
# ------------------------------------------------------------

def normalize_product_for_ai(
    product: Dict[str, Any],
    index: int
) -> Dict[str, Any]:

    trend = extract_trend(product)
    scores = extract_scores(product)

    product_id = get_product_id(product, index)

    selling_price = product.get(
        "selling_price",
        product.get(
            "potential_price",
            product.get("selling_potential")
        )
    )

    commission = product.get(
        "commission",
        product.get("commission_percent")
    )

    shipping = product.get(
        "shipping_countries",
        product.get("ships_to", [])
    )

    if not isinstance(shipping, list):
        shipping = []

    images = product.get("images", [])

    if not isinstance(images, list):
        images = []

    return {
        # Identity
        "product_id": product_id,
        "name": safe_str(product.get("name")),
        "niche": safe_str(product.get("niche")),

        # Financial facts
        "cost": safe_float(product.get("cost")),
        "selling_price": (
            safe_float(selling_price)
            if selling_price is not None
            else None
        ),
        "commission": (
            safe_float(commission)
            if commission is not None
            else None
        ),

        # Product facts
        "rating": safe_float(product.get("rating")),
        "orders": safe_int(product.get("orders")),

        # Trend
        "trend_keyword": trend["keyword"],
        "trend_source": trend["source_kw"],

        # Existing scoring
        "total_score": safe_float(product.get("total_score")),
        "scores": scores,

        # Market
        "shipping_countries": shipping,

        # Visual potential
        "image_count": len(images),

        # Useful metadata
        "url": safe_str(
            product.get(
                "affiliate_url",
                product.get("product_url", "")
            )
        ),
    }


# ------------------------------------------------------------
# BUILD AI INPUT
# ------------------------------------------------------------

def build_ai_input(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:

    result = []

    for index, product in enumerate(products):

        if not isinstance(product, dict):
            continue

        result.append(
            normalize_product_for_ai(product, index)
        )

    return result


# ------------------------------------------------------------
# SORT PRODUCTS
# ------------------------------------------------------------

def sort_products(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    مهم جداً:
    لا نفترض أن products مرتبة مسبقاً.
    """

    return sorted(
        products,
        key=lambda p: safe_float(
            p.get("total_score")
        ),
        reverse=True
    )


# ------------------------------------------------------------
# JSON EXTRACTION
# ------------------------------------------------------------

def extract_json(content: str) -> Any:

    if not content:
        raise ValueError("AI returned empty response")

    content = content.strip()

    # الحالة الطبيعية
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # إذا AI أضاف Markdown
    if "```" in content:

        parts = content.split("```")

        for part in parts:

            cleaned = part.strip()

            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()

            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                continue

    # محاولة استخراج أول [ وآخر ]
    start = content.find("[")
    end = content.rfind("]")

    if start != -1 and end != -1 and end > start:

        candidate = content[start:end + 1]

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError("Could not parse AI JSON response")


# ------------------------------------------------------------
# VALIDATE AI WINNER
# ------------------------------------------------------------

def validate_ai_winner(
    winner: Any,
    valid_ids: set
) -> bool:

    if not isinstance(winner, dict):
        return False

    required = [
        "product_id",
        "marketing_score",
        "why",
        "english_hook",
        "darija_hook",
        "recommended_angle",
        "video_concept",
    ]

    for key in required:
        if key not in winner:
            return False

    product_id = safe_str(winner.get("product_id"))

    if product_id not in valid_ids:
        return False

    marketing_score = safe_float(
        winner.get("marketing_score"),
        -1
    )

    if not 0 <= marketing_score <= 100:
        return False

    why = winner.get("why")

    if not isinstance(why, list):
        return False

    if len(why) < 5:
        return False

    if not safe_str(winner.get("english_hook")):
        return False

    if not safe_str(winner.get("darija_hook")):
        return False

    return True


# ------------------------------------------------------------
# VALIDATE COMPLETE RESPONSE
# ------------------------------------------------------------

def validate_ai_response(
    data: Any,
    products: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    if not isinstance(data, list):
        raise ValueError("AI output is not a JSON array")

    valid_ids = {
        get_product_id(p, i)
        for i, p in enumerate(products)
    }

    clean = []
    seen_ids = set()

    for winner in data:

        if not validate_ai_winner(
            winner,
            valid_ids
        ):
            continue

        product_id = safe_str(
            winner["product_id"]
        )

        # منع التكرار
        if product_id in seen_ids:
            continue

        seen_ids.add(product_id)

        clean.append(winner)

    if not clean:
        raise ValueError(
            "AI returned no valid winners"
        )

    max_winners = safe_int(
        CONFIG["AI"].get("final_winners"),
        1
    )

    return clean[:max_winners]


# ------------------------------------------------------------
# MERGE AI DATA WITH ORIGINAL PRODUCT
# ------------------------------------------------------------

def merge_winner(
    ai_winner: Dict[str, Any],
    original_products: List[Dict[str, Any]]
) -> Dict[str, Any]:

    target_id = safe_str(
        ai_winner["product_id"]
    )

    original = None

    for index, product in enumerate(original_products):

        if get_product_id(product, index) == target_id:
            original = product
            break

    if original is None:
        raise ValueError(
            f"Original product not found: {target_id}"
        )

    # --------------------------------------------------------
    # IMPORTANT:
    # نأخذ الحقائق من المنتج الأصلي
    # وليس من AI
    # --------------------------------------------------------

    result = dict(original)

    result["product_id"] = target_id

    # AI marketing layer
    result["marketing_score"] = safe_float(
        ai_winner.get("marketing_score")
    )

    result["why"] = ai_winner.get(
        "why",
        []
    )

    result["english_hook"] = safe_str(
        ai_winner.get("english_hook")
    )

    result["darija_hook"] = safe_str(
        ai_winner.get("darija_hook")
    )

    result["recommended_angle"] = safe_str(
        ai_winner.get("recommended_angle")
    )

    result["video_concept"] = safe_str(
        ai_winner.get("video_concept")
    )

    # Keep original factual score
    result["original_total_score"] = safe_float(
        original.get("total_score")
    )

    return result


# ------------------------------------------------------------
# GROQ JUDGE
# ------------------------------------------------------------

def groq_judge(
    products: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured"
        )

    client = Groq(
        api_key=api_key
    )

    model = CONFIG["AI"]["model"]

    products_for_ai = build_ai_input(
        products
    )

    products_json = json.dumps(
        products_for_ai,
        ensure_ascii=False,
        indent=2
    )

    final_winners = safe_int(
        CONFIG["AI"].get("final_winners"),
        1
    )

    prompt = PROMPT_TEMPLATE.format(
        final_winners=final_winners,
        products_json=products_json
    )

    print(
        f">> [AI Judge] Sending "
        f"{len(products_for_ai)} products to Groq..."
    )

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict JSON-only "
                    "affiliate product judge."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.4,
    )

    if not completion.choices:
        raise RuntimeError(
            "Groq returned no choices"
        )

    content = completion.choices[0].message.content

    print(
        ">> [AI Judge] Response received."
    )

    parsed = extract_json(content)

    validated = validate_ai_response(
        parsed,
        products
    )

    winners = []

    for ai_winner in validated:

        merged = merge_winner(
            ai_winner,
            products
        )

        winners.append(merged)

    return winners


# ------------------------------------------------------------
# FALLBACK JUDGE
# ------------------------------------------------------------

def fallback_judge(
    products: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    print(
        ">> [AI Judge] Using deterministic fallback."
    )

    sorted_products = sort_products(
        products
    )

    final_winners = safe_int(
        CONFIG["AI"].get("final_winners"),
        1
    )

    winners = []

    for index, product in enumerate(
        sorted_products
    ):

        if len(winners) >= final_winners:
            break

        product_id = get_product_id(
            product,
            index
        )

        scores = extract_scores(
            product
        )

        trend = extract_trend(
            product
        )

        keyword = (
            trend["keyword"]
            or product.get("name", "this product")
        )

        # ----------------------------------------------------
        # Fallback marketing score
        # ----------------------------------------------------

        marketing_score = (
            scores["wow"] * 0.25
            + scores["problem"] * 0.20
            + scores["viral"] * 0.25
            + scores["competition"] * 0.15
            + scores["margin"] * 0.15
        ) * 10

        result = dict(product)

        result["product_id"] = product_id

        result["marketing_score"] = round(
            marketing_score,
            1
        )

        result["why"] = [
            f"WOW: {scores['wow']}/10",
            f"PROBLEM: {scores['problem']}/10",
            f"VIRAL: {scores['viral']}/10",
            f"COMPETITION: {scores['competition']}/10",
            f"MARGIN: {scores['margin']}/10",
        ]

        result["english_hook"] = (
            f"Stop scrolling — "
            f"this solves a real problem "
            f"in seconds."
        )

        result["darija_hook"] = (
            f"حبس شوية! شوف هاد الحاجة، "
            fكتحل مشكل حقيقي فثواني!"
        )

        result["recommended_angle"] = (
            "Problem → Demonstration → Result"
        )

        result["video_concept"] = (
            "Show the problem first, "
            "then demonstrate the product "
            "and finish with the result."
        )

        result["original_total_score"] = safe_float(
            product.get("total_score")
        )

        winners.append(result)

    return winners


# ------------------------------------------------------------
# MAIN AI JUDGE
# ------------------------------------------------------------

def ai_judge(
    products: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    if not isinstance(products, list):
        print(
            "!! [AI Judge] products must be a list"
        )
        return []

    if not products:
        print(
            "!! [AI Judge] No products received"
        )
        return []

    # --------------------------------------------------------
    # Sort BEFORE selecting shortlist
    # --------------------------------------------------------

    sorted_products = sort_products(
        products
    )

    max_products = safe_int(
        CONFIG["AI"].get(
            "max_products_to_judge"
        ),
        10
    )

    to_judge = sorted_products[
        :max_products
    ]

    provider = safe_str(
        CONFIG["AI"].get(
            "provider",
            "groq"
        )
    )

    model = safe_str(
        CONFIG["AI"].get(
            "model",
            ""
        )
    )

    print(
        f">> [AI Judge] "
        f"Provider: {provider} | "
        f"Model: {model} | "
        f"Shortlist: {len(to_judge)}"
    )

    # --------------------------------------------------------
    # AI PROVIDER
    # --------------------------------------------------------

    if provider.lower() == "groq":

        try:

            winners = groq_judge(
                to_judge
            )

            if winners:

                print(
                    f">> [AI Judge] "
                    f"Selected {len(winners)} winner(s)."
                )

                return winners

        except Exception as e:

            print(
                f"!! [AI Judge] Groq failed: {e}"
            )

            print(
                ">> [AI Judge] "
                "Switching to deterministic fallback."
            )

    else:

        print(
            f"!! [AI Judge] "
            f"Provider '{provider}' "
            f"is not implemented."
        )

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    return fallback_judge(
        to_judge
    )


# ------------------------------------------------------------
# OPTIONAL: SAVE WINNERS
# ------------------------------------------------------------

def save_winners(
    winners: List[Dict[str, Any]],
    path: str = "winners.json"
) -> bool:

    try:

        directory = os.path.dirname(
            path
        )

        if directory:
            os.makedirs(
                directory,
                exist_ok=True
            )

        tmp_path = path + ".tmp"

        with open(
            tmp_path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                winners,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(
            tmp_path,
            path
        )

        print(
            f">> [AI Judge] "
            f"Winners saved: {path}"
        )

        return True

    except Exception as e:

        print(
            f"!! [AI Judge] "
            f"Could not save winners: {e}"
        )

        return False
