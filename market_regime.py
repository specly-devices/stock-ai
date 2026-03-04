import yfinance as yf
import pandas as pd
import ta
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Market regime thresholds ─────────────────────────────────────────────
STRONG_BULL_THRESHOLD  =  0.6   # score above this = strong bull market
BULL_THRESHOLD         =  0.2   # score above this = bull market
BEAR_THRESHOLD         = -0.2   # score below this = bear market
STRONG_BEAR_THRESHOLD  = -0.6   # score below this = strong bear market

def get_market_regime():
    """
    Analyze Nifty 50 + Sensex + India VIX to determine
    current market regime.

    Returns:
        regime: STRONG_BULL / BULL / NEUTRAL / BEAR / STRONG_BEAR
        score:  -1.0 to +1.0
        details: dict of individual indicators
    """
    details = {}
    score   = 0
    count   = 0

    # ── Nifty 50 ────────────────────────────────────────────────────────
    try:
        nifty = yf.Ticker("^NSEI")
        df    = nifty.history(period="1y", interval="1d")
        df.dropna(inplace=True)

        close = df["Close"]

        # EMA trend
        ema20  = ta.trend.ema_indicator(close, window=20).iloc[-1]
        ema50  = ta.trend.ema_indicator(close, window=50).iloc[-1]
        ema200 = ta.trend.ema_indicator(close, window=200).iloc[-1]
        price  = float(close.iloc[-1])

        # RSI
        rsi = float(ta.momentum.rsi(close, window=14).iloc[-1])

        # Price vs EMAs
        above_ema20  = price > ema20
        above_ema50  = price > ema50
        above_ema200 = price > ema200

        # EMA alignment
        ema_bullish = ema20 > ema50 > ema200
        ema_bearish = ema20 < ema50 < ema200

        # 1-month and 3-month returns
        ret_1m = (price - float(close.iloc[-22])) / float(close.iloc[-22]) * 100
        ret_3m = (price - float(close.iloc[-66])) / float(close.iloc[-66]) * 100

        # MACD
        macd_obj    = ta.trend.MACD(close)
        macd_val    = float(macd_obj.macd().iloc[-1])
        macd_signal = float(macd_obj.macd_signal().iloc[-1])
        macd_bull   = macd_val > macd_signal

        # Scoring
        nifty_score = 0
        if above_ema200: nifty_score += 2
        else:            nifty_score -= 2
        if above_ema50:  nifty_score += 1
        else:            nifty_score -= 1
        if above_ema20:  nifty_score += 1
        else:            nifty_score -= 1
        if ema_bullish:  nifty_score += 2
        elif ema_bearish: nifty_score -= 2
        if rsi > 50:     nifty_score += 1
        else:            nifty_score -= 1
        if macd_bull:    nifty_score += 1
        else:            nifty_score -= 1
        if ret_1m > 0:   nifty_score += 1
        else:            nifty_score -= 1
        if ret_3m > 0:   nifty_score += 1
        else:            nifty_score -= 1

        nifty_normalized = nifty_score / 10  # normalize to -1 to +1
        score += nifty_normalized
        count += 1

        details["nifty"] = {
            "price":        round(price, 2),
            "ema20":        round(ema20, 2),
            "ema50":        round(ema50, 2),
            "ema200":       round(ema200, 2),
            "rsi":          round(rsi, 2),
            "ret_1m":       round(ret_1m, 2),
            "ret_3m":       round(ret_3m, 2),
            "above_ema200": above_ema200,
            "ema_bullish":  ema_bullish,
            "macd_bull":    macd_bull,
            "score":        nifty_normalized
        }
        print(f"✅ Nifty: ₹{price:.0f} | RSI:{rsi:.1f} | "
              f"{'Above' if above_ema200 else 'Below'} EMA200 | "
              f"1M:{ret_1m:+.1f}% | Score:{nifty_normalized:+.2f}")

    except Exception as e:
        print(f"❌ Nifty fetch failed: {e}")

    # ── India VIX (Fear index) ───────────────────────────────────────────
    try:
        vix    = yf.Ticker("^INDIAVIX")
        vix_df = vix.history(period="1mo", interval="1d")

        if not vix_df.empty:
            vix_current = float(vix_df["Close"].iloc[-1])
            vix_avg     = float(vix_df["Close"].mean())
            vix_high    = vix_current > 20   # above 20 = high fear
            vix_rising  = vix_current > vix_avg

            # High VIX = bearish sentiment
            if vix_current < 15:
                vix_score = 0.3   # low fear = bullish
            elif vix_current < 20:
                vix_score = 0.0   # neutral
            elif vix_current < 25:
                vix_score = -0.3  # elevated fear
            else:
                vix_score = -0.6  # extreme fear

            score += vix_score
            count += 1

            details["vix"] = {
                "current": round(vix_current, 2),
                "avg":     round(vix_avg, 2),
                "score":   vix_score
            }
            print(f"✅ India VIX: {vix_current:.1f} | "
                  f"{'HIGH FEAR' if vix_high else 'Normal'} | "
                  f"Score:{vix_score:+.2f}")

    except Exception as e:
        print(f"⚠️  VIX fetch failed (non-critical): {e}")

    # ── Nifty Bank ───────────────────────────────────────────────────────
    try:
        banknifty = yf.Ticker("^NSEBANK")
        bn_df     = banknifty.history(period="3mo", interval="1d")

        if not bn_df.empty:
            bn_close  = bn_df["Close"]
            bn_price  = float(bn_close.iloc[-1])
            bn_ema50  = float(ta.trend.ema_indicator(bn_close, window=50).iloc[-1])
            bn_ret_1m = (bn_price - float(bn_close.iloc[-22])) / float(bn_close.iloc[-22]) * 100
            bn_bull   = bn_price > bn_ema50

            bn_score  = 0.2 if bn_bull else -0.2
            score    += bn_score
            count    += 1

            details["banknifty"] = {
                "price":   round(bn_price, 2),
                "ema50":   round(bn_ema50, 2),
                "ret_1m":  round(bn_ret_1m, 2),
                "bullish": bn_bull,
                "score":   bn_score
            }
            print(f"✅ Bank Nifty: ₹{bn_price:.0f} | "
                  f"{'Above' if bn_bull else 'Below'} EMA50 | "
                  f"1M:{bn_ret_1m:+.1f}% | Score:{bn_score:+.2f}")

    except Exception as e:
        print(f"⚠️  Bank Nifty fetch failed: {e}")

    # ── Final regime ─────────────────────────────────────────────────────
    final_score = round(score / count if count > 0 else 0, 3)

    if final_score >= STRONG_BULL_THRESHOLD:
        regime = "STRONG_BULL"
        emoji  = "🚀"
    elif final_score >= BULL_THRESHOLD:
        regime = "BULL"
        emoji  = "🟢"
    elif final_score >= BEAR_THRESHOLD:
        regime = "NEUTRAL"
        emoji  = "🟡"
    elif final_score >= STRONG_BEAR_THRESHOLD:
        regime = "BEAR"
        emoji  = "🔴"
    else:
        regime = "STRONG_BEAR"
        emoji  = "🚨"

    print(f"\n{emoji} Market Regime: {regime} (score: {final_score:+.3f})")

    return regime, final_score, details

def should_allow_buy(regime, confidence):
    """
    Decide whether to allow BUY signals based on market regime.
    In bear markets, only allow very high confidence BUYs.
    """
    rules = {
        "STRONG_BULL": 40,   # allow BUYs above 40% confidence
        "BULL":        50,   # allow BUYs above 50% confidence
        "NEUTRAL":     60,   # allow BUYs above 60% confidence
        "BEAR":        75,   # only high confidence BUYs in bear market
        "STRONG_BEAR": 999,  # block ALL BUYs in strong bear market
    }
    min_confidence = rules.get(regime, 60)
    return confidence >= min_confidence, min_confidence

def get_regime_multiplier(regime):
    """
    Return confidence multiplier based on market regime.
    Bull markets boost confidence, bear markets reduce it.
    """
    multipliers = {
        "STRONG_BULL": 1.3,
        "BULL":        1.1,
        "NEUTRAL":     1.0,
        "BEAR":        0.7,
        "STRONG_BEAR": 0.4,
    }
    return multipliers.get(regime, 1.0)

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"Market Regime Analysis: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    regime, score, details = get_market_regime()

    print(f"\n{'='*60}")
    print(f"REGIME DETAILS")
    print(f"{'='*60}")

    if "nifty" in details:
        n = details["nifty"]
        print(f"\nNifty 50:")
        print(f"  Price:    ₹{n['price']}")
        print(f"  EMA 20:   ₹{n['ema20']} {'✅' if n['price'] > n['ema20'] else '❌'}")
        print(f"  EMA 50:   ₹{n['ema50']} {'✅' if n['price'] > n['ema50'] else '❌'}")
        print(f"  EMA 200:  ₹{n['ema200']} {'✅' if n['above_ema200'] else '❌'}")
        print(f"  RSI:      {n['rsi']}")
        print(f"  1M Ret:   {n['ret_1m']:+.1f}%")
        print(f"  3M Ret:   {n['ret_3m']:+.1f}%")

    if "vix" in details:
        v = details["vix"]
        print(f"\nIndia VIX:")
        print(f"  Current:  {v['current']}")
        print(f"  30D Avg:  {v['avg']}")

    allowed, min_conf = should_allow_buy(regime, 60)
    print(f"\n{'='*60}")
    print(f"BUY Signal Rules for current regime ({regime}):")
    print(f"  Minimum confidence required: {min_conf}%")
    print(f"  60% confidence signal: {'ALLOWED' if allowed else 'BLOCKED'}")
    print(f"{'='*60}")