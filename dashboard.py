import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import yfinance as yf
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client
import ta

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="StockAI Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Supabase ──────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

supabase = get_supabase()

# ── Global CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Outfit:wght@300;400;600;700;900&family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

:root {
    --bg:        #07090f;
    --bg2:       #0d1117;
    --bg3:       #111827;
    --card:      #131c2e;
    --border:    #1e2d45;
    --border2:   #243350;
    --green:     #00ff88;
    --green2:    #22c55e;
    --red:       #ff4466;
    --red2:      #ef4444;
    --yellow:    #ffcc00;
    --blue:      #4488ff;
    --purple:    #a855f7;
    --cyan:      #00d4ff;
    --orange:    #ff8844;
    --text:      #e2e8f0;
    --muted:     #64748b;
    --muted2:    #94a3b8;
}

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}

.stApp { background: var(--bg) !important; }

/* Hide streamlit defaults */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1rem 2rem 2rem 2rem !important; max-width: 100% !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--bg2) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: var(--bg2) !important;
    border-bottom: 1px solid var(--border) !important;
    border-radius: 10px 10px 0 0;
    gap: 0;
    padding: 0 1rem;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--muted) !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    letter-spacing: 0.5px !important;
    padding: 12px 20px !important;
    border-bottom: 3px solid transparent !important;
}
.stTabs [aria-selected="true"] {
    color: var(--cyan) !important;
    border-bottom: 3px solid var(--cyan) !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: transparent !important;
    padding-top: 1.5rem !important;
}

/* Metrics */
[data-testid="metric-container"] {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 1rem !important;
}
[data-testid="stMetricValue"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 1.6rem !important;
    font-weight: 500 !important;
}
[data-testid="stMetricLabel"] {
    font-size: 11px !important;
    text-transform: uppercase !important;
    letter-spacing: 2px !important;
    color: var(--muted) !important;
}

/* Selectbox, inputs */
.stSelectbox > div > div,
.stTextInput > div > div {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #4488ff, #00d4ff) !important;
    color: #000 !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    letter-spacing: 0.5px !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

/* DataFrames */
[data-testid="stDataFrame"] { border-radius: 10px !important; overflow: hidden !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg2); }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }

/* Custom cards */
.ai-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.8rem;
    transition: border-color 0.2s;
}
.ai-card:hover { border-color: var(--border2); }

.signal-buy  { border-left: 4px solid var(--green) !important; }
.signal-sell { border-left: 4px solid var(--red) !important; }
.signal-hold { border-left: 4px solid var(--yellow) !important; }

.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}
.badge-buy    { background: rgba(0,255,136,0.15); color: #00ff88; border: 1px solid rgba(0,255,136,0.3); }
.badge-sell   { background: rgba(255,68,102,0.15); color: #ff4466; border: 1px solid rgba(255,68,102,0.3); }
.badge-hold   { background: rgba(255,204,0,0.15);  color: #ffcc00; border: 1px solid rgba(255,204,0,0.3); }
.badge-bull   { background: rgba(0,255,136,0.15); color: #00ff88; }
.badge-bear   { background: rgba(255,68,102,0.15); color: #ff4466; }
.badge-neutral{ background: rgba(255,204,0,0.15);  color: #ffcc00; }

.regime-bull   { color: #00ff88; font-weight: 800; font-size: 1.1rem; }
.regime-bear   { color: #ff4466; font-weight: 800; font-size: 1.1rem; }
.regime-neutral{ color: #ffcc00; font-weight: 800; font-size: 1.1rem; }

.section-label {
    font-size: 10px;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 12px;
    font-family: 'DM Mono', monospace;
}

.conf-bar-bg {
    background: var(--bg3);
    border-radius: 4px;
    height: 6px;
    margin-top: 6px;
    overflow: hidden;
}

.stat-num {
    font-family: 'DM Mono', monospace;
    font-size: 2rem;
    font-weight: 500;
    line-height: 1;
}

.ticker-price {
    font-family: 'DM Mono', monospace;
    font-size: 1.1rem;
    color: var(--cyan);
}

.news-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
}

.pnl-positive { color: var(--green); font-family: 'DM Mono', monospace; font-weight: 600; }
.pnl-negative { color: var(--red);   font-family: 'DM Mono', monospace; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ── Data loaders ──────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_signals():
    try:
        r = supabase.table("signals").select("*").order(
            "created_at", desc=True
        ).limit(500).execute()
        return pd.DataFrame(r.data) if r.data else pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_news():
    try:
        r = supabase.table("news").select("*").order(
            "created_at", desc=True
        ).limit(200).execute()
        return pd.DataFrame(r.data) if r.data else pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_portfolio():
    try:
        r = supabase.table("stocks").select("*").eq(
            "in_portfolio", True
        ).execute()
        return r.data if r.data else []
    except:
        return []

@st.cache_data(ttl=600)
def load_market_regime():
    try:
        from market_regime import get_market_regime
        regime, score, details = get_market_regime()
        return regime, score, details
    except:
        return "UNKNOWN", 0, {}

@st.cache_data(ttl=3600)
def load_nifty_data():
    try:
        df = yf.Ticker("^NSEI").history(period="6mo", interval="1d")
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_index_prices():
    indices = {
        "NIFTY 50":    "^NSEI",
        "SENSEX":      "^BSESN",
        "BANK NIFTY":  "^NSEBANK",
        "NIFTY IT":    "^CNXIT",
    }
    results = {}
    for name, ticker in indices.items():
        try:
            df = yf.Ticker(ticker).history(period="2d", interval="1d")
            if not df.empty:
                curr  = float(df["Close"].iloc[-1])
                prev  = float(df["Close"].iloc[-2]) if len(df) > 1 else curr
                chg   = ((curr - prev) / prev) * 100
                results[name] = {"price": curr, "change": chg}
        except:
            pass
    return results

@st.cache_data(ttl=600)
def load_sector_performance():
    sectors = {
        "Banking":  ["HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","AXISBANK.NS","KOTAKBANK.NS"],
        "IT":       ["TCS.NS","INFY.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS"],
        "Pharma":   ["SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS","LUPIN.NS"],
        "Auto":     ["MARUTI.NS","TATAMOTORS.NS","BAJAJ-AUTO.NS","HEROMOTOCO.NS","EICHERMOT.NS"],
        "FMCG":     ["HINDUNILVR.NS","ITC.NS","NESTLEIND.NS","DABUR.NS","MARICO.NS"],
        "Metals":   ["TATASTEEL.NS","HINDALCO.NS","JSWSTEEL.NS","VEDL.NS","SAIL.NS"],
        "Energy":   ["RELIANCE.NS","ONGC.NS","NTPC.NS","POWERGRID.NS","TATAPOWER.NS"],
        "Realty":   ["DLF.NS","GODREJPROP.NS","OBEROIRLTY.NS","PRESTIGE.NS","BRIGADE.NS"],
    }
    perf = {}
    for sector, stocks in sectors.items():
        changes = []
        for sym in stocks:
            try:
                df = yf.Ticker(sym).history(period="5d", interval="1d")
                if len(df) >= 2:
                    chg = (float(df["Close"].iloc[-1]) - float(df["Close"].iloc[0])) / float(df["Close"].iloc[0]) * 100
                    changes.append(chg)
            except:
                pass
        perf[sector] = round(sum(changes)/len(changes), 2) if changes else 0
    return perf

@st.cache_data(ttl=600)
def get_stock_chart(symbol, period="3mo"):
    try:
        df = yf.Ticker(symbol).history(period=period, interval="1d")
        if df.empty:
            return None
        df["EMA9"]  = ta.trend.ema_indicator(df["Close"], window=9)
        df["EMA21"] = ta.trend.ema_indicator(df["Close"], window=21)
        df["EMA50"] = ta.trend.ema_indicator(df["Close"], window=50)
        df["RSI"]   = ta.momentum.rsi(df["Close"], window=14)
        return df
    except:
        return None

@st.cache_data(ttl=300)
def get_upcoming_events():
    try:
        from economic_calendar import get_upcoming_events as get_events
        return get_events(days_ahead=30)
    except:
        return []

# ── Helper functions ──────────────────────────────────────────────────────
def signal_color(sig):
    if str(sig).startswith("BUY"):  return "#00ff88"
    if str(sig).startswith("SELL"): return "#ff4466"
    return "#ffcc00"

def conf_bar_html(conf, color):
    return f"""
    <div class="conf-bar-bg">
        <div style="width:{min(conf,100)}%;height:6px;
                    background:{color};border-radius:4px;
                    transition:width 0.5s;"></div>
    </div>"""

def pnl_html(val, pct):
    cls = "pnl-positive" if val >= 0 else "pnl-negative"
    arrow = "▲" if val >= 0 else "▼"
    return f'<span class="{cls}">{arrow} ₹{abs(val):,.0f} ({abs(pct):.2f}%)</span>'

def format_time(ts_str):
    try:
        dt = pd.to_datetime(ts_str)
        return dt.strftime("%d %b %H:%M")
    except:
        return str(ts_str)[:16]

# ── Header ────────────────────────────────────────────────────────────────
col_logo, col_indices = st.columns([1, 3])

with col_logo:
    st.markdown("""
    <div style="padding:0.5rem 0">
        <div style="font-family:'Outfit',sans-serif;font-size:1.8rem;
                    font-weight:900;letter-spacing:-1px;
                    background:linear-gradient(135deg,#00ff88,#00d4ff,#4488ff);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
            ⚡ StockAI
        </div>
        <div style="font-size:11px;color:#64748b;letter-spacing:2px;
                    text-transform:uppercase;margin-top:-4px;">
            Indian Market Intelligence
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_indices:
    indices = load_index_prices()
    if indices:
        idx_cols = st.columns(len(indices))
        for i, (name, data) in enumerate(indices.items()):
            with idx_cols[i]:
                chg    = data["change"]
                color  = "#00ff88" if chg >= 0 else "#ff4466"
                arrow  = "▲" if chg >= 0 else "▼"
                st.markdown(f"""
                <div class="ai-card" style="padding:0.7rem 1rem;margin:0">
                    <div style="font-size:10px;color:#64748b;
                                letter-spacing:2px;text-transform:uppercase">
                        {name}</div>
                    <div style="font-family:'DM Mono',monospace;font-size:1rem;
                                font-weight:500;color:#e2e8f0">
                        {data['price']:,.0f}</div>
                    <div style="font-size:12px;color:{color};font-weight:700">
                        {arrow} {abs(chg):.2f}%</div>
                </div>
                """, unsafe_allow_html=True)

st.markdown("<hr style='border:1px solid #1e2d45;margin:0.5rem 0 1rem 0'>",
            unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "🏠  Overview",
    "📡  Signals",
    "💼  Portfolio",
    "📰  News Feed",
    "📊  Charts",
    "🔍  Screener",
    "📅  Calendar",
    "⚙️  Engine"
])

# ══════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════
with tabs[0]:

    # Market Regime Banner
    regime, regime_score, regime_details = load_market_regime()
    regime_colors = {
        "STRONG_BULL": ("#00ff88", "#064e3b", "🚀"),
        "BULL":        ("#00ff88", "#064e3b", "🟢"),
        "NEUTRAL":     ("#ffcc00", "#3d3200", "🟡"),
        "BEAR":        ("#ff4466", "#4a0010", "🔴"),
        "STRONG_BEAR": ("#ff4466", "#4a0010", "🚨"),
        "UNKNOWN":     ("#64748b", "#1e2d45", "⚪"),
    }
    rc, rbg, remoji = regime_colors.get(regime, ("#64748b","#1e2d45","⚪"))

    nifty_info = regime_details.get("nifty", {})
    vix_info   = regime_details.get("vix", {})

    st.markdown(f"""
    <div style="background:{rbg};border:1px solid {rc}33;border-radius:14px;
                padding:1.2rem 1.8rem;margin-bottom:1.5rem;
                display:flex;align-items:center;justify-content:space-between;
                flex-wrap:wrap;gap:1rem">
        <div>
            <div style="font-size:11px;letter-spacing:3px;color:{rc}88;
                        text-transform:uppercase;font-family:'DM Mono',monospace">
                Market Regime</div>
            <div style="font-size:1.8rem;font-weight:900;color:{rc};
                        font-family:'Outfit',sans-serif;letter-spacing:-1px">
                {remoji} {regime.replace('_',' ')}</div>
            <div style="font-size:12px;color:{rc}99;margin-top:2px">
                Score: {regime_score:+.3f} &nbsp;|&nbsp;
                Nifty RSI: {nifty_info.get('rsi',0):.1f} &nbsp;|&nbsp;
                VIX: {vix_info.get('current',0):.1f}
            </div>
        </div>
        <div style="display:flex;gap:1.5rem;flex-wrap:wrap">
            <div style="text-align:center">
                <div style="font-size:10px;color:{rc}88;letter-spacing:2px;
                            text-transform:uppercase">Nifty 1M</div>
                <div style="font-family:'DM Mono',monospace;font-size:1.1rem;
                            color:{'#00ff88' if nifty_info.get('ret_1m',0)>=0 else '#ff4466'};
                            font-weight:600">
                    {nifty_info.get('ret_1m',0):+.2f}%</div>
            </div>
            <div style="text-align:center">
                <div style="font-size:10px;color:{rc}88;letter-spacing:2px;
                            text-transform:uppercase">Nifty 3M</div>
                <div style="font-family:'DM Mono',monospace;font-size:1.1rem;
                            color:{'#00ff88' if nifty_info.get('ret_3m',0)>=0 else '#ff4466'};
                            font-weight:600">
                    {nifty_info.get('ret_3m',0):+.2f}%</div>
            </div>
            <div style="text-align:center">
                <div style="font-size:10px;color:{rc}88;letter-spacing:2px;
                            text-transform:uppercase">VIX vs Avg</div>
                <div style="font-family:'DM Mono',monospace;font-size:1.1rem;
                            color:{'#ff4466' if vix_info.get('current',0)>vix_info.get('avg',20) else '#00ff88'};
                            font-weight:600">
                    {vix_info.get('current',0):.1f} / {vix_info.get('avg',0):.1f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Signal Summary Metrics
    signals_df = load_signals()
    news_df    = load_news()
    portfolio  = load_portfolio()

    latest = pd.DataFrame()
    if not signals_df.empty:
        latest = signals_df.drop_duplicates(subset="symbol", keep="first")

    buy_count  = len(latest[latest["signal"].str.startswith("BUY")])  if not latest.empty else 0
    sell_count = len(latest[latest["signal"].str.startswith("SELL")]) if not latest.empty else 0
    hold_count = len(latest[latest["signal"].str.startswith("HOLD")]) if not latest.empty else 0
    avg_conf   = round(latest["confidence"].mean(), 1) if not latest.empty else 0
    bull_news  = len(news_df[news_df["sentiment"]=="BULLISH"]) if not news_df.empty else 0
    bear_news  = len(news_df[news_df["sentiment"]=="BEARISH"]) if not news_df.empty else 0

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1:
        st.metric("🟢 BUY Signals",  buy_count)
    with m2:
        st.metric("🔴 SELL Signals", sell_count)
    with m3:
        st.metric("🟡 HOLD Signals", hold_count)
    with m4:
        st.metric("📊 Avg Confidence", f"{avg_conf}%")
    with m5:
        st.metric("📰 Bullish News", bull_news)
    with m6:
        st.metric("📰 Bearish News", bear_news)

    st.markdown("<br>", unsafe_allow_html=True)

    # Two columns — Nifty chart + Sector heatmap
    col_chart, col_heat = st.columns([3, 2])

    with col_chart:
        st.markdown('<div class="section-label">Nifty 50 — 6 Month Chart</div>',
                    unsafe_allow_html=True)
        nifty_df = load_nifty_data()
        if not nifty_df.empty:
            nifty_df["EMA50"]  = ta.trend.ema_indicator(nifty_df["Close"], window=50)
            nifty_df["EMA200"] = ta.trend.ema_indicator(nifty_df["Close"], window=200)

            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=nifty_df.index,
                open=nifty_df["Open"], high=nifty_df["High"],
                low=nifty_df["Low"],   close=nifty_df["Close"],
                increasing_line_color="#00ff88",
                decreasing_line_color="#ff4466",
                name="Nifty",
                showlegend=False
            ))
            fig.add_trace(go.Scatter(
                x=nifty_df.index, y=nifty_df["EMA50"],
                line=dict(color="#4488ff", width=1.5),
                name="EMA 50"
            ))
            fig.add_trace(go.Scatter(
                x=nifty_df.index, y=nifty_df["EMA200"],
                line=dict(color="#ff8844", width=1.5),
                name="EMA 200"
            ))
            fig.update_layout(
                height=320, paper_bgcolor="transparent",
                plot_bgcolor="#0d1117",
                xaxis=dict(showgrid=False, color="#64748b",
                           rangeslider=dict(visible=False)),
                yaxis=dict(showgrid=True, gridcolor="#1e2d45",
                           color="#64748b"),
                legend=dict(bgcolor="transparent", font=dict(color="#94a3b8")),
                margin=dict(l=0, r=0, t=0, b=0),
                font=dict(family="DM Mono")
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_heat:
        st.markdown('<div class="section-label">Sector Performance — 5 Day</div>',
                    unsafe_allow_html=True)
        sector_perf = load_sector_performance()
        if sector_perf:
            sectors  = list(sector_perf.keys())
            perfs    = list(sector_perf.values())
            colors   = ["#00ff88" if p >= 0 else "#ff4466" for p in perfs]

            fig2 = go.Figure(go.Bar(
                x=perfs, y=sectors,
                orientation="h",
                marker_color=colors,
                text=[f"{p:+.2f}%" for p in perfs],
                textposition="outside",
                textfont=dict(color="#e2e8f0", size=11, family="DM Mono")
            ))
            fig2.update_layout(
                height=320, paper_bgcolor="transparent",
                plot_bgcolor="#0d1117",
                xaxis=dict(showgrid=True, gridcolor="#1e2d45",
                           color="#64748b", zeroline=True,
                           zerolinecolor="#243350"),
                yaxis=dict(showgrid=False, color="#e2e8f0"),
                margin=dict(l=0, r=60, t=0, b=0),
                font=dict(family="DM Mono", color="#94a3b8")
            )
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Recent strong signals
    st.markdown('<div class="section-label">Recent Strong Signals</div>',
                unsafe_allow_html=True)

    if not latest.empty:
        strong = latest[
            latest["confidence"] >= 30
        ].sort_values("confidence", ascending=False).head(6)

        if not strong.empty:
            sig_cols = st.columns(3)
            for idx, (_, row) in enumerate(strong.iterrows()):
                sig   = str(row.get("signal",""))
                conf  = float(row.get("confidence", 0))
                color = signal_color(sig)
                cls   = ("signal-buy" if sig.startswith("BUY")
                         else "signal-sell" if sig.startswith("SELL")
                         else "signal-hold")
                badge = ("badge-buy" if sig.startswith("BUY")
                         else "badge-sell" if sig.startswith("SELL")
                         else "badge-hold")

                with sig_cols[idx % 3]:
                    st.markdown(f"""
                    <div class="ai-card {cls}">
                        <div style="display:flex;justify-content:space-between;
                                    align-items:center;margin-bottom:6px">
                            <div style="font-weight:700;font-size:14px">
                                {str(row.get('symbol','')).replace('.NS','')}</div>
                            <span class="badge {badge}">{sig.split()[0]}</span>
                        </div>
                        <div style="display:flex;justify-content:space-between;
                                    align-items:center">
                            <div class="ticker-price">
                                ₹{float(row.get('price',0)):,.1f}</div>
                            <div style="font-family:'DM Mono',monospace;
                                        font-size:12px;color:{color}">
                                {conf:.1f}%</div>
                        </div>
                        {conf_bar_html(conf, color)}
                        <div style="font-size:10px;color:#64748b;margin-top:6px">
                            RSI: {float(row.get('rsi',0)):.1f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No strong signals right now — market is in BEAR mode")
    else:
        st.info("No signal data available yet. Run the engine first.")

# ══════════════════════════════════════════════════════════════════════════
# TAB 2 — SIGNALS
# ══════════════════════════════════════════════════════════════════════════
with tabs[1]:
    signals_df = load_signals()

    if signals_df.empty:
        st.info("No signals yet. Run the engine from the Engine tab.")
    else:
        latest = signals_df.drop_duplicates(subset="symbol", keep="first")

        # Filters
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            sig_filter = st.selectbox("Signal", ["All","BUY","SELL","HOLD"])
        with fc2:
            min_conf = st.slider("Min Confidence %", 0, 100, 0)
        with fc3:
            sort_by = st.selectbox("Sort by",
                                   ["Confidence ↓","Confidence ↑","RSI ↓","RSI ↑","Symbol"])
        with fc4:
            search = st.text_input("Search symbol", placeholder="e.g. SBIN")

        # Apply filters
        filtered = latest.copy()
        if sig_filter != "All":
            filtered = filtered[filtered["signal"].str.startswith(sig_filter)]
        filtered = filtered[filtered["confidence"] >= min_conf]
        if search:
            filtered = filtered[
                filtered["symbol"].str.contains(search.upper(), na=False)
            ]

        sort_map = {
            "Confidence ↓": ("confidence", False),
            "Confidence ↑": ("confidence", True),
            "RSI ↓":        ("rsi", False),
            "RSI ↑":        ("rsi", True),
            "Symbol":       ("symbol", True),
        }
        col_s, asc_s = sort_map[sort_by]
        if col_s in filtered.columns:
            filtered = filtered.sort_values(col_s, ascending=asc_s)

        st.markdown(f"""
        <div style="font-size:12px;color:#64748b;margin-bottom:1rem">
            Showing <b style="color:#e2e8f0">{len(filtered)}</b> signals
            out of {len(latest)} total
        </div>
        """, unsafe_allow_html=True)

        # Signal cards grid
        buy_s  = filtered[filtered["signal"].str.startswith("BUY")]
        sell_s = filtered[filtered["signal"].str.startswith("SELL")]
        hold_s = filtered[
            ~filtered["signal"].str.startswith("BUY") &
            ~filtered["signal"].str.startswith("SELL")
        ]

        for label, subset, cls, badge in [
            ("🟢 BUY Signals",  buy_s,  "signal-buy",  "badge-buy"),
            ("🔴 SELL Signals", sell_s, "signal-sell", "badge-sell"),
            ("🟡 HOLD Signals", hold_s, "signal-hold", "badge-hold"),
        ]:
            if len(subset) == 0:
                continue
            st.markdown(f"""
            <div style="font-size:11px;letter-spacing:3px;color:#64748b;
                        text-transform:uppercase;margin:1.2rem 0 0.6rem 0;
                        font-family:'DM Mono',monospace">
                {label} ({len(subset)})</div>
            """, unsafe_allow_html=True)

            cols = st.columns(4)
            for i, (_, row) in enumerate(subset.iterrows()):
                sig   = str(row.get("signal",""))
                conf  = float(row.get("confidence", 0))
                color = signal_color(sig)
                reason = str(row.get("reason",""))[:80] + "..." if len(str(row.get("reason",""))) > 80 else str(row.get("reason",""))

                with cols[i % 4]:
                    st.markdown(f"""
                    <div class="ai-card {cls}">
                        <div style="display:flex;justify-content:space-between;
                                    align-items:center;margin-bottom:8px">
                            <div style="font-weight:700;font-size:15px">
                                {str(row.get('symbol','')).replace('.NS','')}</div>
                            <span class="badge {badge}">{sig.split()[0]}</span>
                        </div>
                        <div class="ticker-price" style="margin-bottom:4px">
                            ₹{float(row.get('price',0)):,.2f}</div>
                        <div style="display:flex;justify-content:space-between;
                                    font-size:12px;color:#94a3b8;margin-bottom:4px">
                            <span>RSI: {float(row.get('rsi',0)):.1f}</span>
                            <span style="color:{color};font-weight:700">
                                {conf:.1f}%</span>
                        </div>
                        {conf_bar_html(conf, color)}
                        <div style="font-size:10px;color:#475569;margin-top:8px;
                                    line-height:1.4">{reason}</div>
                        <div style="font-size:10px;color:#334155;margin-top:4px">
                            {format_time(row.get('created_at',''))}</div>
                    </div>
                    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# TAB 3 — PORTFOLIO
# ══════════════════════════════════════════════════════════════════════════
with tabs[2]:
    portfolio = load_portfolio()

    if not portfolio:
        st.markdown("""
        <div class="ai-card" style="text-align:center;padding:3rem">
            <div style="font-size:3rem;margin-bottom:1rem">💼</div>
            <div style="font-size:1.1rem;font-weight:600;margin-bottom:0.5rem">
                No holdings yet</div>
            <div style="color:#64748b;font-size:13px">
                Add stocks using the form in the sidebar</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        rows         = []
        total_inv    = 0
        total_curr   = 0

        for h in portfolio:
            try:
                sym = h["symbol"]
                bp  = float(h.get("buy_price", 0))
                qty = float(h.get("quantity", 0))
                if not bp or not qty:
                    continue
                df  = yf.Ticker(sym).history(period="5d")
                cp  = float(df["Close"].iloc[-1]) if not df.empty else bp
                pnl_rs  = (cp - bp) * qty
                pnl_pct = (cp - bp) / bp * 100
                wk_chg  = (cp - float(df["Close"].iloc[0])) / float(df["Close"].iloc[0]) * 100 if len(df) > 1 else 0
                total_inv  += bp * qty
                total_curr += cp * qty
                rows.append({
                    "symbol": sym.replace(".NS","").replace(".BO",""),
                    "buy":    bp, "current": cp, "qty": int(qty),
                    "pnl_rs": pnl_rs, "pnl_pct": pnl_pct,
                    "week":   wk_chg, "value": cp * qty
                })
            except:
                pass

        total_pnl     = total_curr - total_inv
        total_pnl_pct = (total_pnl / total_inv * 100) if total_inv else 0

        # Summary metrics
        p1, p2, p3, p4 = st.columns(4)
        pnl_color = "#00ff88" if total_pnl >= 0 else "#ff4466"
        with p1:
            st.metric("💰 Invested",    f"₹{total_inv:,.0f}")
        with p2:
            st.metric("📈 Current",     f"₹{total_curr:,.0f}")
        with p3:
            st.metric("💹 Total P&L",
                      f"₹{total_pnl:+,.0f}",
                      delta=f"{total_pnl_pct:+.2f}%")
        with p4:
            st.metric("🎯 Holdings",    len(rows))

        if rows:
            st.markdown("<br>", unsafe_allow_html=True)
            ch1, ch2 = st.columns([2, 1])

            with ch1:
                st.markdown('<div class="section-label">Holdings Detail</div>',
                            unsafe_allow_html=True)
                for r in sorted(rows, key=lambda x: x["pnl_pct"], reverse=True):
                    pc = "#00ff88" if r["pnl_pct"] >= 0 else "#ff4466"
                    wc = "#00ff88" if r["week"]    >= 0 else "#ff4466"
                    st.markdown(f"""
                    <div class="ai-card" style="border-left:4px solid {pc}">
                        <div style="display:flex;justify-content:space-between;
                                    align-items:center;flex-wrap:wrap;gap:0.5rem">
                            <div>
                                <div style="font-weight:700;font-size:16px">
                                    {r['symbol']}</div>
                                <div style="font-size:12px;color:#64748b">
                                    {r['qty']} shares &nbsp;·&nbsp;
                                    Buy: ₹{r['buy']:,.2f}
                                </div>
                            </div>
                            <div style="text-align:right">
                                <div class="ticker-price">₹{r['current']:,.2f}</div>
                                <div style="font-family:'DM Mono',monospace;
                                            font-size:13px;color:{pc};font-weight:700">
                                    {'+' if r['pnl_pct']>=0 else ''}{r['pnl_pct']:.2f}%
                                    &nbsp;(₹{r['pnl_rs']:+,.0f})</div>
                            </div>
                            <div style="text-align:right">
                                <div style="font-size:10px;color:#64748b">
                                    This week</div>
                                <div style="font-family:'DM Mono',monospace;
                                            font-size:13px;color:{wc};font-weight:600">
                                    {r['week']:+.2f}%</div>
                            </div>
                            <div style="text-align:right">
                                <div style="font-size:10px;color:#64748b">
                                    Value</div>
                                <div style="font-family:'DM Mono',monospace;
                                            font-size:13px;color:#e2e8f0">
                                    ₹{r['value']:,.0f}</div>
                            </div>
                        </div>
                        {conf_bar_html(min(abs(r['pnl_pct'])*5,100), pc)}
                    </div>
                    """, unsafe_allow_html=True)
                    # Trade levels
                    sl  = round(r['current'] * 0.97, 2)
                    t1  = round(r['current'] * 1.04, 2)
                    t2  = round(r['current'] * 1.08, 2)
                    sl_pct = -3.0
                    t1_pct = 4.0
                    t2_pct = 8.0
                    st.markdown(f"""
                    <div style="display:flex;gap:8px;margin-top:6px;flex-wrap:wrap">
                        <div style="background:#4a001022;border:1px solid #ff446633;
                                    border-radius:6px;padding:4px 10px;font-size:11px">
                            <span style="color:#64748b">Stop Loss</span>
                            <span style="color:#ff4466;font-family:'DM Mono',monospace;
                                         font-weight:700;margin-left:6px">
                                ₹{sl} ({sl_pct}%)</span>
                        </div>
                        <div style="background:#06400022;border:1px solid #00ff8833;
                                    border-radius:6px;padding:4px 10px;font-size:11px">
                            <span style="color:#64748b">T1</span>
                            <span style="color:#00ff88;font-family:'DM Mono',monospace;
                                         font-weight:700;margin-left:6px">
                                ₹{t1} (+{t1_pct}%)</span>
                        </div>
                        <div style="background:#06400022;border:1px solid #00ff8833;
                                    border-radius:6px;padding:4px 10px;font-size:11px">
                            <span style="color:#64748b">T2</span>
                            <span style="color:#00ff88;font-family:'DM Mono',monospace;
                                         font-weight:700;margin-left:6px">
                                ₹{t2} (+{t2_pct}%)</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            with ch2:
                st.markdown('<div class="section-label">Allocation</div>',
                            unsafe_allow_html=True)
                labels = [r["symbol"] for r in rows]
                values = [r["value"]  for r in rows]
                colors_pie = [
                    "#00ff88","#4488ff","#ff8844","#a855f7",
                    "#00d4ff","#ffcc00","#ff4466","#22c55e"
                ]
                fig_pie = go.Figure(go.Pie(
                    labels=labels, values=values,
                    hole=0.6,
                    marker_colors=colors_pie[:len(labels)],
                    textinfo="label+percent",
                    textfont=dict(family="DM Mono", size=11, color="#e2e8f0"),
                    hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<extra></extra>"
                ))
                fig_pie.add_annotation(
                    text=f"₹{total_curr:,.0f}",
                    x=0.5, y=0.5, font_size=14,
                    font_color="#e2e8f0",
                    font_family="DM Mono",
                    showarrow=False
                )
                fig_pie.update_layout(
                    height=320, paper_bgcolor="transparent",
                    showlegend=False,
                    margin=dict(l=0, r=0, t=0, b=0)
                )
                st.plotly_chart(fig_pie, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════
# TAB 4 — NEWS FEED
# ══════════════════════════════════════════════════════════════════════════
with tabs[3]:
    news_df = load_news()

    if news_df.empty:
        st.info("No news data yet.")
    else:
        nc1, nc2, nc3 = st.columns(3)
        with nc1:
            sent_filter = st.selectbox("Sentiment",
                                       ["All","BULLISH","BEARISH","NEUTRAL"])
        with nc2:
            sym_filter = st.text_input("Stock Symbol",
                                       placeholder="e.g. RELIANCE")
        with nc3:
            source_filter = st.selectbox(
                "Source",
                ["All"] + list(news_df["source"].dropna().unique())
                if "source" in news_df.columns else ["All"]
            )

        filtered_news = news_df.copy()
        if sent_filter != "All":
            filtered_news = filtered_news[
                filtered_news["sentiment"] == sent_filter
            ]
        if sym_filter:
            filtered_news = filtered_news[
                filtered_news["related_symbol"].str.contains(
                    sym_filter.upper(), na=False
                )
            ]
        if source_filter != "All" and "source" in filtered_news.columns:
            filtered_news = filtered_news[
                filtered_news["source"] == source_filter
            ]

        bull = len(news_df[news_df["sentiment"]=="BULLISH"])
        bear = len(news_df[news_df["sentiment"]=="BEARISH"])
        neut = len(news_df[news_df["sentiment"]=="NEUTRAL"])
        total_news = len(news_df)

        # Sentiment bar
        st.markdown(f"""
        <div class="ai-card" style="margin-bottom:1.2rem">
            <div style="display:flex;justify-content:space-between;
                        margin-bottom:8px;font-size:12px;color:#94a3b8">
                <span>🟢 Bullish: {bull} ({bull/total_news*100:.0f}%)</span>
                <span>🟡 Neutral: {neut} ({neut/total_news*100:.0f}%)</span>
                <span>🔴 Bearish: {bear} ({bear/total_news*100:.0f}%)</span>
            </div>
            <div style="display:flex;height:8px;border-radius:4px;overflow:hidden">
                <div style="width:{bull/total_news*100}%;background:#00ff88"></div>
                <div style="width:{neut/total_news*100}%;background:#ffcc00"></div>
                <div style="width:{bear/total_news*100}%;background:#ff4466"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        for _, row in filtered_news.head(50).iterrows():
            sent  = str(row.get("sentiment","NEUTRAL"))
            score = float(row.get("sentiment_score", 0))
            sc    = {"BULLISH":"#00ff88","BEARISH":"#ff4466"}.get(sent,"#ffcc00")
            badge = {"BULLISH":"badge-bull","BEARISH":"badge-bear"}.get(
                sent,"badge-neutral")
            sym   = str(row.get("related_symbol","GENERAL")).replace(".NS","")
            src   = str(row.get("source",""))
            hl    = str(row.get("headline",""))

            st.markdown(f"""
            <div class="news-card">
                <div style="display:flex;justify-content:space-between;
                            align-items:flex-start;gap:0.5rem;flex-wrap:wrap">
                    <div style="flex:1;min-width:200px">
                        <div style="font-size:13px;font-weight:500;
                                    line-height:1.5;margin-bottom:6px">{hl}</div>
                        <div style="font-size:11px;color:#475569">
                            {src} &nbsp;·&nbsp; {sym}
                            &nbsp;·&nbsp; {format_time(row.get('published_at',''))}</div>
                    </div>
                    <div style="text-align:right;flex-shrink:0">
                        <span class="badge {badge}">{sent}</span>
                        <div style="font-family:'DM Mono',monospace;
                                    font-size:12px;color:{sc};
                                    margin-top:4px">{score:+.3f}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# TAB 5 — CHARTS
# ══════════════════════════════════════════════════════════════════════════
with tabs[4]:
    signals_df = load_signals()
    symbols    = []
    if not signals_df.empty:
        symbols = sorted(
            signals_df["symbol"].dropna().unique().tolist()
        )

    if not symbols:
        symbols = ["RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS"]

    cc1, cc2 = st.columns([2, 1])
    with cc1:
        chart_sym = st.selectbox("Select Stock", symbols,
                                 format_func=lambda x: x.replace(".NS",""))
    with cc2:
        chart_period = st.selectbox("Period",
                                    ["1mo","3mo","6mo","1y"],
                                    index=1)

    df_chart = get_stock_chart(chart_sym, chart_period)

    if df_chart is not None and not df_chart.empty:
        fig_c = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            row_heights=[0.6, 0.2, 0.2],
            vertical_spacing=0.04
        )

        # Candlestick
        fig_c.add_trace(go.Candlestick(
            x=df_chart.index,
            open=df_chart["Open"],  high=df_chart["High"],
            low=df_chart["Low"],    close=df_chart["Close"],
            increasing_line_color="#00ff88",
            decreasing_line_color="#ff4466",
            name="Price", showlegend=False
        ), row=1, col=1)

        for ema, color, width in [
            ("EMA9",  "#4488ff", 1.2),
            ("EMA21", "#ffcc00", 1.2),
            ("EMA50", "#ff8844", 1.5),
        ]:
            fig_c.add_trace(go.Scatter(
                x=df_chart.index, y=df_chart[ema],
                line=dict(color=color, width=width),
                name=ema
            ), row=1, col=1)

        # Volume
        vol_colors = [
            "#00ff88" if c >= o else "#ff4466"
            for c, o in zip(df_chart["Close"], df_chart["Open"])
        ]
        fig_c.add_trace(go.Bar(
            x=df_chart.index, y=df_chart["Volume"],
            marker_color=vol_colors, name="Volume",
            showlegend=False
        ), row=2, col=1)

        # RSI
        rsi_colors = []
        for r in df_chart["RSI"].fillna(50):
            if r >= 70:   rsi_colors.append("#ff4466")
            elif r <= 30: rsi_colors.append("#00ff88")
            else:         rsi_colors.append("#4488ff")

        fig_c.add_trace(go.Scatter(
            x=df_chart.index, y=df_chart["RSI"],
            line=dict(color="#a855f7", width=1.5),
            name="RSI", showlegend=False
        ), row=3, col=1)
        fig_c.add_hline(y=70, line=dict(color="#ff446644", dash="dot"),
                        row=3, col=1)
        fig_c.add_hline(y=30, line=dict(color="#00ff8844", dash="dot"),
                        row=3, col=1)

        fig_c.update_layout(
            height=600, paper_bgcolor="transparent",
            plot_bgcolor="#0d1117",
            xaxis=dict(showgrid=False, color="#64748b",
                       rangeslider=dict(visible=False)),
            xaxis2=dict(showgrid=False, color="#64748b"),
            xaxis3=dict(showgrid=False, color="#64748b"),
            yaxis=dict(showgrid=True, gridcolor="#1e2d45", color="#64748b"),
            yaxis2=dict(showgrid=True, gridcolor="#1e2d45", color="#64748b"),
            yaxis3=dict(showgrid=True, gridcolor="#1e2d45", color="#64748b",
                        range=[0,100]),
            legend=dict(bgcolor="transparent", font=dict(color="#94a3b8"),
                        orientation="h", y=1.02),
            margin=dict(l=0, r=0, t=10, b=0),
            font=dict(family="DM Mono", color="#64748b")
        )
        st.plotly_chart(fig_c, use_container_width=True)

        # Latest stats bar
        latest_row = df_chart.iloc[-1]
        s1,s2,s3,s4,s5 = st.columns(5)
        with s1: st.metric("Close",  f"₹{latest_row['Close']:,.2f}")
        with s2: st.metric("RSI",    f"{latest_row['RSI']:.1f}")
        with s3: st.metric("EMA 9",  f"₹{latest_row['EMA9']:,.2f}")
        with s4: st.metric("EMA 21", f"₹{latest_row['EMA21']:,.2f}")
        with s5: st.metric("EMA 50", f"₹{latest_row['EMA50']:,.2f}")

# ══════════════════════════════════════════════════════════════════════════
# TAB 6 — SCREENER
# ══════════════════════════════════════════════════════════════════════════
with tabs[5]:
    signals_df = load_signals()

    if signals_df.empty:
        st.info("No signal data available.")
    else:
        latest = signals_df.drop_duplicates(subset="symbol", keep="first")

        st.markdown('<div class="section-label">Stock Screener</div>',
                    unsafe_allow_html=True)

        sc1, sc2, sc3, sc4, sc5 = st.columns(5)
        with sc1:
            scr_sig = st.selectbox("Signal Type",
                                   ["All","BUY","SELL","HOLD"],
                                   key="scr_sig")
        with sc2:
            scr_conf = st.slider("Min Confidence", 0, 100, 0, key="scr_conf")
        with sc3:
            scr_rsi_min = st.slider("RSI Min", 0, 100, 0, key="scr_rsi_min")
        with sc4:
            scr_rsi_max = st.slider("RSI Max", 0, 100, 100, key="scr_rsi_max")
        with sc5:
            scr_sort = st.selectbox("Sort By",
                                    ["Confidence","RSI","Price","Symbol"],
                                    key="scr_sort")

        screened = latest.copy()
        if scr_sig != "All":
            screened = screened[screened["signal"].str.startswith(scr_sig)]
        screened = screened[screened["confidence"] >= scr_conf]
        if "rsi" in screened.columns:
            screened = screened[
                (screened["rsi"] >= scr_rsi_min) &
                (screened["rsi"] <= scr_rsi_max)
            ]

        sort_col = {
            "Confidence": "confidence",
            "RSI":        "rsi",
            "Price":      "price",
            "Symbol":     "symbol"
        }.get(scr_sort, "confidence")
        if sort_col in screened.columns:
            screened = screened.sort_values(sort_col, ascending=False)

        st.markdown(f"""
        <div style="font-size:12px;color:#64748b;margin-bottom:1rem">
            <b style="color:#e2e8f0">{len(screened)}</b> stocks match your filters
        </div>
        """, unsafe_allow_html=True)

        if not screened.empty:
            display = screened[[
                c for c in ["symbol","signal","price","confidence","rsi","macd"]
                if c in screened.columns
            ]].copy()
            display["symbol"] = display["symbol"].str.replace(".NS","").str.replace(".BO","")
            display.columns = [c.upper() for c in display.columns]

            st.dataframe(
                display.style.applymap(
                    lambda v: "color: #00ff88; font-weight: bold"
                    if str(v).startswith("BUY")
                    else ("color: #ff4466; font-weight: bold"
                          if str(v).startswith("SELL") else ""),
                    subset=["SIGNAL"] if "SIGNAL" in display.columns else []
                ).format({
                    "PRICE":      "₹{:,.2f}",
                    "CONFIDENCE": "{:.1f}%",
                    "RSI":        "{:.1f}",
                }),
                use_container_width=True,
                height=500
            )

# ══════════════════════════════════════════════════════════════════════════
# TAB 7 — CALENDAR
# ══════════════════════════════════════════════════════════════════════════
with tabs[6]:
    events = get_upcoming_events()

    st.markdown('<div class="section-label">Economic Calendar — Next 30 Days</div>',
                unsafe_allow_html=True)

    impact_styles = {
        "EXTREME": ("#ff4466", "#4a0010", "🚨"),
        "HIGH":    ("#ff8844", "#3d1f00", "⚠️"),
        "MEDIUM":  ("#ffcc00", "#3d3200", "🟡"),
        "HOLIDAY": ("#4488ff", "#001844", "🏖️"),
    }

    today = datetime.now().date()

    if not events:
        st.markdown("""
        <div class="ai-card" style="text-align:center;padding:2rem">
            <div style="font-size:2rem;margin-bottom:0.5rem">✅</div>
            <div style="color:#64748b">No major events in the next 30 days</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for e in events:
            color, bg, emoji = impact_styles.get(
                e["impact"], ("#94a3b8","#1e2d45","⚪")
            )
            days_away = e.get("days_away", 0)
            if days_away == 0:
                timing_label = "TODAY"
                timing_color = "#ff4466"
            elif days_away == 1:
                timing_label = "TOMORROW"
                timing_color = "#ff8844"
            else:
                timing_label = f"in {days_away} days"
                timing_color = "#64748b"

            st.markdown(f"""
            <div style="background:{bg};border:1px solid {color}33;
                        border-left:4px solid {color};border-radius:10px;
                        padding:1rem 1.2rem;margin-bottom:0.6rem;
                        display:flex;justify-content:space-between;
                        align-items:center;flex-wrap:wrap;gap:0.5rem">
                <div>
                    <div style="font-size:14px;font-weight:600;
                                color:{color};margin-bottom:2px">
                        {emoji} {e['event']}</div>
                    <div style="font-size:12px;color:{color}88">
                        {str(e['date'].strftime('%A, %d %B %Y')) if hasattr(e['date'],'strftime') else str(e['date'])}
                    </div>
                </div>
                <div style="text-align:right">
                    <div style="font-size:11px;letter-spacing:2px;
                                text-transform:uppercase;color:{timing_color};
                                font-family:'DM Mono',monospace;font-weight:700">
                        {timing_label}</div>
                    <span style="background:{color}22;color:{color};
                                 border:1px solid {color}44;border-radius:20px;
                                 padding:2px 10px;font-size:11px;
                                 font-weight:700;letter-spacing:1px;
                                 text-transform:uppercase">
                        {e['impact']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # RBI dates quick view
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-label">RBI Policy Dates 2026</div>',
                unsafe_allow_html=True)

    rbi_dates = [
        "2026-02-07", "2026-04-09", "2026-06-05",
        "2026-08-07", "2026-10-09", "2026-12-04"
    ]
    rbi_cols = st.columns(3)
    for i, d in enumerate(rbi_dates):
        dt       = datetime.strptime(d, "%Y-%m-%d").date()
        past     = dt < today
        color    = "#334155" if past else "#ff4466"
        bg       = "#0d1117" if past else "#4a001022"
        label    = "PAST" if past else ("UPCOMING" if dt > today else "TODAY")
        with rbi_cols[i % 3]:
            st.markdown(f"""
            <div style="background:{bg};border:1px solid {color}33;
                        border-radius:8px;padding:0.8rem 1rem;
                        margin-bottom:0.5rem;opacity:{'0.4' if past else '1'}">
                <div style="font-family:'DM Mono',monospace;font-size:13px;
                            color:{color};font-weight:600">
                    {dt.strftime('%d %B %Y')}</div>
                <div style="font-size:10px;letter-spacing:2px;color:{color}88;
                            text-transform:uppercase;margin-top:2px">
                    RBI Policy · {label}</div>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# TAB 8 — ENGINE
# ══════════════════════════════════════════════════════════════════════════
with tabs[7]:
    st.markdown('<div class="section-label">Manual Engine Controls</div>',
                unsafe_allow_html=True)

    e1, e2, e3 = st.columns(3)

    with e1:
        st.markdown("""
        <div class="ai-card signal-buy" style="text-align:center;padding:1.5rem">
            <div style="font-size:2rem;margin-bottom:0.5rem">📊</div>
            <div style="font-weight:700;margin-bottom:0.3rem">Full Engine</div>
            <div style="font-size:12px;color:#64748b;margin-bottom:1rem">
                Technical + News + ML + Risk</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("▶ Run Full Engine", use_container_width=True):
            with st.spinner("Running full analysis..."):
                try:
                    from signal_combiner import run_combiner
                    run_combiner()
                    st.success("✅ Full engine completed")
                    st.cache_data.clear()
                except Exception as ex:
                    st.error(f"❌ {ex}")

    with e2:
        st.markdown("""
        <div class="ai-card signal-hold" style="text-align:center;padding:1.5rem">
            <div style="font-size:2rem;margin-bottom:0.5rem">📰</div>
            <div style="font-weight:700;margin-bottom:0.3rem">News Scan</div>
            <div style="font-size:12px;color:#64748b;margin-bottom:1rem">
                Refresh sentiment only</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("▶ Run News Scan", use_container_width=True):
            with st.spinner("Scanning news..."):
                try:
                    from news_engine import run_news_engine
                    run_news_engine()
                    st.success("✅ News scan completed")
                    st.cache_data.clear()
                except Exception as ex:
                    st.error(f"❌ {ex}")

    with e3:
        st.markdown("""
        <div class="ai-card" style="text-align:center;padding:1.5rem">
            <div style="font-size:2rem;margin-bottom:0.5rem">🛡️</div>
            <div style="font-weight:700;margin-bottom:0.3rem">Risk Check</div>
            <div style="font-size:12px;color:#64748b;margin-bottom:1rem">
                Portfolio stop loss check</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("▶ Run Risk Check", use_container_width=True):
            with st.spinner("Checking risk levels..."):
                try:
                    from risk_manager import run_risk_check
                    run_risk_check()
                    st.success("✅ Risk check completed")
                except Exception as ex:
                    st.error(f"❌ {ex}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-label">System Status</div>',
                unsafe_allow_html=True)

    signals_df = load_signals()
    news_df    = load_news()

    last_signal = "Never"
    last_news   = "Never"
    if not signals_df.empty and "created_at" in signals_df.columns:
        last_signal = format_time(signals_df["created_at"].max())
    if not news_df.empty and "created_at" in news_df.columns:
        last_news = format_time(news_df["created_at"].max())

    ss1, ss2, ss3, ss4 = st.columns(4)
    with ss1:
        st.markdown(f"""
        <div class="ai-card">
            <div class="section-label">Last Signal Run</div>
            <div style="font-family:'DM Mono',monospace;font-size:14px;
                        color:#00d4ff">{last_signal}</div>
        </div>""", unsafe_allow_html=True)
    with ss2:
        st.markdown(f"""
        <div class="ai-card">
            <div class="section-label">Last News Scan</div>
            <div style="font-family:'DM Mono',monospace;font-size:14px;
                        color:#00d4ff">{last_news}</div>
        </div>""", unsafe_allow_html=True)
    with ss3:
        st.markdown(f"""
        <div class="ai-card">
            <div class="section-label">Total Signals</div>
            <div style="font-family:'DM Mono',monospace;font-size:14px;
                        color:#00d4ff">{len(signals_df)}</div>
        </div>""", unsafe_allow_html=True)
    with ss4:
        st.markdown(f"""
        <div class="ai-card">
            <div class="section-label">Total News Items</div>
            <div style="font-family:'DM Mono',monospace;font-size:14px;
                        color:#00d4ff">{len(news_df)}</div>
        </div>""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="font-family:'Outfit',sans-serif;font-size:1.1rem;
                font-weight:700;margin-bottom:1rem;
                background:linear-gradient(135deg,#00ff88,#00d4ff);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent">
        ⚡ StockAI Controls
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-label">Auto Refresh</div>',
                unsafe_allow_html=True)
    auto_refresh = st.toggle("Enable Auto Refresh", value=False)
    if auto_refresh:
        refresh_rate = st.selectbox("Interval", ["30s","1min","5min"], index=1)
        seconds = {"30s":30,"1min":60,"5min":300}[refresh_rate]
        st.markdown(f"""
        <meta http-equiv="refresh" content="{seconds}">
        <div style="font-size:11px;color:#64748b;margin-top:4px">
            Refreshing every {refresh_rate}</div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="section-label">Add to Portfolio</div>',
                unsafe_allow_html=True)

    add_sym = st.text_input("Symbol", placeholder="e.g. SBIN.NS")
    add_qty = st.number_input("Quantity", min_value=1, value=1)
    add_price = st.number_input("Buy Price (₹)", min_value=0.0, value=0.0)

    if st.button("➕ Add Holding", use_container_width=True):
        if add_sym and add_price > 0:
            try:
                supabase.table("stocks").upsert({
                    "symbol":       add_sym.upper(),
                    "company_name": add_sym.upper().replace(".NS",""),
                    "in_portfolio": True,
                    "buy_price":    add_price,
                    "quantity":     add_qty
                }).execute()
                st.success(f"✅ Added {add_sym}")
                st.cache_data.clear()
            except Exception as ex:
                st.error(f"❌ {ex}")

    st.markdown("---")
    st.markdown('<div class="section-label">Position Sizer</div>',
                unsafe_allow_html=True)

    ps_sym   = st.text_input("Symbol", placeholder="RELIANCE.NS", key="ps_sym")
    ps_port  = st.number_input("Portfolio Value (₹)",
                                min_value=10000, value=100000, step=10000)

    if st.button("📐 Calculate Size", use_container_width=True):
        if ps_sym:
            try:
                from risk_manager import suggest_position
                suggest_position(ps_sym, ps_port)
                st.success("Check terminal output for sizing details")
            except Exception as ex:
                st.error(f"❌ {ex}")

    st.markdown("---")
    st.markdown(f"""
    <div style="font-size:10px;color:#334155;text-align:center;
                font-family:'DM Mono',monospace">
        Last updated<br>
        {datetime.now().strftime('%d %b %Y %H:%M:%S')}
    </div>
    """, unsafe_allow_html=True)
