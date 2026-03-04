import feedparser
import requests
import os
import re
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

analyzer = SentimentIntensityAnalyzer()
print("✅ Sentiment analyzer loaded")

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
    # Mid & Small Cap additions
    "TATAMOTORS.NS":  ["tata motors", "tatamotors"],
    "ADANIENT.NS":    ["adani enterprises", "adani ent"],
    "ADANIPORTS.NS":  ["adani ports", "adaniports"],
    "JSWSTEEL.NS":    ["jsw steel", "jswsteel"],
    "TATASTEEL.NS":   ["tata steel", "tatasteel"],
    "HINDALCO.NS":    ["hindalco"],
    "VEDL.NS":        ["vedanta", "vedl"],
    "DRREDDY.NS":     ["dr reddy", "drreddy"],
    "CIPLA.NS":       ["cipla"],
    "BAJAJ-AUTO.NS":  ["bajaj auto"],
    "HEROMOTOCO.NS":  ["hero moto", "hero motocorp"],
    "EICHERMOT.NS":   ["eicher", "royal enfield"],
    "TATAPOWER.NS":   ["tata power"],
    "DLF.NS":         ["dlf"],
    "PERSISTENT.NS":  ["persistent systems"],
    "COFORGE.NS":     ["coforge"],
    "KPITTECH.NS":    ["kpit tech", "kpit"],
    "TATAELXSI.NS":   ["tata elxsi"],
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

def analyze_sentiment(news_items):
    """Score each headline using VADER + TextBlob (lightweight, no GPU needed)"""
    results = []

    for item in news_items:
        try:
            headline = item["headline"]

            # VADER score (-1 to +1)
            vader_scores = analyzer.polarity_scores(headline)
            vader_compound = vader_scores["compound"]

            # TextBlob score (-1 to +1)
            blob_score = TextBlob(headline).sentiment.polarity

            # Average both
            combined = (vader_compound + blob_score) / 2

            # Finance-specific keyword boosts
            bullish_words = [
                "surge", "rally", "gain", "profit", "growth", "beat",
                "record", "strong", "upgrade", "buy", "outperform",
                "expansion", "positive", "rises", "jumps", "soars"
            ]
            bearish_words = [
                "fall", "drop", "loss", "crash", "decline", "miss",
                "weak", "downgrade", "sell", "underperform", "cut",
                "negative", "falls", "tumbles", "plunges", "concern"
            ]

            headline_lower = headline.lower()
            for word in bullish_words:
                if word in headline_lower:
                    combined += 0.1
            for word in bearish_words:
                if word in headline_lower:
                    combined -= 0.1

            combined = max(-1, min(1, combined))  # clamp to -1 to +1

            # Convert to label
            if combined >= 0.05:
                sentiment = "BULLISH"
            elif combined <= -0.05:
                sentiment = "BEARISH"
            else:
                sentiment = "NEUTRAL"

            score = round(abs(combined) * 100, 1)

            item["sentiment"]       = sentiment
            item["sentiment_score"] = score
            item["related_symbol"]  = match_symbol(item["headline"])
            results.append(item)

        except Exception as e:
            print(f"❌ Sentiment failed: {e}")

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