import streamlit as st
import requests


def render():
    st.markdown("## 🔥 Trending Tokens")

    api_key = st.session_state.get("birdeye_api_key", "")
    if not api_key:
        st.warning("Add Birdeye API key in ⚙️ Settings.")
        return

    col1, col2 = st.columns([3, 1])
    with col2:
        refresh = st.button("🔄 Refresh")

    @st.cache_data(ttl=300)
    def fetch_trending(key):
        r = requests.get(
            "https://public-api.birdeye.so/defi/token_trending",
            headers={"X-API-KEY": key, "x-chain": "solana"},
            params={"sort_by": "v24hUSD", "sort_type": "desc", "limit": 20},
            timeout=10
        )
        return r.json().get("data", {}).get("tokens", [])

    if refresh:
        st.cache_data.clear()

    tokens = fetch_trending(api_key)
    if not tokens:
        st.error("No data returned from Birdeye.")
        return

    cols = st.columns(4)
    for i, t in enumerate(tokens[:20]):
        chg = t.get("v24hChangePercent", 0) or 0
        color = "#00d084" if chg >= 0 else "#ff4d4d"
        vol = t.get("v24hUSD", 0)
        vol_str = f"${vol/1e6:.1f}M" if vol >= 1e6 else f"${vol/1e3:.0f}K"
        price = t.get("price", 0)
        price_str = f"${price:.6f}" if price < 0.01 else f"${price:.4f}"
        with cols[i % 4]:
            st.markdown(f"""
            <div style='background:#111827;border-radius:8px;padding:12px;
                        border:1px solid #1e2130;margin-bottom:8px'>
              <div style='font-weight:700'>{t.get("symbol","?")}</div>
              <div style='color:#aaa;font-size:0.8em'>{price_str}</div>
              <div style='color:{color};font-weight:600'>{chg:+.1f}%</div>
              <div style='color:#555;font-size:0.75em'>Vol: {vol_str}</div>
            </div>
            """, unsafe_allow_html=True)
