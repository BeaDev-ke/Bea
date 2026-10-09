import streamlit as st
from groq import Groq
from supabase import create_client
from PIL import Image, ImageDraw
import textwrap, base64
from pathlib import Path

st.set_page_config(page_title="Bea - BehaviorLab AI", layout="wide", page_icon="logo.png")

client_groq = Groq(api_key=st.secrets["GROQ_API_KEY"])
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

if "messages" not in st.session_state: st.session_state.messages = []
if "licence_ok" not in st.session_state: st.session_state.licence_ok = False
if "with_image" not in st.session_state: st.session_state.with_image = False

if st.query_params.get("email"): st.session_state.licence_ok = True

BEA_GRADIENT = "linear-gradient(135deg, #7C3AED 0%, #A855F7 40%, #EC4899 100%)"

# --- CSS CANVA + FIX CASE NOIRE ---
st.markdown(f"""
<style>
.stApp {{ background: #FFFBFE; }}
header, #MainMenu, footer {{ visibility: hidden; }}

/* FIX DEFINITIF CASE NOIRE -> BLANCHE */
div[data-testid="stChatInput"] {{
    background: white!important;
    border: 2px solid #E9D5FF!important;
    border-radius: 20px!important;
    box-shadow: 0 4px 12px rgba(124,58,237,0.1)!important;
}}
div[data-testid="stChatInput"] textarea {{
    background: white!important; color: #111827!important;
}}
div[data-testid="stChatInput"] textarea::placeholder {{ color: #9CA3AF!important; }}
div[data-testid="stChatInput"] button {{
    background: {BEA_GRADIENT}!important; border-radius: 50%!important;
}}

.canva-card {{
    background: white; border-radius: 24px; padding: 28px;
    border: 1px solid #F3E8FF; box-shadow: 0 8px 24px rgba(124,58,237,0.06);
}}
.canva-price-pro {{
    background: white; border-radius: 24px; padding: 28px;
    border: 2.5px solid #7C3AED; box-shadow: 0 12px 32px rgba(124,58,237,0.18);
}}
div[data-testid="stLinkButton"] > a,.stButton > button {{
    background: {BEA_GRADIENT}!important; color: white!important;
    border: none!important; border-radius: 14px!important; font-weight: 800!important;
    height: 48px!important;
}}
</style>
""", unsafe_allow_html=True)

# --- HEADER CANVA ---
logo_path = Path("logo.png")
logo_b64 = base64.b64encode(logo_path.read_bytes()).decode() if logo_path.exists() else ""
c_logo, c_title = st.columns([0.07, 0.93])
with c_logo:
    if logo_b64:
        st.markdown(f'<img src="data:image/png;base64,{logo_b64}" style="width:52px;height:52px;border-radius:14px;box-shadow:0 4px 12px rgba(124,58,237,0.3);">', unsafe_allow_html=True)
with c_title:
    st.markdown(f'<div style="background:{BEA_GRADIENT};padding:14px 20px;border-radius:18px;display:flex;align-items:center;gap:12px;"><div><h1 style="color:white;margin:0;font-size:24px;font-weight:900;letter-spacing:-0.5px;">Bea</h1><p style="color:rgba(255,255,255,0.9);margin:0;font-size:13px;font-weight:600;">BehaviorLab AI • L\'IA qui fait vendre</p></div></div>', unsafe_allow_html=True)

# --- SITE VITRINE CANVA (avant achat) ---
if not st.session_state.licence_ok:
    st.markdown(f"""
    <div style="margin:32px 0 24px 0;">
        <h1 style="font-size:44px;font-weight:900;line-height:1.05;letter-spacing:-1.5px;color:#111827;">L'IA qui transforme ton activité<br>en <span style="background:{BEA_GRADIENT};-webkit-background-clip:text;-webkit-text-fill-color:transparent;">marque qui compte.</span></h1>
        <p style="font-size:19px;color:#6B7280;margin-top:16px;max-width:620px;"><b>Bea n'est pas une IA qui discute. C'est une IA qui vend.</b> Elle utilise les biais cognitifs pour transformer tes visiteurs en acheteurs.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1: st.markdown('<div class="canva-card"><div style="font-size:28px;">🧠</div><h4>Biais cognitifs</h4><p style="color:#6B7280;font-size:14px;">Elle connaît les 200 déclencheurs d\'achat</p></div>', unsafe_allow_html=True)
    with col2: st.markdown('<div class="canva-card"><div style="font-size:28px;">✍️</div><h4>Copy qui convertit</h4><p style="color:#6B7280;font-size:14px;">Pages, pubs, emails qui font cliquer</p></div>', unsafe_allow_html=True)
    with col3: st.markdown('<div class="canva-card"><div style="font-size:28px;">⚡</div><h4>Réponse en 1 sec</h4><p style="color:#6B7280;font-size:14px;">Propulsée par Groq, l\'IA la plus rapide</p></div>', unsafe_allow_html=True)

    st.markdown("### Choisis ton accès")
    p1, p2 = st.columns(2)
    with p1:
        st.markdown('<div class="canva-card"><h3>Basique</h3><h2 style="font-size:32px;">14,90€<span style="font-size:16px;color:#6B7280;">/mois</span></h2><p style="color:#6B7280;">✓ Chat illimité<br>✓ Templates de vente</p></div>', unsafe_allow_html=True)
        st.link_button("S'abonner Basique", "https://buy.stripe.com/test_00w6oH2c0g0S0HN0kB1kE00", use_container_width=True)
    with p2:
        st.markdown('<div class="canva-price-pro"><div style="background:#7C3AED;color:white;display:inline-block;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:800;margin-bottom:10px;">RECOMMANDÉ</div><h3>Pro</h3><h2 style="font-size:32px;">21€<span style="font-size:16px;color:#6B7280;">/mois</span></h2><p style="color:#6B7280;">✓ Tout Basique<br>✓ Générateur d\'images<br>✓ Analyse d\'images galerie</p></div>', unsafe_allow_html=True)
        st.link_button("S'abonner Pro →", "https://buy.stripe.com/test_5kQ8wP8AkaSg0HN1oF1kE01", use_container_width=True)
    st.stop()

# --- APP UTILISABLE (après achat) - SEULEMENT ICI GALERIE ---
st.markdown('<div class="canva-card" style="margin-top:20px;"><h3 style="margin:0;">Parle à Bea 💬</h3><p style="color:#6B7280;margin:4px 0 0 0;">Glisse une image de ton produit ou de ta pub pour qu\'elle l\'améliore</p></div>', unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("image"): st.image(m["image"], use_container_width=True)

# OPTIONS - GALERIE PRESENTE UNIQUEMENT ICI
c_opt1, c_opt2 = st.columns([0.65, 0.35])
with c_opt1:
    st.checkbox("🖼️ Générer un aperçu paysage de la réponse", key="with_image")
with c_opt2:
    uploaded = st.file_uploader("📎 Galerie", type=["png","jpg","jpeg"], label_visibility="collapsed", key="galerie_after_buy")

if uploaded:
    img_user = Image.open(uploaded)
    with st.chat_message("user"):
        st.image(img_user, caption="Image envoyée à Bea", use_container_width=True)
    st.session_state.messages.append({"role":"user","content":"Analyse cette image et améliore-la pour vendre","image":img_user})

if prompt := st.chat_input("Demande à Bea : une page de vente, une pub, un email..."):
    st.session_state.messages.append({"role":"user","content":prompt})
    with st.chat_message("user"): st.markdown(prompt)
    with st.chat_message("assistant"):
        resp = client_groq.chat.completions.create(
            model="llama-3.1-8b-instant", # LE PLUS RAPIDE AU MONDE SUR GROQ
            messages=[{"role":"system","content":"Tu es Bea, BehaviorLab AI. Tu tutoies, tu es cash, experte en biais cognitifs. Tu fais vendre. Réponse courte, punchy, actionnable."}] + [{"role":m["role"],"content":m["content"]} for m in st.session_state.messages[-6:]],
            temperature=0.7,
            max_tokens=550
        )
        rep = resp.choices[0].message.content
        st.markdown(rep)
        gen_img = None
        if st.session_state.with_image:
            W,H = 1280,720
            img = Image.new("RGB",(W,H),"white")
            d = ImageDraw.Draw(img)
            d.rounded_rectangle([60,70,W-60,H-40], radius=24, fill="#FFFBFE", outline="#E9D5FF", width=2)
            d.text((90,90), f"BEA • {prompt[:50].upper()}", fill="#7C3AED")
            y=140
            for line in textwrap.wrap(rep[:380], width=62)[:10]:
                d.text((90,y), line, fill="#111827")
                y+=28
            gen_img = img
            st.image(gen_img, use_container_width=True)
        st.session_state.messages.append({"role":"assistant","content":rep,"image":gen_img} if gen_img else {"role":"assistant","content":rep})
