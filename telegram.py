import os, requests

def send_to_telegram(winners):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("!! TELEGRAM secrets missing, printing report instead")
        for w in winners:
            print_report(w)
        return

    for i, w in enumerate(winners, 1):
        msg = f"""
🔥 #{i} WINNER - Score: {w.get('score','?')}/100

Product: {w.get('name')}
Niche: {w.get('niche')} | Trend: {w.get('trend_keyword')}
Cost: ${w.get('cost')} | Potential: ${w.get('selling_potential')}

Why:
• {w.get('why',["","","","",""])[0]}
• {w.get('why',["","","","",""])[1]}
• {w.get('why',["","","","",""])[2]}
• {w.get('why',["","","","",""])[3]}
• {w.get('why',["","","","",""])[4]}

🇬🇧 English hook:
{w.get('english_hook')}

🇲🇦 Darija:
{w.get('darija_hook')}

🔗 Affiliate: CJ PID {w.get('name')} - search in CJ
"""
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": msg})
        except Exception as e:
            print(f"!! Telegram failed: {e}")

def print_report(w):
    print(f"WINNER: {w}")
