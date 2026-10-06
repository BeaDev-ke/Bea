import streamlit as st
import requests

# --- CONFIG ---
st.set_page_config(page_title="Bea - BehaviorLab AI", layout="wide")

SUPABASE_URL = "https://ftekfkvduiohcwmsyjml.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
MISTRAL_API_KEY = st.secrets.get("MISTRAL_API_KEY", "")

if "theme" not in st.session_state: st.session_state.theme = "clair"
if "lang" not in st.session_state: st.session_state.lang = "FR"
if "licence_ok" not in st.session_state: st.session_state.licence_ok = False
if "messages" not in st.session_state: st.session_state.messages = []

# --- DESIGN ---
bg = "#0e1117" if st.session_state.theme == "sombre" else "#fcfcf9"
text = "#ffffff" if st.session_state.theme == "sombre" else "#111111"
card = "#1c212b" if st.session_state.theme == "sombre" else "#ffffff"

st.markdown(f"""
<style>
.stApp {{background:{bg}; color:{text};}}
section[data-testid="stSidebar"]{{background:{card}!important;}}
div[data-testid="stExpander"]{{border:none; background:transparent;}}
/* enlever les carrés noirs moches */
.stTextInput input{{border-radius:10px!important;}}
</style>
""", unsafe_allow_html=True)

def verifier(email):
    try:
        h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        r = requests.get(f"{SUPABASE_URL}/rest/v1/profiles?email=eq.{email}&select=email", headers=h, timeout=5)
        return len(r.json()) > 0
    except: return False

# --- HEADER ---
col_title, col_icons = st.columns([7,3])
with col_title:
    st.markdown(f"<h1 style='margin-bottom:0; color:{text};'>Bea</h1>
