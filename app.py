import streamlit as st
import requests

st.set_page_config(page_title="Bea - BehaviorLab AI", layout="wide")

SUPABASE_URL = "https://ftekfkvduiohcwmsyjml.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
MISTRAL_API_KEY = st.secrets.get("MISTRAL_API_KEY", "")

if "theme" not in st.session_state: st.session_state.theme = "clair"
if "licence_ok" not in st.session_state: st.session_state.licence_ok = False
if "messages" not in st.session_state: st.session_state.messages = []

bg = "#0e1117" if st.session_state.theme == "sombre" else "#fcfcf9"
text_color = "#ffffff" if st.session_state.theme == "sombre" else "#111111"
card = "#1c212b" if st.session_state.theme == "sombre" else "#ffffff"

st.markdown("""
<style>
section[data-testid="stSidebar"]{background:%s!important;}
.stTextInput input{border-radius:10px!important;}
</style>
""" % card, unsafe_allow_html=True)

def verifier(email):
    try:
        h = {"apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY}
        r = requests.get(SUPABASE_URL + "/rest/v1/profiles?email=eq." + email + "&select=email", headers=h, timeout=5)
        return len(r.json()) > 0
    except:
        return False

# HEADER
col1, col2 = st.columns([7,3])
with col1:
    st.title("Bea")
    st.caption("BehaviorLab AI")
with col2:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.button("FR/EN", help="Langue")
        st.markdown("<div style='text-align:center; font-size:20px;'>🌐</div>", unsafe_allow_html=True)
    with c2:
        if st.button("🌙" if st.session_state.theme=="clair" else "☀️", help="Clair / Sombre"):
            st.session_state.theme = "sombre" if st.session_state.theme=="clair" else "clair"
            st.rerun()
        st.markdown("<div style='text-align:center; font-size:20px;'>🌓</div>", unsafe_allow_html=True)
    with c3:
        st.button("Galerie", help="Galerie souvenirs")
        st.markdown("<div style='text-align:center; font-size:20px;'>🖼️</div>", unsafe_allow_html=True)

# SIDEBAR
with st.sidebar:
    st.header("Acces")

    st.subheader("Debloquer Basique - 14,90€")
    with st.popover("Voir ce qu'elle comporte ▼"):
        st.write("""
        **Basique 14,90€ :**
        - Chat illimite avec Bea
        - Memoire 30 jours
        - Utilisable sur le site
        - Paiement unique
        """)
    st.link_button("Debloquer Basique 14,90€", "https://bea.lemonsqueezy.com/buy/basic", use_container_width=True)

    st.divider()

    st.subheader("Debloquer Pro - 21€")
    with st.popover("Voir les avantages Pro ▼"):
        st.write("""
        **Pro 21€ - Tout le basique + :**
        - Memoire infinie
        - App offline installable
        - Galerie souvenirs
        - Analyse BehaviorLab
        - Stockage crypte
        - Reponses prioritaires
        - MAJ futures incluses
        """)
    st.link_button("Debloquer Pro 21€", "https://bea.lemonsqueezy.com/buy/pro", use_container_width=True, type="primary")

    st.divider()
    email = st.text_input("Email de paiement", placeholder="ton@email.com")
    if st.button("Debloquer l'acces", use_container_width=True):
        if verifier(email):
            st.session_state.licence_ok = True
            st.rerun()
        else:
            st.error("Email non trouve")

# CONTENU
if not st.session_state.licence_ok:
    st.title("Bea, ton second cerveau qui ne t'oublie jamais.")
    st.info("Choisis ton acces a gauche.")
    st.stop()

st.subheader("Parle a Bea")
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Ecris a Bea..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        try:
            headers = {"Authorization": "Bearer " + MISTRAL_API_KEY}
            data = {"model": "mistral-small-latest", "messages": st.session_state.messages}
            r = requests.post("https://api.mistral.ai/v1/chat/completions", json=data, headers=headers, timeout=30)
            rep = r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            rep = "Erreur: " + str(e)
        st.markdown(rep)
    st.session_state.messages.append({"role": "assistant", "content": rep})
