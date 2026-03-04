import numpy as np
import pandas as pd
import os
import joblib
from dotenv import load_dotenv
import yfinance as yf
import ta
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report
from xgboost import XGBClassifier

load_dotenv()

MODEL_PATH   = "models/xgboost_model.pkl"
SCALER_PATH  = "models/scaler.pkl"
FEATURE_PATH = "models/feature_cols.pkl"

os.makedirs("models", exist_ok=True)

# ── Feature engineering ─────────────────────────────────────────────────
def build_features(df, for_prediction=False):
    """
    Build ML features from OHLCV data.
    for_prediction=True  → skip target column (no future data needed)
    for_prediction=False → include target for training
    """
    f = pd.DataFrame(index=df.index)

    # Price-based returns
    f["returns_1d"]  = df["Close"].pct_change(1)
    f["returns_3d"]  = df["Close"].pct_change(3)
    f["returns_5d"]  = df["Close"].pct_change(5)
    f["returns_10d"] = df["Close"].pct_change(10)

    # RSI
    f["rsi"]    = ta.momentum.rsi(df["Close"], window=14)
    f["rsi_6"]  = ta.momentum.rsi(df["Close"], window=6)

    # MACD
    macd             = ta.trend.MACD(df["Close"])
    f["macd"]        = macd.macd()
    f["macd_signal"] = macd.macd_signal()
    f["macd_hist"]   = macd.macd_diff()
    f["macd_cross"]  = (f["macd"] > f["macd_signal"]).astype(int)

    # EMA ratios
    ema9             = ta.trend.ema_indicator(df["Close"], window=9)
    ema21            = ta.trend.ema_indicator(df["Close"], window=21)
    ema50            = ta.trend.ema_indicator(df["Close"], window=50)
    ema200           = ta.trend.ema_indicator(df["Close"], window=200)
    f["ema9_21"]     = ema9 / ema21
    f["ema21_50"]    = ema21 / ema50
    f["price_ema50"] = df["Close"] / ema50
    f["price_ema200"]= df["Close"] / ema200

    # Bollinger Bands
    bb               = ta.volatility.BollingerBands(df["Close"])
    f["bb_position"] = (df["Close"] - bb.bollinger_lband()) / (
                        bb.bollinger_hband() - bb.bollinger_lband() + 1e-10)
    f["bb_width"]    = (bb.bollinger_hband() - bb.bollinger_lband()) / (
                        bb.bollinger_mavg() + 1e-10)

    # Volume
    f["volume_ratio"] = df["Volume"] / (df["Volume"].rolling(20).mean() + 1e-10)
    f["obv"]          = ta.volume.on_balance_volume(df["Close"], df["Volume"])
    f["obv_ema"]      = f["obv"].ewm(span=21).mean()
    f["obv_ratio"]    = f["obv"] / (f["obv_ema"] + 1e-10)

    # Volatility
    f["atr"]       = ta.volatility.average_true_range(
                        df["High"], df["Low"], df["Close"])
    f["atr_ratio"] = f["atr"] / (df["Close"] + 1e-10)

    # Momentum
    f["roc_5"]   = ta.momentum.roc(df["Close"], window=5)
    f["roc_10"]  = ta.momentum.roc(df["Close"], window=10)
    f["stoch_k"] = ta.momentum.stoch(df["High"], df["Low"], df["Close"])
    f["stoch_d"] = ta.momentum.stoch_signal(df["High"], df["Low"], df["Close"])

    # Candlestick patterns
    f["body_size"]    = abs(df["Close"] - df["Open"]) / (df["Open"] + 1e-10)
    f["upper_shadow"] = (df["High"] - df[["Close","Open"]].max(axis=1)) / (df["Open"] + 1e-10)
    f["lower_shadow"] = (df[["Close","Open"]].min(axis=1) - df["Low"]) / (df["Open"] + 1e-10)

    # Market regime
    ema50_slope         = ema50.diff(5) / (ema50.shift(5) + 1e-10) * 100
    f["trend_strength"] = ema50_slope
    f["above_ema50"]    = (df["Close"] > ema50).astype(int)
    f["above_ema200"]   = (df["Close"] > ema200).astype(int)

    # Relative strength vs 52-week and 1-month range
    high_52w     = df["High"].rolling(252).max()
    low_52w      = df["Low"].rolling(252).min()
    f["rs_52w"]  = (df["Close"] - low_52w) / (high_52w - low_52w + 1e-10)

    high_1m      = df["High"].rolling(22).max()
    low_1m       = df["Low"].rolling(22).min()
    f["rs_1m"]   = (df["Close"] - low_1m) / (high_1m - low_1m + 1e-10)

    # Gap
    f["gap_up"]  = (df["Open"] - df["Close"].shift(1)) / (df["Close"].shift(1) + 1e-10)

    # Consecutive up/down days
    daily_ret      = df["Close"].pct_change()
    up_streak      = daily_ret.gt(0)
    f["consec_up"] = up_streak.groupby(
                        (up_streak != up_streak.shift()).cumsum()
                     ).cumcount()
    down_streak      = daily_ret.lt(0)
    f["consec_down"] = down_streak.groupby(
                        (down_streak != down_streak.shift()).cumsum()
                     ).cumcount()

    # Distance from recent high/low
    f["dist_from_high"] = (df["High"].rolling(10).max() - df["Close"]) / (df["Close"] + 1e-10)
    f["dist_from_low"]  = (df["Close"] - df["Low"].rolling(10).min()) / (df["Close"] + 1e-10)

    if not for_prediction:
        # Target — will price gain 0.8%+ in next 5 days?
        future_return = df["Close"].shift(-5) / df["Close"] - 1
        f["target"]   = (future_return > 0.008).astype(int)
        f.dropna(inplace=True)
    else:
        # For prediction — just return all rows, let predict_stock handle it
        pass

    return f

# ── Train model ─────────────────────────────────────────────────────────
def train_model(symbols=None):
    """Train XGBoost on historical data from multiple stocks"""

    if symbols is None:
        symbols = [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
            "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS", "LT.NS",
            "HCLTECH.NS", "AXISBANK.NS", "MARUTI.NS", "SUNPHARMA.NS", "TITAN.NS",
            "BAJFINANCE.NS", "WIPRO.NS", "M&M.NS", "JSWSTEEL.NS", "ONGC.NS",
            "NESTLEIND.NS", "POWERGRID.NS", "NTPC.NS", "TECHM.NS", "COALINDIA.NS",
            "ADANIPORTS.NS", "HINDALCO.NS", "TATASTEEL.NS", "VEDL.NS", "DRREDDY.NS",
            "PIDILITIND.NS", "LUPIN.NS", "AUROPHARMA.NS", "PERSISTENT.NS",
            "COFORGE.NS", "LTIM.NS", "CHOLAFIN.NS", "TORNTPHARM.NS",
            "FEDERALBNK.NS", "IDFCFIRSTB.NS", "TATAPOWER.NS", "DLF.NS",
            "GODREJPROP.NS", "DABUR.NS", "MARICO.NS", "COLPAL.NS",
            "BAJAJ-AUTO.NS", "HEROMOTOCO.NS", "EICHERMOT.NS", "TVSMOTOR.NS"
        ]

    print(f"📊 Training XGBoost on {len(symbols)} stocks...")
    all_features = []

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            df     = ticker.history(period="5y", interval="1d")
            if len(df) < 100:
                continue
            features = build_features(df, for_prediction=False)
            all_features.append(features)
            print(f"  ✅ {symbol}: {len(features)} samples")
        except Exception as e:
            print(f"  ❌ {symbol}: {e}")

    if not all_features:
        print("❌ No data collected")
        return None

    combined = pd.concat(all_features, ignore_index=True)
    combined.dropna(inplace=True)

    feature_cols = [c for c in combined.columns if c != "target"]
    joblib.dump(feature_cols, FEATURE_PATH)

    X = combined[feature_cols]
    y = combined["target"]

    print(f"\n📈 Total samples: {len(X)}")
    print(f"   BUY signals:  {int(y.sum())} ({y.mean()*100:.1f}%)")
    print(f"   HOLD signals: {int((1-y).sum())} ({(1-y.mean())*100:.1f}%)")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    scaler  = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test  = scaler.transform(X_test)

    buy_count  = int(y_train.sum())
    hold_count = int((1 - y_train).sum())
    scale      = hold_count / buy_count

    model = XGBClassifier(
        n_estimators=500,
        max_depth=5,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.7,
        min_child_weight=3,
        gamma=0.1,
        scale_pos_weight=scale,
        eval_metric="auc",
        random_state=42,
        n_jobs=-1
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False
    )

    y_pred   = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\n✅ Model accuracy: {accuracy*100:.1f}%")
    print(classification_report(y_test, y_pred, target_names=["HOLD", "BUY"]))

    joblib.dump(model,  MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    print(f"✅ Model saved to {MODEL_PATH}")

    return model, scaler, feature_cols

# ── Predict for a single stock ───────────────────────────────────────────
def predict_stock(symbol):
    """
    Load trained model and predict BUY/HOLD for a stock.
    Returns (prediction, probability%)
    """
    if not os.path.exists(MODEL_PATH) or not os.path.exists(FEATURE_PATH):
        return None, 50.0

    try:
        model        = joblib.load(MODEL_PATH)
        scaler       = joblib.load(SCALER_PATH)
        feature_cols = joblib.load(FEATURE_PATH)

        ticker = yf.Ticker(symbol)
        df     = ticker.history(period="2y", interval="1d")
        if len(df) < 260:
            return None, 50.0

        # Build features WITHOUT target column
        features = build_features(df, for_prediction=True)
        
        if features.empty:
            return None, 50.0

        # Align columns exactly to training
        missing = [c for c in feature_cols if c not in features.columns]
        if missing:
            return None, 50.0

        # Get last row that has no NaN values
        valid = features[feature_cols].dropna()
        if valid.empty:
            return None, 50.0
        latest = valid.iloc[[-1]]
        latest_scaled = scaler.transform(latest)
        proba         = float(model.predict_proba(latest_scaled)[0][1])
        prediction    = "BUY" if proba > 0.52 else "HOLD"

        return prediction, round(proba * 100, 1)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, 50.0


if __name__ == "__main__":
    print("Training XGBoost model...")
    result = train_model()
    if result:
        model, scaler, cols = result
        print("\nTesting predictions:")
        for sym in ["RELIANCE.NS", "TCS.NS", "INFY.NS", "SBIN.NS", "HDFCBANK.NS"]:
            pred, prob = predict_stock(sym)
            emoji = "🟢" if pred == "BUY" else "🟡"
            print(f"  {emoji} {sym}: {pred} ({prob}% confidence)")