import streamlit as st
import requests


def _fetch_token(address: str) -> tuple:
    try:
        r = requests.get(
            f"https://api.dexscreener.com/latest/dex/tokens/{address.strip()}",
            timeout=10,
        )
        if not r.ok:
            return None, f"HTTP {r.status_code}"
        pairs = r.json().get("pairs") or []
        if not pairs:
            return None, "Adresa nu a fost găsită sau nu are perechi active pe DEX."
        pair = sorted(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0), reverse=True)[0]
        return pair, None
    except Exception as e:
        return None, str(e)


def _fmt_num(val, prefix="$", decimals=2) -> str:
    try:
        v = float(val)
    except (TypeError, ValueError):
        return "—"
    if v >= 1_000_000_000:
        return f"{prefix}{v/1_000_000_000:.{decimals}f}B"
    if v >= 1_000_000:
        return f"{prefix}{v/1_000_000:.{decimals}f}M"
    if v >= 1_000:
        return f"{prefix}{v/1_000:.{decimals}f}K"
    return f"{prefix}{v:.{decimals}f}"


def render() -> None:
    st.markdown("#### Caută token după adresă de contract Solana")
    st.caption("Sursa: DexScreener API · cea mai lichidă pereche DEX")

    with st.form("token_form"):
        token_address = st.text_input(
            "Adresă contract",
            placeholder="ex: So11111111111111111111111111111111111111112",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("🔎 Search", use_container_width=False)

    if not submitted:
        return

    if not token_address.strip():
        st.warning("Introdu o adresă de contract.")
        return

    with st.spinner("Se interoghează DexScreener…"):
        pair, err = _fetch_token(token_address)

    if err:
        st.error(f"❌ {err}")
        return

    base  = pair.get("baseToken", {})
    quote = pair.get("quoteToken", {})
    liq   = pair.get("liquidity", {})
    txns  = pair.get("txns", {}).get("h24", {})
    priceUsd     = pair.get("priceUsd") or pair.get("price")
    price_change = pair.get("priceChange", {}).get("h24")
    dex_url      = pair.get("url", "")

    # ── Header ────────────────────────────────────────────────────────────────
    st.html(f"""
    <div style="display:flex;align-items:center;gap:1rem;margin-bottom:1rem;">
      <div>
        <div style="font-size:1.4rem;font-weight:700;color:#e2e8f0">
          {base.get('name','—')}
          <span style="font-size:0.95rem;color:#64748b;font-weight:400">
            &nbsp;{base.get('symbol','')}
          </span>
        </div>
        <div style="font-size:0.75rem;color:#475569;margin-top:2px">
          {base.get('address', token_address)} · par cu {quote.get('symbol','?')}
        </div>
      </div>
    </div>
    """)

    # ── KPI grid ──────────────────────────────────────────────────────────────
    delta_color = "#22c55e" if (price_change or 0) >= 0 else "#ef4444"
    delta_sign  = "▲" if (price_change or 0) >= 0 else "▼"

    def kpi(label, value, sub=None):
        sub_html = f'<div style="font-size:0.72rem;color:#818cf8;margin-top:3px">{sub}</div>' if sub else ""
        return f"""
        <div style="background:#0f1320;border:1px solid #1e2440;border-radius:10px;
                    padding:1rem 1.2rem;flex:1;min-width:130px">
          <div style="font-size:0.7rem;color:#64748b;letter-spacing:.06em;text-transform:uppercase">{label}</div>
          <div style="font-size:1.35rem;font-weight:700;color:#e2e8f0;margin-top:4px">{value}</div>
          {sub_html}
        </div>"""

    try:
        price_fmt = f"${float(priceUsd):.6f}" if priceUsd else "—"
    except Exception:
        price_fmt = "—"

    buys  = txns.get("buys",  "—")
    sells = txns.get("sells", "—")
    total_txns = (buys + sells) if isinstance(buys, int) and isinstance(sells, int) else "—"

    st.html(f"""
    <div style="display:flex;gap:0.75rem;flex-wrap:wrap;margin-bottom:1rem">
      {kpi("Preț", price_fmt,
           f'<span style="color:{delta_color}">{delta_sign} {abs(price_change or 0):.2f}%</span> 24h')}
      {kpi("Market Cap",   _fmt_num(pair.get("marketCap") or pair.get("fdv")))}
      {kpi("Volum 24h",    _fmt_num(pair.get("volume", {}).get("h24")))}
      {kpi("Lichiditate",  _fmt_num(liq.get("usd")))}
      {kpi("Tranzacții 24h", f"{total_txns:,}" if isinstance(total_txns, int) else total_txns,
           f"↑ {buys:,} cumpărări · ↓ {sells:,} vânzări" if isinstance(buys, int) else None)}
    </div>
    """)

    if dex_url:
        st.markdown(f"[Vezi pe DexScreener →]({dex_url})")

    # ── TA Expander ───────────────────────────────────────────────────────────
    with st.expander("📊 Technical Analysis", expanded=False):
        timeframe = st.selectbox("Timeframe", ["1H", "4H", "1D"], key="ta_tf")
        if st.button("Run TA", key="run_ta_btn"):
            from utils.ohlcv import fetch_ohlcv
            from utils.ta_engine import run_ta
            api_key = st.session_state.get("birdeye_api_key", "")
            with st.spinner("Fetching OHLCV..."):
                candles_1h = fetch_ohlcv(token_address, "1H", 100, api_key)
                candles_1d = fetch_ohlcv(token_address, "1D", 50, api_key)
            if candles_1h:
                result = run_ta(candles_1h, candles_1d)
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Trend Bias", result["trend_bias"].upper())
                with col2:
                    rsi = result["rsi"]
                    rsi_label = "🔴 Overbought" if rsi and rsi > 70 else "🟢 Oversold" if rsi and rsi < 30 else "⚪ Neutral"
                    st.metric("RSI (14)", f"{rsi}" if rsi else "N/A", delta=rsi_label)
                with col3:
                    st.metric("OB Zones", len(result["bullish_obs"]))
                st.caption(f"FVGs: {len(result['fvgs'])} | Equal Highs: {len(result['liquidity']['equal_highs'])} | Equal Lows: {len(result['liquidity']['equal_lows'])}")
            else:
                st.warning("No OHLCV data — check API key or token address")
