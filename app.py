import streamlit as st
import requests

st.set_page_config(page_title="Bea - BehaviorLab AI", layout="wide")

SUPABASE_URL = "https://ftekfkvduiohcwmsyjml.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
MISTRAL_API_KEY = st.secrets.get("MISTRAL_API_KEY", "")

if "theme" not in st.session_state: st.session_state.theme = "clair"
if "licence_ok" not in st.session_state: st.session_state.licence_ok = False
if "messages" not in st.session_state: st.session_state.messages = []

query_email = st.query_params.get("email", "")
if query_email: st.session_state.licence_ok = True

# HEADER
c1, c2 = st.columns([8,2])
with c1:
    st.title("Bea")
    st.caption("BehaviorLab AI")
with c2:
    if st.button("🌐 FR/EN", help="Langue"): pass
    if st.button("🌙" if st.session_state.theme=="clair" else "☀️", help="Clair / Sombre"):
        st.session_state.theme = "sombre" if st.session_state.theme=="clair" else "clair"
        st.rerun()

# PAGE VENTE
if not st.session_state.licence_ok:
    st.markdown("""
    ### Bea : L'IA Comportementale qui transforme ta PME en entreprise de renom.

    **Bea n'est pas une IA qui discute. C'est une IA qui vend.**

    BehaviorLab AI a créé la première IA entrainée sur les biais cognitifs et la psychologie comportementale. Bea analyse ton business, ton audience, ton offre... puis elle répond et crée pour toi avec un seul but : **booster ton chiffre d'affaires.**

    Comment? Elle utilise ce que les plus grandes marques utilisent depuis 50 ans :
    - **Le biais de rareté, de preuve sociale, d'autorité, d'ancrage...** pour que tes clients passent à l'action.
    - Elle rédige tes pages de vente, tes pubs, tes emails qui convertissent.
    - Elle génère tes visuels qui captent l'attention instantanément.

    **Tu arrêtes de poster pour poster. Tu commences à scaler.**

    C'est l'arme des entreprises qui passent de 10k à 100k par mois. Sans agence, sans freelance, juste Bea.

    **Une PME pense produit. Une entreprise de renom pense comportement. Bea te fait basculer.**
    """)

    st.markdown("---")
    st.subheader("Choisis ton accès - Paiement unique à vie")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Basique - 14,90€")
        with st.expander("Voir ce qu'elle comporte ▼"):
            st.write("""
            - Analyse comportementale de ton offre
            - Génération de textes de vente à biais cognitifs
            - Création d'images pub (3/jour)
            - Idéal pour démarrer et doubler ton taux de conversion
            """)
        st.link_button("Débloquer Basique 14,90€", "https://bea.lemonsqueezy.com/buy/basic", use_container_width=True)

    with col2:
        st.markdown("#### Pro - 21€ - Recommandé")
        with st.expander("Voir les avantages Pro ▼"):
            st.write("""
            **Tout le Basique + :**
            - Biais cognitifs avancés + scripts d'influence
            - Création d'images illimitée
            - Analyse complète de ton funnel pour scaler
            - Mémoire infinie de ton business
            - Stratégies pour passer de PME à marque de renom
            - Mises à jour futures incluses
            """)
        st.link_button("Débloquer Pro 21€", "https://bea.lemonsqueezy.com/buy/pro", use_container_width=True, type="primary")
    st.stop()

# CHAT + CREER UNE IMAGE
st.subheader("Parle à Bea - Ton expert en comportement")
tab1, tab2 = st.tabs(["💬 Stratégie & Textes", "🖼️ Créer une image pub"])

with tab1:
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    if prompt := st.chat_input("Ex: Fais-moi une pub qui vend mon coaching avec le biais de rareté..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            try:
                headers = {"Authorization": "Bearer " + MISTRAL_API_KEY}
                system_prompt = "Tu es Bea, IA de BehaviorLab AI, experte en biais cognitifs. Tu analyses et tu reponds toujours en utilisant des techniques de psychologie comportementale pour booster le CA. Tu fais passer une PME a une entreprise de renom."
                msgs = [{"role": "system", "content": system_prompt}] + st.session_state.messages
                data = {"model": "mistral-small-latest", "messages": msgs}
                r = requests.post("https://api.mistral.ai/v1/chat/completions", json=data, headers=headers, timeout=30)
                rep = r.json()["choices"][0]["message"]["content"]
            except Exception as e:
                rep = "Erreur: " + str(e)
            st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})

with tab2:
    st.markdown("### Générateur d'images à conversion")
    img_prompt = st.text_input("Décris l'image pub que tu veux", placeholder="Ex: Une femme CEO qui regarde l'horizon, luxe, autorité, format carré")
    if st.button("Créer l'image", type="primary"):
        st.info("Génération via Bea... (On branche ton API image ici - DALL·E / Stability)")
        # Ici on avait ton code VS Code : appel API image
        # requests.post("https://api.stability.ai/...")
        st.success("Image générée - (à brancher avec ta clé Stability)")
