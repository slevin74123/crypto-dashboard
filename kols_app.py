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

# ── Sorsa lookup ─────────────────────────────────────────────────────────────
st.divider()
st.subheader("🔍 Caută user în Sorsa API")

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
