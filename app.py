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


# ── Layout ──────────────────────────────────────────────────────────────────

st.title("📈 Crypto Analytics Dashboard")
st.caption(f"Date actualizate la fiecare 5 minute · {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")

coin_ids = list(COINS.values())
coin_labels = list(COINS.keys())

with st.spinner("Se încarcă prețurile..."):
    try:
        prices = get_prices(coin_ids)
    except Exception as e:
        st.error(f"Eroare la preluarea prețurilor: {e}")
        st.stop()

# ── KPI row ──────────────────────────────────────────────────────────────────
cols = st.columns(len(COINS))
for col, (label, cid) in zip(cols, COINS.items()):
    with col:
        data = prices.get(cid, {})
        price_card(label, data.get("usd", 0), data.get("usd_24h_change", 0))

st.divider()

# ── Chart ────────────────────────────────────────────────────────────────────
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
        st.stop()

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

# ── Stats ────────────────────────────────────────────────────────────────────
with col2:
    st.subheader("Statistici perioadă")
    if not hist.empty:
        st.metric("Maxim", f"${hist['price'].max():,.2f}")
        st.metric("Minim", f"${hist['price'].min():,.2f}")
        pct = (hist["price"].iloc[-1] - hist["price"].iloc[0]) / hist["price"].iloc[0] * 100
        st.metric("Variație", f"{pct:+.2f}%")
        st.metric("Volatilitate (std)", f"${hist['price'].std():,.2f}")
