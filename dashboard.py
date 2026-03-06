import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import ta

load_dotenv()

st.set_page_config(
    page_title="StockAI Terminal",
    page_icon="▲",
    layout="wide",
    initial_sidebar_state="collapsed"
)

@st.cache_resource
def get_supabase():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

supabase = get_supabase()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700;900&family=Fira+Code:wght@300;400;500;600&family=Manrope:wght@300;400;500;600;700&display=swap');

:root {
  --black:   #0e0e0f;
  --ink:     #141416;
  --deep:    #1a1a1d;
  --card:    #1f1f23;
  --lift:    #252529;
  --edge:    #2e2e34;
  --line:    #38383f;
  --muted:   #5a5a66;
  --dim:     #7a7a88;
  --ghost:   #9898a8;
  --fog:     #b8b8c8;
  --text:    #e8e8f0;
  --bright:  #f5f5fa;
  --emerald: #00e87a;
  --em2:     #00c066;
  --em3:     rgba(0,232,122,0.08);
  --ember:   #ff8f3c;
  --ember2:  rgba(255,143,60,0.10);
  --ruby:    #ff4d6a;
  --ruby2:   rgba(255,77,106,0.08);
  --sapphire:#4d9fff;
  --sap2:    rgba(77,159,255,0.08);
}

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
  font-family: 'Manrope', sans-serif !important;
  background: var(--black) !important;
  color: var(--text) !important;
  -webkit-font-smoothing: antialiased;
}
.stApp { background: var(--black) !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 !important; max-width: 100% !important; }
section[data-testid="stSidebar"] { display: none !important; }

.topbar {
  height: 60px; background: var(--ink);
  border-bottom: 1px solid var(--edge);
  display: flex; align-items: center;
  justify-content: space-between; padding: 0 3rem;
}
.wordmark { display:flex; align-items:baseline; gap:10px; }
.wname { font-family:'Playfair Display',serif; font-size:1.35rem; font-weight:700; color:var(--bright); letter-spacing:-.3px; }
.wtag  { font-family:'Fira Code',monospace; font-size:9px; color:var(--emerald); letter-spacing:2px; border:1px solid var(--em2); padding:2px 7px; border-radius:2px; }
.topbar-r { display:flex; align-items:center; gap:2rem; }
.lpill { display:flex; align-items:center; gap:6px; background:var(--em3); border:1px solid var(--em2); padding:4px 10px; border-radius:20px; }
.ldot  { width:5px; height:5px; border-radius:50%; background:var(--emerald); box-shadow:0 0 6px var(--emerald); animation:pulse 2s ease-in-out infinite; }
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.2}}
.ltxt  { font-family:'Fira Code',monospace; font-size:9px; letter-spacing:2px; color:var(--emerald); }
.clock { font-family:'Fira Code',monospace; font-size:10px; color:var(--muted); }

.istrip { height:42px; background:var(--ink); border-bottom:1px solid var(--edge); display:flex; align-items:stretch; padding:0 3rem; }
.ii { display:flex; align-items:center; gap:12px; padding:0 2.5rem 0 0; margin-right:2.5rem; border-right:1px solid var(--edge); }
.ii:last-child{border-right:none}
.il{font-family:'Fira Code',monospace;font-size:8px;letter-spacing:2px;color:var(--muted)}
.iv{font-family:'Fira Code',monospace;font-size:13px;font-weight:500;color:var(--bright)}

.stTabs [data-baseweb="tab-list"]{background:var(--ink)!important;border-bottom:1px solid var(--edge)!important;gap:0!important;padding:0 3rem!important;margin-bottom:0!important}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--muted)!important;font-family:'Fira Code',monospace!important;font-size:9px!important;font-weight:500!important;letter-spacing:2.5px!important;text-transform:uppercase!important;padding:14px 20px!important;border-bottom:2px solid transparent!important;border-radius:0!important}
.stTabs [aria-selected="true"]{color:var(--bright)!important;border-bottom:2px solid var(--emerald)!important}
.stTabs [data-baseweb="tab-panel"]{background:transparent!important;padding:2.5rem 3rem!important}

[data-testid="metric-container"]{background:var(--card)!important;border:1px solid var(--edge)!important;border-top:2px solid var(--emerald)!important;border-radius:6px!important;padding:1.1rem 1.3rem!important}
[data-testid="stMetricValue"]{font-family:'Fira Code',monospace!important;font-size:1.35rem!important;font-weight:600!important;color:var(--bright)!important}
[data-testid="stMetricLabel"]{font-size:8px!important;letter-spacing:2.5px!important;text-transform:uppercase!important;color:var(--muted)!important;font-family:'Fira Code',monospace!important}
[data-testid="stMetricDelta"]{font-family:'Fira Code',monospace!important;font-size:11px!important}

.regime-wrap{border-radius:6px;padding:1.8rem 2rem;margin-bottom:2rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:1.5rem;border:1px solid}
.re-eyebrow{font-family:'Fira Code',monospace;font-size:9px;letter-spacing:3px;text-transform:uppercase;margin-bottom:8px}
.re-title{font-family:'Playfair Display',serif;font-size:2.1rem;font-weight:700;line-height:1;letter-spacing:-.5px}
.re-sub{font-family:'Fira Code',monospace;font-size:10px;margin-top:8px;opacity:.65;letter-spacing:.5px}
.rstat{text-align:center}
.rstat-n{font-family:'Fira Code',monospace;font-size:1.15rem;font-weight:600}
.rstat-l{font-family:'Fira Code',monospace;font-size:8px;letter-spacing:2px;opacity:.55;margin-top:3px}

.scard{background:var(--card);border:1px solid var(--edge);border-radius:6px;padding:1.1rem 1.2rem;margin-bottom:.6rem}
.scard.buy{border-left:3px solid var(--emerald)}
.scard.sell{border-left:3px solid var(--ruby)}
.scard.hold{border-left:3px solid var(--ember)}
.scard:hover{border-color:var(--line)}
.sname{font-family:'Playfair Display',serif;font-size:15px;font-weight:700;color:var(--bright)}
.spx{font-family:'Fira Code',monospace;font-size:14px;font-weight:600}
.srsi{font-family:'Fira Code',monospace;font-size:9px;color:var(--muted);letter-spacing:1px}
.sconf{font-family:'Fira Code',monospace;font-size:11px;font-weight:600}

.badge{display:inline-block;padding:2px 8px;border-radius:3px;font-family:'Fira Code',monospace;font-size:8px;letter-spacing:2px;font-weight:600;text-transform:uppercase}
.b-buy{background:var(--em3);color:var(--emerald);border:1px solid var(--em2)}
.b-sell{background:var(--ruby2);color:var(--ruby);border:1px solid rgba(255,77,106,.3)}
.b-hold{background:var(--ember2);color:var(--ember);border:1px solid rgba(255,143,60,.3)}
.b-bull{background:var(--em3);color:var(--emerald)}
.b-bear{background:var(--ruby2);color:var(--ruby)}
.b-neut{background:var(--ember2);color:var(--ember)}

.levels{display:flex;gap:5px;flex-wrap:wrap;margin-top:9px}
.lv{padding:3px 9px;border-radius:3px;font-family:'Fira Code',monospace;font-size:9px;font-weight:500}
.lv-e{background:var(--sap2);border:1px solid rgba(77,159,255,.2);color:var(--sapphire)}
.lv-sl{background:var(--ruby2);border:1px solid rgba(255,77,106,.18);color:var(--ruby)}
.lv-t1{background:var(--em3);border:1px solid rgba(0,232,122,.15);color:var(--em2)}
.lv-t2{background:var(--em3);border:1px solid rgba(0,232,122,.25);color:var(--emerald)}

.cbar{height:2px;background:var(--deep);border-radius:1px;margin-top:8px;overflow:hidden}
.cbar-f{height:100%;border-radius:1px}

.sh{font-family:'Playfair Display',serif;font-size:11px;font-weight:600;color:var(--dim);letter-spacing:3px;text-transform:uppercase;margin:1.8rem 0 1rem;display:flex;align-items:center;gap:1rem}
.sh::after{content:'';flex:1;height:1px;background:var(--edge)}

.prow{background:var(--card);border:1px solid var(--edge);border-radius:6px;padding:1.2rem 1.4rem;margin-bottom:.55rem}
.prow-name{font-family:'Playfair Display',serif;font-size:15px;font-weight:700;color:var(--bright)}
.prow-meta{font-family:'Fira Code',monospace;font-size:9px;color:var(--muted);margin-top:2px;letter-spacing:1px}

.ncard{background:var(--card);border:1px solid var(--edge);border-left:3px solid var(--edge);border-radius:6px;padding:.9rem 1.1rem;margin-bottom:.4rem}
.ncard.bull{border-left-color:var(--emerald)}
.ncard.bear{border-left-color:var(--ruby)}
.ncard.neut{border-left-color:var(--ember)}
.nhead{font-family:'Manrope',sans-serif;font-size:12px;font-weight:500;line-height:1.55}
.nmeta{font-family:'Fira Code',monospace;font-size:9px;color:var(--muted);margin-top:4px;letter-spacing:.5px}

.ecard{border-radius:6px;padding:1rem 1.3rem;margin-bottom:.5rem;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem;border:1px solid;border-left:3px solid}
.ev-name{font-family:'Manrope',sans-serif;font-size:13px;font-weight:600}
.ev-dt{font-family:'Fira Code',monospace;font-size:9px;margin-top:3px;letter-spacing:.5px}

.engbox{background:var(--card);border:1px solid var(--edge);border-top:2px solid var(--emerald);border-radius:6px;padding:2rem 1.5rem;text-align:center}
.engbox-icon{font-size:1.8rem;margin-bottom:.6rem}
.engbox-title{font-family:'Playfair Display',serif;font-size:1.05rem;font-weight:700;color:var(--bright)}
.engbox-desc{font-family:'Fira Code',monospace;font-size:9px;color:var(--muted);margin-top:5px;letter-spacing:1px}

.stbox{background:var(--card);border:1px solid var(--edge);border-radius:6px;padding:1rem 1.2rem}
.stbox-lbl{font-family:'Fira Code',monospace;font-size:8px;letter-spacing:2px;color:var(--muted);text-transform:uppercase;margin-bottom:5px}
.stbox-val{font-family:'Fira Code',monospace;font-size:1rem;font-weight:600;color:var(--emerald)}

.stSelectbox>div>div,.stTextInput>div>div,.stNumberInput>div>div{background:var(--card)!important;border:1px solid var(--edge)!important;border-radius:5px!important;color:var(--text)!important;font-family:'Fira Code',monospace!important;font-size:11px!important}
.stButton>button{background:transparent!important;color:var(--emerald)!important;border:1px solid var(--em2)!important;border-radius:4px!important;font-family:'Fira Code',monospace!important;font-size:9px!important;letter-spacing:2.5px!important;text-transform:uppercase!important;font-weight:600!important;padding:8px 20px!important;transition:all 0.15s!important}
.stButton>button:hover{background:var(--em3)!important;box-shadow:0 0 18px rgba(0,232,122,.12)!important}
[data-testid="stDataFrame"]{border:1px solid var(--edge)!important;border-radius:6px!important}
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--line);border-radius:2px}
</style>
""", unsafe_allow_html=True)

# ── DATA LOADERS ──────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_signals():
    try:
        r = supabase.table("signals").select("*").order("created_at", desc=True).limit(500).execute()
        return pd.DataFrame(r.data) if r.data else pd.DataFrame()
    except: return pd.DataFrame()

@st.cache_data(ttl=300)
def load_news():
    try:
        r = supabase.table("news").select("*").order("created_at", desc=True).limit(200).execute()
        return pd.DataFrame(r.data) if r.data else pd.DataFrame()
    except: return pd.DataFrame()

@st.cache_data(ttl=300)
def load_portfolio():
    try:
        r = supabase.table("stocks").select("*").eq("in_portfolio", True).execute()
        return r.data if r.data else []
    except: return []

@st.cache_data(ttl=600)
def load_market_regime():
    try:
        from market_regime import get_market_regime
        return get_market_regime()
    except: return "UNKNOWN", 0, {}

@st.cache_data(ttl=3600)
def load_nifty_data():
    try: return yf.Ticker("^NSEI").history(period="6mo", interval="1d")
    except: return pd.DataFrame()

@st.cache_data(ttl=300)
def load_index_prices():
    tickers = {"NIFTY 50":"^NSEI","SENSEX":"^BSESN","BANK NIFTY":"^NSEBANK","NIFTY IT":"^CNXIT"}
    out = {}
    for name, t in tickers.items():
        try:
            df = yf.Ticker(t).history(period="2d", interval="1d")
            if not df.empty:
                c = float(df["Close"].iloc[-1]); p = float(df["Close"].iloc[-2]) if len(df)>1 else c
                out[name] = {"price": c, "change": (c-p)/p*100}
        except: pass
    return out

@st.cache_data(ttl=600)
def load_sectors():
    sectors = {
        "Banking":["HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","AXISBANK.NS","KOTAKBANK.NS"],
        "IT":["TCS.NS","INFY.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS"],
        "Pharma":["SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS","LUPIN.NS"],
        "Auto":["MARUTI.NS","TATAMOTORS.NS","BAJAJ-AUTO.NS","HEROMOTOCO.NS","EICHERMOT.NS"],
        "FMCG":["HINDUNILVR.NS","ITC.NS","NESTLEIND.NS","DABUR.NS","MARICO.NS"],
        "Metals":["TATASTEEL.NS","HINDALCO.NS","JSWSTEEL.NS","VEDL.NS","SAIL.NS"],
        "Energy":["RELIANCE.NS","ONGC.NS","NTPC.NS","POWERGRID.NS","TATAPOWER.NS"],
        "Realty":["DLF.NS","GODREJPROP.NS","OBEROIRLTY.NS","PRESTIGE.NS","BRIGADE.NS"],
    }
    out = {}
    for s, stocks in sectors.items():
        ch = []
        for sym in stocks:
            try:
                df = yf.Ticker(sym).history(period="5d", interval="1d")
                if len(df)>=2: ch.append((float(df["Close"].iloc[-1])-float(df["Close"].iloc[0]))/float(df["Close"].iloc[0])*100)
            except: pass
        out[s] = round(sum(ch)/len(ch), 2) if ch else 0
    return out

@st.cache_data(ttl=600)
def get_chart(symbol, period="3mo"):
    try:
        df = yf.Ticker(symbol).history(period=period, interval="1d")
        if df.empty: return None
        df["EMA9"]  = ta.trend.ema_indicator(df["Close"], window=9)
        df["EMA21"] = ta.trend.ema_indicator(df["Close"], window=21)
        df["EMA50"] = ta.trend.ema_indicator(df["Close"], window=50)
        df["RSI"]   = ta.momentum.rsi(df["Close"], window=14)
        bb = ta.volatility.BollingerBands(df["Close"])
        df["BB_U"] = bb.bollinger_hband(); df["BB_L"] = bb.bollinger_lband()
        return df
    except: return None

@st.cache_data(ttl=300)
def get_events():
    try:
        from economic_calendar import get_upcoming_events as ge
        return ge(days_ahead=30)
    except: return []

# ── HELPERS ───────────────────────────────────────────────────────────────
def sig_color(s):
    s = str(s)
    if s.startswith("BUY"):  return "#00e87a"
    if s.startswith("SELL"): return "#ff4d6a"
    return "#ff8f3c"

def cbar_html(conf, color):
    return f'<div class="cbar"><div class="cbar-f" style="width:{min(float(conf),100):.0f}%;background:{color}"></div></div>'

def levels_html(price, is_buy):
    if not is_buy: return ""
    p=float(price); sl=round(p*.97,2); t1=round(p*1.04,2); t2=round(p*1.08,2)
    return f"""<div class="levels">
      <div class="lv lv-e">Entry&nbsp;₹{p:,.2f}</div>
      <div class="lv lv-sl">SL&nbsp;₹{sl:,.2f}<span style="opacity:.45">&nbsp;&minus;3%</span></div>
      <div class="lv lv-t1">T1&nbsp;₹{t1:,.2f}<span style="opacity:.45">&nbsp;+4%</span></div>
      <div class="lv lv-t2">T2&nbsp;₹{t2:,.2f}<span style="opacity:.45">&nbsp;+8%</span></div>
    </div>"""

def fmt_t(ts):
    try: return pd.to_datetime(ts).strftime("%d %b  %H:%M")
    except: return str(ts)[:16]

def pt(h=320, r=0):
    return dict(height=h, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#141416",
                margin=dict(l=0, r=r, t=8, b=0), font=dict(family="Fira Code", color="#5a5a66"))

# ── TOP BAR ───────────────────────────────────────────────────────────────
now_str = datetime.now().strftime("%a, %d %b %Y  •  %H:%M:%S IST")
st.markdown(f"""
<div class="topbar">
  <div class="wordmark">
    <span class="wname">StockAI</span>
    <span class="wtag">PRO TERMINAL</span>
  </div>
  <div class="topbar-r">
    <div class="lpill"><div class="ldot"></div><span class="ltxt">LIVE</span></div>
    <span class="clock">{now_str}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── INDEX STRIP ───────────────────────────────────────────────────────────
idx = load_index_prices()
items = ""
for name, d in idx.items():
    c  = "#00e87a" if d["change"]>=0 else "#ff4d6a"
    ar = "&#9650;" if d["change"]>=0 else "&#9660;"
    items += f'<div class="ii"><span class="il">{name}</span><span class="iv">{d["price"]:,.0f}</span><span style="color:{c};font-family:\'Fira Code\',monospace;font-size:10px">{ar} {abs(d["change"]):.2f}%</span></div>'
st.markdown(f'<div class="istrip">{items}</div>', unsafe_allow_html=True)

# ── TABS ──────────────────────────────────────────────────────────────────
tabs = st.tabs(["Overview","Signals","Portfolio","News Feed","Charts","Screener","Calendar","Engine"])

# ══ TAB 1 — OVERVIEW ══════════════════════════════════════════════════════
with tabs[0]:
    regime, rscore, rdet = load_market_regime()
    ni = rdet.get("nifty",{}); vi = rdet.get("vix",{})
    RSTYLE = {
        "STRONG_BULL":("#00e87a","rgba(0,232,122,.06)","rgba(0,232,122,.25)"),
        "BULL":       ("#00e87a","rgba(0,232,122,.04)","rgba(0,232,122,.18)"),
        "NEUTRAL":    ("#ff8f3c","rgba(255,143,60,.05)","rgba(255,143,60,.2)"),
        "BEAR":       ("#ff4d6a","rgba(255,77,106,.06)","rgba(255,77,106,.2)"),
        "STRONG_BEAR":("#ff4d6a","rgba(255,77,106,.08)","rgba(255,77,106,.28)"),
        "UNKNOWN":    ("#5a5a66","rgba(90,90,102,.04)","rgba(90,90,102,.15)"),
    }
    rc,rbg,rbd = RSTYLE.get(regime,("#5a5a66","rgba(0,0,0,.3)","rgba(90,90,102,.15)"))
    EMOJIS = {"STRONG_BULL":"&#8593;&#8593;","BULL":"&#8593;","NEUTRAL":"&mdash;","BEAR":"&#8595;","STRONG_BEAR":"&#8595;&#8595;","UNKNOWN":"?"}
    st.markdown(f"""
    <div class="regime-wrap" style="background:{rbg};border-color:{rbd}">
      <div>
        <div class="re-eyebrow" style="color:{rc}88">Market Regime &nbsp;&bull;&nbsp; AI Assessment</div>
        <div class="re-title"   style="color:{rc}">{EMOJIS.get(regime,"?")} &nbsp;{regime.replace("_"," ").title()}</div>
        <div class="re-sub"     style="color:{rc}">Score: {rscore:+.3f} &nbsp;&nbsp;|&nbsp;&nbsp; Nifty RSI: {ni.get("rsi",0):.1f} &nbsp;&nbsp;|&nbsp;&nbsp; India VIX: {vi.get("current",0):.1f}</div>
      </div>
      <div style="display:flex;gap:3.5rem;flex-wrap:wrap">
        <div class="rstat"><div class="rstat-n" style="color:{'#00e87a' if ni.get('ret_1m',0)>=0 else '#ff4d6a'}">{ni.get('ret_1m',0):+.2f}%</div><div class="rstat-l" style="color:{rc}99">Nifty 1M</div></div>
        <div class="rstat"><div class="rstat-n" style="color:{'#00e87a' if ni.get('ret_3m',0)>=0 else '#ff4d6a'}">{ni.get('ret_3m',0):+.2f}%</div><div class="rstat-l" style="color:{rc}99">Nifty 3M</div></div>
        <div class="rstat"><div class="rstat-n" style="color:{'#ff4d6a' if vi.get('current',0)>vi.get('avg',20) else '#00e87a'}">{vi.get('current',0):.1f}&nbsp;/&nbsp;{vi.get('avg',0):.1f}</div><div class="rstat-l" style="color:{rc}99">VIX / Avg</div></div>
      </div>
    </div>""", unsafe_allow_html=True)

    sdf=load_signals(); ndf=load_news()
    lat=sdf.drop_duplicates(subset="symbol",keep="first") if not sdf.empty else pd.DataFrame()
    bn=len(lat[lat["signal"].str.startswith("BUY")])  if not lat.empty else 0
    sn=len(lat[lat["signal"].str.startswith("SELL")]) if not lat.empty else 0
    hn=len(lat[~lat["signal"].str.startswith("BUY")&~lat["signal"].str.startswith("SELL")]) if not lat.empty else 0
    ac=round(lat["confidence"].mean(),1) if not lat.empty else 0
    bln=len(ndf[ndf["sentiment"]=="BULLISH"]) if not ndf.empty else 0
    brn=len(ndf[ndf["sentiment"]=="BEARISH"]) if not ndf.empty else 0
    m1,m2,m3,m4,m5,m6=st.columns(6)
    with m1: st.metric("Buy Signals",bn)
    with m2: st.metric("Sell Signals",sn)
    with m3: st.metric("Hold Signals",hn)
    with m4: st.metric("Avg Confidence",f"{ac}%")
    with m5: st.metric("Bullish News",bln)
    with m6: st.metric("Bearish News",brn)

    col1,col2=st.columns([3,2])
    with col1:
        st.markdown('<div class="sh">Nifty 50 &nbsp;&bull;&nbsp; 6-Month Chart</div>', unsafe_allow_html=True)
        ndf2=load_nifty_data()
        if not ndf2.empty:
            ndf2["EMA50"]=ta.trend.ema_indicator(ndf2["Close"],window=50)
            ndf2["EMA200"]=ta.trend.ema_indicator(ndf2["Close"],window=200)
            fig=go.Figure()
            fig.add_trace(go.Candlestick(x=ndf2.index,open=ndf2["Open"],high=ndf2["High"],low=ndf2["Low"],close=ndf2["Close"],increasing_line_color="#00e87a",decreasing_line_color="#ff4d6a",showlegend=False))
            fig.add_trace(go.Scatter(x=ndf2.index,y=ndf2["EMA50"],line=dict(color="#4d9fff",width=1.3),name="EMA50"))
            fig.add_trace(go.Scatter(x=ndf2.index,y=ndf2["EMA200"],line=dict(color="#ff8f3c",width=1.3),name="EMA200"))
            fig.update_layout(**pt(310),xaxis=dict(showgrid=False,color="#5a5a66",rangeslider=dict(visible=False)),yaxis=dict(showgrid=True,gridcolor="#1f1f23",color="#5a5a66"),legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(color="#5a5a66"),orientation="h",y=1.05))
            st.plotly_chart(fig,use_container_width=True)
    with col2:
        st.markdown('<div class="sh">Sector Performance &nbsp;&bull;&nbsp; 5 Days</div>', unsafe_allow_html=True)
        sp=load_sectors()
        if sp:
            snames,svals=list(sp.keys()),list(sp.values())
            fig2=go.Figure(go.Bar(x=svals,y=snames,orientation="h",marker_color=["#00e87a" if v>=0 else "#ff4d6a" for v in svals],text=[f"{v:+.2f}%" for v in svals],textposition="outside",textfont=dict(color="#e8e8f0",size=10,family="Fira Code")))
            fig2.update_layout(**pt(310,r=55),xaxis=dict(showgrid=True,gridcolor="#1f1f23",color="#5a5a66",zeroline=True,zerolinecolor="#2e2e34"),yaxis=dict(showgrid=False,color="#b8b8c8"))
            st.plotly_chart(fig2,use_container_width=True)

    st.markdown('<div class="sh">High Conviction Signals &nbsp;&bull;&nbsp; Entry / SL / Targets</div>', unsafe_allow_html=True)
    if not lat.empty:
        strong=lat[lat["confidence"]>=30].sort_values("confidence",ascending=False).head(6)
        if not strong.empty:
            cols=st.columns(3)
            for i,(_,row) in enumerate(strong.iterrows()):
                sig=str(row.get("signal","")); conf=float(row.get("confidence",0)); price=float(row.get("price",0))
                color=sig_color(sig); cls="buy" if sig.startswith("BUY") else ("sell" if sig.startswith("SELL") else "hold")
                with cols[i%3]:
                    st.markdown(f"""<div class="scard {cls}">
                      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:7px">
                        <span class="sname">{str(row.get('symbol','')).replace('.NS','')}</span>
                        <span class="badge b-{cls}">{sig.split()[0]}</span>
                      </div>
                      <div style="display:flex;justify-content:space-between;align-items:baseline">
                        <span class="spx" style="color:{color}">₹{price:,.2f}</span>
                        <span class="sconf" style="color:{color}">{conf:.1f}%</span>
                      </div>
                      <div class="srsi" style="margin-top:3px">RSI &nbsp;{float(row.get('rsi',0)):.1f}</div>
                      {cbar_html(conf,color)}{levels_html(price,sig.startswith("BUY"))}
                    </div>""", unsafe_allow_html=True)
        else: st.info("No high conviction signals right now.")
    else: st.info("No data yet. Run the engine.")

# ══ TAB 2 — SIGNALS ═══════════════════════════════════════════════════════
with tabs[1]:
    sdf=load_signals()
    if sdf.empty: st.info("No signals yet. Run the engine.")
    else:
        lat=sdf.drop_duplicates(subset="symbol",keep="first")
        f1,f2,f3,f4=st.columns(4)
        with f1: sf=st.selectbox("Signal",["All","BUY","SELL","HOLD"])
        with f2: mc=st.slider("Min Confidence %",0,100,0)
        with f3: sb=st.selectbox("Sort By",["Confidence ↓","Confidence ↑","RSI ↓","RSI ↑","Symbol"])
        with f4: srch=st.text_input("Search",placeholder="e.g. SBIN")
        flt=lat.copy()
        if sf!="All": flt=flt[flt["signal"].str.startswith(sf)]
        flt=flt[flt["confidence"]>=mc]
        if srch: flt=flt[flt["symbol"].str.contains(srch.upper(),na=False)]
        sm={"Confidence ↓":("confidence",False),"Confidence ↑":("confidence",True),"RSI ↓":("rsi",False),"RSI ↑":("rsi",True),"Symbol":("symbol",True)}
        sc2,sa2=sm[sb]
        if sc2 in flt.columns: flt=flt.sort_values(sc2,ascending=sa2)
        st.markdown(f'<p style="font-family:\'Fira Code\',monospace;font-size:9px;color:#5a5a66;letter-spacing:1.5px;margin-bottom:1.5rem">SHOWING <span style="color:#e8e8f0">{len(flt)}</span> OF {len(lat)} INSTRUMENTS</p>', unsafe_allow_html=True)
        for label,subset,cls in [("Buy Signals",flt[flt["signal"].str.startswith("BUY")],"buy"),("Sell Signals",flt[flt["signal"].str.startswith("SELL")],"sell"),("Hold Signals",flt[~flt["signal"].str.startswith("BUY")&~flt["signal"].str.startswith("SELL")],"hold")]:
            if len(subset)==0: continue
            st.markdown(f'<div class="sh">{label} &nbsp;&bull;&nbsp; {len(subset)}</div>', unsafe_allow_html=True)
            cols=st.columns(4)
            for i,(_,row) in enumerate(subset.iterrows()):
                sig=str(row.get("signal","")); conf=float(row.get("confidence",0)); price=float(row.get("price",0))
                color=sig_color(sig); rsn=str(row.get("reason",""))
                rsn=rsn[:80]+"..." if len(rsn)>80 else rsn
                with cols[i%4]:
                    st.markdown(f"""<div class="scard {cls}">
                      <div style="display:flex;justify-content:space-between;margin-bottom:7px">
                        <span class="sname">{str(row.get('symbol','')).replace('.NS','')}</span>
                        <span class="badge b-{cls}">{sig.split()[0]}</span>
                      </div>
                      <div class="spx" style="color:{color}">₹{price:,.2f}</div>
                      <div style="display:flex;justify-content:space-between;margin:4px 0">
                        <span class="srsi">RSI {float(row.get('rsi',0)):.1f}</span>
                        <span class="sconf" style="color:{color}">{conf:.1f}%</span>
                      </div>
                      {cbar_html(conf,color)}{levels_html(price,sig.startswith("BUY"))}
                      <div style="font-family:'Fira Code',monospace;font-size:9px;color:#38383f;margin-top:8px;line-height:1.6">{rsn}</div>
                      <div style="font-family:'Fira Code',monospace;font-size:9px;color:#2e2e34;margin-top:4px">{fmt_t(row.get('created_at',''))}</div>
                    </div>""", unsafe_allow_html=True)

# ══ TAB 3 — PORTFOLIO ═════════════════════════════════════════════════════
with tabs[2]:
    portfolio=load_portfolio()
    if not portfolio:
        st.markdown('<div style="text-align:center;padding:4rem;color:#5a5a66"><div style="font-family:\'Playfair Display\',serif;font-size:3rem;opacity:.15;margin-bottom:1rem">&#9650;</div><div style="font-family:\'Fira Code\',monospace;font-size:9px;letter-spacing:3px">NO HOLDINGS &nbsp;&bull;&nbsp; ADD VIA ENGINE TAB</div></div>', unsafe_allow_html=True)
    else:
        rows=[]; ti=tc=0
        for h in portfolio:
            try:
                sym=h["symbol"]; bp=float(h.get("buy_price",0)); qty=float(h.get("quantity",0))
                if not bp or not qty: continue
                df=yf.Ticker(sym).history(period="5d")
                cp=float(df["Close"].iloc[-1]) if not df.empty else bp
                prs=(cp-bp)*qty; ppc=(cp-bp)/bp*100
                wc=(cp-float(df["Close"].iloc[0]))/float(df["Close"].iloc[0])*100 if len(df)>1 else 0
                ti+=bp*qty; tc+=cp*qty
                rows.append({"sym":sym.replace(".NS","").replace(".BO",""),"buy":bp,"cur":cp,"qty":int(qty),"prs":prs,"ppc":ppc,"wc":wc,"val":cp*qty})
            except: pass
        tp=tc-ti; tpp=(tp/ti*100) if ti else 0
        p1,p2,p3,p4=st.columns(4)
        with p1: st.metric("Total Invested",f"₹{ti:,.0f}")
        with p2: st.metric("Current Value", f"₹{tc:,.0f}")
        with p3: st.metric("Total P&L",     f"₹{tp:+,.0f}",delta=f"{tpp:+.2f}%")
        with p4: st.metric("Holdings",      len(rows))
        if rows:
            pc1,pc2=st.columns([2,1])
            with pc1:
                st.markdown('<div class="sh">Holdings &nbsp;&bull;&nbsp; Entry / SL / T1 / T2</div>', unsafe_allow_html=True)
                for r in sorted(rows,key=lambda x:x["ppc"],reverse=True):
                    pc="#00e87a" if r["ppc"]>=0 else "#ff4d6a"
                    wc2="#00e87a" if r["wc"]>=0 else "#ff4d6a"
                    sl=round(r["buy"]*.97,2); t1=round(r["buy"]*1.04,2); t2=round(r["buy"]*1.08,2)
                    st.markdown(f"""<div class="prow" style="border-left:3px solid {pc}">
                      <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:1.2rem;align-items:center">
                        <div><div class="prow-name">{r['sym']}</div><div class="prow-meta">{r['qty']} SHS &nbsp;&bull;&nbsp; BUY ₹{r['buy']:,.2f}</div></div>
                        <div style="text-align:center"><div style="font-family:'Fira Code',monospace;font-size:8px;color:#5a5a66;letter-spacing:2px;margin-bottom:3px">LTP</div><div style="font-family:'Fira Code',monospace;font-size:1rem;font-weight:600;color:#00e87a">₹{r['cur']:,.2f}</div></div>
                        <div style="text-align:center"><div style="font-family:'Fira Code',monospace;font-size:8px;color:#5a5a66;letter-spacing:2px;margin-bottom:3px">P&amp;L</div><div style="font-family:'Fira Code',monospace;font-weight:600;color:{pc}">{r['ppc']:+.2f}%</div><div style="font-family:'Fira Code',monospace;font-size:10px;color:{pc}">₹{r['prs']:+,.0f}</div></div>
                        <div style="text-align:center"><div style="font-family:'Fira Code',monospace;font-size:8px;color:#5a5a66;letter-spacing:2px;margin-bottom:3px">WEEK</div><div style="font-family:'Fira Code',monospace;font-weight:600;color:{wc2}">{r['wc']:+.2f}%</div></div>
                        <div style="text-align:center"><div style="font-family:'Fira Code',monospace;font-size:8px;color:#5a5a66;letter-spacing:2px;margin-bottom:3px">VALUE</div><div style="font-family:'Fira Code',monospace;font-weight:600">₹{r['val']:,.0f}</div></div>
                      </div>
                      <div style="margin-top:10px;padding:9px 11px;background:#1a1a1d;border-radius:4px;border:1px solid #2e2e34">
                        <div style="font-family:'Fira Code',monospace;font-size:8px;color:#5a5a66;letter-spacing:2px;margin-bottom:6px">TRADE LEVELS</div>
                        <div style="display:flex;gap:5px;flex-wrap:wrap">
                          <div class="lv lv-e">Entry ₹{r['buy']:,.2f}</div>
                          <div class="lv lv-sl">SL ₹{sl:,.2f}<span style="opacity:.45"> -3%</span></div>
                          <div class="lv lv-t1">T1 ₹{t1:,.2f}<span style="opacity:.45"> +4%</span></div>
                          <div class="lv lv-t2">T2 ₹{t2:,.2f}<span style="opacity:.45"> +8%</span></div>
                        </div>
                      </div>
                      {cbar_html(min(abs(r['ppc'])*5,100),pc)}
                    </div>""", unsafe_allow_html=True)
            with pc2:
                st.markdown('<div class="sh">Allocation</div>', unsafe_allow_html=True)
                COLORS=["#00e87a","#4d9fff","#ff8f3c","#a855f7","#00c066","#ff4d6a","#f0e040","#5de3a8"]
                fig_pie=go.Figure(go.Pie(labels=[r["sym"] for r in rows],values=[r["val"] for r in rows],hole=0.68,marker_colors=COLORS[:len(rows)],textinfo="label+percent",textfont=dict(family="Fira Code",size=10,color="#e8e8f0"),hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<extra></extra>"))
                fig_pie.add_annotation(text=f"₹{tc:,.0f}",x=0.5,y=0.5,font_size=11,font_color="#e8e8f0",font_family="Fira Code",showarrow=False)
                fig_pie.update_layout(**pt(280),showlegend=False)
                st.plotly_chart(fig_pie,use_container_width=True)

# ══ TAB 4 — NEWS ══════════════════════════════════════════════════════════
with tabs[3]:
    ndf=load_news()
    if ndf.empty: st.info("No news data yet.")
    else:
        nc1,nc2,nc3=st.columns(3)
        with nc1: sf2=st.selectbox("Sentiment",["All","BULLISH","BEARISH","NEUTRAL"])
        with nc2: sy2=st.text_input("Symbol Filter",placeholder="e.g. RELIANCE")
        with nc3:
            srcs=["All"]+list(ndf["source"].dropna().unique()) if "source" in ndf.columns else ["All"]
            src_f=st.selectbox("Source",srcs)
        fn=ndf.copy()
        if sf2!="All": fn=fn[fn["sentiment"]==sf2]
        if sy2: fn=fn[fn["related_symbol"].str.contains(sy2.upper(),na=False)]
        if src_f!="All" and "source" in fn.columns: fn=fn[fn["source"]==src_f]
        tn=len(ndf); bl=len(ndf[ndf["sentiment"]=="BULLISH"]); br=len(ndf[ndf["sentiment"]=="BEARISH"]); nt=len(ndf[ndf["sentiment"]=="NEUTRAL"])
        st.markdown(f'<div style="background:var(--card);border:1px solid var(--edge);border-radius:6px;padding:.9rem 1.2rem;margin-bottom:1.2rem"><div style="display:flex;justify-content:space-between;font-family:\'Fira Code\',monospace;font-size:9px;color:#5a5a66;letter-spacing:1.5px;margin-bottom:7px"><span>BULLISH {bl} ({bl/tn*100:.0f}%)</span><span>NEUTRAL {nt} ({nt/tn*100:.0f}%)</span><span>BEARISH {br} ({br/tn*100:.0f}%)</span></div><div style="display:flex;height:3px;border-radius:2px;overflow:hidden"><div style="width:{bl/tn*100:.0f}%;background:#00e87a"></div><div style="width:{nt/tn*100:.0f}%;background:#ff8f3c"></div><div style="width:{br/tn*100:.0f}%;background:#ff4d6a"></div></div></div>', unsafe_allow_html=True)
        SC={"BULLISH":"#00e87a","BEARISH":"#ff4d6a","NEUTRAL":"#ff8f3c"}
        SB={"BULLISH":"bull","BEARISH":"bear","NEUTRAL":"neut"}
        for _,row in fn.head(60).iterrows():
            sent=str(row.get("sentiment","NEUTRAL")); score=float(row.get("sentiment_score",0))
            sc3=SC.get(sent,"#ff8f3c"); sb2=SB.get(sent,"neut"); st2=f"b-{sb2.replace('bull','buy').replace('bear','sell').replace('neut','hold')}"
            sym=str(row.get("related_symbol","GENERAL")).replace(".NS","")
            src=str(row.get("source","")); hl=str(row.get("headline",""))
            st.markdown(f'<div class="ncard {sb2}"><div style="display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;align-items:flex-start"><div style="flex:1;min-width:200px"><div class="nhead">{hl}</div><div class="nmeta">{src} &nbsp;&bull;&nbsp; {sym} &nbsp;&bull;&nbsp; {fmt_t(row.get("published_at",""))}</div></div><div style="text-align:right;flex-shrink:0"><span class="badge {st2}">{sent}</span><div style="font-family:\'Fira Code\',monospace;font-size:11px;color:{sc3};margin-top:5px">{score:+.3f}</div></div></div></div>', unsafe_allow_html=True)

# ══ TAB 5 — CHARTS ════════════════════════════════════════════════════════
with tabs[4]:
    sdf=load_signals()
    syms=sorted(sdf["symbol"].dropna().unique().tolist()) if not sdf.empty else ["RELIANCE.NS","TCS.NS","HDFCBANK.NS"]
    cc1,cc2=st.columns([2,1])
    with cc1: csym=st.selectbox("Instrument",syms,format_func=lambda x:x.replace(".NS",""))
    with cc2: cper=st.selectbox("Period",["1mo","3mo","6mo","1y"],index=1)
    dfc=get_chart(csym,cper)
    if dfc is not None and not dfc.empty:
        fig_c=make_subplots(rows=3,cols=1,shared_xaxes=True,row_heights=[0.6,.2,.2],vertical_spacing=.025)
        fig_c.add_trace(go.Candlestick(x=dfc.index,open=dfc["Open"],high=dfc["High"],low=dfc["Low"],close=dfc["Close"],increasing_line_color="#00e87a",decreasing_line_color="#ff4d6a",showlegend=False),row=1,col=1)
        fig_c.add_trace(go.Scatter(x=dfc.index,y=dfc["BB_U"],line=dict(color="rgba(77,159,255,.22)",width=1,dash="dot"),showlegend=False),row=1,col=1)
        fig_c.add_trace(go.Scatter(x=dfc.index,y=dfc["BB_L"],line=dict(color="rgba(77,159,255,.22)",width=1,dash="dot"),fill="tonexty",fillcolor="rgba(77,159,255,.03)",showlegend=False),row=1,col=1)
        for ema,color in [("EMA9","#4d9fff"),("EMA21","#ff8f3c"),("EMA50","#a855f7")]:
            fig_c.add_trace(go.Scatter(x=dfc.index,y=dfc[ema],line=dict(color=color,width=1.2),name=ema),row=1,col=1)
        fig_c.add_trace(go.Bar(x=dfc.index,y=dfc["Volume"],marker_color=["#00e87a" if c>=o else "#ff4d6a" for c,o in zip(dfc["Close"],dfc["Open"])],showlegend=False),row=2,col=1)
        fig_c.add_trace(go.Scatter(x=dfc.index,y=dfc["RSI"],line=dict(color="#a855f7",width=1.5),showlegend=False),row=3,col=1)
        fig_c.add_hline(y=70,line=dict(color="rgba(255,77,106,.4)",dash="dot"),row=3,col=1)
        fig_c.add_hline(y=30,line=dict(color="rgba(0,232,122,.4)",dash="dot"),row=3,col=1)
        fig_c.add_hline(y=50,line=dict(color="rgba(90,90,102,.3)",dash="dot"),row=3,col=1)
        fig_c.update_layout(**pt(580),
            xaxis=dict(showgrid=False,color="#5a5a66",rangeslider=dict(visible=False)),
            xaxis2=dict(showgrid=False,color="#5a5a66"),xaxis3=dict(showgrid=False,color="#5a5a66"),
            yaxis=dict(showgrid=True,gridcolor="#1f1f23",color="#5a5a66"),
            yaxis2=dict(showgrid=True,gridcolor="#1f1f23",color="#5a5a66"),
            yaxis3=dict(showgrid=True,gridcolor="#1f1f23",color="#5a5a66",range=[0,100]),
            legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(color="#5a5a66"),orientation="h",y=1.02))
        st.plotly_chart(fig_c,use_container_width=True)
        lr=dfc.iloc[-1]
        s1,s2,s3,s4,s5=st.columns(5)
        with s1: st.metric("Close",  f"₹{lr['Close']:,.2f}")
        with s2: st.metric("RSI",    f"{lr['RSI']:.1f}")
        with s3: st.metric("EMA 9",  f"₹{lr['EMA9']:,.2f}")
        with s4: st.metric("EMA 21", f"₹{lr['EMA21']:,.2f}")
        with s5: st.metric("EMA 50", f"₹{lr['EMA50']:,.2f}")
        st.markdown('<div class="sh">Trade Levels &nbsp;&bull;&nbsp; Current Price</div>', unsafe_allow_html=True)
        cp=float(lr["Close"]); sl=round(cp*.97,2); t1=round(cp*1.04,2); t2=round(cp*1.08,2); rr=round((t1-cp)/(cp-sl),2)
        tl1,tl2,tl3,tl4,tl5=st.columns(5)
        with tl1: st.metric("Entry Price",  f"₹{cp:,.2f}")
        with tl2: st.metric("Stop Loss",    f"₹{sl:,.2f}",delta="-3%",delta_color="inverse")
        with tl3: st.metric("Target 1",     f"₹{t1:,.2f}",delta="+4%")
        with tl4: st.metric("Target 2",     f"₹{t2:,.2f}",delta="+8%")
        with tl5: st.metric("Risk/Reward",  f"1 : {rr}")

# ══ TAB 6 — SCREENER ══════════════════════════════════════════════════════
with tabs[5]:
    sdf=load_signals()
    if sdf.empty: st.info("No signal data.")
    else:
        lat=sdf.drop_duplicates(subset="symbol",keep="first")
        sc1,sc2,sc3,sc4,sc5=st.columns(5)
        with sc1: ssig=st.selectbox("Signal",["All","BUY","SELL","HOLD"],key="ss")
        with sc2: scon=st.slider("Min Conf %",0,100,0,key="sc")
        with sc3: srmi=st.slider("RSI Min",0,100,0,key="srn")
        with sc4: srma=st.slider("RSI Max",0,100,100,key="srx")
        with sc5: ssrt=st.selectbox("Sort By",["Confidence","RSI","Price","Symbol"],key="so")
        scr=lat.copy()
        if ssig!="All": scr=scr[scr["signal"].str.startswith(ssig)]
        scr=scr[scr["confidence"]>=scon]
        if "rsi" in scr.columns: scr=scr[(scr["rsi"]>=srmi)&(scr["rsi"]<=srma)]
        scol2={"Confidence":"confidence","RSI":"rsi","Price":"price","Symbol":"symbol"}.get(ssrt,"confidence")
        if scol2 in scr.columns: scr=scr.sort_values(scol2,ascending=False)
        st.markdown(f'<p style="font-family:\'Fira Code\',monospace;font-size:9px;color:#5a5a66;letter-spacing:1.5px;margin-bottom:1.2rem"><span style="color:#e8e8f0">{len(scr)}</span> instruments matched</p>', unsafe_allow_html=True)
        if not scr.empty:
            scr=scr.copy()
            scr["Entry"]    =scr["price"].apply(lambda x:round(float(x),2))
            scr["Stop Loss"]=scr["price"].apply(lambda x:round(float(x)*.97,2))
            scr["Target 1"] =scr["price"].apply(lambda x:round(float(x)*1.04,2))
            scr["Target 2"] =scr["price"].apply(lambda x:round(float(x)*1.08,2))
            dcols=[c for c in ["symbol","signal","price","confidence","rsi","Entry","Stop Loss","Target 1","Target 2"] if c in scr.columns]
            disp=scr[dcols].copy()
            disp["symbol"]=disp["symbol"].str.replace(".NS","").str.replace(".BO","")
            disp.columns=[c.upper() for c in disp.columns]
            fmt={k:v for k,v in {"PRICE":"₹{:,.2f}","CONFIDENCE":"{:.1f}%","RSI":"{:.1f}","ENTRY":"₹{:,.2f}","STOP LOSS":"₹{:,.2f}","TARGET 1":"₹{:,.2f}","TARGET 2":"₹{:,.2f}"}.items() if k in disp.columns}
            st.dataframe(disp.style.applymap(lambda v:"color:#00e87a;font-weight:bold" if str(v).startswith("BUY") else ("color:#ff4d6a;font-weight:bold" if str(v).startswith("SELL") else ""),subset=["SIGNAL"] if "SIGNAL" in disp.columns else []).format(fmt),use_container_width=True,height=520)

# ══ TAB 7 — CALENDAR ══════════════════════════════════════════════════════
with tabs[6]:
    events=get_events(); today=datetime.now().date()
    IMPACT={"EXTREME":("#ff4d6a","rgba(255,77,106,.06)","rgba(255,77,106,.25)"),"HIGH":("#ff8f3c","rgba(255,143,60,.05)","rgba(255,143,60,.2)"),"MEDIUM":("#4d9fff","rgba(77,159,255,.04)","rgba(77,159,255,.15)"),"HOLIDAY":("#5a5a66","rgba(90,90,102,.03)","rgba(90,90,102,.12)")}
    st.markdown('<div class="sh">Economic Calendar &nbsp;&bull;&nbsp; Next 30 Days</div>', unsafe_allow_html=True)
    if not events:
        st.markdown('<p style="font-family:\'Fira Code\',monospace;font-size:9px;color:#5a5a66;letter-spacing:2px;padding:2rem;text-align:center">NO MAJOR EVENTS SCHEDULED</p>', unsafe_allow_html=True)
    else:
        for e in events:
            c,bg,bd=IMPACT.get(e["impact"],("#5a5a66","rgba(0,0,0,.2)","rgba(90,90,102,.15)"))
            da=e.get("days_away",0)
            tl="Today" if da==0 else ("Tomorrow" if da==1 else f"In {da} days")
            tc2="#ff4d6a" if da<=1 else "#5a5a66"
            dt_s=e['date'].strftime('%A, %d %B %Y') if hasattr(e['date'],'strftime') else str(e['date'])
            st.markdown(f'<div class="ecard" style="background:{bg};border-color:{bd};border-left-color:{c}"><div><div class="ev-name" style="color:{c}">{e["event"]}</div><div class="ev-dt" style="color:{c}88">{dt_s}</div></div><div style="text-align:right;display:flex;flex-direction:column;align-items:flex-end;gap:5px"><div style="font-family:\'Fira Code\',monospace;font-size:9px;letter-spacing:2px;color:{tc2};font-weight:600">{tl.upper()}</div><span class="badge" style="background:{c}18;color:{c};border:1px solid {c}40">{e["impact"]}</span></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="sh">RBI Policy Schedule &nbsp;&bull;&nbsp; 2026</div>', unsafe_allow_html=True)
    rbi=["2026-02-07","2026-04-09","2026-06-05","2026-08-07","2026-10-09","2026-12-04"]
    rcols=st.columns(3)
    for i,d in enumerate(rbi):
        dt2=datetime.strptime(d,"%Y-%m-%d").date(); past=dt2<today
        c2="#2e2e34" if past else "#ff4d6a"; lbl="Concluded" if past else ("Today" if dt2==today else "Upcoming")
        with rcols[i%3]:
            st.markdown(f'<div style="background:{"#1a1a1d" if past else "rgba(255,77,106,.04)"};border:1px solid {c2}55;border-left:3px solid {c2};border-radius:5px;padding:.85rem 1rem;margin-bottom:.5rem;opacity:{"0.35" if past else "1"}"><div style="font-family:\'Playfair Display\',serif;font-size:13px;font-weight:600;color:{c2}">{dt2.strftime("%d %B %Y")}</div><div style="font-family:\'Fira Code\',monospace;font-size:8px;letter-spacing:2px;color:{c2}88;margin-top:3px;text-transform:uppercase">RBI Policy &nbsp;&bull;&nbsp; {lbl}</div></div>', unsafe_allow_html=True)

# ══ TAB 8 — ENGINE ════════════════════════════════════════════════════════
with tabs[7]:
    st.markdown('<div class="sh">Engine Controls</div>', unsafe_allow_html=True)
    e1,e2,e3=st.columns(3)
    for col,title,desc,icon,fn,mod in [(e1,"Full Engine","Technical · News · ML · Risk","&#9650;","run_combiner","signal_combiner"),(e2,"News Scan","Refresh sentiment & headlines","&#9711;","run_news_engine","news_engine"),(e3,"Risk Check","Portfolio stop-loss monitor","&#9675;","run_risk_check","risk_manager")]:
        with col:
            st.markdown(f'<div class="engbox"><div class="engbox-icon">{icon}</div><div class="engbox-title">{title}</div><div class="engbox-desc">{desc}</div></div>', unsafe_allow_html=True)
            st.markdown("<div style='height:8px'></div>",unsafe_allow_html=True)
            if st.button(f"Run {title}",use_container_width=True,key=f"btn_{fn}"):
                with st.spinner(f"Running {title}..."):
                    try:
                        m=__import__(mod); getattr(m,fn)(); st.success(f"✅ {title} completed"); st.cache_data.clear()
                    except Exception as ex: st.error(f"❌ {ex}")

    st.markdown('<div class="sh">System Status</div>', unsafe_allow_html=True)
    sdf2=load_signals(); ndf2=load_news()
    ls=fmt_t(sdf2["created_at"].max()) if not sdf2.empty else "Never"
    ln=fmt_t(ndf2["created_at"].max()) if not ndf2.empty else "Never"
    ss1,ss2,ss3,ss4=st.columns(4)
    for col2,lbl2,val2 in [(ss1,"Last Signal Run",ls),(ss2,"Last News Scan",ln),(ss3,"Total Signals",str(len(sdf2))),(ss4,"Total News Items",str(len(ndf2)))]:
        with col2: st.markdown(f'<div class="stbox"><div class="stbox-lbl">{lbl2}</div><div class="stbox-val">{val2}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="sh">Add to Portfolio</div>', unsafe_allow_html=True)
    a1,a2,a3,a4=st.columns(4)
    with a1: add_sym=st.text_input("Symbol",placeholder="e.g. SBIN.NS",key="asym")
    with a2: add_qty=st.number_input("Quantity",min_value=1,value=1,key="aqty")
    with a3: add_price=st.number_input("Buy Price",min_value=0.0,value=0.0,step=0.5,key="aprice")
    with a4:
        st.markdown("<div style='height:26px'></div>",unsafe_allow_html=True)
        if st.button("Add Holding",use_container_width=True,key="addbtn"):
            if add_sym and add_price>0:
                try:
                    supabase.table("stocks").upsert({"symbol":add_sym.upper(),"company_name":add_sym.upper().replace(".NS",""),"in_portfolio":True,"buy_price":add_price,"quantity":add_qty}).execute()
                    st.success(f"✅ Added {add_sym}"); st.cache_data.clear()
                except Exception as ex: st.error(f"❌ {ex}")

    st.markdown('<div class="sh">Position Sizer</div>', unsafe_allow_html=True)
    ps1,ps2,ps3=st.columns(3)
    with ps1: ps_sym=st.text_input("Symbol",placeholder="RELIANCE.NS",key="ps")
    with ps2: ps_port=st.number_input("Portfolio Value",min_value=10000,value=100000,step=10000,key="pp")
    with ps3:
        st.markdown("<div style='height:26px'></div>",unsafe_allow_html=True)
        if st.button("Calculate Size",use_container_width=True,key="psb"):
            if ps_sym:
                try:
                    from risk_manager import suggest_position
                    suggest_position(ps_sym,ps_port); st.success("Check terminal output")
                except Exception as ex: st.error(f"❌ {ex}")
                