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


def fetch_new_following_7d(username: str) -> tuple[list, str | None]:
    """Returns (list_of_accounts, error_message)."""
    try:
        r = requests.get(
            "https://api.sorsa.io/v3/new-following-7d",
            headers={"ApiKey": API_KEY},
            params={"username": username},
            timeout=10,
        )
        if r.ok:
            return r.json(), None
        return [], f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return [], str(e)


def aggregate_followings(kols: list[str]) -> tuple[dict, dict]:
    """
    Returns:
        aggregated: {project_username: [kol1, kol2, ...]}
        errors:     {kol: error_message}
    """
    aggregated: dict[str, list[str]] = {}
    errors: dict[str, str] = {}
    for kol in kols:
        following, err = fetch_new_following_7d(kol)
        if err:
            errors[kol] = err
            continue
        # API may return a list of strings or list of dicts
        for item in following:
            project = item if isinstance(item, str) else item.get("username") or item.get("name") or str(item)
            aggregated.setdefault(project, []).append(kol)
    return aggregated, errors


def fetch_sorsa_info(username: str) -> dict:
    try:
        r = requests.get(
            "https://api.sorsa.io/v3/info",
            headers={"ApiKey": API_KEY},
            params={"username": username},
            timeout=8,
        )
        if r.ok:
            return r.json()
    except Exception:
        pass
    return {}


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

# ── Tabel ────────────────────────────────────────────────────────────────────
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
        column_config={
            "username": st.column_config.TextColumn("Username", width="large"),
        },
    )

# ── New Following 7d ─────────────────────────────────────────────────────────
st.divider()
st.subheader("📡 New Following 7d — toate KOL-urile")
st.caption("Agregare: proiect → lista de KOLs care l-au urmărit în ultimele 7 zile")

if st.button("▶ Run agregare", use_container_width=False):
    if not API_KEY:
        st.error("SORSA_API_KEY lipsă din .env")
    elif df.empty:
        st.warning("Nu există usernami în CSV.")
    else:
        kols = df["username"].tolist()
        progress = st.progress(0, text="Se interoghează KOLs...")
        raw_responses: dict[str, list] = {}
        errors: dict[str, str] = {}

        for i, kol in enumerate(kols):
            progress.progress((i + 1) / len(kols), text=f"Fetch: @{kol}")
            following, err = fetch_new_following_7d(kol)
            if err:
                errors[kol] = err
            else:
                raw_responses[kol] = following

        progress.empty()

        # Agregare proiect → KOLs
        aggregated: dict[str, list[str]] = {}
        for kol, following in raw_responses.items():
            for item in following:
                project = item if isinstance(item, str) else (
                    item.get("username") or item.get("name") or str(item)
                )
                aggregated.setdefault(project, []).append(kol)

        st.subheader("Rezultat brut per KOL")
        st.json(raw_responses if raw_responses else {"info": "Niciun răspuns primit (API key inactiv sau endpoint indisponibil)"})

        st.subheader("Agregat: proiect → KOLs")
        st.json(aggregated if aggregated else {"info": "Nicio dată de agregat"})

        if errors:
            st.subheader("Erori")
            st.json(errors)

# ── Sorsa info lookup ─────────────────────────────────────────────────────────
st.divider()
st.subheader("🔍 Caută user în Sorsa API (/info)")

selected = st.selectbox("Selectează username", df["username"].tolist() if not df.empty else [])

if st.button("Fetch din Sorsa API"):
    if not API_KEY:
        st.error("SORSA_API_KEY lipsă din .env")
    elif selected:
        with st.spinner(f"Se interoghează {selected}..."):
            result = fetch_sorsa_info(selected)
        if result:
            st.json(result)
        else:
            st.warning("Nu s-a primit răspuns de la Sorsa API.")
