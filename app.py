import streamlit as st
from groq import Groq
from supabase import create_client, Client
import time

# --- CONFIG ---
st.set_page_config(page_title="Bea - Ton assistante", page_icon="✨", layout="centered")

# Secrets depuis Streamlit Cloud
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client_groq = Groq(api_key=GROQ_API_KEY)

# --- PROMPT DE BEA (TON PERSONA) ---
SYSTEM_PROMPT = """
Tu es Bea, une assistante bienveillante, chaleureuse et experte en développement personnel, organisation et mindset pour femmes entrepreneures.
Tu parles en français, tu tutoies, tu es directe mais douce.
Tu donnes des conseils concrets, actionnables, jamais de blabla.
Si on te demande qui tu es, tu es Bea, créée par [Ton Prénom].
"""

# --- 1. VERIFICATION ABONNEMENT ---
query_params = st.query_params
email_client = query_params.get("email", None)

is_subscribed = False
plan_client = None

if email_client:
    try:
        response = supabase.table("profiles").select("*").eq("email", email_client).single().execute()
        if response.data and response.data.get("is_subscribed"):
            is_subscribed = True
            plan_client = response.data.get("plan")
    except:
        is_subscribed = False

# --- 2. SI PAS ABONNÉ -> PAYWALL ---
if not is_subscribed:
    st.title("✨ Rencontre Bea")
    st.subheader("Ton assistante mindset & organisation qui ne te juge jamais.")
    st.write("Pour discuter avec Bea, choisis ton accès :")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🌸 Basique - 14,90€/mois")
        st.write("- Accès à Bea 24/7\n- Réponses illimitées")
        st.link_button("Choisir Basique", "https://buy.stripe.com/test_00w6oH2c0g0S0HN0kB1kE00")
    with col2:
        st.markdown("#### 👑 Pro - 21€/mois")
        st.write("- Tout du Basique\n- + Exercices perso\n- + Suivi")
        st.link_button("Choisir Pro", "https://buy.stripe.com/test_5kQ8wP8AkaSg0HN1oF1kE01")

    st.info("Après paiement, tu seras redirigée automatiquement et Bea se débloquera.")
    st.stop()

# --- 3. SI ABONNÉ -> CHAT BEA (GRATUIT AVEC GROQ) ---
st.title(f"✨ Hey! C'est Bea ({plan_client})")
st.write(f"Connectée en tant que : **{email_client}**")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

# Afficher historique
for msg in st.session_state.messages:
    if msg["role"]!= "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# Input utilisateur
if prompt := st.chat_input("Pose ta question à Bea..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Bea réfléchit..."):
            try:
                chat_completion = client_groq.chat.completions.create(
                    model="llama-3.3-70b-versatile", # 100% GRATUIT
                    messages=st.session_state.messages,
                    temperature=0.7,
                    max_tokens=1024,
                )
                response = chat_completion.choices[0].message.content

                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

            except Exception as e:
                st.error(f"Oups, petite erreur : {e}")
