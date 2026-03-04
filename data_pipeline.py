import yfinance as yf
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime
import ta  # technical analysis library

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# ── Indian Stocks Watchlist ─────────────────────────────────────────────
# These are Nifty 50 top stocks — you can add/remove any
WATCHLIST = [
    # Nifty 50 Large Cap
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
    "LT.NS", "HCLTECH.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS", "BAJFINANCE.NS", "WIPRO.NS",
    "NESTLEIND.NS", "POWERGRID.NS", "NTPC.NS", "TECHM.NS", "ONGC.NS",
    "TATAMOTORS.NS", "ADANIENT.NS", "ADANIPORTS.NS", "COALINDIA.NS", "JSWSTEEL.NS",

    # Mid Cap
    "PIDILITIND.NS", "MUTHOOTFIN.NS", "LUPIN.NS", "BIOCON.NS", "AUROPHARMA.NS",
    "VOLTAS.NS", "TATACOMM.NS", "PERSISTENT.NS", "COFORGE.NS", "LTIM.NS",
    "INDHOTEL.NS", "ABCAPITAL.NS", "FEDERALBNK.NS", "IDFCFIRSTB.NS", "RBLBANK.NS",
    "CHOLAFIN.NS", "MFSL.NS", "APLLTD.NS", "ALKEM.NS", "TORNTPHARM.NS",

    # Small Cap — High momentum
    "TANLA.NS", "HAPPSTMNDS.NS", "ROUTE.NS", "CLEAN.NS", "NAZARA.NS",
    "LATENTVIEW.NS", "INTELLECT.NS", "KPITTECH.NS", "TATAELXSI.NS", "RAILTEL.NS",

    # Sectors — Banking
    "BANDHANBNK.NS", "INDUSINDBK.NS", "AUBANK.NS", "CANBK.NS", "BANKBARODA.NS",

    # Sectors — IT
    "MPHASIS.NS", "LTTS.NS", "CYIENT.NS", "NIITTECH.NS", "HEXAWARE.NS",

    # Sectors — Auto
    "BAJAJ-AUTO.NS", "HEROMOTOCO.NS", "EICHERMOT.NS", "TVSMOTOR.NS", "MOTHERSON.NS",

    # Sectors — Pharma
    "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "GLENMARK.NS", "IPCALAB.NS",

    # Sectors — Energy
    "TATAPOWER.NS", "ADANIGREEN.NS", "ADANITRANS.NS", "CESC.NS", "TORNTPOWER.NS",

    # Sectors — FMCG
    "DABUR.NS", "MARICO.NS", "COLPAL.NS", "EMAMILTD.NS", "GODREJCP.NS",

    # Sectors — Metals
    "TATASTEEL.NS", "HINDALCO.NS", "VEDL.NS", "SAIL.NS", "NATIONALUM.NS",

    # Sectors — Real Estate
    "DLF.NS", "GODREJPROP.NS", "OBEROIRLTY.NS", "PRESTIGE.NS", "BRIGADE.NS",
]

# ── Fetch Stock Data ────────────────────────────────────────────────────
def fetch_stock_data(symbol, period="6mo", interval="1d"):
    """Fetch OHLCV data from Yahoo Finance"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            print(f"❌ No data for {symbol}")
            return None
        df.dropna(inplace=True)
        print(f"✅ Fetched {symbol} — {len(df)} rows")
        return df
    except Exception as e:
        print(f"❌ Error fetching {symbol}: {e}")
        return None

# ── Calculate Technical Indicators ─────────────────────────────────────
def calculate_indicators(df):
    """Calculate RSI, MACD, EMA, Bollinger Bands, Supertrend, OBV"""

    # EMA
    df["EMA_9"]   = ta.trend.ema_indicator(df["Close"], window=9)
    df["EMA_21"]  = ta.trend.ema_indicator(df["Close"], window=21)
    df["EMA_50"]  = ta.trend.ema_indicator(df["Close"], window=50)
    df["EMA_200"] = ta.trend.ema_indicator(df["Close"], window=200)

    # RSI
    df["RSI"] = ta.momentum.rsi(df["Close"], window=14)

    # MACD
    macd = ta.trend.MACD(df["Close"])
    df["MACD"]        = macd.macd()
    df["MACD_Signal"] = macd.macd_signal()
    df["MACD_Hist"]   = macd.macd_diff()

    # Bollinger Bands
    bb = ta.volatility.BollingerBands(df["Close"], window=20, window_dev=2)
    df["BB_Upper"] = bb.bollinger_hband()
    df["BB_Lower"] = bb.bollinger_lband()
    df["BB_Mid"]   = bb.bollinger_mavg()

    # OBV (On Balance Volume)
    df["OBV"] = ta.volume.on_balance_volume(df["Close"], df["Volume"])

    # ATR (Average True Range — measures volatility)
    df["ATR"] = ta.volatility.average_true_range(df["High"], df["Low"], df["Close"])

    # Supertrend (manual — ta library doesn't have it)
    df = calculate_supertrend(df)

    return df

def calculate_supertrend(df, period=10, multiplier=3):
    """Calculate Supertrend indicator"""
    hl_avg = (df["High"] + df["Low"]) / 2
    atr    = ta.volatility.average_true_range(df["High"], df["Low"], df["Close"], window=period)

    upper_band = hl_avg + (multiplier * atr)
    lower_band = hl_avg - (multiplier * atr)

    supertrend  = [True] * len(df)  # True = uptrend
    final_upper = upper_band.copy()
    final_lower = lower_band.copy()

    for i in range(1, len(df)):
        # Upper band
        if upper_band.iloc[i] < final_upper.iloc[i-1] or df["Close"].iloc[i-1] > final_upper.iloc[i-1]:
            final_upper.iloc[i] = upper_band.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i-1]

        # Lower band
        if lower_band.iloc[i] > final_lower.iloc[i-1] or df["Close"].iloc[i-1] < final_lower.iloc[i-1]:
            final_lower.iloc[i] = lower_band.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i-1]

        # Trend
        if df["Close"].iloc[i] > final_upper.iloc[i-1]:
            supertrend[i] = True
        elif df["Close"].iloc[i] < final_lower.iloc[i-1]:
            supertrend[i] = False
        else:
            supertrend[i] = supertrend[i-1]

    df["Supertrend"]       = supertrend  # True = bullish, False = bearish
    df["Supertrend_Upper"] = final_upper
    df["Supertrend_Lower"] = final_lower

    return df

# ── Generate Signal ─────────────────────────────────────────────────────
def generate_signal(df, symbol):
    """
    Combine all indicators into a BUY / SELL / HOLD signal with confidence
    """
    latest = df.iloc[-1]
    prev   = df.iloc[-2]

    score   = 0  # positive = bullish, negative = bearish
    reasons = []

    # 1. RSI
    if latest["RSI"] < 35:
        score += 2
        reasons.append("RSI oversold")
    elif latest["RSI"] > 65:
        score -= 2
        reasons.append("RSI overbought")

    # 2. MACD crossover
    if latest["MACD"] > latest["MACD_Signal"] and prev["MACD"] <= prev["MACD_Signal"]:
        score += 2
        reasons.append("MACD bullish crossover")
    elif latest["MACD"] < latest["MACD_Signal"] and prev["MACD"] >= prev["MACD_Signal"]:
        score -= 2
        reasons.append("MACD bearish crossover")

    # 3. EMA trend
    if latest["EMA_9"] > latest["EMA_21"] > latest["EMA_50"]:
        score += 1
        reasons.append("EMA bullish alignment")
    elif latest["EMA_9"] < latest["EMA_21"] < latest["EMA_50"]:
        score -= 1
        reasons.append("EMA bearish alignment")

    # 4. Price vs EMA 200
    if latest["Close"] > latest["EMA_200"]:
        score += 1
        reasons.append("Above EMA200")
    else:
        score -= 1
        reasons.append("Below EMA200")

    # 5. Bollinger Bands
    if latest["Close"] <= latest["BB_Lower"]:
        score += 2
        reasons.append("Price at BB lower band (oversold)")
    elif latest["Close"] >= latest["BB_Upper"]:
        score -= 2
        reasons.append("Price at BB upper band (overbought)")

    # 6. Supertrend
    if latest["Supertrend"]:
        score += 2
        reasons.append("Supertrend bullish")
    else:
        score -= 2
        reasons.append("Supertrend bearish")

    # 7. Volume confirmation
    avg_volume = df["Volume"].tail(20).mean()
    if latest["Volume"] > avg_volume * 1.5:
        if score > 0:
            score += 1
            reasons.append("High volume confirms bullish move")
        else:
            score -= 1
            reasons.append("High volume confirms bearish move")

    # ── Convert score to signal ──
    max_score  = 11
    confidence = round((abs(score) / max_score) * 100, 1)
    confidence = min(confidence, 95.0)  # cap at 95% — never claim 100%

    if score >= 4:
        signal = "BUY"
    elif score <= -4:
        signal = "SELL"
    else:
        signal = "HOLD"

    return {
        "symbol":     symbol,
        "signal":     signal,
        "confidence": confidence,
        "price":      round(float(latest["Close"]), 2),
        "rsi":        round(float(latest["RSI"]), 2),
        "macd":       round(float(latest["MACD"]), 4),
        "score":      score,
        "reason":     ", ".join(reasons)
    }

# ── Save to Supabase ────────────────────────────────────────────────────
def save_signal(signal_data):
    """Save signal to database"""
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
        print(f"❌ DB save failed: {e}")

def save_price(symbol, latest_row):
    """Save latest price to price_history"""
    try:
        supabase.table("price_history").insert({
            "symbol": symbol,
            "open":   round(float(latest_row["Open"]), 2),
            "high":   round(float(latest_row["High"]), 2),
            "low":    round(float(latest_row["Low"]), 2),
            "close":  round(float(latest_row["Close"]), 2),
            "volume": int(latest_row["Volume"])
        }).execute()
    except Exception as e:
        print(f"❌ Price save failed: {e}")

# ── Main Pipeline ───────────────────────────────────────────────────────
def run_pipeline():
    """Run full pipeline for all watchlist stocks"""
    print(f"\n{'='*50}")
    print(f"Pipeline started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    results = []

    for symbol in WATCHLIST:
        df = fetch_stock_data(symbol)
        if df is None or len(df) < 50:
            continue

        df = calculate_indicators(df)
        signal = generate_signal(df, symbol)
        save_signal(signal)
        save_price(symbol, df.iloc[-1])

        results.append(signal)

        # Print result
        emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}.get(signal["signal"], "⚪")
        print(f"{emoji} {symbol:<20} {signal['signal']:<5} "
              f"₹{signal['price']:<10} RSI:{signal['rsi']:<7} "
              f"Conf:{signal['confidence']}% | {signal['reason']}")

    print(f"\n✅ Pipeline complete — {len(results)} stocks analyzed")
    return results

if __name__ == "__main__":
    run_pipeline()
    