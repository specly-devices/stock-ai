import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

# ── Hardcoded RBI policy dates 2025-2026 ────────────────────────────────
# Update these annually from rbi.org.in
RBI_POLICY_DATES = [
    "2025-04-09", "2025-06-06", "2025-08-08",
    "2025-10-08", "2025-12-05", "2026-02-07",
    "2026-04-09", "2026-06-05", "2026-08-07",
]

# ── NSE quarterly results calendar (major stocks) ────────────────────────
# Results typically announced in these windows every quarter
RESULTS_WINDOWS = [
    # Q1 results (Apr-Jun quarter) — announced Jul-Aug
    {"start": "2025-07-10", "end": "2025-08-15", "quarter": "Q1 FY26"},
    # Q2 results (Jul-Sep quarter) — announced Oct-Nov
    {"start": "2025-10-10", "end": "2025-11-15", "quarter": "Q2 FY26"},
    # Q3 results (Oct-Dec quarter) — announced Jan-Feb
    {"start": "2026-01-10", "end": "2026-02-15", "quarter": "Q3 FY26"},
    # Q4 results (Jan-Mar quarter) — announced Apr-May
    {"start": "2026-04-10", "end": "2026-05-15", "quarter": "Q4 FY26"},
]

# ── Known high-impact dates ──────────────────────────────────────────────
HIGH_IMPACT_EVENTS = [
    {"date": "2026-02-01", "event": "Union Budget 2026-27",        "impact": "EXTREME"},
    {"date": "2025-07-23", "event": "Union Budget 2025-26",        "impact": "EXTREME"},
    {"date": "2026-03-31", "event": "Financial Year End",          "impact": "HIGH"},
    {"date": "2025-03-31", "event": "Financial Year End",          "impact": "HIGH"},
    {"date": "2026-01-01", "event": "New Year — Low Liquidity",    "impact": "MEDIUM"},
    {"date": "2025-08-15", "event": "Independence Day — Market Holiday", "impact": "HOLIDAY"},
    {"date": "2025-10-02", "event": "Gandhi Jayanti — Market Holiday",   "impact": "HOLIDAY"},
    {"date": "2025-10-24", "event": "Diwali Muhurat Trading",      "impact": "HIGH"},
    {"date": "2025-11-05", "event": "Diwali Holiday",              "impact": "HOLIDAY"},
]

# ── Stock-specific results dates (update quarterly) ──────────────────────
STOCK_RESULTS = [
    # Q3 FY26 results (Jan-Feb 2026)
    {"symbol": "TCS.NS",        "date": "2026-01-09",  "event": "Q3 Results"},
    {"symbol": "INFY.NS",       "date": "2026-01-16",  "event": "Q3 Results"},
    {"symbol": "HDFCBANK.NS",   "date": "2026-01-22",  "event": "Q3 Results"},
    {"symbol": "RELIANCE.NS",   "date": "2026-01-17",  "event": "Q3 Results"},
    {"symbol": "ICICIBANK.NS",  "date": "2026-01-25",  "event": "Q3 Results"},
    {"symbol": "WIPRO.NS",      "date": "2026-01-15",  "event": "Q3 Results"},
    {"symbol": "HCLTECH.NS",    "date": "2026-01-13",  "event": "Q3 Results"},
    {"symbol": "SBIN.NS",       "date": "2026-02-05",  "event": "Q3 Results"},
    {"symbol": "AXISBANK.NS",   "date": "2026-01-24",  "event": "Q3 Results"},
    {"symbol": "KOTAKBANK.NS",  "date": "2026-02-01",  "event": "Q3 Results"},
    {"symbol": "LT.NS",         "date": "2026-01-28",  "event": "Q3 Results"},
    {"symbol": "BAJFINANCE.NS", "date": "2026-01-28",  "event": "Q3 Results"},
    {"symbol": "MARUTI.NS",     "date": "2026-01-29",  "event": "Q3 Results"},
    {"symbol": "SUNPHARMA.NS",  "date": "2026-02-06",  "event": "Q3 Results"},
    {"symbol": "TITAN.NS",      "date": "2026-01-17",  "event": "Q3 Results"},
]

# ── Core functions ───────────────────────────────────────────────────────
def get_upcoming_events(days_ahead=7):
    """
    Get all high-impact events in the next N days.
    Returns list of events sorted by date.
    """
    today    = datetime.now().date()
    end_date = today + timedelta(days=days_ahead)
    events   = []

    # RBI policy dates
    for date_str in RBI_POLICY_DATES:
        event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        if today <= event_date <= end_date:
            events.append({
                "date":   event_date,
                "event":  "RBI Monetary Policy Decision",
                "impact": "EXTREME",
                "symbol": "MARKET",
                "days_away": (event_date - today).days
            })

    # High impact events
    for e in HIGH_IMPACT_EVENTS:
        event_date = datetime.strptime(e["date"], "%Y-%m-%d").date()
        if today <= event_date <= end_date:
            events.append({
                "date":     event_date,
                "event":    e["event"],
                "impact":   e["impact"],
                "symbol":   "MARKET",
                "days_away": (event_date - today).days
            })

    # Stock results
    for r in STOCK_RESULTS:
        event_date = datetime.strptime(r["date"], "%Y-%m-%d").date()
        if today <= event_date <= end_date:
            events.append({
                "date":     event_date,
                "event":    f"{r['symbol'].replace('.NS','')} {r['event']}",
                "impact":   "HIGH",
                "symbol":   r["symbol"],
                "days_away": (event_date - today).days
            })

    # Results windows
    for w in RESULTS_WINDOWS:
        start = datetime.strptime(w["start"], "%Y-%m-%d").date()
        end   = datetime.strptime(w["end"],   "%Y-%m-%d").date()
        if start <= end_date and end >= today:
            events.append({
                "date":     start,
                "event":    f"Quarterly Results Season — {w['quarter']}",
                "impact":   "MEDIUM",
                "symbol":   "MARKET",
                "days_away": max(0, (start - today).days)
            })

    events.sort(key=lambda x: x["date"])
    return events

def should_avoid_trade(symbol, days_buffer=2):
    """
    Check if a trade should be avoided for a symbol
    due to upcoming high-impact events.

    Returns:
        avoid: True/False
        reason: explanation string
        events: list of nearby events
    """
    today    = datetime.now().date()
    end_date = today + timedelta(days=days_buffer)
    warnings = []

    # Check RBI dates
    for date_str in RBI_POLICY_DATES:
        event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        days_away  = (event_date - today).days
        if -1 <= days_away <= days_buffer:
            warnings.append({
                "event":     "RBI Monetary Policy Decision",
                "date":      event_date,
                "days_away": days_away,
                "impact":    "EXTREME"
            })

    # Check high impact events
    for e in HIGH_IMPACT_EVENTS:
        event_date = datetime.strptime(e["date"], "%Y-%m-%d").date()
        days_away  = (event_date - today).days
        if -1 <= days_away <= days_buffer:
            if e["impact"] in ["EXTREME", "HIGH"]:
                warnings.append({
                    "event":     e["event"],
                    "date":      event_date,
                    "days_away": days_away,
                    "impact":    e["impact"]
                })

    # Check stock-specific results
    for r in STOCK_RESULTS:
        if r["symbol"] == symbol or symbol == "MARKET":
            event_date = datetime.strptime(r["date"], "%Y-%m-%d").date()
            days_away  = (event_date - today).days
            if -1 <= days_away <= days_buffer:
                warnings.append({
                    "event":     f"{r['symbol'].replace('.NS','')} {r['event']}",
                    "date":      event_date,
                    "days_away": days_away,
                    "impact":    "HIGH"
                })

    if warnings:
        reasons = []
        for w in warnings:
            if w["days_away"] == 0:
                timing = "TODAY"
            elif w["days_away"] == 1:
                timing = "TOMORROW"
            elif w["days_away"] < 0:
                timing = "YESTERDAY"
            else:
                timing = f"in {w['days_away']} days"
            reasons.append(
                f"{w['impact']}: {w['event']} {timing}"
            )
        return True, " | ".join(reasons), warnings

    return False, "", []

def get_market_calendar_status():
    """
    Get overall market calendar status for today.
    Returns status and any warnings.
    """
    today    = datetime.now().date()
    upcoming = get_upcoming_events(days_ahead=3)

    if not upcoming:
        return "CLEAR", "No major events in next 3 days"

    extreme = [e for e in upcoming if e["impact"] == "EXTREME"]
    high    = [e for e in upcoming if e["impact"] == "HIGH"]
    holiday = [e for e in upcoming if e["impact"] == "HOLIDAY"]

    if holiday and any(e["days_away"] == 0 for e in holiday):
        return "HOLIDAY", holiday[0]["event"]

    if extreme:
        e = extreme[0]
        return "DANGER", (f"RBI/Budget in {e['days_away']} days "
                          f"— avoid new entries")

    if high:
        e = high[0]
        return "CAUTION", (f"{e['event']} in {e['days_away']} days "
                           f"— reduce position size")

    return "CLEAR", "No major events in next 3 days"

def print_calendar(days_ahead=14):
    """Print upcoming events calendar"""
    events = get_upcoming_events(days_ahead=days_ahead)

    print(f"\n{'='*60}")
    print(f"ECONOMIC CALENDAR — Next {days_ahead} days")
    print(f"Today: {datetime.now().strftime('%d %B %Y')}")
    print(f"{'='*60}")

    if not events:
        print("✅ No major events in this period")
        return

    impact_emoji = {
        "EXTREME": "🚨",
        "HIGH":    "⚠️ ",
        "MEDIUM":  "🟡",
        "HOLIDAY": "🏖️ ",
    }

    for e in events:
        emoji    = impact_emoji.get(e["impact"], "⚪")
        days_str = (f"TODAY" if e["days_away"] == 0
                    else f"in {e['days_away']} days")
        print(f"{emoji} {e['date'].strftime('%d %b')}  "
              f"({days_str:<12})  "
              f"{e['event']}")

    print(f"{'='*60}")
    status, msg = get_market_calendar_status()
    status_emoji = {
        "CLEAR":   "✅",
        "CAUTION": "⚠️ ",
        "DANGER":  "🚨",
        "HOLIDAY": "🏖️ "
    }.get(status, "⚪")
    print(f"\n{status_emoji} Status: {status} — {msg}")

if __name__ == "__main__":
    print_calendar(days_ahead=30)

    print("\n\nTesting trade filter:")
    for sym in ["TCS.NS", "RELIANCE.NS", "INFY.NS", "SBIN.NS"]:
        avoid, reason, events = should_avoid_trade(sym, days_buffer=3)
        print(f"  {'🚫' if avoid else '✅'} {sym:<20} "
              f"{'AVOID — ' + reason if avoid else 'CLEAR'}")