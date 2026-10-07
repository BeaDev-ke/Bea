import streamlit as st
from groq import Groq
from supabase import create_client, Client
from PIL import Image, ImageDraw
import textwrap, base64
from pathlib import Path

st.set_page_config(page_title="Bea - BehaviorLab AI", layout="wide", page_icon="logo.png")

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client_groq = Groq(api_key=GROQ_API_KEY)

if "theme" not in st.session_state: st.session_state.theme = "clair"
if "licence_ok" not in st.session_state: st.session_state.licence_ok = False
if "messages" not in st.session_state: st.session_state.messages = []
if "with_image" not in st.session_state: st.session_state.with_image = False
if "lang" not in st.session_state: st.session_state.lang = "FR"

query_email = st.query_params.get("email", "")
if query_email: st.session_state.licence_ok = True

BEA_GRADIENT = "linear-gradient(135deg, #7C3AED 0%, #A855F7 50%, #EC4899 100%)"
bg = "#FFFBFE" if st.session_state.theme=="clair" else "#0F0A1E"
card = "#FFFFFF" if st.session_state.theme=="clair" else "#1C1333"
text_color = "#1A1A1A" if st.session_state.theme=="clair" else "#F5F3FF"
sub_text = "#6B7280" if st.session_state.theme=="clair" else "#A78BFA"

logo_path = Path("logo.png")
logo_b64 = ""
if logo_path.exists():
    logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@700;800&display=swap');
.stApp {{ background: {bg}; color: {text_color}; }}
header, #MainMenu, footer {{ visibility: hidden; }}
.bea-header {{
    background: {BEA_GRADIENT}; padding: 14px 18px; border-radius: 18px;
    display:flex; align-items:center; gap:14px;
    box-shadow: 0 12px 24px rgba(124,58,237,0.25);
}}
.canva-card {{
    background: {card}; border-radius: 20px; padding: 28px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06); border: 1px solid rgba(124,58,237,0.08);
    margin-bottom: 20px;
}}
div[data-testid="stLinkButton"] > a,.stButton > button {{
    background: {BEA_GRADIENT}!important; color: white!important; border: none!important;
    border-radius: 14px!important; font-weight: 800!important;
    box-shadow: 0 6px 16px rgba(124,58,237,0.3)!important;
}}
div[data-testid="stHorizontalBlock"] {{ gap: 8px!important; align-items: center!important; }}
.icon-btn button {{
    width: 48px!important; height: 48px!important; border-radius: 12px!important; padding:0!important;
    background: {BEA_GRADIENT}!important;
}}
</style>
""", unsafe_allow_html=True)

# HEADER AVEC LOGO CERVEAU + CRAYON + BOUTONS COLLES
c_logo, c_text, c_lang, c_theme = st.columns([0.07, 0.77, 0.08, 0.08], gap="small")
with c_logo:
    if logo_b64:
        st.markdown(f'<div style="background:white;padding:6px;border-radius:14px;display:flex;justify-content:center;"><img src="data:image/png;base64,{logo_b64}" style="width:40px;height:40px;border-radius:10px;"></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="width:48px;height:48px;border-radius:12px;background:{BEA_GRADIENT};display:flex;align-items:center;justify-content:center;color:white;font-weight:900;">B</div>', unsafe_allow_html=True)
with c_text:
    st.markdown(f'<div class="bea-header"><div><h1 style="color:white;margin:0;font-size:26px;font-weight:800;">Bea</h1><span style="color:rgba(255,255,255,0.9);font-size:13px;">BehaviorLab AI • L\'IA qui fait vendre</span></div></div>', unsafe_allow_html=True)
with c_lang:
    st.markdown('<div class="icon-btn">', unsafe_allow_html=True)
    if st.button("🌐", key="lang_btn"): st.session_state.lang = "EN" if st.session_state.lang=="FR" else "FR"
    st.markdown('</div>', unsafe_allow_html=True)
with c_theme:
    st.markdown('<div class="icon-btn">', unsafe_allow_html=True)
    if st.button("🌙" if st.session_state.theme=="clair" else "☀️", key="theme_btn"):
        st.session_state.theme = "sombre" if st.session_state.theme=="clair" else "clair"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

if not st.session_state.licence_ok:
    st.markdown(f'<div class="canva-card"><h2 style="font-size:32px;line-height:1.1;font-weight:800;">L\'IA qui transforme ton activité<br>en <span style="background:{BEA_GRADIENT};-webkit-background-clip:text;-webkit-text-fill-color:transparent;">marque qui compte.</span></h2><p style="color:{sub_text};font-size:17px;margin-top:16px;"><b>Bea n\'est pas une IA qui discute. C\'est une IA qui vend.</b><br><br>BehaviorLab AI a créé la première IA entraînée sur les biais cognitifs et la psychologie comportementale. Bea analyse ton activité, ton audience, ton offre... puis elle répond et crée pour toi avec un seul but : <b>augmenter ton chiffre d\'affaires.</b><br><br>Elle utilise ce que les plus grandes marques utilisent depuis 50 ans : le biais de rareté, de preuve sociale, d\'autorité, d\'ancrage... pour que tes clients passent à l\'action. Elle rédige tes pages de vente, tes publicités, tes emails qui convertissent et génère tes visuels qui captent l\'attention instantanément.<br><br><b>Une petite entreprise pense produit. Une grande marque pense comportement. Bea te fait basculer.</b></p></div>', unsafe_allow_html=True)

    st.markdown("### Choisis ton accès")
    col1, col2 = st.columns(2, gap="medium")
    with col1:
        st.markdown(f'<div class="canva-card" style="border:2px solid #E9D5FF;"><h3>Basique - 14,90€/mois</h3><p style="color:{sub_text};">Parfait pour démarrer et améliorer ta conversion</p></div>', unsafe_allow_html=True)
        with st.expander("Voir ce qu'elle comporte ▼"):
            st.write("- Analyse comportementale de ton offre\n- Textes de vente basés sur la psychologie\n- Aperçus de ton app (3/jour)")
        st.link_button("S'abonner Basique 14,90€/mois", "https://buy.stripe.com/test_00w6oH2c0g0S0HN0kB1kE00", use_container_width=True)
    with col2:
        st.markdown(f'<div class="canva-card" style="border:2px solid #7C3AED;"><h3>Pro - 21€/mois • Recommandé</h3><p style="color:{sub_text};">Pour celles qui veulent devenir une référence</p><div style="background:{BEA_GRADIENT};color:white;padding:4px 10px;border-radius:999px;display:inline-block;font-size:12px;font-weight:800;margin-top:8px;">LE PLUS CHOISI</div></div>', unsafe_allow_html=True)
        with st.expander("Voir les avantages Pro ▼"):
            st.write("**Tout le Basique + :**\n- Biais cognitifs avancés\n- Aperçus illimités\n- Analyse complète de ton parcours client\n- Mémoire infinie\n- Stratégies pour passer de petite entreprise à marque reconnue")
        st.link_button("S'abonner Pro 21€/mois →", "https://buy.stripe.com/test_5kQ8wP8AkaSg0HN1oF1kE01", use_container_width=True)
    st.stop()

# CHAT
st.markdown(f'<div class="canva-card"><h3>Parle à Bea</h3><p style="color:{sub_text};margin:0;">Ton experte en comportement. Elle répond comme une vendeuse qui convertit.</p></div>', unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("image"): st.image(m["image"], caption="Aperçu généré par Bea", use_container_width=True)

st.checkbox("🖼️ Illustrer ce que dit Bea avec un aperçu paysage", key="with_image")

if prompt := st.chat_input("Demande à Bea : une page de vente, une pub, un email..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    with st.chat_message("assistant"):
        try:
            system_prompt = "Tu es Bea, IA de BehaviorLab AI, experte en biais cognitifs. Tu ne dois jamais utiliser les mots scale, scaler, scaling. Tu tutoies, directe et business."
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
            draw.rounded_rectangle([W-300, 12, W-20, 38], radius=999, fill="#7C3AED")
            draw.text((W-280, 15), "APERCU BEA", fill="white")
            draw.rounded_rectangle([80, 90, W-80, H-40], radius=20, fill="#FFFBFE", outline="#E9D5FF", width=2)
            draw.text((120, 120), f"SUJET : {prompt[:70].upper()}", fill="#7C3AED")
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
