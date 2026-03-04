import os
import yfinance as yf
from dotenv import load_dotenv
from supabase import create_client
from alerts import send_alert
from datetime import datetime

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# ── Risk settings ────────────────────────────────────────────────────────
STOP_LOSS_PCT    = 5.0   # Exit if stock falls 5% from buy price
TARGET_1_PCT     = 8.0   # First target — book 50% profit
TARGET_2_PCT     = 15.0  # Second target — book remaining
TRAILING_STOP    = 3.0   # Trailing stop — exit if falls 3% from peak
MAX_RISK_PER_TRADE = 2.0 # Never risk more than 2% of total portfolio

# ── Position sizing ──────────────────────────────────────────────────────
def calculate_position_size(portfolio_value, stock_price, stop_loss_price):
    """
    Kelly-inspired position sizing.
    Risk only MAX_RISK_PER_TRADE% of portfolio per trade.
    """
    risk_amount    = portfolio_value * (MAX_RISK_PER_TRADE / 100)
    risk_per_share = stock_price - stop_loss_price

    if risk_per_share <= 0:
        return 0

    quantity       = int(risk_amount / risk_per_share)
    position_value = quantity * stock_price
    position_pct   = (position_value / portfolio_value) * 100

    return {
        "quantity":       quantity,
        "position_value": round(position_value, 2),
        "position_pct":   round(position_pct, 2),
        "risk_amount":    round(risk_amount, 2),
        "stop_loss":      round(stop_loss_price, 2)
    }

# ── Check stop loss and targets ──────────────────────────────────────────
def check_risk_levels(holding, current_price):
    """
    Check if stop loss or target has been hit for a holding.
    Returns action: STOP_LOSS / TARGET_1 / TARGET_2 / TRAILING_STOP / HOLD
    """
    buy_price  = holding.get("buy_price", 0)
    if not buy_price:
        return "HOLD", ""

    pnl_pct    = ((current_price - buy_price) / buy_price) * 100
    peak_price = holding.get("peak_price", buy_price)

    # Update peak price
    if current_price > peak_price:
        peak_price = current_price
        try:
            supabase.table("stocks").update(
                {"peak_price": current_price}
            ).eq("symbol", holding["symbol"]).execute()
        except:
            pass

    # Trailing stop from peak
    trailing_drop = ((peak_price - current_price) / peak_price) * 100

    # Check levels in priority order
    if pnl_pct <= -STOP_LOSS_PCT:
        reason = (f"Stop loss hit — down {pnl_pct:.1f}% from buy "
                  f"₹{buy_price} → ₹{current_price:.1f}")
        return "STOP_LOSS", reason

    if pnl_pct >= TARGET_2_PCT:
        reason = (f"Target 2 hit — up {pnl_pct:.1f}% from buy "
                  f"₹{buy_price} → ₹{current_price:.1f}")
        return "TARGET_2", reason

    if pnl_pct >= TARGET_1_PCT:
        reason = (f"Target 1 hit — up {pnl_pct:.1f}% from buy "
                  f"₹{buy_price} → ₹{current_price:.1f}")
        return "TARGET_1", reason

    if trailing_drop >= TRAILING_STOP and pnl_pct > 0:
        reason = (f"Trailing stop — fell {trailing_drop:.1f}% from peak "
                  f"₹{peak_price:.1f} → ₹{current_price:.1f}")
        return "TRAILING_STOP", reason

    return "HOLD", f"P&L: {pnl_pct:+.1f}%"

# ── Run risk check on full portfolio ────────────────────────────────────
def run_risk_check():
    """Check all portfolio holdings for risk levels"""
    print(f"\n{'='*60}")
    print(f"Risk Manager: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    try:
        result = supabase.table("stocks").select("*").eq(
            "in_portfolio", True
        ).execute()
        holdings = result.data
    except Exception as e:
        print(f"❌ Failed to load portfolio: {e}")
        return

    if not holdings:
        print("📭 No holdings in portfolio")
        return

    alerts_sent = 0

    for holding in holdings:
        symbol = holding["symbol"]
        try:
            ticker  = yf.Ticker(symbol)
            hist    = ticker.history(period="2d")
            if hist.empty:
                continue

            current_price = round(float(hist["Close"].iloc[-1]), 2)
            action, reason = check_risk_levels(holding, current_price)

            buy_price = holding.get("buy_price", 0)
            quantity  = holding.get("quantity", 0)
            pnl_rs    = (current_price - buy_price) * quantity
            pnl_pct   = ((current_price - buy_price) / buy_price * 100
                         if buy_price else 0)

            emoji = {
                "STOP_LOSS":     "🚨",
                "TARGET_1":      "🎯",
                "TARGET_2":      "🎯🎯",
                "TRAILING_STOP": "⚠️",
                "HOLD":          "✅"
            }.get(action, "⚪")

            print(f"{emoji} {symbol:<20} ₹{current_price:<10} "
                  f"P&L: ₹{pnl_rs:+.0f} ({pnl_pct:+.1f}%) — {action}")

            # Send alert for any action except HOLD
            if action != "HOLD":
                signal = "SELL" if action in [
                    "STOP_LOSS", "TRAILING_STOP"
                ] else "SELL (Partial)"

                send_alert(
                    symbol=symbol,
                    signal=f"{action}: {signal}",
                    price=current_price,
                    confidence=95.0,
                    reason=reason
                )
                alerts_sent += 1

        except Exception as e:
            print(f"❌ {symbol}: {e}")

    print(f"\n✅ Risk check complete — {len(holdings)} holdings, "
          f"{alerts_sent} alerts sent")

# ── Position size calculator ─────────────────────────────────────────────
def suggest_position(symbol, portfolio_value):
    """
    Suggest how many shares to buy based on portfolio size and risk.
    """
    try:
        ticker        = yf.Ticker(symbol)
        hist          = ticker.history(period="5d")
        current_price = float(hist["Close"].iloc[-1])
        stop_loss     = current_price * (1 - STOP_LOSS_PCT / 100)
        sizing        = calculate_position_size(
                            portfolio_value, current_price, stop_loss
                        )

        print(f"\n📊 Position Sizing for {symbol}")
        print(f"   Current price:  ₹{current_price:.2f}")
        print(f"   Stop loss:      ₹{sizing['stop_loss']} (-{STOP_LOSS_PCT}%)")
        print(f"   Target 1:       ₹{current_price * (1 + TARGET_1_PCT/100):.2f} "
              f"(+{TARGET_1_PCT}%)")
        print(f"   Target 2:       ₹{current_price * (1 + TARGET_2_PCT/100):.2f} "
              f"(+{TARGET_2_PCT}%)")
        print(f"   Suggested qty:  {sizing['quantity']} shares")
        print(f"   Position value: ₹{sizing['position_value']:,.0f} "
              f"({sizing['position_pct']}% of portfolio)")
        print(f"   Max risk:       ₹{sizing['risk_amount']:,.0f} "
              f"({MAX_RISK_PER_TRADE}% of portfolio)")

        return sizing

    except Exception as e:
        print(f"❌ Position sizing failed: {e}")
        return None

if __name__ == "__main__":
    # Test risk check
    run_risk_check()

    # Test position sizing — change portfolio value to your actual value
    print("\n" + "="*60)
    suggest_position("RELIANCE.NS", portfolio_value=100000)
    suggest_position("TCS.NS",      portfolio_value=100000)