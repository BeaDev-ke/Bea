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

# --- DESIGN SYSTEM BEA x CANVA ---
CLAIR_BG = "#FFFBFE"
CLAIR_CARD = "#FFFFFF"
SOMBRE_BG = "#0F0A1E"
SOMBRE_CARD = "#1C1333"
BEA_GRADIENT = "linear-gradient(135deg, #7C3AED 0%, #A855F7 50%, #EC4899 100%)"
BEA_PRIMARY = "#7C3AED"

theme = st.session_state.theme
bg = CLAIR_BG if theme=="clair" else SOMBRE_BG
card = CLAIR_CARD if theme=="clair" else SOMBRE_CARD
text_color = "#1A1A1A" if theme=="clair" else "#F5F3FF"
sub_text = "#6B7280" if theme=="clair" else "#A78BFA"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;700;800&display=swap');
html, body, [class*="css"] {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
.stApp {{ background: {bg}; color: {text_color}; }}
header, #MainMenu, footer {{ visibility: hidden; }}
h1, h2, h3 {{ font-weight: 800!important; letter-spacing: -0.02em; }}
/* HEADER BEA */
.bea-header {{
    background: {BEA_GRADIENT};
    padding: 18px 26px; border-radius: 18px; margin-bottom: 24px;
    display: flex; justify-content: space-between; align-items: center;
    box-shadow: 0 12px 24px rgba(124,58,237,0.25);
}}
.bea-header h1 {{ color: white!important; margin:0; font-size: 28px; }}
.bea-header span {{ color: rgba(255,255,255,0.9); font-weight: 500; }}
/* CARDS */
.canva-card {{
    background: {card}; border-radius: 20px; padding: 28px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06); border: 1px solid rgba(124,58,237,0.08);
    margin-bottom: 20px;
}}
.stButton > button {{
    border-radius: 12px!important; font-weight: 700!important;
    border: none!important; transition: 0.2s;
}}
div[data-testid="stExpander"] {{
    background: {card}; border-radius: 16px; border: 1px solid rgba(124,58,237,0.1);
}}
/* Bouton principal achat */
a[href*="stripe"] {{
    background: {BEA_GRADIENT}!important;
}}
/* Checkbox style */
div[data-testid="stCheckbox"] label {{ font-weight: 600; color: {BEA_PRIMARY}; }}
</style>
""", unsafe_allow_html=True)

# HEADER
c1, c2 = st.columns([8,2])
with c1:
    st.markdown(f'<div class="bea-header"><div><h1>Bea</h1><span>BehaviorLab AI • L\'IA qui fait vendre</span></div><div style="background:white;color:#7C3AED;padding:8px 14px;border-radius:999px;font-weight:800;font-size:12px;">BETA</div></div>', unsafe_allow_html=True)
with c2:
    if st.button("🌙 Sombre" if theme=="clair" else "☀️ Clair", use_container_width=True):
        st.session_state.theme = "sombre" if theme=="clair" else "clair"
        st.rerun()

if not st.session_state.licence_ok:
    st.markdown(f'<div class="canva-card"><h2 style="font-size:32px;line-height:1.1;">L\'IA qui transforme ton activité<br>en <span style="background:{BEA_GRADIENT};-webkit-background-clip:text;-webkit-text-fill-color:transparent;">marque qui compte.</span></h2><p style="color:{sub_text};font-size:17px;margin-top:12px;"><b>Bea n\'est pas une IA qui discute. C\'est une IA qui vend.</b><br><br>BehaviorLab AI a créé la première IA entraînée sur les biais cognitifs. Elle analyse ton activité et crée pour toi : pages de vente, pubs, emails qui convertissent et visuels qui captent l\'attention.<br><br><b>Tu arrêtes de poster au hasard. Tu commences à vendre plus et mieux.</b></p></div>', unsafe_allow_html=True)

    st.markdown("### Choisis ton accès - Paiement unique, à vie")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="canva-card" style="border:2px solid #E5E7EB;"><h3>Basique - 14,90€</h3><p style="color:{sub_text};">Parfait pour démarrer et améliorer ta conversion</p></div>', unsafe_allow_html=True)
        with st.expander("Voir ce qu'elle comporte ▼"):
            st.write("- Analyse comportementale de ton offre\n- Textes de vente basés sur la psychologie\n- Aperçus de ton app (3/jour)")
        st.link_button("Débloquer Basique 14,90€", "https://buy.stripe.com/test_00w6oH2c0g0S0HN0kB1kE00", use_container_width=True)
    with col2:
        st.markdown(f'<div class="canva-card" style="border:2px solid {BEA_PRIMARY};"><h3>Pro - 21€ • Recommandé</h3><p style="color:{sub_text};">Pour celles qui veulent devenir une référence</p><div style="background:{BEA_GRADIENT};color:white;padding:4px 10px;border-radius:999px;display:inline-block;font-size:12px;font-weight:800;margin-top:8px;">LE PLUS CHOISI</div></div>', unsafe_allow_html=True)
        with st.expander("Voir les avantages Pro ▼"):
            st.write("**Tout le Basique + :**\n- Biais cognitifs avancés\n- Aperçus illimités\n- Analyse complète de ton parcours client\n- Mémoire infinie\n- Stratégies pour passer de petite entreprise à marque reconnue")
        st.link_button("Débloquer Pro 21€ →", "https://buy.stripe.com/test_5kQ8wP8AkaSg0HN1oF1kE01", use_container_width=True, type="primary")
    st.stop()

# CHAT
st.markdown(f'<div class="canva-card"><h3>Parle à Bea</h3><p style="color:{sub_text};margin:0;">Ton experte en comportement. Elle répond comme une vendeuse qui convertit.</p></div>', unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("image"):
            st.image(m["image"], caption="Aperçu généré par Bea", use_container_width=True)

st.checkbox("🖼️ Illustrer ce que dit Bea avec un aperçu paysage", key="with_image")

if prompt := st.chat_input("Demande à Bea : une page de vente, une pub, un email..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    with st.chat_message("assistant"):
        try:
            system_prompt = "Tu es Bea, IA de BehaviorLab AI, experte en biais cognitifs. Tu ne dois jamais utiliser les mots scale, scaler, scaling. Utilise developper, faire grandir, passer a l'etape superieure. Tu tutoies, directe et business."
            msgs = [{"role": "system", "content": system_prompt}] + [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
            chat_completion = client_groq.chat.completions.create(model="openai/gpt-oss-20b", messages=msgs, temperature=0.7)
            rep = chat_completion.choices[0].message.content
        except Exception as e:
            rep = f"Erreur: {e}"
        st.markdown(rep)
        gen_img = None
        if st.session_state.with_image:
            W, H = 1280, 720
            img = Image.new("RGB", (W, H), color="#FFFFFF")
            draw = ImageDraw.Draw(img)
            draw.rectangle([0, 0, W, 50], fill="#0F0A1E")
            draw.text((20, 15), "● ● ● bea-preview.app", fill="white")
            draw.rectangle([W-300, 12, W-20, 38], fill="#7C3AED")
            draw.text((W-280, 15), "APERCU BEA", fill="white")
            draw.rounded_rectangle([80, 90, W-80, H-40], radius=20, fill="#FFFBFE", outline="#E9D5FF", width=2)
            draw.text((120, 120), f"SUJET : {prompt[:70].upper()}", fill="#7C3AED")
            draw.line([120, 155, W-120, 155], fill="#E9D5FF", width=2)
            wrapped = textwrap.wrap(rep[:450], width=65)
            y = 180
            for line in wrapped[:14]:
                draw.text((120, y), line, fill="#1F2937")
                y += 28
            draw.rounded_rectangle([120, H-90, 320, H-50], radius=999, fill="#7C3AED")
            draw.text((135, H-80), "✓ Optimise par Bea", fill="white")
            gen_img = img
            st.image(gen_img, use_container_width=True)
        msg_to_save = {"role": "assistant", "content": rep}
        if gen_img: msg_to_save["image"] = gen_img
        st.session_state.messages.append(msg_to_save)
