import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Crypto Dashboard", page_icon="📈", layout="wide")

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

COINS = {
    "Bitcoin (BTC)": "bitcoin",
    "Ethereum (ETH)": "ethereum",
    "Solana (SOL)": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
}

TIMEFRAMES = {"24h": 1, "7 zile": 7, "30 zile": 30, "90 zile": 90, "1 an": 365}


@st.cache_data(ttl=300)
def get_prices(coin_ids: list[str]) -> dict:
    ids = ",".join(coin_ids)
    r = requests.get(
        f"{COINGECKO_BASE}/simple/price",
        params={"ids": ids, "vs_currencies": "usd", "include_24hr_change": "true"},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=300)
def get_history(coin_id: str, days: int) -> pd.DataFrame:
    r = requests.get(
        f"{COINGECKO_BASE}/coins/{coin_id}/market_chart",
        params={"vs_currency": "usd", "days": days},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()["prices"]
    df = pd.DataFrame(data, columns=["timestamp", "price"])
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df[["date", "price"]]


def price_card(label: str, price: float, change: float) -> None:
    color = "green" if change >= 0 else "red"
    arrow = "▲" if change >= 0 else "▼"
    st.metric(
        label=label,
        value=f"${price:,.2f}",
        delta=f"{arrow} {abs(change):.2f}%",
    )


# ── Sidebar ──────────────────────────────────────────────────────────────────

_SIGNALS = [
    {"name": "SWORDCAT",  "mc": "$2.19M", "pattern": "floor_hold", "bs": "2.16", "live": False},
    {"name": "DACITYCOIN","mc": "$1.60M", "pattern": "floor_hold", "bs": "2.16", "live": False},
    {"name": "HOOKED",    "mc": "$1.40M", "pattern": "live signal","bs": "1.93", "live": True},
]

with st.sidebar:
    st.markdown("### 🛡️ Floor Signals")
    st.divider()

    for sig in _SIGNALS:
        badge_bg  = "#14532d" if not sig["live"] else "#3d2c00"
        badge_col = "#4ade80" if not sig["live"] else "#fbbf24"
        icon      = "✅" if not sig["live"] else "⚡"
        st.html(f"""
        <div style="background:#1a1f2e;border:1px solid #1e2440;border-radius:8px;
                    padding:10px 12px;margin-bottom:8px">
          <div style="font-size:0.82rem;font-weight:700;color:#e2e8f0;margin-bottom:3px">
            {sig['name']}
          </div>
          <div style="font-size:0.88rem;color:#ffffff;margin-bottom:5px">{sig['mc']}</div>
          <div style="display:flex;align-items:center;justify-content:space-between">
            <span style="background:{badge_bg};color:{badge_col};font-size:0.68rem;
                         padding:2px 7px;border-radius:4px">{icon} {sig['pattern']}</span>
            <span style="font-size:0.72rem;color:#64748b">B/S {sig['bs']}</span>
          </div>
        </div>
        """)

    st.divider()
    st.caption("Upload GMGN JSON in tab → GMGN Analyzer")


# ── Layout ──────────────────────────────────────────────────────────────────

st.title("📈 Crypto Analytics Dashboard")
st.caption(f"Date actualizate la fiecare 5 minute · {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")

tab_prices, tab_trending, tab_kol = st.tabs(["💰 Prices", "🔥 Trending", "👑 KOL Intel"])

# ── TAB: PRICES ───────────────────────────────────────────────────────────────
with tab_prices:
    coin_ids = list(COINS.values())
    coin_labels = list(COINS.keys())

    with st.spinner("Se încarcă prețurile..."):
        try:
            prices = get_prices(coin_ids)
        except Exception as e:
            st.error(f"Eroare la preluarea prețurilor: {e}")
            prices = {}

    cols = st.columns(len(COINS))
    for col, (label, cid) in zip(cols, COINS.items()):
        with col:
            data = prices.get(cid, {})
            price_card(label, data.get("usd", 0), data.get("usd_24h_change", 0))

    st.divider()

    col1, col2 = st.columns([2, 1])

    with col1:
        selected_label = st.selectbox("Monedă", coin_labels)
        selected_tf = st.select_slider("Perioadă", options=list(TIMEFRAMES.keys()))

    selected_id = COINS[selected_label]
    days = TIMEFRAMES[selected_tf]

    with st.spinner("Se încarcă istoricul..."):
        try:
            hist = get_history(selected_id, days)
        except Exception as e:
            st.error(f"Eroare la preluarea istoricului: {e}")
            hist = __import__('pandas').DataFrame(columns=["date", "price"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=hist["date"],
            y=hist["price"],
            mode="lines",
            name=selected_label,
            line=dict(color="#f7931a", width=2),
            fill="tozeroy",
            fillcolor="rgba(247,147,26,0.1)",
        )
    )
    fig.update_layout(
        title=f"{selected_label} — {selected_tf}",
        xaxis_title="",
        yaxis_title="Preț (USD)",
        template="plotly_dark",
        height=420,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Statistici perioadă")
        if not hist.empty:
            st.metric("Maxim", f"${hist['price'].max():,.2f}")
            st.metric("Minim", f"${hist['price'].min():,.2f}")
            pct = (hist["price"].iloc[-1] - hist["price"].iloc[0]) / hist["price"].iloc[0] * 100
            st.metric("Variație", f"{pct:+.2f}%")
            st.metric("Volatilitate (std)", f"${hist['price'].std():,.2f}")

# ── TAB: TRENDING ─────────────────────────────────────────────────────────────
with tab_trending:
    from tabs.trending import render as render_trending
    render_trending()

# ── TAB: KOL INTEL ────────────────────────────────────────────────────────────
with tab_kol:
    from tabs.kol_intel import render as render_kol_intel
    render_kol_intel()
