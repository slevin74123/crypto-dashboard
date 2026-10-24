from __future__ import annotations
import json
import streamlit as st
import pandas as pd
from utils.floor_hold import analyze_trades


_ARCHETYPE_LABELS = {
    "single_trader":       ("👤 Single Trader",       "#64748b"),
    "pure_support_bot":    ("🤖 Support Bot",          "#818cf8"),
    "pure_dump_bot":       ("💣 Dump Bot",             "#ef4444"),
    "accumulation_wallet": ("📈 Accumulation Wallet",  "#22c55e"),
    "distribution_wallet": ("📤 Distribution Wallet",  "#f59e0b"),
    "mixed_trader":        ("🔀 Mixed Trader",         "#38bdf8"),
    "unknown":             ("❓ Unknown",              "#475569"),
}

_PATTERN_BADGES = {
    "real_time_floor_hold":  ('<span style="background:#1e3a5f;color:#60a5fa;padding:2px 8px;border-radius:4px;font-size:0.7rem">Floor Hold</span>', ),
    "bundler_graduation":    ('<span style="background:#3d2c00;color:#fbbf24;padding:2px 8px;border-radius:4px;font-size:0.7rem">Bundler Grad</span>', ),
    "exit_scam":             ('<span style="background:#3b0a0a;color:#f87171;padding:2px 8px;border-radius:4px;font-size:0.7rem">Exit Scam</span>', ),
    "unknown":               ('<span style="background:#1e2440;color:#94a3b8;padding:2px 8px;border-radius:4px;font-size:0.7rem">Unknown</span>', ),
}


def _kpi_card(label: str, value: str, color: str = "#e2e8f0") -> str:
    return f"""
    <div style="background:#0f1320;border:1px solid #1e2440;border-radius:10px;
                padding:1rem 1.2rem;flex:1;min-width:140px">
      <div style="font-size:0.68rem;color:#64748b;letter-spacing:.06em;text-transform:uppercase">{label}</div>
      <div style="font-size:1.25rem;font-weight:700;color:{color};margin-top:4px">{value}</div>
    </div>"""


def _archetype_card(archetype: str, count: int, pct: float) -> str:
    label, color = _ARCHETYPE_LABELS.get(archetype, (archetype, "#e2e8f0"))
    bar_w = max(int(pct), 2)
    return f"""
    <div style="background:#0f1320;border:1px solid #1e2440;border-radius:10px;
                padding:1rem 1.2rem;flex:1;min-width:160px">
      <div style="font-size:0.75rem;color:{color};font-weight:600;margin-bottom:6px">{label}</div>
      <div style="font-size:1.4rem;font-weight:700;color:#e2e8f0">{count}</div>
      <div style="font-size:0.72rem;color:#64748b;margin-bottom:6px">{pct}% of wallets</div>
      <div style="background:#1e2440;border-radius:4px;height:4px">
        <div style="background:{color};width:{bar_w}%;height:4px;border-radius:4px"></div>
      </div>
    </div>"""


def render() -> None:
    st.markdown("#### 📂 GMGN Trade Analyzer")
    st.caption("Încarcă un export JSON de la GMGN pentru a analiza structura tranzacțiilor și floor hold.")

    uploaded = st.file_uploader(
        "Selectează fișierul JSON exportat din GMGN",
        type=["json"],
        label_visibility="collapsed",
    )

    if uploaded is None:
        st.info("Încarcă un fișier JSON din GMGN pentru a începe analiza.")
        return

    try:
        raw = json.loads(uploaded.read())
    except json.JSONDecodeError as e:
        st.error(f"Fișier JSON invalid: {e}")
        return

    with st.spinner("Se analizează tranzacțiile…"):
        result = analyze_trades(raw)

    # ── Section A: Token Overview ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown("##### A · Token Overview")

    bs_val = f"{result['bs_ratio']:.2f}" if result["bs_ratio"] else "—"
    bs_color = "#22c55e" if (result["bs_ratio"] or 0) >= 1.5 else (
        "#f59e0b" if (result["bs_ratio"] or 0) >= 1.0 else "#ef4444"
    )
    time_window = f"{result['time_first']} → {result['time_last']}"

    st.html(f"""
    <div style="display:flex;gap:0.75rem;flex-wrap:wrap;margin-bottom:1rem">
      {_kpi_card("Token", result['coin_name'] or result['coin_id'] or "—")}
      {_kpi_card("Total Trades", f"{result['total_trades']:,}")}
      {_kpi_card("Time Window", time_window, "#94a3b8")}
      {_kpi_card("B/S Ratio", bs_val, bs_color)}
    </div>
    """)

    if result["coin_id"]:
        st.caption(f"Contract: `{result['coin_id']}`")

    # ── Section B: Wallet Breakdown ───────────────────────────────────────────
    st.markdown("##### B · Wallet Breakdown")

    breakdown = result["wallet_breakdown"]
    if not breakdown:
        st.info("Insuficiente date despre portofele.")
    else:
        ordered = sorted(breakdown.items(), key=lambda x: x[1]["count"], reverse=True)
        row_chunks = [ordered[i:i+3] for i in range(0, len(ordered), 3)]
        for chunk in row_chunks:
            cards_html = "".join(
                _archetype_card(arch, d["count"], d["pct"])
                for arch, d in chunk
            )
            st.html(f'<div style="display:flex;gap:0.75rem;flex-wrap:wrap;margin-bottom:0.75rem">{cards_html}</div>')

    # ── Section C: Dump Events Table ──────────────────────────────────────────
    st.markdown("##### C · Dump Events")

    dump_events = result["dump_events"]
    if not dump_events:
        st.info("Niciun dump event detectat în istoricul MC.")
    else:
        rows = []
        for idx, ev in enumerate(dump_events, 1):
            badge = _PATTERN_BADGES.get(ev["pattern"], _PATTERN_BADGES["unknown"])[0]
            signal = "✅ YES" if ev["entry_signal"] else "❌ NO"
            rows.append({
                "#":             idx,
                "Dump %":        ev["dump_pct"],
                "Pattern":       badge,
                "Recovery (s)":  ev["recovery_s"] if ev["recovery_s"] is not None else "—",
                "B/S Window":    f"{ev['buys_window']}↑ / {ev['sells_window']}↓",
                "Floor Score":   ev["floor_score"],
                "Entry Signal":  signal,
            })

        df_events = pd.DataFrame(rows).set_index("#")

        def _color_signal(val: str):
            if "YES" in str(val):
                return "color: #22c55e; font-weight: 600"
            if "NO" in str(val):
                return "color: #ef4444"
            return ""

        styled = df_events.style.applymap(_color_signal, subset=["Entry Signal"])
        st.dataframe(styled, use_container_width=True)

    # ── Section D: Confluence Summary ─────────────────────────────────────────
    st.markdown("##### D · Confluence Summary")

    score = result["confluence_score"]
    signal = result["entry_signal"]
    insight = result["insight"]

    score_color = "#22c55e" if score >= 70 else "#f59e0b" if score >= 40 else "#ef4444"
    signal_label = "YES — INTRĂ" if signal else "NO — EVITĂ"
    signal_color = "#22c55e" if signal else "#ef4444"

    bar_w = max(score, 2)

    st.html(f"""
    <div style="background:#0f1320;border:1px solid #1e2440;border-radius:12px;padding:1.5rem">
      <div style="display:flex;gap:2rem;align-items:center;flex-wrap:wrap;margin-bottom:1rem">
        <div>
          <div style="font-size:0.68rem;color:#64748b;text-transform:uppercase;letter-spacing:.06em">Confluence Score</div>
          <div style="font-size:2.2rem;font-weight:800;color:{score_color}">{score}<span style="font-size:1rem;color:#475569">/100</span></div>
        </div>
        <div>
          <div style="font-size:0.68rem;color:#64748b;text-transform:uppercase;letter-spacing:.06em">Entry Signal</div>
          <div style="font-size:1.5rem;font-weight:700;color:{signal_color}">{signal_label}</div>
        </div>
      </div>
      <div style="background:#1e2440;border-radius:6px;height:8px;margin-bottom:1rem">
        <div style="background:{score_color};width:{bar_w}%;height:8px;border-radius:6px;
                    transition:width 0.4s ease"></div>
      </div>
      <div style="font-size:0.88rem;color:#94a3b8;line-height:1.5">💡 {insight}</div>
    </div>
    """)
