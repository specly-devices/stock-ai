import os
import yfinance as yf
import pandas as pd
import numpy as np
import ta
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Settings ─────────────────────────────────────────────────────────────
INITIAL_CAPITAL  = 100000
POSITION_SIZE    = 0.10
STOP_LOSS_PCT    = 3.0   # tightened from 5%
TARGET_PCT       = 3.0   # reduced from 8% — realistic for 5 days
HOLD_DAYS        = 7
BROKERAGE        = 0.03
STT              = 0.001

# ── Generate signals (same logic as data_pipeline) ───────────────────────
def generate_backtest_signals(df):
    """
    Generate BUY/SELL signals for entire historical dataframe.
    Returns dataframe with signal column.
    """
    df = df.copy()

    # Technical indicators
    df["EMA_9"]   = ta.trend.ema_indicator(df["Close"], window=9)
    df["EMA_21"]  = ta.trend.ema_indicator(df["Close"], window=21)
    df["EMA_50"]  = ta.trend.ema_indicator(df["Close"], window=50)
    df["EMA_200"] = ta.trend.ema_indicator(df["Close"], window=200)
    df["RSI"]     = ta.momentum.rsi(df["Close"], window=14)

    macd              = ta.trend.MACD(df["Close"])
    df["MACD"]        = macd.macd()
    df["MACD_Signal"] = macd.macd_signal()

    bb                = ta.volatility.BollingerBands(df["Close"])
    df["BB_Upper"]    = bb.bollinger_hband()
    df["BB_Lower"]    = bb.bollinger_lband()

    df["Volume_MA"]   = df["Volume"].rolling(20).mean()

    df.dropna(inplace=True)

    # Score each day
    scores = []
    for i in range(1, len(df)):
        score = 0
        row   = df.iloc[i]
        prev  = df.iloc[i-1]

        # RSI
        if row["RSI"] < 35:
            score += 2
        elif row["RSI"] > 65:
            score -= 2

        # MACD crossover
        if row["MACD"] > row["MACD_Signal"] and prev["MACD"] <= prev["MACD_Signal"]:
            score += 2
        elif row["MACD"] < row["MACD_Signal"] and prev["MACD"] >= prev["MACD_Signal"]:
            score -= 2

        # EMA alignment
        if row["EMA_9"] > row["EMA_21"] > row["EMA_50"]:
            score += 1
        elif row["EMA_9"] < row["EMA_21"] < row["EMA_50"]:
            score -= 1

        # Price vs EMA200
        if row["Close"] > row["EMA_200"]:
            score += 1
        else:
            score -= 1

        # Bollinger
        if row["Close"] <= row["BB_Lower"]:
            score += 2
        elif row["Close"] >= row["BB_Upper"]:
            score -= 2

        # Volume confirmation
        if row["Volume"] > row["Volume_MA"] * 1.5:
            if score > 0:
                score += 1
            else:
                score -= 1

        scores.append(score)

    scores = [0] + scores  # pad first row
    df["Score"]  = scores
    df["Signal"] = df["Score"].apply(
        lambda x: "BUY" if x >= 3 else ("SELL" if x <= -3 else "HOLD")
    )

    return df

# ── Run backtest for one stock ────────────────────────────────────────────
def backtest_symbol(symbol, period="3y"):
    """
    Backtest a single stock and return trade results.
    """
    try:
        ticker = yf.Ticker(symbol)
        df     = ticker.history(period=period, interval="1d")
        if len(df) < 100:
            return None

        df = generate_backtest_signals(df)

        capital    = INITIAL_CAPITAL
        trades     = []
        in_trade   = False
        entry_price = 0
        entry_date  = None
        entry_idx   = 0
        quantity    = 0

        for i in range(len(df)):
            row          = df.iloc[i]
            current_price = float(row["Close"])
            current_date  = df.index[i]

            if not in_trade:
                # Enter trade on BUY signal
                if row["Signal"] == "BUY":
                    position_value = capital * POSITION_SIZE
                    quantity       = int(position_value / current_price)
                    if quantity < 1:
                        continue

                    entry_price = current_price
                    entry_date  = current_date
                    entry_idx   = i
                    in_trade    = True

            else:
                # Check exit conditions
                pnl_pct      = ((current_price - entry_price) / entry_price) * 100
                days_held    = i - entry_idx
                exit_reason  = None

                if pnl_pct <= -STOP_LOSS_PCT:
                    exit_reason = "STOP_LOSS"
                elif pnl_pct >= TARGET_PCT:
                    exit_reason = "TARGET"
                elif days_held >= HOLD_DAYS:
                    exit_reason = "TIME_EXIT"

                if exit_reason:
                    # Calculate trade P&L
                    gross_pnl  = (current_price - entry_price) * quantity
                    brokerage  = (entry_price + current_price) * quantity * BROKERAGE/100
                    stt_cost   = current_price * quantity * STT / 100
                    net_pnl    = gross_pnl - brokerage - stt_cost

                    capital   += net_pnl
                    in_trade   = False

                    trades.append({
                        "symbol":       symbol,
                        "entry_date":   entry_date,
                        "exit_date":    current_date,
                        "entry_price":  round(entry_price, 2),
                        "exit_price":   round(current_price, 2),
                        "quantity":     quantity,
                        "days_held":    days_held,
                        "pnl_pct":      round(pnl_pct, 2),
                        "net_pnl":      round(net_pnl, 2),
                        "exit_reason":  exit_reason,
                        "capital":      round(capital, 2),
                        "win":          net_pnl > 0
                    })

        return trades, df, capital

    except Exception as e:
        print(f"❌ {symbol}: {e}")
        return None

# ── Analyze results ───────────────────────────────────────────────────────
def analyze_results(all_trades, final_capital):
    """Calculate backtest statistics"""
    if not all_trades:
        return {}

    df = pd.DataFrame(all_trades)

    total_trades  = len(df)
    winning       = df[df["win"] == True]
    losing        = df[df["win"] == False]
    win_rate      = round(len(winning) / total_trades * 100, 1)

    avg_win       = round(winning["pnl_pct"].mean(), 2) if len(winning) > 0 else 0
    avg_loss      = round(losing["pnl_pct"].mean(), 2)  if len(losing) > 0 else 0
    avg_hold      = round(df["days_held"].mean(), 1)

    total_pnl     = round(df["net_pnl"].sum(), 2)
    total_return  = round((final_capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100, 2)

    # Max drawdown
    capital_curve = [INITIAL_CAPITAL] + list(df["capital"])
    peak          = INITIAL_CAPITAL
    max_drawdown  = 0
    for c in capital_curve:
        if c > peak:
            peak = c
        dd = ((peak - c) / peak) * 100
        if dd > max_drawdown:
            max_drawdown = dd

    # Profit factor
    gross_profit = winning["net_pnl"].sum() if len(winning) > 0 else 0
    gross_loss   = abs(losing["net_pnl"].sum()) if len(losing) > 0 else 1
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0

    # Stop loss vs target vs time exit
    stop_losses  = len(df[df["exit_reason"] == "STOP_LOSS"])
    targets_hit  = len(df[df["exit_reason"] == "TARGET"])
    time_exits   = len(df[df["exit_reason"] == "TIME_EXIT"])

    # Best and worst trades
    best_trade  = df.loc[df["net_pnl"].idxmax()]
    worst_trade = df.loc[df["net_pnl"].idxmin()]

    return {
        "total_trades":   total_trades,
        "win_rate":       win_rate,
        "avg_win":        avg_win,
        "avg_loss":       avg_loss,
        "avg_hold_days":  avg_hold,
        "total_pnl":      total_pnl,
        "total_return":   total_return,
        "max_drawdown":   round(max_drawdown, 2),
        "profit_factor":  profit_factor,
        "stop_losses":    stop_losses,
        "targets_hit":    targets_hit,
        "time_exits":     time_exits,
        "best_trade":     best_trade,
        "worst_trade":    worst_trade,
        "final_capital":  round(final_capital, 2)
    }

# ── Print report ──────────────────────────────────────────────────────────
def print_report(symbol, stats, trades):
    """Print formatted backtest report"""
    print(f"\n{'='*60}")
    print(f"BACKTEST REPORT: {symbol}")
    print(f"Period: 3 years | Capital: ₹{INITIAL_CAPITAL:,}")
    print(f"{'='*60}")

    if not stats:
        print("❌ No trades generated")
        return

    ret_color  = "+" if stats["total_return"] >= 0 else ""
    wl_color   = "✅" if stats["win_rate"] >= 50 else "⚠️"

    print(f"{'─'*60}")
    print(f"  Total Trades:     {stats['total_trades']}")
    print(f"  Win Rate:         {wl_color} {stats['win_rate']}%")
    print(f"  Avg Win:          +{stats['avg_win']}%")
    print(f"  Avg Loss:         {stats['avg_loss']}%")
    print(f"  Avg Hold:         {stats['avg_hold_days']} days")
    print(f"{'─'*60}")
    print(f"  Total Return:     {ret_color}{stats['total_return']}%")
    print(f"  Total P&L:        ₹{stats['total_pnl']:+,.0f}")
    print(f"  Final Capital:    ₹{stats['final_capital']:,.0f}")
    print(f"  Max Drawdown:     -{stats['max_drawdown']}%")
    print(f"  Profit Factor:    {stats['profit_factor']}x")
    print(f"{'─'*60}")
    print(f"  Stop Losses Hit:  {stats['stop_losses']}")
    print(f"  Targets Hit:      {stats['targets_hit']}")
    print(f"  Time Exits:       {stats['time_exits']}")
    print(f"{'─'*60}")

    best  = stats["best_trade"]
    worst = stats["worst_trade"]
    print(f"  Best Trade:  {best['symbol'].replace('.NS','')} "
          f"+{best['pnl_pct']}% ₹{best['net_pnl']:+,.0f}")
    print(f"  Worst Trade: {worst['symbol'].replace('.NS','')} "
          f"{worst['pnl_pct']}% ₹{worst['net_pnl']:+,.0f}")
    print(f"{'='*60}")

# ── Run full backtest ─────────────────────────────────────────────────────
def run_full_backtest(symbols=None):
    """Run backtest across multiple stocks and show combined results"""

    if symbols is None:
        symbols = [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS",
            "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS",
            "KOTAKBANK.NS", "LT.NS", "HCLTECH.NS", "AXISBANK.NS",
            "MARUTI.NS", "SUNPHARMA.NS", "TITAN.NS", "BAJFINANCE.NS",
            "WIPRO.NS", "M&M.NS", "JSWSTEEL.NS", "ONGC.NS"
        ]

    print(f"\n{'='*60}")
    print(f"FULL BACKTEST — {len(symbols)} stocks — 3 years")
    print(f"Capital: ₹{INITIAL_CAPITAL:,} | Stop: {STOP_LOSS_PCT}% | "
          f"Target: {TARGET_PCT}% | Hold: {HOLD_DAYS} days")
    print(f"{'='*60}\n")

    all_trades    = []
    stock_results = []
    final_capital = INITIAL_CAPITAL

    for symbol in symbols:
        result = backtest_symbol(symbol)
        if not result:
            continue

        trades, df, capital = result
        if not trades:
            print(f"⚪ {symbol:<20} — No trades generated")
            continue

        trades_df    = pd.DataFrame(trades)
        win_rate     = round(len(trades_df[trades_df["win"]]) / len(trades_df) * 100, 1)
        total_pnl    = round(trades_df["net_pnl"].sum(), 2)
        total_return = round((capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100, 2)

        emoji = "✅" if total_return > 0 else "❌"
        print(f"{emoji} {symbol:<20} Trades:{len(trades):<5} "
              f"WinRate:{win_rate}%  "
              f"Return:{total_return:+.1f}%  "
              f"P&L:₹{total_pnl:+,.0f}")

        all_trades.extend(trades)
        stock_results.append({
            "symbol":    symbol,
            "trades":    len(trades),
            "win_rate":  win_rate,
            "return":    total_return,
            "pnl":       total_pnl
        })

    # Combined stats
    if all_trades:
        print(f"\n{'='*60}")
        print("COMBINED RESULTS")
        print(f"{'='*60}")

        stats = analyze_results(all_trades, final_capital)
        results_df = pd.DataFrame(stock_results).sort_values(
            "return", ascending=False
        )

        print(f"  Total Trades:    {stats['total_trades']}")
        print(f"  Overall Win Rate:{stats['win_rate']}%")
        print(f"  Profit Factor:   {stats['profit_factor']}x")
        print(f"  Max Drawdown:    -{stats['max_drawdown']}%")
        print(f"  Avg Hold:        {stats['avg_hold_days']} days")

        print(f"\n  🏆 TOP 5 STOCKS:")
        for _, row in results_df.head(5).iterrows():
            print(f"     {row['symbol'].replace('.NS',''):<15} "
                  f"{row['return']:+.1f}% ({row['win_rate']}% win rate)")

        print(f"\n  ⚠️  BOTTOM 5 STOCKS:")
        for _, row in results_df.tail(5).iterrows():
            print(f"     {row['symbol'].replace('.NS',''):<15} "
                  f"{row['return']:+.1f}% ({row['win_rate']}% win rate)")

    return all_trades, stock_results

if __name__ == "__main__":
    # Run full backtest
    all_trades, results = run_full_backtest()

    # Detailed report for top stock
    print("\n\nDetailed report for RELIANCE:")
    result = backtest_symbol("RELIANCE.NS", period="3y")
    if result:
        trades, df, capital = result
        stats = analyze_results(trades, capital)
        print_report("RELIANCE.NS", stats, trades)