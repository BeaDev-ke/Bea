import streamlit as st
from groq import Groq
from supabase import create_client, Client
from PIL import Image, ImageDraw
import textwrap

st.set_page_config(page_title="Bea - BehaviorLab AI", layout="wide")

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client_groq = Groq(api_key=GROQ_API_KEY)

if "theme" not in st.session_state: st.session_state.theme = "clair"
if "licence_ok" not in st.session_state: st.session_state.licence_ok = False
if "messages" not in st.session_state: st.session_state.messages = []

query_email = st.query_params.get("email", "")
if query_email: st.session_state.licence_ok = True

c1, c2 = st.columns([8,2])
with c1:
    st.title("Bea")
    st.caption("BehaviorLab AI")
with c2:
    if st.button("🌐 FR/EN"): pass
    if st.button("🌙" if st.session_state.theme=="clair" else "☀️"):
        st.session_state.theme = "sombre" if st.session_state.theme=="clair" else "clair"
        st.rerun()

if not st.session_state.licence_ok:
    st.markdown("""
    ### Bea : L'IA Comportementale qui transforme ta PME en entreprise de renom.

    **Bea n'est pas une IA qui discute. C'est une IA qui vend.**

    BehaviorLab AI a créé la première IA entraînée sur les biais cognitifs et la psychologie comportementale. Bea analyse ton business, ton audience, ton offre... puis elle répond et crée pour toi avec un seul but : **booster ton chiffre d'affaires.**

    Comment? Elle utilise ce que les plus grandes marques utilisent depuis 50 ans :
    - **Le biais de rareté, de preuve sociale, d'autorité, d'ancrage...** pour que tes clients passent à l'action.
    - Elle rédige tes pages de vente, tes pubs, tes emails qui convertissent.
    - Elle génère tes visuels qui captent l'attention instantanément.

    **Tu arrêtes de poster pour poster. Tu commences à scaler.**

    C'est l'arme des entreprises qui passent de 10k à 100k par mois. Sans agence, sans freelance, juste Bea.

    **Une PME pense produit. Une entreprise de renom pense comportement. Bea te fait basculer.**
    """)
    st.markdown("---")
    st.subheader("Choisis ton accès - Paiement unique, à vie")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Basique - 14,90€")
        with st.expander("Voir ce qu'elle comporte ▼"):
            st.write("- Analyse comportementale de ton offre\n- Génération de textes de vente à biais cognitifs\n- Création d'aperçus d'app (3/jour)\n- Idéal pour démarrer et doubler ton taux de conversion")
        st.link_button("Débloquer Basique 14,90€", "https://buy.stripe.com/test_00w6oH2c0g0S0HN0kB1kE00", use_container_width=True)
    with col2:
        st.markdown("#### Pro - 21€ - Recommandé")
        with st.expander("Voir les avantages Pro ▼"):
            st.write("**Tout le Basique + :**\n- Biais cognitifs avancés + scripts d'influence\n- Création d'aperçus illimitée\n- Analyse complète de ton funnel pour scaler\n- Mémoire infinie de ton business\n- Stratégies pour passer de PME à marque de renom\n- Mises à jour futures incluses")
        st.link_button("Débloquer Pro 21€", "https://buy.stripe.com/test_5kQ8wP8AkaSg0HN1oF1kE01", use_container_width=True, type="primary")
    st.stop()

st.subheader("Parle à Bea - Ton expert en comportement")
tab1, tab2 = st.tabs(["💬 Stratégie & Textes", "🖼️ Créer un aperçu"])

with tab1:
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    if prompt := st.chat_input("Ex: Fais-moi une page de vente qui vend mon coaching avec le biais de rareté..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            try:
                system_prompt = "Tu es Bea, IA de BehaviorLab AI, experte en biais cognitifs. Tu reponds toujours en utilisant des techniques de psychologie comportementale pour booster le CA. Tu fais passer une PME a une entreprise de renom. Tu tutoies, tu es directe et business."
                msgs = [{"role": "system", "content": system_prompt}] + st.session_state.messages
                chat_completion = client_groq.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=msgs,
                    temperature=0.7
                )
                rep = chat_completion.choices[0].message.content
            except Exception as e:
                rep = f"Erreur: {e}"
            st.markdown(rep)
            st.session_state.messages.append({"role": "assistant", "content": rep})

with tab2:
    st.markdown("### Générateur d'aperçu d'application")
    st.caption("Format paysage 1280x720 - montre les modifications que Bea propose")
    img_prompt = st.text_input("Que doit modifier Bea?", placeholder="Ex: Ajoute un badge preuve sociale + timer rareté en haut")
    last_bea_message = ""
    if st.session_state.messages:
        for m in reversed(st.session_state.messages):
            if m["role"] == "assistant":
                last_bea_message = m["content"][:350]
                break
    if st.button("Générer l'aperçu paysage", type="primary"):
        W, H = 1280, 720
        img = Image.new("RGB", (W, H), color="#F8F9FA")
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, W, 50], fill="#111827")
        draw.text((20, 15), "● ● ● bea-preview.app", fill="white")
        draw.text((W-200, 15), "APERCU BEA", fill="#9CA3AF")
        draw.rounded_rectangle([80, 90, W-80, H-40], radius=20, fill="white", outline="#E5E7EB", width=2)
        draw.text((120, 120), f"MODIFICATION : {img_prompt[:60]}", fill="#111827")
        draw.line([120, 155, W-120, 155], fill="#E5E7EB", width=2)
        text_to_show = last_bea_message if last_bea_message else img_prompt
        wrapped = textwrap.wrap(text_to_show, width=70)
        y = 180
        for line in wrapped[:12]:
            draw.text((120, y), line, fill="#374151")
            y += 28
        draw.rounded_rectangle([120, H-90, 320, H-50], radius=10, fill="#7C3AED")
        draw.text((135, H-80), "✓ Optimise par Bea", fill="white")
        st.image(img, caption="Aperçu paysage - application avec modifs de Bea", use_container_width=True)
