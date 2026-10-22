import streamlit as st
import pandas as pd
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("SORSA_API_KEY", "")

st.set_page_config(
    page_title="KOLs Dashboard",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
/* ── Global dark theme ─────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background-color: #0b0e17 !important;
    color: #e2e8f0 !important;
}
[data-testid="stHeader"] { background-color: #0b0e17 !important; }
[data-testid="stSidebar"] { background-color: #0f1320 !important; }
.block-container { padding: 1.5rem 2rem 3rem 2rem !important; max-width: 1400px; }

/* ── Top nav bar ──────────────────────────────────────────────── */
.nav-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.6rem 0 1.2rem 0;
    border-bottom: 1px solid #1e2440;
    margin-bottom: 1.5rem;
}
.nav-logo {
    font-size: 1.1rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: #7c8cf8;
}
.nav-logo span { color: #e2e8f0; }
.nav-badge {
    font-size: 0.72rem;
    background: #1e2440;
    color: #7c8cf8;
    border: 1px solid #2d3561;
    padding: 2px 10px;
    border-radius: 20px;
    letter-spacing: 0.06em;
}

/* ── Tabs ──────────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
    gap: 0;
    border-bottom: 1px solid #1e2440;
    background: transparent;
}
[data-testid="stTabs"] button[role="tab"] {
    color: #64748b !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    padding: 0.5rem 1.2rem !important;
    border-radius: 0 !important;
    border-bottom: 2px solid transparent !important;
    background: transparent !important;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: #7c8cf8 !important;
    border-bottom: 2px solid #7c8cf8 !important;
    background: transparent !important;
}
[data-testid="stTabs"] [role="tabpanel"] { padding-top: 1.5rem; }

/* ── KPI cards ────────────────────────────────────────────────── */
.kpi-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
.kpi-card {
    flex: 1; min-width: 140px;
    background: #0f1320;
    border: 1px solid #1e2440;
    border-radius: 10px;
    padding: 1rem 1.2rem;
}
.kpi-label { font-size: 0.72rem; color: #64748b; letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 0.3rem; }
.kpi-value { font-size: 1.6rem; font-weight: 700; color: #e2e8f0; line-height: 1; }
.kpi-sub { font-size: 0.75rem; color: #7c8cf8; margin-top: 0.3rem; }

/* ── Section headers ──────────────────────────────────────────── */
.section-header {
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #64748b;
    margin: 1.5rem 0 0.75rem 0;
}

/* ── Table ────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid #1e2440 !important;
    border-radius: 10px !important;
    overflow: hidden;
}
[data-testid="stDataFrame"] > div { background: #0f1320 !important; }

/* ── Buttons ──────────────────────────────────────────────────── */
[data-testid="stButton"] > button {
    background: #1e2440 !important;
    color: #7c8cf8 !important;
    border: 1px solid #2d3561 !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    padding: 0.4rem 1.2rem !important;
    transition: background 0.15s;
}
[data-testid="stButton"] > button:hover {
    background: #2d3561 !important;
}

/* ── Expander ─────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: #0f1320 !important;
    border: 1px solid #1e2440 !important;
    border-radius: 8px !important;
}

/* ── Progress bar ─────────────────────────────────────────────── */
[data-testid="stProgressBar"] > div > div { background: #7c8cf8 !important; }

/* ── Selectbox ────────────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
    background: #0f1320 !important;
    border: 1px solid #1e2440 !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
}

/* ── Hide streamlit branding ──────────────────────────────────── */
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

CSV_PATH = "kols.csv"
BASE = "https://api.sorsa.io/v3"


# ── API helpers ───────────────────────────────────────────────────────────────

def sorsa_get(endpoint: str, username: str) -> tuple[dict | list, str | None]:
    try:
        r = requests.get(
            f"{BASE}/{endpoint}",
            headers={"ApiKey": API_KEY},
            params={"username": username},
            timeout=10,
        )
        if r.ok:
            return r.json(), None
        return {}, f"HTTP {r.status_code}"
    except Exception as e:
        return {}, str(e)


def fetch_new_following_7d(username: str) -> tuple[list, str | None]:
    data, err = sorsa_get("new-following-7d", username)
    if err:
        return [], err
    return data if isinstance(data, list) else [], None


def enrich_project(project: str) -> dict:
    row: dict = {"Profile": project}

    score_data, _ = sorsa_get("score", project)
    row["Score"] = (
        score_data.get("score") or score_data.get("value") or score_data.get("data", {}).get("score")
        if isinstance(score_data, dict) else None
    )

    changes_data, _ = sorsa_get("score-changes", project)
    row["Score Change 7d"] = (
        changes_data.get("change_7d") or changes_data.get("7d") or changes_data.get("data", {}).get("change_7d")
        if isinstance(changes_data, dict) else None
    )

    stats_data, _ = sorsa_get("followers-stats", project)
    if isinstance(stats_data, dict):
        d = stats_data.get("data", stats_data)
        row["Total Followers"]      = d.get("total_followers") or d.get("totalFollowers") or d.get("total")
        row["Influencer Followers"] = d.get("influencer_followers") or d.get("influencerFollowers") or d.get("influencers")
        row["VC Followers"]         = d.get("vc_followers") or d.get("vcFollowers") or d.get("vcs")
    else:
        row["Total Followers"] = row["Influencer Followers"] = row["VC Followers"] = None

    return row


def load_kols() -> pd.DataFrame:
    try:
        df = pd.read_csv(CSV_PATH)
        if "username" not in df.columns:
            st.error("kols.csv nu are coloana 'username'.")
            return pd.DataFrame(columns=["username"])
        return df[["username"]].dropna().reset_index(drop=True)
    except FileNotFoundError:
        st.error(f"'{CSV_PATH}' nu a fost găsit.")
        return pd.DataFrame(columns=["username"])


# ── Session state ─────────────────────────────────────────────────────────────
if "kols_df" not in st.session_state:
    st.session_state.kols_df = load_kols()

kols_df = st.session_state.kols_df
n_kols = len(kols_df)

# ── Nav bar ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="nav-bar">
  <div class="nav-logo">SORSA <span>KOLs</span></div>
  <div class="nav-badge">{'🟢 API KEY SET' if API_KEY else '🔴 NO API KEY'}</div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_trending, tab_kols, tab_lookup = st.tabs(["📈  Trending", "👥  KOLs", "🔍  Lookup"])


# ════════════════════════════════════════════════════════════════════
#  TAB 1 — TRENDING
# ════════════════════════════════════════════════════════════════════
with tab_trending:

    # KPI row
    st.markdown(f"""
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-label">KOLs monitorizați</div>
        <div class="kpi-value">{n_kols}</div>
        <div class="kpi-sub">din kols.csv</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Endpoint</div>
        <div class="kpi-value" style="font-size:0.9rem;padding-top:0.4rem">/new-following-7d</div>
        <div class="kpi-sub">agregare proiect → KOLs</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Enrich / proiect</div>
        <div class="kpi-value">4</div>
        <div class="kpi-sub">score · changes · followers · info</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_run, col_spacer = st.columns([2, 8])
    with col_run:
        run_btn = st.button("▶  Run analiză completă", use_container_width=True)

    if run_btn:
        if not API_KEY:
            st.error("SORSA_API_KEY lipsă din .env")
        elif kols_df.empty:
            st.warning("Nu există usernami în CSV.")
        else:
            kols = kols_df["username"].tolist()

            # Pasul 1
            prog1 = st.progress(0, text="Pasul 1/2 — se colectează following-uri...")
            kol_following_map: dict[str, list] = {}
            step1_errors: dict[str, str] = {}

            for i, kol in enumerate(kols):
                prog1.progress((i + 1) / len(kols), text=f"[1/2] @{kol}")
                following, err = fetch_new_following_7d(kol)
                if err:
                    step1_errors[kol] = err
                else:
                    kol_following_map[kol] = following
            prog1.empty()

            # Agregare
            project_kols: dict[str, list[str]] = {}
            for kol, following in kol_following_map.items():
                for item in following:
                    project = item if isinstance(item, str) else (
                        item.get("username") or item.get("name") or str(item)
                    )
                    project_kols.setdefault(project, []).append(kol)

            unique_projects = list(project_kols.keys())

            if not unique_projects:
                st.info("Niciun proiect detectat — API key inactiv sau KOLs nu urmăresc proiecte noi.")
                with st.expander("Răspunsuri brute pasul 1"):
                    st.json(kol_following_map if kol_following_map else {"info": "Niciun răspuns primit"})
                if step1_errors:
                    with st.expander("Erori"):
                        st.json(step1_errors)
            else:
                # Pasul 2
                prog2 = st.progress(0, text="Pasul 2/2 — se îmbogățesc proiectele...")
                rows = []
                for i, project in enumerate(unique_projects):
                    prog2.progress((i + 1) / len(unique_projects), text=f"[2/2] @{project}")
                    row = enrich_project(project)
                    row["KOLs Following"] = len(project_kols[project])
                    row["KOLs List"] = ", ".join(project_kols[project])
                    rows.append(row)
                prog2.empty()

                result_df = pd.DataFrame(rows, columns=[
                    "Profile", "Score", "Score Change 7d",
                    "Total Followers", "Influencer Followers", "VC Followers",
                    "KOLs Following", "KOLs List",
                ])
                result_df = result_df.sort_values("KOLs Following", ascending=False).reset_index(drop=True)
                result_df.index += 1
                result_df.index.name = "#"

                st.markdown('<div class="section-header">Proiecte trending — sortate după KOLs Following</div>', unsafe_allow_html=True)
                st.dataframe(
                    result_df,
                    use_container_width=True,
                    column_config={
                        "Profile":              st.column_config.TextColumn("Profile"),
                        "Score":                st.column_config.NumberColumn("Score", format="%.1f"),
                        "Score Change 7d":      st.column_config.NumberColumn("Score Δ 7d", format="%+.2f"),
                        "Total Followers":      st.column_config.NumberColumn("Total Flw", format="%d"),
                        "Influencer Followers": st.column_config.NumberColumn("Influencer Flw", format="%d"),
                        "VC Followers":         st.column_config.NumberColumn("VC Flw", format="%d"),
                        "KOLs Following":       st.column_config.NumberColumn("KOLs Following", format="%d"),
                        "KOLs List":            st.column_config.TextColumn("KOLs"),
                    },
                )

                with st.expander("Răspunsuri brute pasul 1 (new-following-7d)"):
                    st.json(kol_following_map)
                if step1_errors:
                    with st.expander("Erori"):
                        st.json(step1_errors)


# ════════════════════════════════════════════════════════════════════
#  TAB 2 — KOLs
# ════════════════════════════════════════════════════════════════════
with tab_kols:
    col_h, col_btn = st.columns([8, 2])
    with col_h:
        st.markdown('<div class="section-header">Lista KOLs</div>', unsafe_allow_html=True)
    with col_btn:
        if st.button("🔄  Refresh CSV", use_container_width=True):
            st.session_state.kols_df = load_kols()
            kols_df = st.session_state.kols_df
            st.success("Reîncărcat!")

    if kols_df.empty:
        st.warning("Nu există usernami de afișat.")
    else:
        display_df = kols_df.copy()
        display_df.index += 1
        display_df.index.name = "#"
        st.dataframe(
            display_df,
            use_container_width=True,
            column_config={"username": st.column_config.TextColumn("Username", width="large")},
        )


# ════════════════════════════════════════════════════════════════════
#  TAB 3 — LOOKUP
# ════════════════════════════════════════════════════════════════════
with tab_lookup:
    st.markdown('<div class="section-header">Caută un username în Sorsa API</div>', unsafe_allow_html=True)

    usernames = kols_df["username"].tolist() if not kols_df.empty else []
    selected = st.selectbox("Username", usernames)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("📋  /info", use_container_width=True):
            with st.spinner():
                res, err = sorsa_get("info", selected)
            st.json(res if not err else {"error": err})
    with col_b:
        if st.button("⭐  /score", use_container_width=True):
            with st.spinner():
                res, err = sorsa_get("score", selected)
            st.json(res if not err else {"error": err})
    with col_c:
        if st.button("👥  /followers-stats", use_container_width=True):
            with st.spinner():
                res, err = sorsa_get("followers-stats", selected)
            st.json(res if not err else {"error": err})
