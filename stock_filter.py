# Based on backtesting results — stocks with proven positive returns
# Update this monthly after running backtester.py

HIGH_CONFIDENCE_STOCKS = [
    "ICICIBANK.NS",   # 71.4% win rate
    "SUNPHARMA.NS",   # 68.2% win rate
    "SBIN.NS",        # 62.5% win rate
    "BHARTIARTL.NS",  # 51.6% win rate
    "M&M.NS",         # 51.6% win rate
    "KOTAKBANK.NS",   # 55.0% win rate
    "AXISBANK.NS",    # 58.3% win rate
    "WIPRO.NS",       # 51.7% win rate
    "ONGC.NS",        # 55.6% win rate
    "RELIANCE.NS",    # 47.4% win rate
]

AVOID_STOCKS = [
    "TCS.NS",         # 33.3% win rate
    "JSWSTEEL.NS",    # 40.0% win rate
    "INFY.NS",        # 43.5% win rate
    "BAJFINANCE.NS",  # 18.2% win rate (previous test)
]

NEUTRAL_STOCKS = [
    "HDFCBANK.NS",
    "ITC.NS",
    "LT.NS",
    "HCLTECH.NS",
    "TITAN.NS",
]

def get_stock_tier(symbol):
    """Return tier for a stock based on backtest results"""
    if symbol in HIGH_CONFIDENCE_STOCKS:
        return "HIGH", 1.2   # boost confidence by 20%
    elif symbol in AVOID_STOCKS:
        return "AVOID", 0.6  # reduce confidence by 40%
    else:
        return "NEUTRAL", 1.0