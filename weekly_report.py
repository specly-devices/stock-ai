import os
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client
from alerts import send_email

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# ── Fetch data from Supabase ─────────────────────────────────────────────
def get_weekly_signals():
    """Get all signals from the past 7 days"""
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    try:
        result = supabase.table("signals").select("*").gte(
            "created_at", week_ago
        ).order("created_at", desc=True).execute()
        return pd.DataFrame(result.data) if result.data else pd.DataFrame()
    except:
        return pd.DataFrame()

def get_weekly_news():
    """Get sentiment summary from past 7 days"""
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    try:
        result = supabase.table("news").select("*").gte(
            "created_at", week_ago
        ).execute()
        return pd.DataFrame(result.data) if result.data else pd.DataFrame()
    except:
        return pd.DataFrame()

def get_portfolio():
    """Get all portfolio holdings"""
    try:
        result = supabase.table("stocks").select("*").eq(
            "in_portfolio", True
        ).execute()
        return result.data if result.data else []
    except:
        return []

# ── Portfolio performance ────────────────────────────────────────────────
def calculate_portfolio_performance(holdings):
    """Calculate current P&L for all holdings"""
    rows = []
    total_invested = 0
    total_current  = 0

    for holding in holdings:
        try:
            symbol    = holding["symbol"]
            buy_price = holding.get("buy_price", 0)
            quantity  = holding.get("quantity", 0)
            if not buy_price or not quantity:
                continue

            ticker        = yf.Ticker(symbol)
            hist          = ticker.history(period="5d")
            current_price = float(hist["Close"].iloc[-1])
            week_ago_price = float(hist["Close"].iloc[0]) if len(hist) > 1 else current_price

            pnl_total  = (current_price - buy_price) * quantity
            pnl_pct    = ((current_price - buy_price) / buy_price) * 100
            week_chg   = ((current_price - week_ago_price) / week_ago_price) * 100

            total_invested += buy_price * quantity
            total_current  += current_price * quantity

            rows.append({
                "symbol":        symbol.replace(".NS","").replace(".BO",""),
                "buy_price":     buy_price,
                "current_price": round(current_price, 2),
                "quantity":      quantity,
                "pnl_rs":        round(pnl_total, 2),
                "pnl_pct":       round(pnl_pct, 2),
                "week_change":   round(week_chg, 2)
            })
        except Exception as e:
            print(f"❌ {holding['symbol']}: {e}")

    return rows, total_invested, total_current

# ── Signal accuracy tracker ──────────────────────────────────────────────
def analyze_signal_accuracy(signals_df):
    """
    Check how many BUY signals from earlier this week actually went up.
    Compares signal price vs current price.
    """
    if signals_df.empty:
        return []

    results = []
    buy_signals = signals_df[
        signals_df["signal"].str.startswith("BUY")
    ].drop_duplicates(subset="symbol")

    for _, row in buy_signals.iterrows():
        try:
            ticker        = yf.Ticker(row["symbol"])
            hist          = ticker.history(period="5d")
            current_price = float(hist["Close"].iloc[-1])
            signal_price  = float(row["price"])
            change_pct    = ((current_price - signal_price) / signal_price) * 100
            correct       = change_pct > 0

            results.append({
                "symbol":       row["symbol"].replace(".NS",""),
                "signal_price": signal_price,
                "current":      round(current_price, 2),
                "change_pct":   round(change_pct, 2),
                "correct":      correct
            })
        except:
            pass

    return results

# ── Build HTML email ─────────────────────────────────────────────────────
def build_report_html(portfolio_rows, total_invested, total_current,
                      signals_df, news_df, accuracy_results):
    """Build a professional HTML email report"""

    total_pnl     = total_current - total_invested
    total_pnl_pct = ((total_pnl / total_invested) * 100) if total_invested else 0
    pnl_color     = "#22c55e" if total_pnl >= 0 else "#ef4444"

    # Signal stats
    buy_count  = sell_count = hold_count = 0
    if not signals_df.empty:
        latest = signals_df.drop_duplicates(subset="symbol")
        buy_count  = len(latest[latest["signal"].str.startswith("BUY")])
        sell_count = len(latest[latest["signal"].str.startswith("SELL")])
        hold_count = len(latest[latest["signal"].str.startswith("HOLD")])
        avg_conf   = round(latest["confidence"].mean(), 1)
    else:
        avg_conf = 0

    # News sentiment
    bull_count = bear_count = neut_count = 0
    if not news_df.empty:
        bull_count = len(news_df[news_df["sentiment"] == "BULLISH"])
        bear_count = len(news_df[news_df["sentiment"] == "BEARISH"])
        neut_count = len(news_df[news_df["sentiment"] == "NEUTRAL"])

    # Accuracy stats
    correct   = sum(1 for r in accuracy_results if r["correct"])
    total_sig = len(accuracy_results)
    acc_pct   = round((correct / total_sig * 100) if total_sig else 0, 1)

    # Portfolio rows HTML
    portfolio_html = ""
    for row in portfolio_rows:
        color = "#22c55e" if row["pnl_pct"] >= 0 else "#ef4444"
        wk_color = "#22c55e" if row["week_change"] >= 0 else "#ef4444"
        portfolio_html += f"""
        <tr>
            <td style="padding:10px; border-bottom:1px solid #1e2d45;
                       font-weight:600;">{row['symbol']}</td>
            <td style="padding:10px; border-bottom:1px solid #1e2d45;">
                ₹{row['buy_price']}</td>
            <td style="padding:10px; border-bottom:1px solid #1e2d45;">
                ₹{row['current_price']}</td>
            <td style="padding:10px; border-bottom:1px solid #1e2d45;">
                {row['quantity']}</td>
            <td style="padding:10px; border-bottom:1px solid #1e2d45;
                       color:{color}; font-weight:700;">
                ₹{row['pnl_rs']:+,.0f}</td>
            <td style="padding:10px; border-bottom:1px solid #1e2d45;
                       color:{color}; font-weight:700;">
                {row['pnl_pct']:+.2f}%</td>
            <td style="padding:10px; border-bottom:1px solid #1e2d45;
                       color:{wk_color};">
                {row['week_change']:+.2f}%</td>
        </tr>"""

    # Accuracy rows HTML
    accuracy_html = ""
    for row in accuracy_results[:10]:
        color = "#22c55e" if row["correct"] else "#ef4444"
        tick  = "✅" if row["correct"] else "❌"
        accuracy_html += f"""
        <tr>
            <td style="padding:8px; border-bottom:1px solid #1e2d45;">{row['symbol']}</td>
            <td style="padding:8px; border-bottom:1px solid #1e2d45;">₹{row['signal_price']}</td>
            <td style="padding:8px; border-bottom:1px solid #1e2d45;">₹{row['current']}</td>
            <td style="padding:8px; border-bottom:1px solid #1e2d45;
                       color:{color}; font-weight:700;">{row['change_pct']:+.2f}% {tick}</td>
        </tr>"""

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="background:#080c14; color:#e2e8f0; font-family: Arial, sans-serif;
             margin:0; padding:20px;">

  <div style="max-width:700px; margin:0 auto;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#0d1421,#1a2744);
                border:1px solid #1e2d45; border-radius:12px;
                padding:30px; margin-bottom:20px; text-align:center;">
      <div style="font-size:28px; font-weight:800; color:#3b82f6;
                  letter-spacing:-1px;">📈 StockAI</div>
      <div style="font-size:14px; color:#64748b; margin-top:4px;">
        Weekly Performance Report
      </div>
      <div style="font-size:13px; color:#475569; margin-top:8px;">
        {datetime.now().strftime('%d %B %Y')}
      </div>
    </div>

    <!-- Portfolio Summary -->
    <div style="background:#0d1421; border:1px solid #1e2d45;
                border-radius:12px; padding:24px; margin-bottom:20px;">
      <div style="font-size:11px; letter-spacing:3px; color:#3b82f6;
                  text-transform:uppercase; margin-bottom:16px;">
        Portfolio Summary
      </div>
      <div style="display:flex; gap:16px; flex-wrap:wrap;">
        <div style="flex:1; background:#111827; border-radius:8px;
                    padding:16px; text-align:center; min-width:120px;">
          <div style="font-size:11px; color:#64748b; margin-bottom:4px;">
            INVESTED</div>
          <div style="font-size:20px; font-weight:700;">
            ₹{total_invested:,.0f}</div>
        </div>
        <div style="flex:1; background:#111827; border-radius:8px;
                    padding:16px; text-align:center; min-width:120px;">
          <div style="font-size:11px; color:#64748b; margin-bottom:4px;">
            CURRENT</div>
          <div style="font-size:20px; font-weight:700;">
            ₹{total_current:,.0f}</div>
        </div>
        <div style="flex:1; background:#111827; border-radius:8px;
                    padding:16px; text-align:center; min-width:120px;">
          <div style="font-size:11px; color:#64748b; margin-bottom:4px;">
            TOTAL P&L</div>
          <div style="font-size:20px; font-weight:700; color:{pnl_color};">
            ₹{total_pnl:+,.0f}</div>
          <div style="font-size:13px; color:{pnl_color};">
            {total_pnl_pct:+.2f}%</div>
        </div>
      </div>
    </div>

    <!-- Holdings Table -->
    {'<div style="background:#0d1421; border:1px solid #1e2d45; border-radius:12px; padding:24px; margin-bottom:20px;"><div style="font-size:11px; letter-spacing:3px; color:#3b82f6; text-transform:uppercase; margin-bottom:16px;">Holdings</div><table style="width:100%; border-collapse:collapse; font-size:13px;"><tr style="color:#64748b; font-size:11px; text-transform:uppercase;"><th style="padding:10px; text-align:left;">Stock</th><th style="padding:10px; text-align:left;">Buy</th><th style="padding:10px; text-align:left;">Current</th><th style="padding:10px; text-align:left;">Qty</th><th style="padding:10px; text-align:left;">P&L ₹</th><th style="padding:10px; text-align:left;">P&L %</th><th style="padding:10px; text-align:left;">Week</th></tr>' + portfolio_html + '</table></div>' if portfolio_rows else ''}

    <!-- Signal Stats -->
    <div style="background:#0d1421; border:1px solid #1e2d45;
                border-radius:12px; padding:24px; margin-bottom:20px;">
      <div style="font-size:11px; letter-spacing:3px; color:#3b82f6;
                  text-transform:uppercase; margin-bottom:16px;">
        Weekly Signal Summary
      </div>
      <div style="display:flex; gap:12px; flex-wrap:wrap;">
        <div style="flex:1; background:#064e3b; border-radius:8px;
                    padding:12px; text-align:center; min-width:100px;">
          <div style="font-size:22px; font-weight:700;
                      color:#34d399;">{buy_count}</div>
          <div style="font-size:11px; color:#6ee7b7;">BUY</div>
        </div>
        <div style="flex:1; background:#450a0a; border-radius:8px;
                    padding:12px; text-align:center; min-width:100px;">
          <div style="font-size:22px; font-weight:700;
                      color:#f87171;">{sell_count}</div>
          <div style="font-size:11px; color:#fca5a5;">SELL</div>
        </div>
        <div style="flex:1; background:#1c1a05; border-radius:8px;
                    padding:12px; text-align:center; min-width:100px;">
          <div style="font-size:22px; font-weight:700;
                      color:#fbbf24;">{hold_count}</div>
          <div style="font-size:11px; color:#fde68a;">HOLD</div>
        </div>
        <div style="flex:1; background:#111827; border-radius:8px;
                    padding:12px; text-align:center; min-width:100px;">
          <div style="font-size:22px; font-weight:700;
                      color:#60a5fa;">{avg_conf}%</div>
          <div style="font-size:11px; color:#93c5fd;">AVG CONF</div>
        </div>
      </div>
    </div>

    <!-- Signal Accuracy -->
    {'<div style="background:#0d1421; border:1px solid #1e2d45; border-radius:12px; padding:24px; margin-bottom:20px;"><div style="font-size:11px; letter-spacing:3px; color:#3b82f6; text-transform:uppercase; margin-bottom:8px;">BUY Signal Accuracy This Week</div><div style="font-size:24px; font-weight:800; color:' + ("#22c55e" if acc_pct >= 50 else "#ef4444") + '; margin-bottom:16px;">' + str(acc_pct) + '% (' + str(correct) + '/' + str(total_sig) + ' correct)</div><table style="width:100%; border-collapse:collapse; font-size:13px;"><tr style="color:#64748b; font-size:11px;"><th style="padding:8px; text-align:left;">Stock</th><th style="padding:8px; text-align:left;">Signal Price</th><th style="padding:8px; text-align:left;">Current</th><th style="padding:8px; text-align:left;">Result</th></tr>' + accuracy_html + '</table></div>' if accuracy_results else ''}

    <!-- News Sentiment -->
    <div style="background:#0d1421; border:1px solid #1e2d45;
                border-radius:12px; padding:24px; margin-bottom:20px;">
      <div style="font-size:11px; letter-spacing:3px; color:#3b82f6;
                  text-transform:uppercase; margin-bottom:16px;">
        Weekly News Sentiment
      </div>
      <div style="display:flex; gap:20px;">
        <div style="flex:1; text-align:center;">
          <div style="font-size:22px; color:#34d399; font-weight:700;">
            {bull_count}</div>
          <div style="font-size:11px; color:#64748b;">BULLISH</div>
        </div>
        <div style="flex:1; text-align:center;">
          <div style="font-size:22px; color:#f87171; font-weight:700;">
            {bear_count}</div>
          <div style="font-size:11px; color:#64748b;">BEARISH</div>
        </div>
        <div style="flex:1; text-align:center;">
          <div style="font-size:22px; color:#fbbf24; font-weight:700;">
            {neut_count}</div>
          <div style="font-size:11px; color:#64748b;">NEUTRAL</div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div style="text-align:center; font-size:11px; color:#475569;
                padding:20px 0;">
      StockAI — Indian Market Intelligence<br>
      This report is for informational purposes only.<br>
      Not financial advice. Always do your own research.
    </div>

  </div>
</body>
</html>"""

    return html

# ── Main ─────────────────────────────────────────────────────────────────
def run_weekly_report():
    print(f"\n{'='*60}")
    print(f"Weekly Report: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    print("📊 Fetching signals...")
    signals_df = get_weekly_signals()

    print("📰 Fetching news...")
    news_df = get_weekly_news()

    print("💼 Fetching portfolio...")
    holdings = get_portfolio()

    print("📈 Calculating performance...")
    portfolio_rows, total_invested, total_current = calculate_portfolio_performance(
        holdings
    )

    print("🎯 Analyzing signal accuracy...")
    accuracy_results = analyze_signal_accuracy(signals_df)

    print("📧 Building report...")
    html = build_report_html(
        portfolio_rows, total_invested, total_current,
        signals_df, news_df, accuracy_results
    )

    subject = (f"📈 StockAI Weekly Report — "
               f"{datetime.now().strftime('%d %b %Y')}")
    send_email(subject, html)
    print("✅ Weekly report sent to your email")

if __name__ == "__main__":
    run_weekly_report()