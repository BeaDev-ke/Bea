import streamlit as st
from groq import Groq
from supabase import create_client
from PIL import Image, ImageDraw, ImageFont
import os

st.set_page_config(page_title="Bea - BehaviorLab AI", layout="wide")

# --- SECRETS ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]
GROQ_KEY = st.secrets["GROQ_API_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
groq_client = Groq(api_key=GROQ_KEY)

# --- THEME + LANGUE ---
if "theme" not in st.session_state:
    st.session_state.theme = "sombre"
if "lang" not in st.session_state:
    st.session_state.lang = "FR"

def generer_apercu_paysage(texte_modif):
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), (18, 18, 40))
    draw = ImageDraw.Draw(img)
    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 32)
        font_text = ImageFont.truetype("DejaVuSans.ttf", 22)
    except:
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()
    draw.rectangle([0, 0, W, 90], fill=(120, 60, 255))
    draw.text((30, 25), "Bea - Aperçu bureau 1280x720", font=font_title, fill="white")
    draw.rectangle([30, 120, W-30, H-30], fill=(35, 35, 70), outline=(120, 60, 255), width=2)
    draw.text((60, 150), f"Modif : {texte_modif[:110]}", font=font_text, fill="white")
    draw.text((60, 210), "→ Simulation format ordinateur", font=font_text, fill="#B0A0FF")
    return img

# --- LICENCE ---
licence_key = st.query_params.get("key", "")
if not licence_key:
    st.error("Ajoute?key=TA-CLE dans l'URL")
    st.stop()

try:
    res = supabase.table("licences").select("*").eq("key", licence_key).execute()
    if not res.data:
        st.error("Licence invalide")
        st.stop()
    licence = res.data[0]
    plan = licence.get("plan", "BASIC")
except Exception as e:
    st.error(f"Erreur Supabase: {e}")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- HEADER AVEC TITRE + BOUTONS A DROITE ---
col_title, col_btns = st.columns([3, 1])

with col_title:
    # Remplace Discussion - PRO par Bea + BehaviorLab AI
    st.markdown("# Bea")
    st.markdown("<p style='margin-top:-15px; color:gray; font-size:16px;'>BehaviorLab AI</p>", unsafe_allow_html=True)
    if plan == "BASIC":
        st.caption(f"Mémoire intacte : 15 dernières requêtes pour BASIC, illimité pour PRO")

with col_btns:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🌙 / ☀️", help="Clair / Sombre"):
            st.session_state.theme = "clair" if st.session_state.theme == "sombre" else "sombre"
            st.rerun()
    with c2:
        if st.button("FR / EN"):
            st.session_state.lang = "EN" if st.session_state.lang == "FR" else "FR"
            st.rerun()
    st.caption(f"{st.session_state.theme} | {st.session_state.lang}")

# CSS pour simuler clair/sombre
if st.session_state.theme == "clair":
    st.markdown("<style>.stApp{background-color:#F8F8FF; color:#111}</style>", unsafe_allow_html=True)

# --- SIDEBAR GAUCHE AVEC LOGO AU LIEU DE L'ETOILE ---
with st.sidebar:
    # Logo à la place de l'étoile
    col_logo, col_name = st.columns([1, 2])
    with col_logo:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=45)
        else:
            st.markdown("### 🧠") # fallback si pas de logo.png
    with col_name:
        st.markdown("### Bea")
        st.caption(f"Licence : {licence_key}")
        st.caption(f"Plan : {plan}")

    st.divider()
    st.markdown("**Historique**")
    for m in reversed(st.session_state.messages[-15:]):
        if m["role"] == "user":
            st.markdown(f"💬 {m['content'][:40]}...")

    st.divider()
    st.markdown("**Galerie PRO**")
    if plan == "PRO":
        uploaded = st.file_uploader("Glisse une image", type=["png","jpg","jpeg"], label_visibility="collapsed")
        if uploaded:
            st.image(uploaded, use_container_width=True)
            st.session_state["last_upload"] = uploaded
    else:
        st.info("Passe en PRO pour la galerie")

    if st.button("🗑️ Nouvelle discussion"):
        st.session_state.messages = []
        st.rerun()

# --- DISCUSSION CENTRALE EN GROS ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(f"<div style='font-size:18px'>{m['content']}</div>", unsafe_allow_html=True)
        if "image" in m and m["image"] is not None:
            st.image(m["image"], use_container_width=True)

# --- CASE COCHABLE JUSTE AU DESSUS DU TEXTE ---
st.divider()
generer_case = st.checkbox("🖼️ Générer un aperçu paysage (format ordi 1280x720) avec Pillow", value=False)

prompt = st.chat_input("Décris une situation de ton entreprise et ton état d'esprit actuel...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    if plan!= "PRO":
        if len(st.session_state.messages) > 30:
            st.session_state.messages = st.session_state.messages[-30:]

    with st.chat_message("user"):
        st.markdown(f"<div style='font-size:18px'>{prompt}</div>", unsafe_allow_html=True)

    with st.chat_message("assistant"):
        if generer_case:
            img = generer_apercu_paysage(prompt)
            st.markdown("Voici l'aperçu paysage généré avec Pillow :")
            st.image(img, use_container_width=True, caption="Aperçu 1280x720")
            st.session_state.messages.append({"role": "assistant", "content": f"Aperçu généré pour : {prompt}", "image": img})
        else:
            try:
                history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if "image" not in m]
                if plan!= "PRO":
                    history = history[-30:]
                completion = groq_client.chat.completions.create(
                    model="llama-3.1-70b-versatile",
                    messages=[{"role": "system", "content": "Tu es Bea, coach business bienveillante, directe, pour entrepreneurs."}] + history
                )
                reponse = completion.choices[0].message.content
                st.markdown(f"<div style='font-size:18px'>{reponse}</div>", unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": reponse})
            except Exception as e:
                st.error(f"Erreur Groq: {e}")
