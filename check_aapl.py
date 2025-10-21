from news_influence_gemini_improved import fetch_financial_news
from datetime import datetime, timedelta

now = datetime.now()
start = now - timedelta(days=2)
end = now

print("Fetching AAPL news data...")
news = fetch_financial_news("AAPL", start, end)
print(f"Found {len(news)} news items:")

for item in news:
    is_mock = "mock" in item.get("summary", "").lower()
    status = "MOCK" if is_mock else "REAL"
    print(f"- {item.get('timestamp', '')} | {item.get('headline', '')} | {status}")
