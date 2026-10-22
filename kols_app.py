import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("SORSA_API_KEY", "")
BASE    = "https://api.sorsa.io/v3"
CSV_PATH = "kols.csv"

st.set_page_config(page_title="KOL Trending", page_icon="📡", layout="wide")

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

/* hide branding */
#MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── helpers ───────────────────────────────────────────────────────────────────

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
        following = sg("new-following-7d", kol)
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

        info    = sg("info", proj)
        score_d = sg("score", proj)
        chg_d   = sg("score-changes", proj)
        stat_d  = sg("followers-stats", proj)

        info = info.get("data", info) if isinstance(info, dict) else {}
        score_d = score_d.get("data", score_d) if isinstance(score_d, dict) else {}
        chg_d   = chg_d.get("data",   chg_d)   if isinstance(chg_d,   dict) else {}
        stat_d  = stat_d.get("data",  stat_d)  if isinstance(stat_d,  dict) else {}

        avatar = _pick(info, "profile_image_url", "avatar", "image_url") or ""
        name   = _pick(info, "name", "displayName", "display_name") or proj

        rows.append({
            "_avatar":              avatar,
            "Profile":              name,
            "username":             proj,
            "Score":                _pick(score_d, "score", "value"),
            "Score Change 7d":      _pick(chg_d,   "change_7d", "7d", "weekly"),
            "Total Followers":      _pick(stat_d,   "total_followers",     "totalFollowers",     "total"),
            "Influencer Followers": _pick(stat_d,   "influencer_followers","influencerFollowers","influencers"),
            "VC Followers":         _pick(stat_d,   "vc_followers",        "vcFollowers",        "vcs"),
            "KOLs Following":       len(project_kols[proj]),
            "_kols_list":           ", ".join(project_kols[proj]),
        })
    prog2.empty()

    df = pd.DataFrame(rows).sort_values("KOLs Following", ascending=False).reset_index(drop=True)
    df.index += 1
    df.index.name = "#"
    return df


# ── layout ────────────────────────────────────────────────────────────────────

col_title, col_refresh = st.columns([7, 1])
with col_title:
    st.markdown("## 📡 KOL Trending")
with col_refresh:
    st.write("")
    refresh = st.button("🔄 Refresh", use_container_width=True)

# timestamp
ts_placeholder = st.empty()
if "last_refresh" in st.session_state:
    ts_placeholder.caption(f"Ultimul refresh: {st.session_state.last_refresh}")

st.divider()

kols = load_kols()
if not kols:
    st.warning(f"Niciun username găsit în `{CSV_PATH}`.")
    st.stop()

if not API_KEY:
    st.error("SORSA_API_KEY lipsă din fișierul .env")
    st.stop()

# auto-run la prima încărcare sau la refresh
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
    st.stop()

# ── tabel principal ───────────────────────────────────────────────────────────

display = df[[
    "_avatar", "Profile", "Score", "Score Change 7d",
    "Total Followers", "Influencer Followers", "VC Followers",
    "KOLs Following", "_kols_list",
]].copy()

st.dataframe(
    display,
    use_container_width=True,
    column_config={
        "_avatar": st.column_config.ImageColumn(
            "Avatar", width="small",
        ),
        "Profile": st.column_config.TextColumn("Profile", width="medium"),
        "Score": st.column_config.NumberColumn("Score", format="%.1f"),
        "Score Change 7d": st.column_config.NumberColumn("Score Δ 7d", format="%+.2f"),
        "Total Followers": st.column_config.NumberColumn("Total Flw", format="%d"),
        "Influencer Followers": st.column_config.NumberColumn("Influencer Flw", format="%d"),
        "VC Followers": st.column_config.NumberColumn("VC Flw", format="%d"),
        "KOLs Following": st.column_config.NumberColumn("KOLs Following", format="%d"),
        "_kols_list": st.column_config.TextColumn("KOLs"),
    },
    hide_index=False,
)

st.caption(f"{len(df)} proiecte detectate · {len(kols)} KOLs monitorizați")
