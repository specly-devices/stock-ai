import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import os
import yfinance as yf
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timedelta
import time

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# ── Page config ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="StockAI — Indian Market Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ───────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap');

/* Base */
html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background-color: #080C14;
    color: #E2E8F0;
}

/* Hide streamlit branding */
#MainMenu, footer, header { visibility: hidden; }

/* Main background */
.stApp {
    background: linear-gradient(135deg, #080C14 0%, #0D1421 50%, #080C14 100%);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0D1421;
    border-right: 1px solid #1E2D45;
}

/* Metric cards */
.metric-card {
    background: linear-gradient(135deg, #0D1421 0%, #111827 100%);
    border: 1px solid #1E2D45;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    transition: all 0.3s ease;
}
.metric-card:hover {
    border-color: #3B82F6;
    box-shadow: 0 0 20px rgba(59,130,246,0.15);
}

/* Signal badges */
.badge-buy {
    background: linear-gradient(135deg, #064E3B, #065F46);
    color: #34D399;
    border: 1px solid #34D399;
    border-radius: 20px;
    padding: 4px 14px;
    font-family: 'Space Mono', monospace;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
}
.badge-sell {
    background: linear-gradient(135deg, #450a0a, #5c1212);
    color: #F87171;
    border: 1px solid #F87171;
    border-radius: 20px;
    padding: 4px 14px;
    font-family: 'Space Mono', monospace;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
}
.badge-hold {
    background: linear-gradient(135deg, #1c1a05, #2d2a08);
    color: #FBBF24;
    border: 1px solid #FBBF24;
    border-radius: 20px;
    padding: 4px 14px;
    font-family: 'Space Mono', monospace;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
}

/* Section headers */
.section-header {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 11px;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #3B82F6;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid #1E2D45;
}

/* News card */
.news-card {
    background: #0D1421;
    border: 1px solid #1E2D45;
    border-left: 3px solid #3B82F6;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
}
.news-bullish { border-left-color: #34D399; }
.news-bearish { border-left-color: #F87171; }
.news-neutral { border-left-color: #6B7280; }

/* Ticker header */
.ticker-header {
    font-family: 'Space Mono', monospace;
    font-size: 28px;
    font-weight: 700;
    color: #F1F5F9;
    letter-spacing: -1px;
}

/* Live dot */
.live-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    background: #34D399;
    border-radius: 50%;
    animation: pulse 2s infinite;
    margin-right: 6px;
}
@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(1.3); }
}

/* Streamlit metric overrides */
[data-testid="metric-container"] {
    background: #0D1421;
    border: 1px solid #1E2D45;
    border-radius: 12px;
    padding: 16px;
}
[data-testid="metric-container"] label {
    color: #64748B !important;
    font-size: 11px !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: 'Space Mono', monospace !important;
    font-size: 24px !important;
    color: #F1F5F9 !important;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid #1E2D45;
    border-radius: 8px;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #0D1421;
    border-bottom: 1px solid #1E2D45;
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    color: #64748B;
    font-family: 'Syne', sans-serif;
    font-weight: 600;
    font-size: 13px;
    letter-spacing: 1px;
}
.stTabs [aria-selected="true"] {
    color: #3B82F6 !important;
    border-bottom: 2px solid #3B82F6 !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #080C14; }
::-webkit-scrollbar-thumb { background: #1E2D45; border-radius: 2px; }
</style>
""", unsafe_allow_html=True)

# ── Data loaders ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_signals():
    try:
        result = supabase.table("signals").select("*").order(
            "created_at", desc=True
        ).limit(200).execute()
        return pd.DataFrame(result.data) if result.data else pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_news():
    try:
        result = supabase.table("news").select("*").order(
            "created_at", desc=True
        ).limit(100).execute()
        return pd.DataFrame(result.data) if result.data else pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_portfolio():
    try:
        result = supabase.table("stocks").select("*").eq(
            "in_portfolio", True
        ).execute()
        return pd.DataFrame(result.data) if result.data else pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def fetch_live_price(symbol):
    try:
        ticker = yf.Ticker(symbol)
        hist   = ticker.history(period="2d", interval="1d")
        if len(hist) >= 2:
            curr  = hist["Close"].iloc[-1]
            prev  = hist["Close"].iloc[-2]
            chg   = ((curr - prev) / prev) * 100
            return round(curr, 2), round(chg, 2)
        return None, None
    except:
        return None, None

def get_latest_signals(df):
    """Get the most recent signal per symbol"""
    if df.empty:
        return df
    return df.sort_values("created_at", ascending=False).drop_duplicates(
        subset="symbol"
    )

# ── Sidebar ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding: 20px 0 10px 0;'>
        <div style='font-family: Space Mono, monospace; font-size: 20px;
                    font-weight: 700; color: #3B82F6; letter-spacing: -1px;'>
            📈 STOCK<span style='color:#F1F5F9'>AI</span>
        </div>
        <div style='font-size: 11px; color: #475569; letter-spacing: 2px;
                    text-transform: uppercase; margin-top: 4px;'>
            Indian Market Intelligence
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown("**⚙️ Controls**")

    auto_refresh = st.toggle("Auto Refresh (5 min)", value=False)
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()

    # Add stock to portfolio
    st.markdown("**➕ Add to Portfolio**")
    new_symbol   = st.text_input("Symbol (e.g. TCS.NS)")
    new_qty      = st.number_input("Quantity", min_value=1, value=10)
    new_price    = st.number_input("Buy Price (₹)", min_value=0.0, value=100.0)
    if st.button("Add Stock", use_container_width=True):
        if new_symbol:
            try:
                supabase.table("stocks").upsert({
                    "symbol":       new_symbol.upper(),
                    "in_portfolio": True,
                    "buy_price":    new_price,
                    "quantity":     new_qty
                }).execute()
                st.success(f"✅ Added {new_symbol}")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"❌ {e}")

    st.divider()
    st.markdown(
        f"<div style='font-size:11px; color:#475569;'>"
        f"Last updated<br>"
        f"<span style='font-family: Space Mono; color:#64748B;'>"
        f"{datetime.now().strftime('%H:%M:%S')}</span></div>",
        unsafe_allow_html=True
    )

# ── Main header ──────────────────────────────────────────────────────────
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown(f"""
    <div style='padding: 10px 0 20px 0;'>
        <div class='ticker-header'>
            <span class='live-dot'></span>
            Market Intelligence Dashboard
        </div>
        <div style='font-size:13px; color:#475569; margin-top:4px;'>
            NSE · BSE · {datetime.now().strftime('%A, %d %B %Y')}
        </div>
    </div>
    """, unsafe_allow_html=True)
with col_h2:
    market_time = datetime.now()
    is_market_open = (
        market_time.weekday() < 5 and
        9 <= market_time.hour < 15 or
        (market_time.hour == 15 and market_time.minute <= 30)
    )
    status_color = "#34D399" if is_market_open else "#F87171"
    status_text  = "MARKET OPEN" if is_market_open else "MARKET CLOSED"
    st.markdown(f"""
    <div style='text-align:right; padding-top:16px;'>
        <span style='background:#0D1421; border:1px solid {status_color};
                     color:{status_color}; border-radius:20px; padding:6px 16px;
                     font-family: Space Mono; font-size:11px; font-weight:700;
                     letter-spacing:2px;'>
            ● {status_text}
        </span>
    </div>
    """, unsafe_allow_html=True)

# ── Load data ────────────────────────────────────────────────────────────
signals_df  = load_signals()
news_df     = load_news()
portfolio_df = load_portfolio()
latest_signals = get_latest_signals(signals_df) if not signals_df.empty else pd.DataFrame()

# ── Top metrics ──────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Overview</div>', unsafe_allow_html=True)

m1, m2, m3, m4, m5 = st.columns(5)

if not latest_signals.empty:
    buy_count  = len(latest_signals[latest_signals["signal"].str.startswith("BUY")])
    sell_count = len(latest_signals[latest_signals["signal"].str.startswith("SELL")])
    hold_count = len(latest_signals[latest_signals["signal"].str.startswith("HOLD")])
    avg_conf   = round(latest_signals["confidence"].mean(), 1)
else:
    buy_count = sell_count = hold_count = avg_conf = 0

news_bull = len(news_df[news_df["sentiment"] == "BULLISH"]) if not news_df.empty else 0
news_bear = len(news_df[news_df["sentiment"] == "BEARISH"]) if not news_df.empty else 0

with m1:
    st.metric("🟢 BUY Signals",  buy_count)
with m2:
    st.metric("🔴 SELL Signals", sell_count)
with m3:
    st.metric("🟡 HOLD Signals", hold_count)
with m4:
    st.metric("🎯 Avg Confidence", f"{avg_conf}%")
with m5:
    sentiment_ratio = f"{news_bull}B / {news_bear}S"
    st.metric("📰 News Sentiment", sentiment_ratio)

st.divider()

# ── Tabs ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Signals", "💼 Portfolio", "📰 News Feed",
    "📈 Charts", "⚙️ Run Engine"
])

# ══════════════════════════════════════════════════════════════
# TAB 1 — SIGNALS
# ══════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-header">Latest Signals — All Stocks</div>',
                unsafe_allow_html=True)

    if latest_signals.empty:
        st.info("No signals yet. Run the engine from the ⚙️ tab.")
    else:
        # Signal filter
        col_f1, col_f2 = st.columns([2, 3])
        with col_f1:
            filter_signal = st.selectbox(
                "Filter by signal",
                ["ALL", "BUY", "SELL", "HOLD"]
            )
        with col_f2:
            min_conf = st.slider("Minimum confidence %", 0, 100, 0)

        filtered = latest_signals.copy()
        if filter_signal != "ALL":
            filtered = filtered[filtered["signal"].str.startswith(filter_signal)]
        filtered = filtered[filtered["confidence"] >= min_conf]
        filtered = filtered.sort_values("confidence", ascending=False)

        # Display as cards
        for _, row in filtered.iterrows():
            signal_type = row["signal"].split()[0]
            badge_class = {
                "BUY": "badge-buy", "SELL": "badge-sell"
            }.get(signal_type, "badge-hold")
            emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}.get(signal_type, "⚪")

            conf_color = (
                "#34D399" if row["confidence"] >= 70 else
                "#FBBF24" if row["confidence"] >= 50 else
                "#F87171"
            )

            st.markdown(f"""
            <div style='background:#0D1421; border:1px solid #1E2D45;
                        border-radius:10px; padding:16px; margin-bottom:8px;
                        display:flex; align-items:center; gap:16px;'>
                <div style='min-width:160px;'>
                    <div style='font-family:Space Mono; font-size:15px;
                                font-weight:700; color:#F1F5F9;'>
                        {row['symbol'].replace('.NS','').replace('.BO','')}
                    </div>
                    <div style='font-size:11px; color:#475569; margin-top:2px;'>
                        ₹{row['price']}
                    </div>
                </div>
                <div style='min-width:120px;'>
                    <span class='{badge_class}'>{emoji} {row['signal']}</span>
                </div>
                <div style='min-width:120px; text-align:center;'>
                    <div style='font-family:Space Mono; font-size:18px;
                                font-weight:700; color:{conf_color};'>
                        {row['confidence']}%
                    </div>
                    <div style='font-size:10px; color:#475569;'>confidence</div>
                </div>
                <div style='flex:1; font-size:12px; color:#64748B;'>
                    RSI: <span style='color:#94A3B8;'>{row['rsi']}</span> &nbsp;|&nbsp;
                    {row.get('reason','')[:120]}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Signal distribution chart
        st.divider()
        st.markdown('<div class="section-header">Signal Distribution</div>',
                    unsafe_allow_html=True)

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            signal_counts = latest_signals["signal"].apply(
                lambda x: x.split()[0]
            ).value_counts()
            fig_pie = go.Figure(go.Pie(
                labels=signal_counts.index,
                values=signal_counts.values,
                hole=0.6,
                marker_colors=["#34D399", "#F87171", "#FBBF24"],
            ))
            fig_pie.update_layout(
                paper_bgcolor="#0D1421", plot_bgcolor="#0D1421",
                font_color="#94A3B8", showlegend=True,
                legend=dict(font=dict(color="#94A3B8")),
                margin=dict(t=20, b=20, l=20, r=20),
                height=280
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_c2:
            fig_conf = px.histogram(
                latest_signals, x="confidence", nbins=10,
                color_discrete_sequence=["#3B82F6"]
            )
            fig_conf.update_layout(
                paper_bgcolor="#0D1421", plot_bgcolor="#0D1421",
                font_color="#94A3B8", xaxis_title="Confidence %",
                yaxis_title="Count",
                margin=dict(t=20, b=20, l=20, r=20),
                height=280
            )
            st.plotly_chart(fig_conf, use_container_width=True)

# ══════════════════════════════════════════════════════════════
# TAB 2 — PORTFOLIO
# ══════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-header">Your Portfolio</div>',
                unsafe_allow_html=True)

    if portfolio_df.empty:
        st.info("No stocks in portfolio. Add stocks using the sidebar.")
    else:
        total_invested = 0
        total_current  = 0
        rows = []

        for _, stock in portfolio_df.iterrows():
            live_price, change_pct = fetch_live_price(stock["symbol"])
            if live_price and stock.get("buy_price"):
                buy_p   = stock["buy_price"]
                qty     = stock.get("quantity", 0)
                invested = buy_p * qty
                current  = live_price * qty
                pnl      = current - invested
                pnl_pct  = ((live_price - buy_p) / buy_p) * 100

                total_invested += invested
                total_current  += current

                rows.append({
                    "Symbol":    stock["symbol"].replace(".NS","").replace(".BO",""),
                    "Qty":       qty,
                    "Buy ₹":     buy_p,
                    "LTP ₹":     live_price,
                    "Change %":  f"{change_pct:+.2f}%" if change_pct else "—",
                    "P&L ₹":     round(pnl, 0),
                    "P&L %":     round(pnl_pct, 2),
                    "Invested":  round(invested, 0),
                    "Current":   round(current, 0)
                })

        if rows:
            total_pnl     = total_current - total_invested
            total_pnl_pct = ((total_current - total_invested) / total_invested * 100
                             if total_invested else 0)

            pm1, pm2, pm3, pm4 = st.columns(4)
            with pm1:
                st.metric("Total Invested", f"₹{total_invested:,.0f}")
            with pm2:
                st.metric("Current Value", f"₹{total_current:,.0f}")
            with pm3:
                st.metric("Total P&L",
                          f"₹{total_pnl:+,.0f}",
                          delta=f"{total_pnl_pct:+.2f}%")
            with pm4:
                st.metric("Holdings", len(rows))

            st.divider()

            port_df = pd.DataFrame(rows)
            st.dataframe(
                port_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "P&L ₹":   st.column_config.NumberColumn(format="₹%.0f"),
                    "P&L %":   st.column_config.NumberColumn(format="%.2f%%"),
                    "Invested": st.column_config.NumberColumn(format="₹%.0f"),
                    "Current":  st.column_config.NumberColumn(format="₹%.0f"),
                }
            )

            # Portfolio allocation chart
            fig_alloc = go.Figure(go.Bar(
                x=port_df["Symbol"],
                y=port_df["Current"],
                marker_color=[
                    "#34D399" if v >= 0 else "#F87171"
                    for v in port_df["P&L ₹"]
                ],
                text=[f"₹{v:,.0f}" for v in port_df["Current"]],
                textposition="outside"
            ))
            fig_alloc.update_layout(
                paper_bgcolor="#0D1421", plot_bgcolor="#0D1421",
                font_color="#94A3B8", xaxis_title="Stock",
                yaxis_title="Current Value (₹)",
                margin=dict(t=30, b=20, l=20, r=20),
                height=300
            )
            st.plotly_chart(fig_alloc, use_container_width=True)

# ══════════════════════════════════════════════════════════════
# TAB 3 — NEWS FEED
# ══════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-header">Live News Feed + Sentiment</div>',
                unsafe_allow_html=True)

    if news_df.empty:
        st.info("No news yet. Run the engine from the ⚙️ tab.")
    else:
        # Sentiment summary
        nc1, nc2, nc3 = st.columns(3)
        with nc1:
            bull_pct = round(len(news_df[news_df["sentiment"]=="BULLISH"]) / len(news_df) * 100)
            st.metric("🟢 Bullish Headlines", f"{bull_pct}%")
        with nc2:
            bear_pct = round(len(news_df[news_df["sentiment"]=="BEARISH"]) / len(news_df) * 100)
            st.metric("🔴 Bearish Headlines", f"{bear_pct}%")
        with nc3:
            neut_pct = 100 - bull_pct - bear_pct
            st.metric("🟡 Neutral Headlines", f"{neut_pct}%")

        st.divider()

        # Filter
        col_nf1, col_nf2 = st.columns(2)
        with col_nf1:
            news_filter = st.selectbox(
                "Filter sentiment", ["ALL", "BULLISH", "BEARISH", "NEUTRAL"]
            )
        with col_nf2:
            symbol_filter = st.text_input("Filter by symbol (e.g. RELIANCE)")

        filtered_news = news_df.copy()
        if news_filter != "ALL":
            filtered_news = filtered_news[filtered_news["sentiment"] == news_filter]
        if symbol_filter:
            filtered_news = filtered_news[
                filtered_news["related_symbol"].str.contains(
                    symbol_filter.upper(), na=False
                )
            ]

        for _, row in filtered_news.head(40).iterrows():
            sent  = row.get("sentiment", "NEUTRAL")
            color = {"BULLISH": "#34D399", "BEARISH": "#F87171"}.get(sent, "#6B7280")
            emoji = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "🟡"}.get(sent, "⚪")
            score = row.get("sentiment_score", 0)

            st.markdown(f"""
            <div class='news-card news-{sent.lower()}'>
                <div style='display:flex; justify-content:space-between;
                            align-items:flex-start;'>
                    <div style='flex:1; font-size:13px; color:#CBD5E1;
                                line-height:1.5;'>
                        {row['headline']}
                    </div>
                    <div style='min-width:80px; text-align:right; padding-left:12px;'>
                        <span style='color:{color}; font-family:Space Mono;
                                     font-size:12px; font-weight:700;'>
                            {emoji} {score:.0f}%
                        </span>
                    </div>
                </div>
                <div style='margin-top:6px; font-size:11px; color:#475569;'>
                    {row.get('source','Unknown')} &nbsp;·&nbsp;
                    {row.get('related_symbol','GENERAL')}
                </div>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# TAB 4 — CHARTS
# ══════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-header">Stock Charts</div>',
                unsafe_allow_html=True)

    chart_symbol = st.selectbox("Select stock to chart", [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
        "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
        "LT.NS", "HCLTECH.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
        "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS", "BAJFINANCE.NS", "WIPRO.NS"
    ])
    chart_period = st.select_slider(
        "Period", options=["1mo", "3mo", "6mo", "1y"], value="3mo"
    )

    @st.cache_data(ttl=300)
    def load_chart_data(symbol, period):
        ticker = yf.Ticker(symbol)
        return ticker.history(period=period)

    chart_df = load_chart_data(chart_symbol, chart_period)

    if not chart_df.empty:
        # Candlestick + Volume + RSI
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            row_heights=[0.6, 0.2, 0.2],
            vertical_spacing=0.04
        )

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=chart_df.index,
            open=chart_df["Open"], high=chart_df["High"],
            low=chart_df["Low"],  close=chart_df["Close"],
            increasing_line_color="#34D399",
            decreasing_line_color="#F87171",
            name="Price"
        ), row=1, col=1)

        # EMA lines
        ema9  = chart_df["Close"].ewm(span=9).mean()
        ema21 = chart_df["Close"].ewm(span=21).mean()
        ema50 = chart_df["Close"].ewm(span=50).mean()

        fig.add_trace(go.Scatter(
            x=chart_df.index, y=ema9,
            line=dict(color="#60A5FA", width=1),
            name="EMA 9"
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=chart_df.index, y=ema21,
            line=dict(color="#FBBF24", width=1),
            name="EMA 21"
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=chart_df.index, y=ema50,
            line=dict(color="#A78BFA", width=1),
            name="EMA 50"
        ), row=1, col=1)

        # Volume
        colors = [
            "#34D399" if chart_df["Close"].iloc[i] >= chart_df["Open"].iloc[i]
            else "#F87171"
            for i in range(len(chart_df))
        ]
        fig.add_trace(go.Bar(
            x=chart_df.index, y=chart_df["Volume"],
            marker_color=colors, name="Volume", opacity=0.7
        ), row=2, col=1)

        # RSI
        delta  = chart_df["Close"].diff()
        gain   = delta.where(delta > 0, 0).rolling(14).mean()
        loss   = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs     = gain / loss
        rsi    = 100 - (100 / (1 + rs))

        fig.add_trace(go.Scatter(
            x=chart_df.index, y=rsi,
            line=dict(color="#F472B6", width=1.5),
            name="RSI"
        ), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#F87171",
                      opacity=0.5, row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#34D399",
                      opacity=0.5, row=3, col=1)

        fig.update_layout(
            paper_bgcolor="#0D1421", plot_bgcolor="#0D1421",
            font_color="#94A3B8",
            xaxis_rangeslider_visible=False,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02,
                font=dict(color="#94A3B8", size=11)
            ),
            margin=dict(t=40, b=20, l=20, r=20),
            height=620
        )
        fig.update_xaxes(
            gridcolor="#1E2D45", showgrid=True, zeroline=False
        )
        fig.update_yaxes(
            gridcolor="#1E2D45", showgrid=True, zeroline=False
        )

        st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════
# TAB 5 — RUN ENGINE
# ══════════════════════════════════════════════════════════════
with tab5:
    st.markdown('<div class="section-header">Run Analysis Engine</div>',
                unsafe_allow_html=True)

    st.markdown("""
    <div style='background:#0D1421; border:1px solid #1E2D45; border-radius:10px;
                padding:20px; margin-bottom:20px;'>
        <div style='font-size:13px; color:#64748B; line-height:1.8;'>
            Run the full analysis pipeline manually from here.<br>
            The scheduler runs this automatically every 5 minutes when deployed.
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_r1, col_r2, col_r3 = st.columns(3)

    with col_r1:
        if st.button("📊 Run Technical Analysis", use_container_width=True):
            with st.spinner("Running pipeline..."):
                try:
                    from data_pipeline import run_pipeline
                    results = run_pipeline()
                    st.success(f"✅ Analyzed {len(results)} stocks")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"❌ {e}")

    with col_r2:
        if st.button("📰 Run News Engine", use_container_width=True):
            with st.spinner("Fetching & analyzing news..."):
                try:
                    from news_engine import run_news_engine
                    results = run_news_engine()
                    st.success(f"✅ Analyzed {len(results)} headlines")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"❌ {e}")

    with col_r3:
        if st.button("🧠 Run Full Engine + Alerts", use_container_width=True):
            with st.spinner("Running full analysis..."):
                try:
                    from signal_combiner import run_combiner
                    results = run_combiner()
                    st.success(f"✅ Full engine complete — {len(results)} signals")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"❌ {e}")

    st.divider()
    st.markdown('<div class="section-header">Signal History</div>',
                unsafe_allow_html=True)

    if not signals_df.empty:
        st.dataframe(
            signals_df[["symbol","signal","confidence","price","rsi","reason","created_at"]
            ].head(50),
            use_container_width=True,
            hide_index=True
        )

# ── Auto refresh ─────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(300)
    st.cache_data.clear()
    st.rerun()
    