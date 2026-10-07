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
if "with_image" not in st.session_state: st.session_state.with_image = False

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
    ### Bea : L'IA Comportementale qui transforme ton activité en marque qui compte.

    **Bea n'est pas une IA qui discute. C'est une IA qui vend.**

    BehaviorLab AI a créé la première IA entraînée sur les biais cognitifs et la psychologie comportementale. Bea analyse ton activité, ton audience, ton offre... puis elle répond et crée pour toi avec un seul but : **augmenter ton chiffre d'affaires.**

    Comment? Elle utilise ce que les plus grandes marques utilisent depuis 50 ans :
    - **Le biais de rareté, de preuve sociale, d'autorité, d'ancrage...** pour que tes clients passent à l'action.
    - Elle rédige tes pages de vente, tes publicités, tes emails qui convertissent vraiment.
    - Elle génère tes visuels qui captent l'attention instantanément.

    **Tu arrêtes de poster au hasard. Tu commences à vendre plus et mieux.**

    C'est l'outil des entreprises qui passent de 10k à 100k par mois. Sans agence, sans freelance, juste Bea.

    **Une petite entreprise pense produit. Une grande marque pense comportement. Bea te fait basculer.**
    """)
    st.markdown("---")
    st.subheader("Choisis ton accès - Paiement unique, à vie")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Basique - 14,90€")
        with st.expander("Voir ce qu'elle comporte ▼"):
            st.write("- Analyse comportementale de ton offre\n- Génération de textes de vente basés sur la psychologie\n- Création d'aperçus de ton app (3/jour)\n- Idéal pour démarrer et améliorer ton taux de conversion")
        st.link_button("Débloquer Basique 14,90€", "https://buy.stripe.com/test_00w6oH2c0g0S0HN0kB1kE00", use_container_width=True)
    with col2:
        st.markdown("#### Pro - 21€ - Recommandé")
        with st.expander("Voir les avantages Pro ▼"):
            st.write("**Tout le Basique + :**\n- Biais cognitifs avancés + méthodes d'influence\n- Création d'aperçus illimitée\n- Analyse complète de ton parcours client pour mieux vendre\n- Mémoire infinie de ton activité\n- Stratégies pour te faire passer de petite entreprise à marque reconnue\n- Mises à jour futures incluses")
        st.link_button("Débloquer Pro 21€", "https://buy.stripe.com/test_5kQ8wP8AkaSg0HN1oF1kE01", use_container_width=True, type="primary")
    st.stop()

st.subheader("Parle à Bea - Ton expert en comportement")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("image"):
            st.image(m["image"], caption="Aperçu généré par Bea", use_container_width=True)

st.checkbox("🖼️ Illustrer ce que dit Bea avec un aperçu paysage", key="with_image")

if prompt := st.chat_input("Ex: Fais-moi une page de vente qui vend mon coaching avec le biais de rareté..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            system_prompt = "Tu es Bea, IA de BehaviorLab AI, experte en biais cognitifs. Tu ne dois jamais utiliser les mots scale, scaler, scaling. Utilise developper, faire grandir, passer a l'etape superieure, augmenter le chiffre d'affaires. Tu tutoies, tu es directe et business."
            msgs = [{"role": "system", "content": system_prompt}] + [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
            chat_completion = client_groq.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=msgs,
                temperature=0.7
            )
            rep = chat_completion.choices[0].message.content
        except Exception as e:
            rep = f"Erreur: {e}"

        st.markdown(rep)

        gen_img = None
        if st.session_state.with_image:
            W, H = 1280, 720
            img = Image.new("RGB", (W, H), color="#F8F9FA")
            draw = ImageDraw.Draw(img)
            draw.rectangle([0, 0, W, 50], fill="#111827")
            draw.text((20, 15), "● ● ● bea-preview.app", fill="white")
            draw.text((W-250, 15), "APERCU BEA - ILLUSTRATION", fill="#9CA3AF")
            draw.rounded_rectangle([80, 90, W-80, H-40], radius=20, fill="white", outline="#E5E7EB", width=2)
            draw.text((120, 120), f"SUJET : {prompt[:70]}", fill="#111827")
            draw.line([120, 155, W-120, 155], fill="#E5E7EB", width=2)
            wrapped = textwrap.wrap(rep[:400], width=65)
            y = 180
            for line in wrapped[:14]:
                draw.text((120, y), line, fill="#374151")
                y += 28
            draw.rounded_rectangle([120, H-90, 320, H-50], radius=10, fill="#7C3AED")
            draw.text((135, H-80), "✓ Optimise par Bea", fill="white")
            gen_img = img
            st.image(gen_img, caption="Aperçu paysage - illustration de ce que dit Bea", use_container_width=True)

        msg_to_save = {"role": "assistant", "content": rep}
        if gen_img: msg_to_save["image"] = gen_img
        st.session_state.messages.append(msg_to_save)
