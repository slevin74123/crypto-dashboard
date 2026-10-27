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

    # ── Confluence + TA Expander ──────────────────────────────────────────────
    # stash pair data for confluence (used after TA expander)
    _pair = pair
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
                st.session_state["_last_ta_result"] = result
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

    # ── Confluence Score Card ─────────────────────────────────────────────────
    st.divider()
    st.markdown("#### 🎯 Confluence Score")

    birdeye_data = {
        "mc":      pair.get("marketCap") or pair.get("fdv") or 0,
        "volume":  pair.get("volume", {}).get("h24") or 0,
        "holders": 0,
    }

    # pull ta_result from session if already computed this run
    ta_for_conf = st.session_state.get("_last_ta_result") or {}

    from utils.confluence import calculate_confluence
    conf = calculate_confluence(token_address, birdeye_data, ta_for_conf, [])

    _SIGNAL_COLORS = {
        "STRONG BUY": ("#052e16", "#22c55e"),
        "BUY":        ("#0f2317", "#4ade80"),
        "WATCH":      ("#2d2000", "#fbbf24"),
        "AVOID":      ("#2d0a0a", "#ef4444"),
    }
    badge_bg, badge_fg = _SIGNAL_COLORS.get(conf["signal"], ("#1a1f2e", "#94a3b8"))

    def _bar(label, score, max_score, color):
        pct = int(score / max_score * 100)
        return f"""
        <div style="margin-bottom:10px">
          <div style="display:flex;justify-content:space-between;
                      font-size:0.72rem;color:#94a3b8;margin-bottom:3px">
            <span>{label}</span>
            <span style="color:#e2e8f0;font-weight:600">{score}/{max_score}</span>
          </div>
          <div style="background:#1e2440;border-radius:4px;height:7px;overflow:hidden">
            <div style="width:{pct}%;background:{color};height:100%;
                        border-radius:4px;transition:width .4s"></div>
          </div>
        </div>"""

    st.html(f"""
    <div style="background:#0f1320;border:1px solid #1e2440;border-radius:14px;
                padding:1.4rem 1.6rem;display:flex;gap:2rem;align-items:center;
                flex-wrap:wrap">

      <!-- circle -->
      <div style="display:flex;flex-direction:column;align-items:center;min-width:110px">
        <div style="position:relative;width:100px;height:100px">
          <svg viewBox="0 0 36 36" style="width:100px;height:100px;transform:rotate(-90deg)">
            <circle cx="18" cy="18" r="15.9" fill="none"
                    stroke="#1e2440" stroke-width="3"/>
            <circle cx="18" cy="18" r="15.9" fill="none"
                    stroke="{badge_fg}" stroke-width="3"
                    stroke-dasharray="{conf['total_score']},100"
                    stroke-linecap="round"/>
          </svg>
          <div style="position:absolute;top:50%;left:50%;
                      transform:translate(-50%,-50%);text-align:center">
            <div style="font-size:1.5rem;font-weight:800;color:#e2e8f0;line-height:1">
              {conf['total_score']}
            </div>
            <div style="font-size:0.6rem;color:#64748b">/ 100</div>
          </div>
        </div>
        <div style="margin-top:10px;background:{badge_bg};color:{badge_fg};
                    font-size:0.75rem;font-weight:700;padding:3px 12px;
                    border-radius:20px;letter-spacing:.05em">
          {conf['signal']}
        </div>
      </div>

      <!-- bars -->
      <div style="flex:1;min-width:200px">
        {_bar("📣 Social",       conf['social_score'],      25, "#818cf8")}
        {_bar("🧠 Smart Money",  conf['smart_money_score'], 25, "#22d3ee")}
        {_bar("📊 Technical",    conf['ta_score'],          35, "#4ade80")}
        {_bar("📈 Market",       conf['market_score'],      15, "#fb923c")}
      </div>

    </div>
    """)

    st.caption(
        f"Holders: {conf['debug']['holders']} · "
        f"KOLs: {conf['debug']['kol_count']} · "
        f"RSI: {conf['debug']['rsi'] or '—'} · "
        f"Trend: {conf['debug']['trend']} · "
        f"OBs: {conf['debug']['ob_count']} · "
        f"FVGs: {conf['debug']['fvg_count']}"
    )
