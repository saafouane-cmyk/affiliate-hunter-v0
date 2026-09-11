import os

# قابل للتعديل بدون لمس الكود
CONFIG = {
    "TRENDS": {
        "geo": "US",  # غيّرها لـ MA للسوق المغربي
        "keywords_seed": ["kitchen gadgets", "home fitness", "pet accessories", "car accessories", "beauty tools"],
        "max_trends": 5
    },
    "CJ": {
        "daily_points_limit": 50000,
        "points_per_search": 200, # تقديري، نراقبه في اللوغ
        "cache_file": "/tmp/cj_cache.json",
        "min_orders": 50,
        "min_rating": 4.0
    },
    "SCORING": {
        "weights": {"wow": 0.25, "problem": 0.25, "viral": 0.20, "margin": 0.15, "competition": 0.15}
    },
    "AI": {
        # هادي هي النقطة اللي صححتي - اسم الموديل متغير
        "provider": os.getenv("AI_PROVIDER", "groq"), # groq | gemini | openai
        "model": os.getenv("AI_MODEL_NAME", "llama-3.1-70b-versatile"), # تقدر تبدلو لـ gemini-3.7-flash لاحقا
        "max_products_to_judge": 15,
        "final_winners": 5
    }
}
