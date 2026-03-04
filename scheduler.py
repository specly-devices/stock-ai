import schedule
import time
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def is_market_hours():
    """
    Returns True during NSE market hours + 30 min before/after
    Mon-Fri, 9:00 AM to 4:00 PM IST
    """
    now     = datetime.now()
    weekday = now.weekday()  # 0=Mon, 6=Sun
    hour    = now.hour
    minute  = now.minute

    if weekday >= 5:  # Saturday or Sunday
        return False

    # 8:30 AM to 4:00 PM IST
    after_start  = (hour > 8) or (hour == 8 and minute >= 30)
    before_close = (hour < 16)

    return after_start and before_close

def run_full_engine():
    """Run complete pipeline — technical + news + alerts"""
    print(f"\n{'='*60}")
    print(f"🔄 Scheduler triggered: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if not is_market_hours():
        print("⏸️  Outside market hours — skipping full engine")
        print("   (News scan still runs every 30 min)")
        return

    print(f"{'='*60}")
    try:
        from signal_combiner import run_combiner
        run_combiner()
    except Exception as e:
        print(f"❌ Engine error: {e}")

def run_news_only():
    """Run news engine even outside market hours"""
    print(f"\n📰 News scan: {datetime.now().strftime('%H:%M:%S')}")
    try:
        from news_engine import run_news_engine
        run_news_engine()
    except Exception as e:
        print(f"❌ News error: {e}")

def run_morning_scan():
    """Full scan at 9:00 AM before market opens"""
    print(f"\n🌅 Morning scan starting...")
    try:
        from signal_combiner import run_combiner
        run_combiner()
    except Exception as e:
        print(f"❌ Morning scan error: {e}")

def run_closing_scan():
    """Full scan at 3:30 PM market close"""
    print(f"\n🔔 Closing scan starting...")
    try:
        from signal_combiner import run_combiner
        run_combiner()
    except Exception as e:
        print(f"❌ Closing scan error: {e}")

# ── Schedule jobs ────────────────────────────────────────────────────────

# Full engine every 5 minutes (market hours only — checked inside function)
schedule.every(5).minutes.do(run_full_engine)

# News scan every 30 minutes (runs 24/7 — catches after-hours news)
schedule.every(30).minutes.do(run_news_only)

# Special scans at fixed times
schedule.every().day.at("09:00").do(run_morning_scan)
schedule.every().day.at("15:30").do(run_closing_scan)

# ── Start ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════════╗
║           StockAI Scheduler Started                  ║
║  Full engine : Every 5 min (market hours only)       ║
║  News scan   : Every 30 min (24/7)                   ║
║  Morning scan: 9:00 AM daily                         ║
║  Closing scan: 3:30 PM daily                         ║
╚══════════════════════════════════════════════════════╝
    """)

    # Run once immediately on start
    print("▶️  Running initial scan on startup...")
    run_full_engine()

    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(30)  # check every 30 seconds
        