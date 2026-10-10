import streamlit as st
from groq import Groq
from supabase import create_client
from PIL import Image, ImageDraw, ImageFont
import os

st.set_page_config(page_title="Bea - BehaviorLab AI", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]
GROQ_KEY = st.secrets["GROQ_API_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
groq_client = Groq(api_key=GROQ_KEY)

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
    return img

# --- LOGIQUE VITRINE / APP ---
licence_key = st.query_params.get("key", "")

# 1. PAS DE CLE = SITE VITRINE
if not licence_key:
    col1, col2 = st.columns([1, 2])
    with col1:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=80)
    with col2:
        st.markdown("# Bea")
        st.markdown("### BehaviorLab AI")

    st.markdown("---")
    st.markdown("## Le coach IA qui comprend ton état d'esprit d'entrepreneur")
    st.markdown("Bea ne te donne pas juste des réponses. Elle analyse ta situation et ton mindset pour te débloquer.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("### 🧠 Analyse comportementale")
        st.write("Bea capte ton stress, tes doutes, ton énergie du moment.")
    with c2:
        st.markdown("### 🖼️ Aperçu instantané")
        st.write("Génération d'aperçu paysage 1280x720 avec Pillow pour tes clients.")
    with c3:
        st.markdown("### 🔒 Licences PRO")
        st.write("Galerie, mémoire illimitée, support prioritaire.")

    st.markdown("---")
    st.markdown("## Tarifs")
    p1, p2 = st.columns(2)
    with p1:
        st.markdown("#### BASIC - Gratuit")
        st.write("- 15 dernières requêtes intactes\n- Discussion illimitée\n- Sans galerie")
    with p2:
        st.markdown("#### PRO - 29€/mois")
        st.write("- Mémoire illimitée\n- Galerie PRO\n- Aperçu Pillow HD\n- Support")

    st.markdown("---")
    st.info("Tu as déjà une licence? Ajoute?key=TA-CLE dans l'URL. Ex:...streamlit.app/?key=TEST-PRO-123")
    st.text_input("Ou colle ta clé ici :", key="vitrine_key")
    if st.session_state.vitrine_key:
        st.markdown(f"[Accéder à Bea avec cette clé](?key={st.session_state.vitrine_key})")
    st.stop()

# 2. AVEC CLE = APP CHAT (ton code que tu avais sur la capture)
try:
    res = supabase.table("licences").select("*").eq("key", licence_key).execute()
    licence = res.data[0]
    plan = licence.get("plan", "BASIC")
except:
    st.error("Licence invalide")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

# HEADER
col_title, col_btns = st.columns([3, 1])
with col_title:
    st.markdown("# Bea")
    st.markdown("<p style='margin-top:-15px; color:gray; font-size:16px;'>BehaviorLab AI</p>", unsafe_allow_html=True)
    if plan!= "PRO":
        st.caption("Mémoire intacte : 15 dernières requêtes pour BASIC, illimité pour PRO")

with col_btns:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🌙 / ☀️"):
            st.session_state.theme = "clair" if st.session_state.theme == "sombre" else "sombre"
            st.rerun()
    with c2:
        if st.button("FR / EN"):
            st.session_state.lang = "EN" if st.session_state.lang == "FR" else "FR"
            st.rerun()

if st.session_state.theme == "clair":
    st.markdown("<style>.stApp{background-color:#F8F8FF;}</style>", unsafe_allow_html=True)

# SIDEBAR
with st.sidebar:
    col_logo, col_name = st.columns([1, 2])
    with col_logo:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=45)
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
    if st.button("🗑️ Nouvelle discussion"):
        st.session_state.messages = []
        st.rerun()

# CHAT
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(f"<div style='font-size:18px'>{m['content']}</div>", unsafe_allow_html=True)
        if "image" in m and m["image"] is not None:
            st.image(m["image"], use_container_width=True)

st.divider()
generer_case = st.checkbox("🖼️ Générer un aperçu paysage (format ordi 1280x720) avec Pillow", value=False)
prompt = st.chat_input("Décris une situation de ton entreprise et ton état d'esprit actuel...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    if plan!= "PRO" and len(st.session_state.messages) > 30:
        st.session_state.messages = st.session_state.messages[-30:]
    with st.chat_message("user"):
        st.markdown(f"<div style='font-size:18px'>{prompt}</div>", unsafe_allow_html=True)
    with st.chat_message("assistant"):
        if generer_case:
            img = generer_apercu_paysage(prompt)
            st.image(img, use_container_width=True, caption="Aperçu 1280x720")
            st.session_state.messages.append({"role": "assistant", "content": f"Aperçu généré pour : {prompt}", "image": img})
        else:
            history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if "image" not in m]
            if plan!= "PRO":
                history = history[-30:]
            completion = groq_client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[{"role": "system", "content": "Tu es Bea, coach business bienveillante."}] + history
            )
            reponse = completion.choices[0].message.content
            st.markdown(f"<div style='font-size:18px'>{reponse}</div>", unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": reponse})
