from __future__ import annotations
import streamlit as st
import pandas as pd
from utils.sorsa import SorsaClient


@st.cache_data(ttl=600)
def _fetch_top_kols(api_key: str) -> list[dict]:
    return SorsaClient(api_key).get_top_kols(limit=20)


@st.cache_data(ttl=600)
def _fetch_new_following(api_key: str) -> list[dict]:
    return SorsaClient(api_key).get_new_following_7d(limit=20)


def render() -> None:
    st.markdown("#### 🧠 KOL Intel")

    api_key: str = st.session_state.get("sorsa_api_key", "")
    if not api_key:
        st.warning("Add Sorsa API key in Settings.")
        return

    # ── Section 1: Top KOLs ──────────────────────────────────────────────────
    st.markdown("##### Top KOLs")

    with st.spinner("Se încarcă top KOLs…"):
        top_kols = _fetch_top_kols(api_key)

    if not top_kols:
        st.info("Niciun KOL returnat. Verifică API key-ul.")
    else:
        rows = []
        for item in top_kols:
            rows.append({
                "Name":      item.get("display_name") or item.get("name") or item.get("username") or "—",
                "Score":     item.get("score") or item.get("kol_score"),
                "Followers": item.get("followers_count") or item.get("followers") or item.get("total_followers"),
            })
        df = pd.DataFrame(rows)
        df.index += 1
        df.index.name = "#"
        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "Name":      st.column_config.TextColumn("Name", width="medium"),
                "Score":     st.column_config.NumberColumn("Score", format="%.1f"),
                "Followers": st.column_config.NumberColumn("Followers", format="%d"),
            },
        )
        st.caption(f"{len(rows)} KOLs · cache 10 min")

    st.divider()

    # ── Section 2: New Following 7d ──────────────────────────────────────────
    st.markdown("##### New Following — Last 7 Days")

    with st.spinner("Se încarcă new following…"):
        following = _fetch_new_following(api_key)

    if not following:
        st.info("Niciun token detectat în ultimele 7 zile.")
        return

    # aggregate by token symbol / name
    token_kols: dict[str, int] = {}
    for item in following:
        token = (
            item.get("symbol") or item.get("token_symbol") or
            item.get("name") or item.get("username") or "Unknown"
        )
        token_kols[token] = token_kols.get(token, 0) + 1

    sorted_tokens = sorted(token_kols.items(), key=lambda x: x[1], reverse=True)

    for symbol, count in sorted_tokens:
        kol_label = "KOL" if count == 1 else "KOLs"
        st.html(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
                    padding:7px 12px;margin-bottom:4px;background:#0f1320;
                    border:1px solid #1e2440;border-radius:7px">
          <span style="font-size:0.88rem;font-weight:600;color:#e2e8f0">{symbol}</span>
          <span style="font-size:0.78rem;color:#818cf8;font-weight:500">{count} {kol_label}</span>
        </div>
        """)

    st.caption(f"{len(sorted_tokens)} tokens detectați · cache 10 min")
