import streamlit as st
import requests

SUPABASE_URL = "https://ftekfkvduiohcwmsyjml.supabase.co"
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
MISTRAL_API_KEY = st.secrets["MISTRAL_API_KEY"]

st.set_page_config(page_title="Bea - Ton second cerveau", layout="wide")

st.markdown("<style>section[data-testid='stSidebar']{background:#f5f5f7}</style>", unsafe_allow_html=True)

def verifier(email):
    try:
        h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        r = requests.get(f"{SUPABASE_URL}/rest/v1/profiles?email=eq.{email}&select=email", headers=h, timeout=5)
        return len(r.json()) > 0
    except: return False

with st.sidebar:
    st.title("Bea 🧠")
    if "licence_ok" not in st.session_state: st.session_state.licence_ok = False
    if not st.session_state.licence_ok:
        st.markdown("### Débloque ton second cerveau")
        st.link_button("💳 Débloquer pour 39,90€", "https://bea.lemonsqueezy.com/buy/TON_ID", use_container_width=True)
        email = st.text_input("Déjà payé? Ton email")
        if st.button("Débloquer l'accès"):
            if verifier(email):
                st.session_state.licence_ok = True
                st.rerun()
            else: st.error("Email non trouvé dans Supabase")
    else:
        st.success("✅ Pro activé")
        st.link_button("📥 Installer l'app offline", "https://drive.google.com", use_container_width=True)

if not st.session_state.get("licence_ok", False):
    st.title("Bea, ton second cerveau qui ne t'oublie jamais.")
    st.info("Paye une fois et parle directement ici dans le site.")
    st.stop()

st.title("Parle à Bea")
if "messages" not in st.session_state: st.session_state.messages = []
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("Demande quelque chose..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    with st.chat_message("assistant"):
        try:
            headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}"}
            data = {"model": "mistral-small-latest", "messages": st.session_state.messages}
            r = requests.post("https://api.mistral.ai/v1/chat/completions", json=data, headers=headers, timeout=30)
            rep = r.json()["choices"][0]["message"]["content"]
        except Exception as e: rep = f"Erreur: {e}"
        st.markdown(rep)
    st.session_state.messages.append({"role": "assistant", "content": rep})
