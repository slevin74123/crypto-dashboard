from __future__ import annotations
import streamlit as st
import requests


@st.cache_data(ttl=300)
def _fetch_trending(api_key: str) -> list[dict]:
    try:
        r = requests.get(
            "https://public-api.birdeye.so/defi/token_trending",
            headers={
                "X-API-KEY": api_key,
                "x-chain": "solana",
            },
            params={
                "sort_type": "desc",
                "limit": 20,
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("data", {}).get("tokens", [])
    except requests.HTTPError as e:
        st.error(f"Birdeye API error: {e.response.status_code} — {e.response.text[:200]}")
        return []
    except requests.RequestException as e:
        st.error(f"Request failed: {e}")
        return []
    except ValueError:
        st.error("Invalid JSON response from Birdeye.")
        return []


def _fmt_price(val) -> str:
    try:
        v = float(val)
    except (TypeError, ValueError):
        return "—"
    if v >= 1:
        return f"${v:,.4f}"
    if v >= 0.0001:
        return f"${v:.6f}"
    return f"${v:.2e}"


def _fmt_volume(val) -> str:
    try:
        v = float(val)
    except (TypeError, ValueError):
        return "—"
    if v >= 1_000_000_000:
        return f"${v / 1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"${v / 1_000_000:.2f}M"
    if v >= 1_000:
        return f"${v / 1_000:.1f}K"
    return f"${v:.2f}"


def _token_card(token: dict) -> str:
    symbol   = token.get("symbol") or token.get("name") or "—"
    price    = _fmt_price(token.get("price"))
    change   = token.get("price24hChangePercent") or 0
    volume   = _fmt_volume(token.get("volume24hUSD"))
    logo     = token.get("logoURI") or token.get("logo") or ""

    try:
        change_f = float(change)
    except (TypeError, ValueError):
        change_f = 0.0

    chg_color = "#22c55e" if change_f >= 0 else "#ef4444"
    chg_sign  = "▲" if change_f >= 0 else "▼"
    chg_label = f"{chg_sign} {abs(change_f):.2f}%"

    logo_html = (
        f'<img src="{logo}" style="width:28px;height:28px;border-radius:50%;'
        f'object-fit:cover;margin-right:8px;flex-shrink:0" onerror="this.style.display=\'none\'">'
        if logo else
        '<div style="width:28px;height:28px;border-radius:50%;background:#1e2130;'
        'margin-right:8px;flex-shrink:0"></div>'
    )

    return f"""
    <div style="background:#111827;border:1px solid #1e2130;border-radius:10px;
                padding:14px 16px;display:flex;flex-direction:column;gap:6px;
                min-height:110px">
      <div style="display:flex;align-items:center">
        {logo_html}
        <span style="font-size:0.95rem;font-weight:700;color:#e2e8f0;
                     white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{symbol}</span>
      </div>
      <div style="font-size:1.1rem;font-weight:600;color:#f8fafc">{price}</div>
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span style="font-size:0.78rem;font-weight:600;color:{chg_color}">{chg_label}</span>
        <span style="font-size:0.72rem;color:#64748b">Vol {volume}</span>
      </div>
    </div>"""


def render() -> None:
    col_title, col_btn = st.columns([8, 1])
    with col_title:
        st.markdown("#### 🔥 Trending Tokens — Solana")
    with col_btn:
        if st.button("🔄", use_container_width=True, key="trending_refresh"):
            st.cache_data.clear()

    api_key: str = st.session_state.get("birdeye_api_key", "")
    if not api_key:
        st.warning("Adaugă Birdeye API key în sidebar pentru a vedea trending tokens.")
        return

    with st.spinner("Se încarcă trending tokens…"):
        tokens = _fetch_trending(api_key)

    if not tokens:
        st.info("Niciun token returnat. Verifică API key-ul sau încearcă din nou.")
        return

    # 4-column grid
    cols = st.columns(4)
    for i, token in enumerate(tokens):
        with cols[i % 4]:
            st.html(_token_card(token))

    st.caption(f"{len(tokens)} tokens · sortat după volum 24h · cache 5 min")
