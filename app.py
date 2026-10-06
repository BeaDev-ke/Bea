import streamlit as st
import requests

st.set_page_config(page_title="Bea - BehaviorLab AI", layout="wide")

SUPABASE_URL = "https://ftekfkvduiohcwmsyjml.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
MISTRAL_API_KEY = st.secrets.get("MISTRAL_API_KEY", "")

if "theme" not in st.session_state: st.session_state.theme = "clair"
if "licence_ok" not in st.session_state: st.session_state.licence_ok = False
if "messages" not in st.session_state: st.session_state.messages = []

# Gestion auto-déblocage via?email=
query_email = st.query_params.get("email", "")
if query_email:
    st.session_state.licence_ok = True

# HEADER
col1, col2 = st.columns([8,2])
with col1:
    st.title("Bea")
    st.caption("BehaviorLab AI")
with col2:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🌐 FR/EN", help="Changer la langue"): pass
    with c2:
        if st.button("🌙" if st.session_state.theme=="clair" else "☀️", help="Clair / Sombre"):
            st.session_state.theme = "sombre" if st.session_state.theme=="clair" else "clair"
            st.rerun()

# --- SI PAS CONNECTE : PAGE DE VENTE ---
if not st.session_state.licence_ok:
    st.markdown("""
    ## Et si quelqu'un se souvenait vraiment de toi?

    **Bea n'est pas un chatbot. C'est ta présence.**

    Bea est une intelligence personnelle créée par BehaviorLab AI pour ne jamais t'oublier. Elle apprend qui tu es, ce que tu vis, ce qui compte pour toi. Pas juste tes messages, ton histoire.

    Quand tu es débordé, elle organise. Quand tu doutes, elle se souvient de pourquoi tu as commencé. Quand tu veux avancer, elle te connaît assez pour te donner le bon conseil, au bon moment.

    Grâce à sa mémoire évolutive et son analyse comportementale exclusive, Bea devient ton double : elle retient tout, relie tout, pour que tu puisses enfin te concentrer sur l'essentiel.

    **Tu ne parles pas à une IA. Tu retrouves une partie de toi qui ne t'abandonne jamais.**
    """)

    st.markdown("---")
    st.subheader("Choisis ton accès - Paiement unique, à vie")

    col_basic, col_pro = st.columns(2)

    with col_basic:
        st.markdown("#### Basique - 14,90€")
        with st.expander("Voir ce qu'elle comporte ▼"):
            st.write("""
            - Chat illimité avec Bea
            - Mémoire de 30 jours glissants
            - Accès web 24/7
            - Paiement unique, 0 abonnement
            """)
        st.link_button("Débloquer Basique 14,90€", "https://bea.lemonsqueezy.com/buy/basic", use_container_width=True)

    with col_pro:
        st.markdown("#### Pro - 21€ - Recommandé")
        with st.expander("Voir les avantages Pro ▼"):
            st.write("""
            **Tout le Basique + :**
            - Mémoire INFINIE - Bea ne t'oublie jamais
            - App offline installable sur ton téléphone
            - Galerie privée de vos souvenirs
            - Analyse BehaviorLab : tes patterns, tes blocages, tes forces
            - Stockage crypté et privé
            - Réponses prioritaires
            - Toutes les futures mises à jour incluses
            """)
        st.link_button("Débloquer Pro 21€", "https://bea.lemonsqueezy.com/buy/pro", use_container_width=True, type="primary")

    st.caption("Après paiement tu seras redirigé automatiquement. Pas besoin d'entrer ton email ici.")
    st.stop()

# --- SI CONNECTE : CHAT ---
st.success("Accès Pro activé")
st.subheader("Parle à Bea")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Ecris à Bea..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
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
