import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime
from dotenv import load_dotenv
from tabs.gmgn_analyzer import render as render_gmgn
from tabs.trending import render as render_birdeye
from tabs.token_analysis import render as render_token_analysis

load_dotenv()
API_KEY = os.getenv("SORSA_API_KEY", "")
BASE    = "https://api.sorsa.io/v3"
CSV_PATH = "kols.csv"

st.set_page_config(page_title="KOL Dashboard", page_icon="📡", layout="wide")

st.markdown("""
<style>
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
    background: #0b0e17 !important;
    color: #e2e8f0 !important;
}
[data-testid="stHeader"]  { background: #0b0e17 !important; }
.block-container           { padding: 2rem 2.5rem 3rem !important; max-width: 1300px; }

/* button */
[data-testid="stButton"] > button {
    background: #161b2e !important;
    color: #818cf8 !important;
    border: 1px solid #2e3561 !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
}
[data-testid="stButton"] > button:hover { background: #1e2440 !important; }

/* dataframe */
[data-testid="stDataFrame"]       { border: 1px solid #1e2440 !important; border-radius: 10px !important; overflow: hidden; }
[data-testid="stDataFrame"] > div { background: #0f1320 !important; }

/* progress */
[data-testid="stProgressBar"] > div > div { background: #818cf8 !important; }

/* sidebar */
[data-testid="stSidebar"] {
    background: #0f1320 !important;
    border-right: 1px solid #1e2440 !important;
}
[data-testid="stSidebar"] h3 { color: #e2e8f0 !important; }
[data-testid="stSidebar"] [data-testid="stTextInput"] input {
    background: #161b2e !important;
    border: 1px solid #2e3561 !important;
    color: #e2e8f0 !important;
    border-radius: 6px !important;
}

/* hide branding */
#MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── dexscreener helper ───────────────────────────────────────────────────────

def fetch_token(address: str) -> tuple[dict | None, str | None]:
    try:
        r = requests.get(
            f"https://api.dexscreener.com/latest/dex/tokens/{address.strip()}",
            timeout=10,
        )
        if not r.ok:
            return None, f"HTTP {r.status_code}"
        data = r.json()
        pairs = data.get("pairs") or []
        if not pairs:
            return None, "Adresa nu a fost găsită sau nu are perechi active pe DEX."
        # ia cea mai lichidă pereche
        pair = sorted(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0), reverse=True)[0]
        return pair, None
    except Exception as e:
        return None, str(e)


def fmt_num(val, prefix="$", decimals=2) -> str:
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


# ── sorsa helpers ─────────────────────────────────────────────────────────────

def sg(endpoint: str, username: str) -> dict | list:
    try:
        r = requests.get(f"{BASE}/{endpoint}", headers={"ApiKey": API_KEY},
                         params={"username": username}, timeout=10)
        return r.json() if r.ok else {}
    except Exception:
        return {}


def load_kols() -> list[str]:
    try:
        df = pd.read_csv(CSV_PATH)
        return df["username"].dropna().tolist() if "username" in df.columns else []
    except FileNotFoundError:
        return []


def save_kol(username: str) -> bool:
    username = username.strip().lstrip("@")
    if not username:
        return False
    kols = load_kols()
    if username.lower() in [k.lower() for k in kols]:
        return False
    kols.append(username)
    pd.DataFrame({"username": kols}).to_csv(CSV_PATH, index=False)
    return True


def _pick(d: dict, *keys):
    for k in keys:
        v = d.get(k)
        if v is not None:
            return v
    return None


def run_analysis(kols: list[str]) -> pd.DataFrame:
    # step 1: new-following-7d per KOL → project → [kols]
    project_kols: dict[str, list[str]] = {}
    prog = st.progress(0, text="Pasul 1/2 — new-following-7d…")
    for i, kol in enumerate(kols):
        prog.progress((i + 1) / len(kols), text=f"[1/2] @{kol}")
        resp = sg("new-following-7d", kol)
        # API returns {"users": [...]} with full user objects
        following = resp.get("users", resp) if isinstance(resp, dict) else resp
        if isinstance(following, list):
            for item in following:
                proj = item if isinstance(item, str) else (
                    _pick(item, "username", "name") or str(item))
                project_kols.setdefault(proj, []).append(kol)
    prog.empty()

    projects = list(project_kols.keys())
    if not projects:
        return pd.DataFrame()

    # step 2: enrich each project
    rows = []
    prog2 = st.progress(0, text="Pasul 2/2 — enrich proiecte…")
    for i, proj in enumerate(projects):
        prog2.progress((i + 1) / len(projects), text=f"[2/2] @{proj}")

        info_d  = sg("info", proj)
        score_d = sg("score", proj)
        chg_d   = sg("score-changes", proj)
        stat_d  = sg("followers-stats", proj)

        # /info → flat dict
        info_d = info_d if isinstance(info_d, dict) else {}
        # /score → {"score": 825.21}
        score_d = score_d if isinstance(score_d, dict) else {}
        # /score-changes → {"score_change_7d": ...} (fallback keys)
        chg_d = chg_d if isinstance(chg_d, dict) else {}
        # /followers-stats → {"followers_count":..., "influencers_count":..., "venture_capitals_count":...}
        stat_d = stat_d if isinstance(stat_d, dict) else {}

        avatar = _pick(info_d, "profile_image_url", "avatar", "image_url") or ""
        name   = _pick(info_d, "display_name", "name", "username") or proj

        rows.append({
            "_avatar":              avatar,
            "Profile":              name,
            "username":             proj,
            "Score":                _pick(score_d, "score", "value", "data"),
            "Score Change 7d":      _pick(chg_d,   "score_change_7d", "change_7d", "7d", "weekly"),
            "Total Followers":      _pick(stat_d,   "followers_count",  "total_followers",     "total"),
            "Influencer Followers": _pick(stat_d,   "influencers_count","influencer_followers","influencers"),
            "VC Followers":         _pick(stat_d,   "venture_capitals_count","vc_followers",   "vcs"),
            "KOLs Following":       len(project_kols[proj]),
            "_kols_list":           ", ".join(project_kols[proj]),
        })
    prog2.empty()

    df = pd.DataFrame(rows).sort_values("KOLs Following", ascending=False).reset_index(drop=True)
    df.index += 1
    df.index.name = "#"
    return df


# ── sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 👥 KOL List")
    st.divider()

    kols_sidebar = load_kols()
    if kols_sidebar:
        for i, kol in enumerate(kols_sidebar, 1):
            st.markdown(
                f'<div style="padding:4px 0;color:#e2e8f0;font-size:0.88rem">'
                f'<span style="color:#475569;margin-right:8px">{i}.</span>@{kol}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.caption("Niciun KOL adăugat încă.")

    st.divider()
    st.markdown('<p style="font-size:0.78rem;color:#64748b;margin-bottom:6px">Adaugă KOL</p>',
                unsafe_allow_html=True)

    with st.form("add_kol_form", clear_on_submit=True):
        new_kol = st.text_input(
            "Username",
            placeholder="ex: ansem",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("＋ Adaugă KOL", use_container_width=True)

    if submitted:
        if save_kol(new_kol):
            st.success(f"@{new_kol.strip().lstrip('@')} adăugat!")
            st.rerun()
        elif new_kol.strip():
            st.warning("Username deja în listă.")
        else:
            st.warning("Introdu un username.")

    st.divider()
    st.markdown('<p style="font-size:0.78rem;color:#64748b;margin-bottom:6px">Birdeye API Key</p>',
                unsafe_allow_html=True)
    birdeye_key = st.text_input(
        "Birdeye API Key",
        value=st.session_state.get("birdeye_api_key", ""),
        placeholder="a91bde8f...",
        type="password",
        label_visibility="collapsed",
        key="birdeye_key_input",
    )
    if birdeye_key:
        st.session_state["birdeye_api_key"] = birdeye_key


# ── layout ────────────────────────────────────────────────────────────────────

st.markdown("## 📡 KOL Dashboard")
tab_trending, tab_birdeye, tab_token, tab_gmgn = st.tabs([
    "📈  KOL Trending", "🔥  Birdeye", "🔎  Token Analysis", "📂  GMGN Analyzer"
])


# ════════════════════════════════════════════════════════════════
#  TAB 1 — TRENDING
# ════════════════════════════════════════════════════════════════
with tab_trending:
    col_title, col_refresh = st.columns([8, 1])
    with col_title:
        ts_placeholder = st.empty()
        if "last_refresh" in st.session_state:
            ts_placeholder.caption(f"Ultimul refresh: {st.session_state.last_refresh}")
    with col_refresh:
        refresh = st.button("🔄 Refresh", use_container_width=True)

    kols = load_kols()
    if not kols:
        st.warning(f"Niciun username găsit în `{CSV_PATH}`.")
    elif not API_KEY:
        st.error("SORSA_API_KEY lipsă din fișierul .env")
    else:
        if refresh or "result_df" not in st.session_state:
            with st.spinner("Se rulează analiza…"):
                st.session_state.result_df = run_analysis(kols)
            st.session_state.last_refresh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ts_placeholder.caption(f"Ultimul refresh: {st.session_state.last_refresh}")

        df: pd.DataFrame = st.session_state.result_df

        if df.empty:
            st.info("Niciun proiect detectat. API key-ul poate fi inactiv.")
            with st.expander("Debug: KOLs încărcați"):
                st.write(kols)
        else:
            display = df[[
                "_avatar", "Profile", "Score",
                "Total Followers", "Influencer Followers", "VC Followers",
                "KOLs Following", "_kols_list",
            ]].copy()
            display = display.rename(columns={"_kols_list": "Urmărit de"})

            st.dataframe(
                display,
                use_container_width=True,
                column_config={
                    "_avatar":              st.column_config.ImageColumn("", width="small"),
                    "Profile":              st.column_config.TextColumn("Profile", width="medium"),
                    "Score":                st.column_config.NumberColumn("Score", format="%.1f"),
                    "Total Followers":      st.column_config.NumberColumn("Total Flw", format="%d"),
                    "Influencer Followers": st.column_config.NumberColumn("Influencer Flw", format="%d"),
                    "VC Followers":         st.column_config.NumberColumn("VC Flw", format="%d"),
                    "KOLs Following":       st.column_config.NumberColumn("KOLs Following", format="%d"),
                    "Urmărit de":           st.column_config.TextColumn("Urmărit de KOLs"),
                },
                hide_index=False,
            )
            st.caption(f"{len(df)} proiecte detectate · {len(kols)} KOLs monitorizați")


# ════════════════════════════════════════════════════════════════
#  TAB 2 — BIRDEYE TRENDING
# ════════════════════════════════════════════════════════════════
with tab_birdeye:
    render_birdeye()


# ════════════════════════════════════════════════════════════════
#  TAB 3 — TOKEN ANALYSIS
# ════════════════════════════════════════════════════════════════
with tab_token:
    render_token_analysis()


# ════════════════════════════════════════════════════════════════
#  TAB 3 — GMGN ANALYZER
# ════════════════════════════════════════════════════════════════
with tab_gmgn:
    render_gmgn()
