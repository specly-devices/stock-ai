import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from data_pipeline import run_pipeline, fetch_stock_data, calculate_indicators, generate_signal
from news_engine import run_news_engine
from alerts import send_alert
from risk_manager import run_risk_check
from stock_filter import get_stock_tier

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# ── Weightings ──────────────────────────────────────────────────────────
# How much each layer contributes to final decision
WEIGHT_TECHNICAL  = 0.50  # 50% — technical indicators
WEIGHT_SENTIMENT  = 0.25  # 25% — news sentiment
WEIGHT_ML         = 0.25  # 25% — XGBoost ML model

# Minimum confidence to send an alert (avoid weak signals)
MIN_CONFIDENCE_ALERT = 55.0

# ── Get sentiment score for a symbol ───────────────────────────────────
def get_sentiment_score(symbol, news_items):
    """
    Calculate net sentiment score for a specific stock
    Returns value between -100 (very bearish) and +100 (very bullish)
    """
    # Get news for this stock + general market news
    relevant = [
        n for n in news_items
        if n.get("related_symbol") == symbol or n.get("related_symbol") == "GENERAL"
    ]

    if not relevant:
        return 0  # neutral if no news

    score = 0
    for item in relevant:
        s = item.get("sentiment_score", 50) / 100
        if item["sentiment"] == "BULLISH":
            score += s
        elif item["sentiment"] == "BEARISH":
            score -= s
        # NEUTRAL adds 0

    # Normalize to -100 to +100
    max_possible = len(relevant)
    normalized   = (score / max_possible) * 100 if max_possible > 0 else 0
    return round(normalized, 1)

# ── Combine technical + sentiment ──────────────────────────────────────
def combine_signals(technical_signal, sentiment_score):
    """Merge technical + sentiment + ML into final signal"""
    from ml_model import predict_stock

    tech_direction = {
        "BUY": 1, "SELL": -1, "HOLD": 0
    }.get(technical_signal["signal"], 0)

    tech_score = tech_direction * technical_signal["confidence"]

    # ML prediction
    ml_prediction, ml_prob = predict_stock(technical_signal["symbol"])
    ml_score = (ml_prob - 50) * 2  # convert 0-100% to -100 to +100

    # Weighted combination
    combined_score = (
        (tech_score    * WEIGHT_TECHNICAL) +
        (sentiment_score * WEIGHT_SENTIMENT) +
        (ml_score      * WEIGHT_ML)
    )

    if combined_score >= 25:
        final_signal = "BUY"
    elif combined_score <= -25:
        final_signal = "SELL"
    else:
        final_signal = "HOLD"

    combined_confidence = round(min(abs(combined_score), 95.0), 1)

    if sentiment_score > 10:
        sentiment_label = f"Sentiment BULLISH ({sentiment_score:+.1f})"
    elif sentiment_score < -10:
        sentiment_label = f"Sentiment BEARISH ({sentiment_score:+.1f})"
    else:
        sentiment_label = "Sentiment NEUTRAL"

    ml_label = f"ML {ml_prediction} ({ml_prob}%)" if ml_prediction else "ML N/A"
    full_reason = f"{technical_signal['reason']} | {sentiment_label} | {ml_label}"

    # Apply backtest-based tier adjustment
    tier, multiplier = get_stock_tier(technical_signal["symbol"])
    combined_confidence = round(min(combined_confidence * multiplier, 95.0), 1)

    if tier == "AVOID" and final_signal == "BUY":
        final_signal = "HOLD"
        full_reason  = f"[BACKTESTED: AVOID] {full_reason}"
    elif tier == "HIGH":
        full_reason  = f"[BACKTESTED: HIGH CONFIDENCE] {full_reason}"

    return {
        "symbol":          technical_signal["symbol"],
        "signal":          final_signal,
        "confidence":      combined_confidence,
        "price":           technical_signal["price"],
        "rsi":             technical_signal["rsi"],
        "macd":            technical_signal["macd"],
        "tech_score":      round(tech_score, 1),
        "sentiment_score": sentiment_score,
        "ml_score":        round(ml_score, 1),
        "combined_score":  round(combined_score, 1),
        "reason":          full_reason
    }
# ── Portfolio check ─────────────────────────────────────────────────────
def check_portfolio(symbol, signal, price):
    """
    If stock is in portfolio — check whether to HOLD or SELL
    Returns portfolio context string
    """
    try:
        result = supabase.table("stocks").select("*").eq(
            "symbol", symbol
        ).eq("in_portfolio", True).execute()

        if not result.data:
            return None  # not in portfolio

        holding   = result.data[0]
        buy_price = holding.get("buy_price", 0)
        quantity  = holding.get("quantity", 0)

        if not buy_price:
            return None

        pnl_pct = ((price - buy_price) / buy_price) * 100
        pnl_rs  = (price - buy_price) * quantity

        portfolio_info = (
            f"PORTFOLIO | Bought @ ₹{buy_price} | "
            f"Qty: {quantity} | "
            f"P&L: ₹{pnl_rs:+.0f} ({pnl_pct:+.1f}%)"
        )

        # Override signal if in portfolio
        if signal == "SELL" and pnl_pct > 0:
            action = "SELL (Take Profit)"
        elif signal == "SELL" and pnl_pct < -5:
            action = "SELL (Stop Loss)"
        elif signal == "BUY":
            action = "HOLD (Already owned)"
        else:
            action = "HOLD"

        return {"info": portfolio_info, "action": action}

    except Exception as e:
        print(f"❌ Portfolio check failed: {e}")
        return None

# ── Save final signal ───────────────────────────────────────────────────
def save_final_signal(signal_data):
    """Save combined signal to database"""
    try:
        supabase.table("signals").insert({
            "symbol":     signal_data["symbol"],
            "signal":     signal_data["signal"],
            "confidence": signal_data["confidence"],
            "price":      signal_data["price"],
            "rsi":        signal_data["rsi"],
            "macd":       signal_data["macd"],
            "reason":     signal_data["reason"]
        }).execute()
    except Exception as e:
        print(f"❌ Signal save failed: {e}")

# ── Main combiner ───────────────────────────────────────────────────────
def run_combiner():
    print(f"\n{'='*60}")
    print(f"Signal Combiner started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    # Run risk check on portfolio
    print("\n🛡️  Running portfolio risk check...")
    run_risk_check()

    # Step 1: Run technical analysis
    print("📊 Step 1: Running technical analysis...")
    technical_signals = run_pipeline()

    # Step 2: Run news sentiment
    print("\n📰 Step 2: Running news sentiment engine...")
    news_items = run_news_engine()

    # Step 3: Combine and alert
    print(f"\n🧠 Step 3: Combining signals...")
    print(f"{'='*60}")

    final_signals = []
    alerts_sent   = 0

    for tech_signal in technical_signals:
        symbol = tech_signal["symbol"]

        # Get sentiment for this stock
        sentiment_score = get_sentiment_score(symbol, news_items)

        # Combine
        final = combine_signals(tech_signal, sentiment_score)

        # Check portfolio
        portfolio = check_portfolio(symbol, final["signal"], final["price"])
        if portfolio:
            final["reason"]  = f"{final['reason']} | {portfolio['info']}"
            final["signal"]  = portfolio["action"]

        # Save to DB
        save_final_signal(final)
        final_signals.append(final)

        # Print result
        emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}.get(
            final["signal"].split()[0], "⚪"
        )
        print(
            f"{emoji} {symbol:<20} {final['signal']:<25} "
            f"₹{final['price']:<10} Conf:{final['confidence']}%"
        )

        # Send alert only for strong BUY or SELL signals
        if (
            final["signal"].startswith("BUY") or final["signal"].startswith("SELL")
        ) and final["confidence"] >= MIN_CONFIDENCE_ALERT:
            send_alert(
                symbol=symbol,
                signal=final["signal"],
                price=final["price"],
                confidence=final["confidence"],
                reason=final["reason"]
            )
            alerts_sent += 1

    # ── Summary ──
    buys  = [s for s in final_signals if s["signal"].startswith("BUY")]
    sells = [s for s in final_signals if s["signal"].startswith("SELL")]
    holds = [s for s in final_signals if s["signal"].startswith("HOLD")]

    print(f"\n{'='*60}")
    print(f"FINAL SUMMARY — {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    print(f"🟢 BUY signals:  {len(buys)}")
    print(f"🔴 SELL signals: {len(sells)}")
    print(f"🟡 HOLD signals: {len(holds)}")
    print(f"🔔 Alerts sent:  {alerts_sent}")
    print(f"{'='*60}")

    return final_signals

if __name__ == "__main__":
    run_combiner()
    