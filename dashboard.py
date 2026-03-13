import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client
import ta

load_dotenv()

st.set_page_config(
    page_title="StockAI Terminal",
    page_icon="ðŸ“ˆ",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def get_supabase():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

supabase = get_supabase()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Outfit:wght@400;700;900&family=Space+Grotesk:wght@400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Space Grotesk',sans-serif!important;background:#07090f!important;color:#e2e8f0!important}
.stApp{background:#07090f!important}
#MainMenu,footer,header{visibility:hidden}
.block-container{padding:1rem 2rem 2rem!important;max-width:100%!important}
[data-testid="stSidebar"]{background:#0d1117!important;border-right:1px solid #1e2d45!important}
[data-testid="stSidebar"] *{color:#e2e8f0!important}
.stTabs [data-baseweb="tab-list"]{background:#0d1117!important;border-bottom:1px solid #1e2d45!important;border-radius:10px 10px 0 0;gap:0;padding:0 1rem}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:#64748b!important;font-family:'Space Grotesk',sans-serif!important;font-weight:600!important;font-size:13px!important;padding:12px 20px!important;border-bottom:3px solid transparent!important}
.stTabs [aria-selected="true"]{color:#00d4ff!important;border-bottom:3px solid #00d4ff!important}
.stTabs [data-baseweb="tab-panel"]{background:transparent!important;padding-top:1.5rem!important}
[data-testid="metric-container"]{background:#131c2e!important;border:1px solid #1e2d45!important;border-radius:12px!important;padding:1rem!important}
[data-testid="stMetricValue"]{font-family:'DM Mono',monospace!important;font-size:1.5rem!important}
[data-testid="stMetricLabel"]{font-size:11px!important;text-transform:uppercase!important;letter-spacing:2px!important;color:#64748b!important}
.stSelectbox>div>div,.stTextInput>div>div{background:#131c2e!important;border:1px solid #1e2d45!important;border-radius:8px!important;color:#e2e8f0!important}
.stButton>button{background:linear-gradient(135deg,#4488ff,#00d4ff)!important;color:#000!important;font-weight:700!important;border:none!important;border-radius:8px!important}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:#0d1117}
::-webkit-scrollbar-thumb{background:#243350;border-radius:3px}
.card{background:#131c2e;border:1px solid #1e2d45;border-radius:14px;padding:1.2rem 1.4rem;margin-bottom:0.8rem}
.sig-buy{border-left:4px solid #00ff88!important}
.sig-sell{border-left:4px solid #ff4466!important}
.sig-hold{border-left:4px solid #ffcc00!important}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase}
.b-buy{background:rgba(0,255,136,.15);color:#00ff88;border:1px solid rgba(0,255,136,.3)}
.b-sell{background:rgba(255,68,102,.15);color:#ff4466;border:1px solid rgba(255,68,102,.3)}
.b-hold{background:rgba(255,204,0,.15);color:#ffcc00;border:1px solid rgba(255,204,0,.3)}
.b-bull{background:rgba(0,255,136,.15);color:#00ff88}
.b-bear{background:rgba(255,68,102,.15);color:#ff4466}
.b-neut{background:rgba(255,204,0,.15);color:#ffcc00}
.slabel{font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#64748b;margin-bottom:12px;font-family:'DM Mono',monospace}
.cbar{background:#111827;border-radius:4px;height:6px;margin-top:6px;overflow:hidden}
.mono{font-family:'DM Mono',monospace}
</style>
""", unsafe_allow_html=True)

# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def sig_color(s):
    s = str(s)
    if s.startswith("BUY"):  return "#00ff88"
    if s.startswith("SELL"): return "#ff4466"
    return "#ffcc00"

def cbar_html(conf, color):
    return f'<div class="cbar"><div style="width:{min(float(conf),100):.0f}%;height:6px;background:{color};border-radius:4px"></div></div>'

def levels_html(price, is_buy):
    if not is_buy:
        return ""
    p  = float(price)
    sl = round(p * 0.97, 2)
    t1 = round(p * 1.04, 2)
    t2 = round(p * 1.08, 2)
    return f"""
    <div style="display:flex;gap:6px;margin-top:10px;flex-wrap:wrap">
        <div style="background:rgba(68,136,255,.1);border:1px solid rgba(68,136,255,.3);border-radius:6px;padding:4px 10px;font-size:11px;font-family:'DM Mono',monospace">
            <span style="color:#64748b">Entry</span>
            <span style="color:#4488ff;font-weight:700;margin-left:5px">&#8377;{p:,.2f}</span>
        </div>
        <div style="background:rgba(255,68,102,.1);border:1px solid rgba(255,68,102,.3);border-radius:6px;padding:4px 10px;font-size:11px;font-family:'DM Mono',monospace">
            <span style="color:#64748b">SL</span>
            <span style="color:#ff4466;font-weight:700;margin-left:5px">&#8377;{sl:,.2f}</span>
            <span style="color:#475569;font-size:9px"> -3%</span>
        </div>
        <div style="background:rgba(0,255,136,.1);border:1px solid rgba(0,255,136,.3);border-radius:6px;padding:4px 10px;font-size:11px;font-family:'DM Mono',monospace">
            <span style="color:#64748b">T1</span>
            <span style="color:#00ff88;font-weight:700;margin-left:5px">&#8377;{t1:,.2f}</span>
            <span style="color:#475569;font-size:9px"> +4%</span>
        </div>
        <div style="background:rgba(0,255,136,.15);border:1px solid rgba(0,255,136,.4);border-radius:6px;padding:4px 10px;font-size:11px;font-family:'DM Mono',monospace">
            <span style="color:#64748b">T2</span>
            <span style="color:#00ff88;font-weight:700;margin-left:5px">&#8377;{t2:,.2f}</span>
            <span style="color:#475569;font-size:9px"> +8%</span>
        </div>
    </div>"""

def fmt_t(ts):
    try: return pd.to_datetime(ts).strftime("%d %b %H:%M")
    except: return str(ts)[:16]

def base_layout(h=320):
    return dict(height=h, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1117",
                margin=dict(l=0,r=0,t=10,b=0), font=dict(family="DM Mono",color="#64748b"))

# â”€â”€ Data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@st.cache_data(ttl=300)
def get_signals():
    try:
        r = supabase.table("signals").select("*").order("created_at",desc=True).limit(500).execute()
        return pd.DataFrame(r.data) if r.data else pd.DataFrame()
    except: return pd.DataFrame()

@st.cache_data(ttl=300)
def get_news():
    try:
        r = supabase.table("news").select("*").order("created_at",desc=True).limit(200).execute()
        return pd.DataFrame(r.data) if r.data else pd.DataFrame()
    except: return pd.DataFrame()

@st.cache_data(ttl=300)
def get_portfolio():
    try:
        r = supabase.table("stocks").select("*").eq("in_portfolio",True).execute()
        return r.data if r.data else []
    except: return []

@st.cache_data(ttl=600)
def get_regime():
    try:
        from market_regime import get_market_regime
        return get_market_regime()
    except: return "UNKNOWN", 0, {}

@st.cache_data(ttl=900)
def get_nifty():
    try:
        df = yf.Ticker("^NSEI").history(period="6mo",interval="1d")
        df["EMA50"]  = ta.trend.ema_indicator(df["Close"],window=50)
        df["EMA200"] = ta.trend.ema_indicator(df["Close"],window=200)
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=300)
def get_indices():
    tickers = {"NIFTY 50":"^NSEI","SENSEX":"^BSESN","BANK NIFTY":"^NSEBANK","NIFTY IT":"^CNXIT"}
    out = {}
    for name, t in tickers.items():
        try:
            df = yf.Ticker(t).history(period="2d")
            if len(df)>=2:
                c,p = float(df["Close"].iloc[-1]), float(df["Close"].iloc[-2])
                out[name] = {"price":c,"change":(c-p)/p*100}
        except: pass
    return out

@st.cache_data(ttl=900)
def get_sectors():
    sec = {
        "Banking":["HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","AXISBANK.NS","KOTAKBANK.NS"],
        "IT":["TCS.NS","INFY.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS"],
        "Pharma":["SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS","LUPIN.NS"],
        "Auto":["MARUTI.NS","BAJAJ-AUTO.NS","HEROMOTOCO.NS","EICHERMOT.NS","TVSMOTOR.NS"],
        "FMCG":["HINDUNILVR.NS","ITC.NS","NESTLEIND.NS","DABUR.NS","MARICO.NS"],
        "Metals":["TATASTEEL.NS","HINDALCO.NS","JSWSTEEL.NS","VEDL.NS","SAIL.NS"],
        "Energy":["RELIANCE.NS","ONGC.NS","NTPC.NS","POWERGRID.NS","TATAPOWER.NS"],
        "Realty":["DLF.NS","GODREJPROP.NS","OBEROIRLTY.NS","PRESTIGE.NS","BRIGADE.NS"],
    }
    out = {}
    for s, stocks in sec.items():
        ch = []
        for sym in stocks:
            try:
                df = yf.Ticker(sym).history(period="5d")
                if len(df)>=2:
                    ch.append((float(df["Close"].iloc[-1])-float(df["Close"].iloc[0]))/float(df["Close"].iloc[0])*100)
            except: pass
        out[s] = round(sum(ch)/len(ch),2) if ch else 0
    return out

@st.cache_data(ttl=600)
def get_chart(sym, period="3mo"):
    try:
        df = yf.Ticker(sym).history(period=period,interval="1d")
        if df.empty: return None
        df["EMA9"]  = ta.trend.ema_indicator(df["Close"],window=9)
        df["EMA21"] = ta.trend.ema_indicator(df["Close"],window=21)
        df["EMA50"] = ta.trend.ema_indicator(df["Close"],window=50)
        df["RSI"]   = ta.momentum.rsi(df["Close"],window=14)
        bb = ta.volatility.BollingerBands(df["Close"])
        df["BB_U"]  = bb.bollinger_hband()
        df["BB_L"]  = bb.bollinger_lband()
        return df
    except: return None

@st.cache_data(ttl=300)
def get_calendar():
    try:
        from economic_calendar import get_upcoming_events
        return get_upcoming_events(days_ahead=30)
    except: return []

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# HEADER
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
h1, h2 = st.columns([1,3])
with h1:
    st.markdown("""
    <div style="padding:.5rem 0">
        <div style="font-family:'Outfit',sans-serif;font-size:1.8rem;font-weight:900;letter-spacing:-1px;background:linear-gradient(135deg,#00ff88,#00d4ff,#4488ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent">
            &#9889; StockAI</div>
        <div style="font-size:11px;color:#64748b;letter-spacing:2px;text-transform:uppercase;margin-top:-4px">Indian Market Intelligence</div>
    </div>""", unsafe_allow_html=True)

with h2:
    idx = get_indices()
    if idx:
        icols = st.columns(len(idx))
        for i,(name,data) in enumerate(idx.items()):
            c = "#00ff88" if data["change"]>=0 else "#ff4466"
            a = "&#9650;" if data["change"]>=0 else "&#9660;"
            with icols[i]:
                st.markdown(f"""
                <div class="card" style="padding:.7rem 1rem;margin:0">
                    <div style="font-size:10px;color:#64748b;letter-spacing:2px;text-transform:uppercase">{name}</div>
                    <div class="mono" style="font-size:1rem;font-weight:500">{data['price']:,.0f}</div>
                    <div style="font-size:12px;color:{c};font-weight:700">{a} {abs(data['change']):.2f}%</div>
                </div>""", unsafe_allow_html=True)

st.markdown("<hr style='border:1px solid #1e2d45;margin:.5rem 0 1rem 0'>", unsafe_allow_html=True)

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# TABS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
tabs = st.tabs(["&#127968;  Overview","&#128225;  Signals","&#128188;  Portfolio",
                "&#128240;  News","&#128202;  Charts","&#128269;  Screener",
                "&#128197;  Calendar","&#9881;&#65039;  Engine"])

# â”€â”€ TAB 1: OVERVIEW â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
with tabs[0]:
    regime, rscore, rdet = get_regime()
    nd = rdet.get("nifty",{})
    vd = rdet.get("vix",{})

    RS = {
        "STRONG_BULL":("#00ff88","#064e3b","&#128640;"),
        "BULL":       ("#00ff88","#064e3b","&#128994;"),
        "NEUTRAL":    ("#ffcc00","#3d3200","&#128993;"),
        "BEAR":       ("#ff4466","#4a0010","&#128308;"),
        "STRONG_BEAR":("#ff4466","#4a0010","&#128680;"),
        "UNKNOWN":    ("#64748b","#1e2d45","&#9898;"),
    }
    rc,rbg,remoji = RS.get(regime,("#64748b","#1e2d45","&#9898;"))

    st.markdown(f"""
    <div style="background:{rbg};border:1px solid {rc}55;border-radius:14px;padding:1.2rem 1.8rem;margin-bottom:1.5rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:1rem">
        <div>
            <div style="font-size:10px;letter-spacing:3px;color:{rc}88;text-transform:uppercase;font-family:'DM Mono',monospace">Market Regime</div>
            <div style="font-size:1.8rem;font-weight:900;color:{rc};font-family:'Outfit',sans-serif;letter-spacing:-1px">{remoji} {regime.replace('_',' ')}</div>
            <div style="font-size:12px;color:{rc}99;margin-top:2px">Score: {rscore:+.3f} &nbsp;|&nbsp; Nifty RSI: {nd.get('rsi',0):.1f} &nbsp;|&nbsp; VIX: {vd.get('current',0):.1f}</div>
        </div>
        <div style="display:flex;gap:2rem;flex-wrap:wrap">
            <div style="text-align:center">
                <div style="font-size:10px;color:{rc}88;letter-spacing:2px;text-transform:uppercase">1M Return</div>
                <div class="mono" style="font-size:1.2rem;font-weight:700;color:{'#00ff88' if nd.get('ret_1m',0)>=0 else '#ff4466'}">{nd.get('ret_1m',0):+.2f}%</div>
            </div>
            <div style="text-align:center">
                <div style="font-size:10px;color:{rc}88;letter-spacing:2px;text-transform:uppercase">3M Return</div>
                <div class="mono" style="font-size:1.2rem;font-weight:700;color:{'#00ff88' if nd.get('ret_3m',0)>=0 else '#ff4466'}">{nd.get('ret_3m',0):+.2f}%</div>
            </div>
            <div style="text-align:center">
                <div style="font-size:10px;color:{rc}88;letter-spacing:2px;text-transform:uppercase">VIX / Avg</div>
                <div class="mono" style="font-size:1.2rem;font-weight:700;color:{'#ff4466' if vd.get('current',0)>vd.get('avg',20) else '#00ff88'}">{vd.get('current',0):.1f} / {vd.get('avg',0):.1f}</div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

    sdf = get_signals()
    ndf = get_news()
    lat = sdf.drop_duplicates(subset="symbol",keep="first") if not sdf.empty else pd.DataFrame()

    bn = len(lat[lat["signal"].str.startswith("BUY")])  if not lat.empty else 0
    sn = len(lat[lat["signal"].str.startswith("SELL")]) if not lat.empty else 0
    hn = len(lat[~lat["signal"].str.startswith("BUY") & ~lat["signal"].str.startswith("SELL")]) if not lat.empty else 0
    ac = round(lat["confidence"].mean(),1) if not lat.empty else 0
    bln= len(ndf[ndf["sentiment"]=="BULLISH"]) if not ndf.empty else 0
    brn= len(ndf[ndf["sentiment"]=="BEARISH"]) if not ndf.empty else 0

    m1,m2,m3,m4,m5,m6 = st.columns(6)
    with m1: st.metric("&#128994; BUY",  bn)
    with m2: st.metric("&#128308; SELL", sn)
    with m3: st.metric("&#128993; HOLD", hn)
    with m4: st.metric("&#128202; Avg Conf", f"{ac}%")
    with m5: st.metric("&#128240; Bullish", bln)
    with m6: st.metric("&#128240; Bearish", brn)

    st.markdown("<br>", unsafe_allow_html=True)
    ov1,ov2 = st.columns([3,2])

    with ov1:
        st.markdown('<div class="slabel">Nifty 50 â€” 6 Month</div>', unsafe_allow_html=True)
        nf = get_nifty()
        if not nf.empty:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=nf.index,open=nf["Open"],high=nf["High"],low=nf["Low"],close=nf["Close"],increasing_line_color="#00ff88",decreasing_line_color="#ff4466",showlegend=False))
            fig.add_trace(go.Scatter(x=nf.index,y=nf["EMA50"],line=dict(color="#4488ff",width=1.5),name="EMA50"))
            fig.add_trace(go.Scatter(x=nf.index,y=nf["EMA200"],line=dict(color="#ff8844",width=1.5),name="EMA200"))
            fig.update_layout(**base_layout(320),xaxis=dict(showgrid=False,color="#64748b",rangeslider=dict(visible=False)),yaxis=dict(showgrid=True,gridcolor="#1e2d45",color="#64748b"),legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(color="#94a3b8")))
            st.plotly_chart(fig, use_container_width=True)

    with ov2:
        st.markdown('<div class="slabel">Sector Performance â€” 5 Day</div>', unsafe_allow_html=True)
        sp = get_sectors()
        if sp:
            sn2,sv = list(sp.keys()),list(sp.values())
            fig2 = go.Figure(go.Bar(x=sv,y=sn2,orientation="h",marker_color=["#00ff88" if v>=0 else "#ff4466" for v in sv],text=[f"{v:+.2f}%" for v in sv],textposition="outside",textfont=dict(color="#e2e8f0",size=11,family="DM Mono")))
            fig2.update_layout(**base_layout(320),xaxis=dict(showgrid=True,gridcolor="#1e2d45",color="#64748b",zeroline=True,zerolinecolor="#243350"),yaxis=dict(showgrid=False,color="#e2e8f0"))
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="slabel">Top Signals with Trade Levels</div>', unsafe_allow_html=True)

    if not lat.empty:
        strong = lat[lat["confidence"]>=25].sort_values("confidence",ascending=False).head(6)
        if not strong.empty:
            sc = st.columns(3)
            for i,(_,row) in enumerate(strong.iterrows()):
                sig   = str(row.get("signal",""))
                conf  = float(row.get("confidence",0))
                price = float(row.get("price",0))
                color = sig_color(sig)
                is_buy = sig.startswith("BUY")
                cls   = "sig-buy" if is_buy else ("sig-sell" if sig.startswith("SELL") else "sig-hold")
                badge = "b-buy"   if is_buy else ("b-sell"   if sig.startswith("SELL") else "b-hold")
                with sc[i%3]:
                    st.markdown(f"""
                    <div class="card {cls}">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                            <div style="font-weight:700;font-size:15px">{str(row.get('symbol','')).replace('.NS','')}</div>
                            <span class="badge {badge}">{sig.split()[0]}</span>
                        </div>
                        <div class="mono" style="font-size:1.1rem;color:#00d4ff">&#8377;{price:,.2f}</div>
                        <div style="display:flex;justify-content:space-between;font-size:12px;color:#94a3b8;margin-top:4px">
                            <span>RSI: {float(row.get('rsi',0)):.1f}</span>
                            <span style="color:{color};font-weight:700">{conf:.1f}%</span>
                        </div>
                        {cbar_html(conf,color)}
                        {levels_html(price,is_buy)}
                    </div>""", unsafe_allow_html=True)
        else:
            st.info("No strong signals â€” market is in BEAR mode. System is protecting capital.")
    else:
        st.info("No signal data yet. Run the engine first.")

# â”€â”€ TAB 2: SIGNALS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
with tabs[1]:
    sdf = get_signals()
    if sdf.empty:
        st.info("No signals yet.")
    else:
        lat = sdf.drop_duplicates(subset="symbol",keep="first")
        fc1,fc2,fc3,fc4 = st.columns(4)
        with fc1: sf = st.selectbox("Signal",["All","BUY","SELL","HOLD"])
        with fc2: mc = st.slider("Min Confidence %",0,100,0)
        with fc3: srt= st.selectbox("Sort By",["Confidence â†“","Confidence â†‘","RSI â†“","RSI â†‘","Symbol"])
        with fc4: srch=st.text_input("Search",placeholder="e.g. SBIN")

        f = lat.copy()
        if sf!="All": f = f[f["signal"].str.startswith(sf)]
        f = f[f["confidence"]>=mc]
        if srch: f = f[f["symbol"].str.contains(srch.upper(),na=False)]
        sm2 = {"Confidence â†“":("confidence",False),"Confidence â†‘":("confidence",True),"RSI â†“":("rsi",False),"RSI â†‘":("rsi",True),"Symbol":("symbol",True)}
        sc2,sa2 = sm2[srt]
        if sc2 in f.columns: f = f.sort_values(sc2,ascending=sa2)

        st.markdown(f'<div style="font-size:12px;color:#64748b;margin-bottom:1rem">Showing <b style="color:#e2e8f0">{len(f)}</b> of {len(lat)} stocks</div>', unsafe_allow_html=True)

        for label,subset,cls,badge in [
            ("&#128994; BUY Signals",  f[f["signal"].str.startswith("BUY")],  "sig-buy","b-buy"),
            ("&#128308; SELL Signals", f[f["signal"].str.startswith("SELL")], "sig-sell","b-sell"),
            ("&#128993; HOLD Signals", f[~f["signal"].str.startswith("BUY")&~f["signal"].str.startswith("SELL")], "sig-hold","b-hold"),
        ]:
            if len(subset)==0: continue
            st.markdown(f'<div style="font-size:11px;letter-spacing:3px;color:#64748b;text-transform:uppercase;margin:1.2rem 0 .6rem;font-family:\'DM Mono\',monospace">{label} ({len(subset)})</div>', unsafe_allow_html=True)
            cols = st.columns(4)
            for i,(_,row) in enumerate(subset.iterrows()):
                sig   = str(row.get("signal",""))
                conf  = float(row.get("confidence",0))
                price = float(row.get("price",0))
                color = sig_color(sig)
                is_buy= sig.startswith("BUY")
                rsn   = str(row.get("reason",""))
                rsn   = rsn[:90]+"..." if len(rsn)>90 else rsn
                with cols[i%4]:
                    st.markdown(f"""
                    <div class="card {cls}">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                            <div style="font-weight:700;font-size:15px">{str(row.get('symbol','')).replace('.NS','')}</div>
                            <span class="badge {badge}">{sig.split()[0]}</span>
                        </div>
                        <div class="mono" style="font-size:1.1rem;color:#00d4ff">&#8377;{price:,.2f}</div>
                        <div style="display:flex;justify-content:space-between;font-size:12px;color:#94a3b8;margin:4px 0">
                            <span>RSI: {float(row.get('rsi',0)):.1f}</span>
                            <span style="color:{color};font-weight:700">{conf:.1f}%</span>
                        </div>
                        {cbar_html(conf,color)}
                        {levels_html(price,is_buy)}
                        <div style="font-size:10px;color:#475569;margin-top:8px;line-height:1.5">{rsn}</div>
                        <div style="font-size:10px;color:#334155;margin-top:4px">{fmt_t(row.get('created_at',''))}</div>
                    </div>""", unsafe_allow_html=True)

# â”€â”€ TAB 3: PORTFOLIO â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
with tabs[2]:
    portfolio = get_portfolio()
    if not portfolio:
        st.markdown('<div class="card" style="text-align:center;padding:3rem"><div style="font-size:3rem;margin-bottom:1rem">&#128188;</div><div style="font-size:1.1rem;font-weight:600">No holdings yet</div><div style="color:#64748b;font-size:13px;margin-top:.5rem">Add stocks using the sidebar</div></div>', unsafe_allow_html=True)
    else:
        rows=[];ti=tc=0
        for h in portfolio:
            try:
                sym=h["symbol"];bp=float(h.get("buy_price",0));qty=float(h.get("quantity",0))
                if not bp or not qty: continue
                df=yf.Ticker(sym).history(period="5d")
                cp=float(df["Close"].iloc[-1]) if not df.empty else bp
                wc=(cp-float(df["Close"].iloc[0]))/float(df["Close"].iloc[0])*100 if len(df)>1 else 0
                prs=(cp-bp)*qty;ppc=(cp-bp)/bp*100
                ti+=bp*qty;tc+=cp*qty
                rows.append({"sym":sym.replace(".NS","").replace(".BO",""),"buy":bp,"cur":cp,"qty":int(qty),"prs":prs,"ppc":ppc,"wc":wc,"val":cp*qty,"sl":round(cp*.97,2),"t1":round(cp*1.04,2),"t2":round(cp*1.08,2)})
            except: pass

        tp=tc-ti;tpp=(tp/ti*100) if ti else 0
        p1,p2,p3,p4=st.columns(4)
        with p1: st.metric("&#128176; Invested",   f"&#8377;{ti:,.0f}")
        with p2: st.metric("&#128200; Current",    f"&#8377;{tc:,.0f}")
        with p3: st.metric("&#128185; Total P&L",  f"&#8377;{tp:+,.0f}", delta=f"{tpp:+.2f}%")
        with p4: st.metric("&#127919; Holdings",   len(rows))

        if rows:
            pc1,pc2=st.columns([2,1])
            with pc1:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="slabel">Holdings + Trade Levels</div>', unsafe_allow_html=True)
                for r in sorted(rows,key=lambda x:x["ppc"],reverse=True):
                    pc="#00ff88" if r["ppc"]>=0 else "#ff4466"
                    wc2="#00ff88" if r["wc"]>=0 else "#ff4466"
                    st.markdown(f"""
                    <div class="card" style="border-left:4px solid {pc}">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:1rem">
                            <div>
                                <div style="font-weight:700;font-size:17px">{r['sym']}</div>
                                <div style="font-size:12px;color:#64748b;margin-top:2px">{r['qty']} shares &nbsp;&#183;&nbsp; Bought @ &#8377;{r['buy']:,.2f}</div>
                            </div>
                            <div style="text-align:center">
                                <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:1px">Current</div>
                                <div class="mono" style="font-size:1.1rem;color:#00d4ff">&#8377;{r['cur']:,.2f}</div>
                            </div>
                            <div style="text-align:center">
                                <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:1px">P&amp;L</div>
                                <div class="mono" style="color:{pc};font-weight:700;font-size:14px">{r['ppc']:+.2f}%</div>
                                <div class="mono" style="color:{pc};font-size:12px">&#8377;{r['prs']:+,.0f}</div>
                            </div>
                            <div style="text-align:center">
                                <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:1px">Week</div>
                                <div class="mono" style="color:{wc2};font-weight:600;font-size:14px">{r['wc']:+.2f}%</div>
                            </div>
                            <div style="text-align:center">
                                <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:1px">Value</div>
                                <div class="mono" style="font-size:14px">&#8377;{r['val']:,.0f}</div>
                            </div>
                        </div>
                        <div style="margin-top:12px;padding:10px 12px;background:#080c14;border-radius:8px">
                            <div style="font-size:10px;color:#64748b;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;font-family:'DM Mono',monospace">Trade Levels</div>
                            <div style="display:flex;gap:8px;flex-wrap:wrap;font-family:'DM Mono',monospace;font-size:12px">
                                <div style="background:rgba(68,136,255,.1);border:1px solid rgba(68,136,255,.3);border-radius:6px;padding:5px 12px">
                                    <span style="color:#64748b">Entry</span>
                                    <span style="color:#4488ff;font-weight:700;margin-left:6px">&#8377;{r['buy']:,.2f}</span>
                                </div>
                                <div style="background:rgba(255,68,102,.1);border:1px solid rgba(255,68,102,.3);border-radius:6px;padding:5px 12px">
                                    <span style="color:#64748b">Stop Loss</span>
                                    <span style="color:#ff4466;font-weight:700;margin-left:6px">&#8377;{r['sl']:,.2f}</span>
                                    <span style="color:#475569;font-size:10px"> -3%</span>
                                </div>
                                <div style="background:rgba(0,255,136,.1);border:1px solid rgba(0,255,136,.3);border-radius:6px;padding:5px 12px">
                                    <span style="color:#64748b">Target 1</span>
                                    <span style="color:#00ff88;font-weight:700;margin-left:6px">&#8377;{r['t1']:,.2f}</span>
                                    <span style="color:#475569;font-size:10px"> +4%</span>
                                </div>
                                <div style="background:rgba(0,255,136,.15);border:1px solid rgba(0,255,136,.4);border-radius:6px;padding:5px 12px">
                                    <span style="color:#64748b">Target 2</span>
                                    <span style="color:#00ff88;font-weight:700;margin-left:6px">&#8377;{r['t2']:,.2f}</span>
                                    <span style="color:#475569;font-size:10px"> +8%</span>
                                </div>
                            </div>
                        </div>
                        {cbar_html(min(abs(r['ppc'])*5,100),pc)}
                    </div>""", unsafe_allow_html=True)

            with pc2:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="slabel">Allocation</div>', unsafe_allow_html=True)
                COLORS=["#00ff88","#4488ff","#ff8844","#a855f7","#00d4ff","#ffcc00","#ff4466","#22c55e"]
                fig_pie=go.Figure(go.Pie(labels=[r["sym"] for r in rows],values=[r["val"] for r in rows],hole=0.6,marker_colors=COLORS[:len(rows)],textinfo="label+percent",textfont=dict(family="DM Mono",size=11,color="#e2e8f0"),hovertemplate="<b>%{label}</b><br>&#8377;%{value:,.0f}<extra></extra>"))
                fig_pie.add_annotation(text=f"&#8377;{tc:,.0f}",x=0.5,y=0.5,font_size=13,font_color="#e2e8f0",font_family="DM Mono",showarrow=False)
                fig_pie.update_layout(**base_layout(300),showlegend=False)
                st.plotly_chart(fig_pie, use_container_width=True)

# â”€â”€ TAB 4: NEWS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
with tabs[3]:
    ndf=get_news()
    if ndf.empty:
        st.info("No news data yet.")
    else:
        nc1,nc2,nc3=st.columns(3)
        with nc1: sf2=st.selectbox("Sentiment",["All","BULLISH","BEARISH","NEUTRAL"])
        with nc2: sy2=st.text_input("Stock",placeholder="e.g. RELIANCE")
        with nc3:
            so=["All"]+list(ndf["source"].dropna().unique()) if "source" in ndf.columns else ["All"]
            sr=st.selectbox("Source",so)

        fn=ndf.copy()
        if sf2!="All": fn=fn[fn["sentiment"]==sf2]
        if sy2: fn=fn[fn["related_symbol"].str.contains(sy2.upper(),na=False)]
        if sr!="All" and "source" in fn.columns: fn=fn[fn["source"]==sr]

        tn=len(ndf);bl=len(ndf[ndf["sentiment"]=="BULLISH"]);br2=len(ndf[ndf["sentiment"]=="BEARISH"]);nt=len(ndf[ndf["sentiment"]=="NEUTRAL"])
        st.markdown(f"""
        <div class="card" style="margin-bottom:1.2rem">
            <div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:12px;color:#94a3b8">
                <span>&#128994; Bullish: {bl} ({bl/tn*100:.0f}%)</span>
                <span>&#128993; Neutral: {nt} ({nt/tn*100:.0f}%)</span>
                <span>&#128308; Bearish: {br2} ({br2/tn*100:.0f}%)</span>
            </div>
            <div style="display:flex;height:8px;border-radius:4px;overflow:hidden">
                <div style="width:{bl/tn*100:.0f}%;background:#00ff88"></div>
                <div style="width:{nt/tn*100:.0f}%;background:#ffcc00"></div>
                <div style="width:{br2/tn*100:.0f}%;background:#ff4466"></div>
            </div>
        </div>""", unsafe_allow_html=True)

        SC={"BULLISH":"#00ff88","BEARISH":"#ff4466","NEUTRAL":"#ffcc00"}
        SB={"BULLISH":"b-bull","BEARISH":"b-bear","NEUTRAL":"b-neut"}
        for _,row in fn.head(60).iterrows():
            sent=str(row.get("sentiment","NEUTRAL"));score=float(row.get("sentiment_score",0))
            sc3=SC.get(sent,"#ffcc00");sb=SB.get(sent,"b-neut")
            sym=str(row.get("related_symbol","GENERAL")).replace(".NS","")
            src=str(row.get("source",""));hl=str(row.get("headline",""))
            st.markdown(f"""
            <div class="card" style="padding:.9rem 1.1rem;margin-bottom:.5rem">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:.5rem;flex-wrap:wrap">
                    <div style="flex:1;min-width:200px">
                        <div style="font-size:13px;font-weight:500;line-height:1.5;margin-bottom:5px">{hl}</div>
                        <div style="font-size:11px;color:#475569">{src} &nbsp;&#183;&nbsp; {sym} &nbsp;&#183;&nbsp; {fmt_t(row.get('published_at',''))}</div>
                    </div>
                    <div style="text-align:right;flex-shrink:0">
                        <span class="badge {sb}">{sent}</span>
                        <div class="mono" style="font-size:12px;color:{sc3};margin-top:4px">{score:+.3f}</div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)

# â”€â”€ TAB 5: CHARTS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
with tabs[4]:
    sdf=get_signals()
    syms=sorted(sdf["symbol"].dropna().unique().tolist()) if not sdf.empty else ["RELIANCE.NS","TCS.NS","HDFCBANK.NS"]
    cc1,cc2=st.columns([2,1])
    with cc1: csym=st.selectbox("Stock",syms,format_func=lambda x:x.replace(".NS",""))
    with cc2: cper=st.selectbox("Period",["1mo","3mo","6mo","1y"],index=1)

    dfc=get_chart(csym,cper)
    if dfc is not None and not dfc.empty:
        fig_c=make_subplots(rows=3,cols=1,shared_xaxes=True,row_heights=[0.6,0.2,0.2],vertical_spacing=0.04)
        fig_c.add_trace(go.Candlestick(x=dfc.index,open=dfc["Open"],high=dfc["High"],low=dfc["Low"],close=dfc["Close"],increasing_line_color="#00ff88",decreasing_line_color="#ff4466",showlegend=False),row=1,col=1)
        fig_c.add_trace(go.Scatter(x=dfc.index,y=dfc["BB_U"],line=dict(color="rgba(68,136,255,0.3)",width=1,dash="dot"),showlegend=False,name="BB_U"),row=1,col=1)
        fig_c.add_trace(go.Scatter(x=dfc.index,y=dfc["BB_L"],line=dict(color="rgba(68,136,255,0.3)",width=1,dash="dot"),fill="tonexty",fillcolor="rgba(68,136,255,0.05)",showlegend=False,name="BB_L"),row=1,col=1)
        for ema,color in [("EMA9","#4488ff"),("EMA21","#ffcc00"),("EMA50","#ff8844")]:
            fig_c.add_trace(go.Scatter(x=dfc.index,y=dfc[ema],line=dict(color=color,width=1.3),name=ema),row=1,col=1)
        fig_c.add_trace(go.Bar(x=dfc.index,y=dfc["Volume"],marker_color=["#00ff88" if c>=o else "#ff4466" for c,o in zip(dfc["Close"],dfc["Open"])],showlegend=False),row=2,col=1)
        fig_c.add_trace(go.Scatter(x=dfc.index,y=dfc["RSI"],line=dict(color="#a855f7",width=1.5),showlegend=False),row=3,col=1)
        # Use rgba instead of 8-digit hex for hlines
        fig_c.add_hline(y=70,line=dict(color="rgba(255,68,102,0.4)",dash="dot"),row=3,col=1)
        fig_c.add_hline(y=30,line=dict(color="rgba(0,255,136,0.4)",dash="dot"),row=3,col=1)
        fig_c.add_hline(y=50,line=dict(color="rgba(100,116,139,0.3)",dash="dot"),row=3,col=1)
        fig_c.update_layout(**base_layout(580),xaxis=dict(showgrid=False,color="#64748b",rangeslider=dict(visible=False)),xaxis2=dict(showgrid=False,color="#64748b"),xaxis3=dict(showgrid=False,color="#64748b"),yaxis=dict(showgrid=True,gridcolor="#1e2d45",color="#64748b"),yaxis2=dict(showgrid=True,gridcolor="#1e2d45",color="#64748b"),yaxis3=dict(showgrid=True,gridcolor="#1e2d45",color="#64748b",range=[0,100]),legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(color="#94a3b8"),orientation="h",y=1.02))
        st.plotly_chart(fig_c,use_container_width=True)

        lr=dfc.iloc[-1]
        s1,s2,s3,s4,s5=st.columns(5)
        with s1: st.metric("Close",  f"&#8377;{lr['Close']:,.2f}")
        with s2: st.metric("RSI",    f"{lr['RSI']:.1f}")
        with s3: st.metric("EMA 9",  f"&#8377;{lr['EMA9']:,.2f}")
        with s4: st.metric("EMA 21", f"&#8377;{lr['EMA21']:,.2f}")
        with s5: st.metric("EMA 50", f"&#8377;{lr['EMA50']:,.2f}")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="slabel">Trade Levels at Current Price</div>', unsafe_allow_html=True)
        cp=float(lr["Close"]);sl=round(cp*.97,2);t1=round(cp*1.04,2);t2=round(cp*1.08,2);rr=round((t1-cp)/(cp-sl),2)
        tl1,tl2,tl3,tl4,tl5=st.columns(5)
        with tl1: st.metric("&#128205; Entry",    f"&#8377;{cp:,.2f}")
        with tl2: st.metric("&#128721; Stop Loss",f"&#8377;{sl:,.2f}",delta="-3%",delta_color="inverse")
        with tl3: st.metric("&#127919; Target 1", f"&#8377;{t1:,.2f}",delta="+4%")
        with tl4: st.metric("&#127919; Target 2", f"&#8377;{t2:,.2f}",delta="+8%")
        with tl5: st.metric("&#9878;&#65039; R:R", f"1:{rr}")

# â”€â”€ TAB 6: SCREENER â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
with tabs[5]:
    sdf=get_signals()
    if sdf.empty:
        st.info("No signal data available.")
    else:
        lat=sdf.drop_duplicates(subset="symbol",keep="first")
        sc1,sc2,sc3,sc4,sc5=st.columns(5)
        with sc1: ssig=st.selectbox("Signal",["All","BUY","SELL","HOLD"],key="ss2")
        with sc2: scon=st.slider("Min Conf %",0,100,0,key="sc2")
        with sc3: srmi=st.slider("RSI Min",0,100,0,key="srn2")
        with sc4: srma=st.slider("RSI Max",0,100,100,key="srx2")
        with sc5: ssrt=st.selectbox("Sort By",["Confidence","RSI","Price","Symbol"],key="ss3")

        sc4f=lat.copy()
        if ssig!="All": sc4f=sc4f[sc4f["signal"].str.startswith(ssig)]
        sc4f=sc4f[sc4f["confidence"]>=scon]
        if "rsi" in sc4f.columns: sc4f=sc4f[(sc4f["rsi"]>=srmi)&(sc4f["rsi"]<=srma)]
        scol2={"Confidence":"confidence","RSI":"rsi","Price":"price","Symbol":"symbol"}.get(ssrt,"confidence")
        if scol2 in sc4f.columns: sc4f=sc4f.sort_values(scol2,ascending=False)

        st.markdown(f'<div style="font-size:12px;color:#64748b;margin-bottom:1rem"><b style="color:#e2e8f0">{len(sc4f)}</b> stocks match filters</div>', unsafe_allow_html=True)

        if not sc4f.empty:
            sc4f=sc4f.copy()
            sc4f["Entry"]    =sc4f["price"].apply(lambda x: f"&#8377;{float(x):,.2f}")
            sc4f["Stop Loss"]=sc4f["price"].apply(lambda x: f"&#8377;{round(float(x)*.97,2):,.2f}")
            sc4f["Target 1"] =sc4f["price"].apply(lambda x: f"&#8377;{round(float(x)*1.04,2):,.2f}")
            sc4f["Target 2"] =sc4f["price"].apply(lambda x: f"&#8377;{round(float(x)*1.08,2):,.2f}")
            dcols=[c for c in ["symbol","signal","price","confidence","rsi","Entry","Stop Loss","Target 1","Target 2"] if c in sc4f.columns]
            disp=sc4f[dcols].copy()
            disp["symbol"]=disp["symbol"].str.replace(".NS","").str.replace(".BO","")
            disp.columns=[c.upper() for c in disp.columns]
            st.dataframe(disp,use_container_width=True,height=520)

# â”€â”€ TAB 7: CALENDAR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
with tabs[6]:
    events=get_calendar()
    today=datetime.now().date()
    st.markdown('<div class="slabel">Economic Calendar â€” Next 30 Days</div>', unsafe_allow_html=True)
    IMPACT={"EXTREME":("#ff4466","#4a0010","&#128680;"),"HIGH":("#ff8844","#3d1f00","&#9888;&#65039;"),"MEDIUM":("#ffcc00","#3d3200","&#128993;"),"HOLIDAY":("#4488ff","#001844","&#127958;&#65039;")}

    if not events:
        st.markdown('<div class="card" style="text-align:center;padding:2rem"><div style="font-size:2rem">&#9989;</div><div style="color:#64748b;margin-top:.5rem">No major events in next 30 days</div></div>', unsafe_allow_html=True)
    else:
        for e in events:
            color,bg,emoji=IMPACT.get(e["impact"],("#94a3b8","#1e2d45","&#9898;"))
            da=e.get("days_away",0)
            tl="TODAY" if da==0 else ("TOMORROW" if da==1 else f"in {da} days")
            tc2="#ff4466" if da<=1 else "#64748b"
            dt_str=e['date'].strftime('%A, %d %B %Y') if hasattr(e['date'],'strftime') else str(e['date'])
            st.markdown(f"""
            <div style="background:{bg};border:1px solid {color}33;border-left:4px solid {color};border-radius:10px;padding:1rem 1.2rem;margin-bottom:.6rem;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem">
                <div>
                    <div style="font-size:14px;font-weight:600;color:{color}">{emoji} {e['event']}</div>
                    <div style="font-size:12px;color:{color}88;margin-top:2px">{dt_str}</div>
                </div>
                <div style="text-align:right">
                    <div class="mono" style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:{tc2};font-weight:700">{tl}</div>
                    <span style="background:{color}22;color:{color};border:1px solid {color}44;border-radius:20px;padding:2px 10px;font-size:11px;font-weight:700;text-transform:uppercase">{e['impact']}</span>
                </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="slabel">RBI Policy Dates 2026</div>', unsafe_allow_html=True)
    rbi=["2026-02-07","2026-04-09","2026-06-05","2026-08-07","2026-10-09","2026-12-04"]
    rc2=st.columns(3)
    for i,d in enumerate(rbi):
        dt2=datetime.strptime(d,"%Y-%m-%d").date();past=dt2<today
        c2="#334155" if past else "#ff4466";bg2="#0d1117" if past else "rgba(74,0,16,0.2)"
        lbl="PAST" if past else ("TODAY" if dt2==today else "UPCOMING")
        with rc2[i%3]:
            st.markdown(f'<div style="background:{bg2};border:1px solid {c2}33;border-radius:8px;padding:.8rem 1rem;margin-bottom:.5rem;opacity:{"0.4" if past else "1"}"><div class="mono" style="font-size:13px;color:{c2};font-weight:600">{dt2.strftime("%d %B %Y")}</div><div style="font-size:10px;letter-spacing:2px;color:{c2}88;text-transform:uppercase;margin-top:2px">RBI Policy &#183; {lbl}</div></div>', unsafe_allow_html=True)

# â”€â”€ TAB 8: ENGINE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
with tabs[7]:
    st.markdown('<div class="slabel">Manual Engine Controls</div>', unsafe_allow_html=True)
    e1,e2,e3=st.columns(3)
    for col,title,desc,icon,fn,mod in [
        (e1,"Full Engine","Technical + News + ML + Risk","&#128202;","run_combiner","signal_combiner"),
        (e2,"News Scan","Refresh sentiment only","&#128240;","run_news_engine","news_engine"),
        (e3,"Risk Check","Portfolio stop loss check","&#128737;&#65039;","run_risk_check","risk_manager"),
    ]:
        with col:
            st.markdown(f'<div class="card" style="text-align:center;padding:1.5rem;margin-bottom:.5rem"><div style="font-size:2.5rem">{icon}</div><div style="font-weight:700;margin:.5rem 0 .2rem">{title}</div><div style="font-size:12px;color:#64748b">{desc}</div></div>', unsafe_allow_html=True)
            if st.button(f"&#9654; Run {title}",use_container_width=True,key=f"btn_{fn}"):
                with st.spinner(f"Running {title}..."):
                    try:
                        m=__import__(mod);getattr(m,fn)()
                        st.success(f"&#9989; {title} completed")
                        st.cache_data.clear()
                    except Exception as ex: st.error(f"&#10060; {ex}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="slabel">System Status</div>', unsafe_allow_html=True)
    sdf2=get_signals();ndf2=get_news()
    ls=fmt_t(sdf2["created_at"].max()) if not sdf2.empty else "Never"
    ln=fmt_t(ndf2["created_at"].max()) if not ndf2.empty else "Never"
    ss1,ss2,ss3,ss4=st.columns(4)
    for col2,lbl2,val2 in [(ss1,"Last Signal Run",ls),(ss2,"Last News Scan",ln),(ss3,"Total Signals",str(len(sdf2))),(ss4,"Total News",str(len(ndf2)))]:
        with col2:
            st.markdown(f'<div class="card"><div class="slabel">{lbl2}</div><div class="mono" style="font-size:15px;color:#00d4ff;font-weight:500">{val2}</div></div>', unsafe_allow_html=True)

# â”€â”€ SIDEBAR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
with st.sidebar:
    st.markdown('<div style="font-family:\'Outfit\',sans-serif;font-size:1.1rem;font-weight:700;margin-bottom:1rem;background:linear-gradient(135deg,#00ff88,#00d4ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent">&#9889; StockAI Controls</div>', unsafe_allow_html=True)
    st.markdown('<div class="slabel">Auto Refresh</div>', unsafe_allow_html=True)
    auto=st.toggle("Enable Auto Refresh",value=False)
    if auto:
        rate=st.selectbox("Interval",["30s","1min","5min"],index=1)
        secs={"30s":30,"1min":60,"5min":300}[rate]
        st.markdown(f'<meta http-equiv="refresh" content="{secs}">',unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="slabel">Add to Portfolio</div>', unsafe_allow_html=True)
    add_sym  =st.text_input("Symbol",placeholder="e.g. SBIN.NS")
    add_qty  =st.number_input("Qty",min_value=1,value=1)
    add_price=st.number_input("Buy &#8377;",min_value=0.0,value=0.0,step=0.5)
    if st.button("&#10133; Add Holding",use_container_width=True):
        if add_sym and add_price>0:
            try:
                supabase.table("stocks").upsert({"symbol":add_sym.upper(),"company_name":add_sym.upper().replace(".NS",""),"in_portfolio":True,"buy_price":add_price,"quantity":add_qty}).execute()
                st.success(f"&#9989; Added {add_sym}")
                st.cache_data.clear()
            except Exception as ex: st.error(f"&#10060; {ex}")

    st.markdown("---")
    st.markdown('<div class="slabel">Position Sizer</div>', unsafe_allow_html=True)
    ps_sym =st.text_input("Symbol",placeholder="RELIANCE.NS",key="ps")
    ps_port=st.number_input("Portfolio &#8377;",min_value=10000,value=100000,step=10000)
    if st.button("&#128208; Calculate Size",use_container_width=True):
        if ps_sym:
            try:
                from risk_manager import suggest_position
                suggest_position(ps_sym,ps_port)
                st.success("Check terminal for sizing")
            except Exception as ex: st.error(f"&#10060; {ex}")

    st.markdown("---")
    st.markdown(f'<div style="font-size:10px;color:#334155;text-align:center;font-family:\'DM Mono\',monospace">{datetime.now().strftime("%d %b %Y %H:%M:%S")}</div>', unsafe_allow_html=True)

