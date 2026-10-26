import streamlit as st
from utils.sorsa import SorsaClient


def render():
    st.markdown("## 👑 KOL Intelligence")

    api_key = st.session_state.get("sorsa_api_key", "")
    if not api_key:
        st.warning("Add Sorsa API key in ⚙️ Settings.")
        return

    client = SorsaClient(api_key)

    @st.cache_data(ttl=600)
    def fetch_kols(key):
        c = SorsaClient(key)
        return c.get_top_kols(limit=20)

    @st.cache_data(ttl=600)
    def fetch_following(key):
        c = SorsaClient(key)
        return c.get_new_following_7d(limit=20)

    st.markdown("### Top KOLs")
    kols = fetch_kols(api_key)
    if kols:
        st.dataframe(kols, use_container_width=True)
    else:
        st.info("No KOL data returned.")

    st.markdown("### 🔍 Tokens KOLs Are Watching (7d)")
    following = fetch_following(api_key)
    if following:
        st.dataframe(following, use_container_width=True)
    else:
        st.info("No following data returned.")
