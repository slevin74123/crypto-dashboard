import streamlit as st
import pandas as pd
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("SORSA_API_KEY", "")

st.set_page_config(page_title="KOLs Dashboard", page_icon="🔑", layout="wide")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0e1117; }
    [data-testid="stHeader"] { background-color: #0e1117; }
    .block-container { padding-top: 2rem; }
    h1, h2, h3, p, label { color: #fafafa !important; }
    .stDataFrame { background-color: #1a1d27; border-radius: 8px; }
    div[data-testid="stDataFrame"] > div { background-color: #1a1d27 !important; }
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
    """Fetch score, score-changes, followers-stats, info for a project username."""
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


# ── CSV loader ────────────────────────────────────────────────────────────────

def load_kols() -> pd.DataFrame:
    try:
        df = pd.read_csv(CSV_PATH)
        if "username" not in df.columns:
            st.error("Fișierul kols.csv nu are coloana 'username'.")
            return pd.DataFrame(columns=["username"])
        return df[["username"]].dropna().reset_index(drop=True)
    except FileNotFoundError:
        st.error(f"Fișierul '{CSV_PATH}' nu a fost găsit.")
        return pd.DataFrame(columns=["username"])


# ── State ────────────────────────────────────────────────────────────────────
if "kols_df" not in st.session_state:
    st.session_state.kols_df = load_kols()

# ── Header ───────────────────────────────────────────────────────────────────
col_title, col_btn = st.columns([6, 1])
with col_title:
    st.title("🔑 KOLs Dashboard")
    st.caption(f"{len(st.session_state.kols_df)} usernami încărcați din `{CSV_PATH}`")
with col_btn:
    st.write("")
    st.write("")
    if st.button("🔄 Refresh", use_container_width=True):
        st.session_state.kols_df = load_kols()
        st.success("Listă reîncărcată!")

st.divider()

# ── Tabel KOLs ───────────────────────────────────────────────────────────────
df = st.session_state.kols_df

if df.empty:
    st.warning("Nu există usernami de afișat.")
else:
    display_df = df.copy()
    display_df.index += 1
    display_df.index.name = "#"
    st.dataframe(
        display_df,
        use_container_width=True,
        column_config={"username": st.column_config.TextColumn("Username", width="large")},
    )

# ── Run complet ───────────────────────────────────────────────────────────────
st.divider()
st.subheader("📊 Proiecte urmărite de KOLs — tabel final")
st.caption("Pasul 1: new-following-7d per KOL → Pasul 2: enrich per proiect unic")

if st.button("▶ Run analiză completă", use_container_width=False):
    if not API_KEY:
        st.error("SORSA_API_KEY lipsă din .env")
    elif df.empty:
        st.warning("Nu există usernami în CSV.")
    else:
        kols = df["username"].tolist()

        # ── Pasul 1: new-following-7d ─────────────────────────────────────
        prog1 = st.progress(0, text="Pasul 1: se colectează following-uri...")
        kol_following_map: dict[str, list] = {}
        step1_errors: dict[str, str] = {}

        for i, kol in enumerate(kols):
            prog1.progress((i + 1) / len(kols), text=f"[1/2] Fetch following: @{kol}")
            following, err = fetch_new_following_7d(kol)
            if err:
                step1_errors[kol] = err
            else:
                kol_following_map[kol] = following

        prog1.empty()

        # Agregare proiect → lista KOLs
        project_kols: dict[str, list[str]] = {}
        for kol, following in kol_following_map.items():
            for item in following:
                project = item if isinstance(item, str) else (
                    item.get("username") or item.get("name") or str(item)
                )
                project_kols.setdefault(project, []).append(kol)

        unique_projects = list(project_kols.keys())

        if not unique_projects:
            st.info("Niciun proiect detectat (API key inactiv sau KOLs nu urmăresc proiecte noi).")
            st.subheader("Răspunsuri brute (pasul 1)")
            st.json(kol_following_map if kol_following_map else {"info": "Niciun răspuns primit"})
            if step1_errors:
                st.subheader("Erori pasul 1")
                st.json(step1_errors)
        else:
            # ── Pasul 2: enrich per proiect ───────────────────────────────
            prog2 = st.progress(0, text="Pasul 2: se îmbogățesc proiectele...")
            rows = []

            for i, project in enumerate(unique_projects):
                prog2.progress((i + 1) / len(unique_projects), text=f"[2/2] Enrich: @{project}")
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

            st.dataframe(
                result_df,
                use_container_width=True,
                column_config={
                    "Profile":              st.column_config.TextColumn("Profile"),
                    "Score":                st.column_config.NumberColumn("Score", format="%.1f"),
                    "Score Change 7d":      st.column_config.NumberColumn("Score Δ 7d", format="%+.2f"),
                    "Total Followers":      st.column_config.NumberColumn("Total Followers", format="%d"),
                    "Influencer Followers": st.column_config.NumberColumn("Influencer Followers", format="%d"),
                    "VC Followers":         st.column_config.NumberColumn("VC Followers", format="%d"),
                    "KOLs Following":       st.column_config.NumberColumn("KOLs Following", format="%d"),
                    "KOLs List":            st.column_config.TextColumn("KOLs"),
                },
            )

            with st.expander("Răspunsuri brute pasul 1 (new-following-7d)"):
                st.json(kol_following_map)
            if step1_errors:
                with st.expander("Erori"):
                    st.json(step1_errors)

# ── Sorsa info lookup ─────────────────────────────────────────────────────────
st.divider()
st.subheader("🔍 Caută user în Sorsa API (/info)")

selected = st.selectbox("Selectează username", df["username"].tolist() if not df.empty else [])

if st.button("Fetch info"):
    if not API_KEY:
        st.error("SORSA_API_KEY lipsă din .env")
    elif selected:
        with st.spinner(f"Se interoghează {selected}..."):
            result, err = sorsa_get("info", selected)
        if err:
            st.warning(f"Eroare: {err}")
        elif result:
            st.json(result)
        else:
            st.warning("Răspuns gol de la Sorsa API.")
