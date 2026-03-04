import feedparser
import requests
import os
import re
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from transformers import pipeline

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# ── Load FinBERT (Finance-specific sentiment AI) ────────────────────────
print("Loading FinBERT model (first time takes 2-3 minutes to download)...")
sentiment_model = pipeline(
    "text-classification",
    model="ProsusAI/finbert",
    truncation=True,
    max_length=512
)
print("✅ FinBERT loaded")

# ── News Sources (Indian Market RSS Feeds) ──────────────────────────────
NEWS_FEEDS = [
    {
        "name": "Economic Times Markets",
        "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"
    },
    {
        "name": "Moneycontrol",
        "url": "https://www.moneycontrol.com/rss/marketoutlook.xml"
    },
    {
        "name": "Business Standard Markets",
        "url": "https://www.business-standard.com/rss/markets-106.rss"
    },
    {
        "name": "LiveMint Markets",
        "url": "https://www.livemint.com/rss/markets"
    },
    {
        "name": "NDTV Profit",
        "url": "https://feeds.feedburner.com/ndtvprofit-latest"
    }
]

# ── Stock name to symbol mapping ────────────────────────────────────────
STOCK_KEYWORDS = {
    "RELIANCE.NS":   ["reliance", "ril", "mukesh ambani"],
    "TCS.NS":        ["tcs", "tata consultancy"],
    "HDFCBANK.NS":   ["hdfc bank", "hdfcbank"],
    "INFY.NS":       ["infosys", "infy"],
    "ICICIBANK.NS":  ["icici bank", "icicibank"],
    "SBIN.NS":       ["sbi", "state bank"],
    "BHARTIARTL.NS": ["airtel", "bharti airtel"],
    "ITC.NS":        ["itc"],
    "KOTAKBANK.NS":  ["kotak", "kotak bank"],
    "LT.NS":         ["larsen", "l&t", "larsen & toubro"],
    "HCLTECH.NS":    ["hcl tech", "hcltech"],
    "AXISBANK.NS":   ["axis bank", "axisbank"],
    "ASIANPAINT.NS": ["asian paint", "asianpaint"],
    "MARUTI.NS":     ["maruti", "maruti suzuki"],
    "SUNPHARMA.NS":  ["sun pharma", "sunpharma"],
    "TITAN.NS":      ["titan"],
    "BAJFINANCE.NS": ["bajaj finance", "bajfinance"],
    "WIPRO.NS":      ["wipro"],
    "HINDUNILVR.NS": ["hindustan unilever", "hul"],
    "ULTRACEMCO.NS": ["ultratech cement", "ultratech"]
}

# ── Match headline to stock symbol ──────────────────────────────────────
def match_symbol(headline):
    """Find which stock a headline is about"""
    headline_lower = headline.lower()
    for symbol, keywords in STOCK_KEYWORDS.items():
        for keyword in keywords:
            if keyword in headline_lower:
                return symbol
    return "GENERAL"  # market-wide news

# ── Fetch and parse news ────────────────────────────────────────────────
def fetch_news():
    """Fetch headlines from all RSS feeds"""
    all_news = []

    for feed_info in NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries[:10]:  # top 10 from each source
                headline = entry.get("title", "").strip()
                if headline and len(headline) > 20:
                    all_news.append({
                        "headline": headline,
                        "source":   feed_info["name"],
                        "published_at": datetime.now().isoformat()
                    })
            print(f"✅ {feed_info['name']}: {len(feed.entries[:10])} headlines")
        except Exception as e:
            print(f"❌ {feed_info['name']} failed: {e}")

    # Remove duplicates
    seen = set()
    unique_news = []
    for item in all_news:
        if item["headline"] not in seen:
            seen.add(item["headline"])
            unique_news.append(item)

    print(f"\n📰 Total unique headlines: {len(unique_news)}")
    return unique_news

# ── Run FinBERT sentiment analysis ─────────────────────────────────────
def analyze_sentiment(news_items):
    """Score each headline with FinBERT"""
    results = []

    for item in news_items:
        try:
            result    = sentiment_model(item["headline"])[0]
            label     = result["label"]    # positive / negative / neutral
            score     = result["score"]    # confidence 0-1

            # Normalize label
            sentiment_map = {
                "positive": "BULLISH",
                "negative": "BEARISH",
                "neutral":  "NEUTRAL"
            }
            sentiment = sentiment_map.get(label.lower(), "NEUTRAL")

            item["sentiment"]       = sentiment
            item["sentiment_score"] = round(score * 100, 1)
            item["related_symbol"]  = match_symbol(item["headline"])

            results.append(item)

        except Exception as e:
            print(f"❌ Sentiment failed for: {item['headline'][:50]} — {e}")

    return results

# ── Save to Supabase ────────────────────────────────────────────────────
def save_news(news_items):
    """Save analyzed news to database"""
    saved = 0
    for item in news_items:
        try:
            supabase.table("news").insert({
                "headline":        item["headline"],
                "source":          item["source"],
                "sentiment":       item.get("sentiment", "NEUTRAL"),
                "sentiment_score": item.get("sentiment_score", 0),
                "related_symbol":  item.get("related_symbol", "GENERAL"),
                "published_at":    item.get("published_at")
            }).execute()
            saved += 1
        except Exception as e:
            print(f"❌ Save failed: {e}")
    print(f"✅ Saved {saved} news items to database")

# ── Print summary ───────────────────────────────────────────────────────
def print_summary(news_items):
    """Print sentiment summary"""
    bullish = [n for n in news_items if n.get("sentiment") == "BULLISH"]
    bearish = [n for n in news_items if n.get("sentiment") == "BEARISH"]
    neutral = [n for n in news_items if n.get("sentiment") == "NEUTRAL"]

    print(f"\n{'='*60}")
    print(f"SENTIMENT SUMMARY")
    print(f"{'='*60}")
    print(f"🟢 BULLISH: {len(bullish)} headlines")
    print(f"🔴 BEARISH: {len(bearish)} headlines")
    print(f"🟡 NEUTRAL: {len(neutral)} headlines")
    print(f"{'='*60}")

    print("\n🔥 TOP BULLISH NEWS:")
    for n in sorted(bullish, key=lambda x: x["sentiment_score"], reverse=True)[:3]:
        print(f"  [{n['sentiment_score']}%] {n['headline'][:80]}")
        print(f"  Stock: {n['related_symbol']} | Source: {n['source']}")

    print("\n⚠️  TOP BEARISH NEWS:")
    for n in sorted(bearish, key=lambda x: x["sentiment_score"], reverse=True)[:3]:
        print(f"  [{n['sentiment_score']}%] {n['headline'][:80]}")
        print(f"  Stock: {n['related_symbol']} | Source: {n['source']}")

# ── Main ────────────────────────────────────────────────────────────────
def run_news_engine():
    print(f"\n{'='*60}")
    print(f"News Engine started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    news_items = fetch_news()
    if not news_items:
        print("❌ No news fetched")
        return []

    print("\n🤖 Running FinBERT sentiment analysis...")
    analyzed = analyze_sentiment(news_items)
    save_news(analyzed)
    print_summary(analyzed)

    return analyzed

if __name__ == "__main__":
    run_news_engine()