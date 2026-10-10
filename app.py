import streamlit as st
import os
from groq import Groq

st.set_page_config(page_title="Bea - BehaviorLab AI", page_icon="logo.png", layout="wide")

STRIPE_BASIQUE = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"
STRIPE_PRO = "https://buy.stripe.com/test_cNieVea1P0c62B08523wQ00"

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    client = None

if "theme" not in st.session_state: st.session_state.theme = "light"
if "lang" not in st.session_state: st.session_state.lang = "FR"
if "show_uploader" not in st.session_state: st.session_state.show_uploader = False
if "messages" not in st.session_state: st.session_state.messages = []

query = st.query_params
is_paid = "email" in query

def toggle_theme():
    st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"

is_dark = st.session_state.theme == "dark"

st.markdown(f"""
<style>
/* FIX DEFINITIF HAUT COUPE ET BOUTONS NOIRS */
header[data-testid="stHeader"] {{ background: transparent!important; }}
.stApp {{ background: {"#0f172a" if is_dark else "#ffffff"}!important; }}
.block-container {{ max-width: 1240px!important; padding-top: 4rem!important; padding-bottom: 5rem; }}
div[data-testid="stColumn"]:nth-child(3) button {{
    background: white!important;
    color: #1e1b4b!important;
    border: 1px solid #ede9fe!important;
    border-radius: 10px!important;
}}
.header-card {{ background: linear-gradient(135deg, #4338ca 0%, #7c3aed 50%, #db2777 100%); border-radius: 20px; padding: 18px 28px; }}
.hero-title {{ font-size:52px; line-height:1.05; font-weight:850; color: {"#f8fafc" if is_dark else "#0f172a"}!important; }}
.hero-desc {{ font-size:18px; line-height:1.7; color:#111827!important; }}
.hero-desc b {{ color:#000000!important; font-weight:700; }}
</style>
""", unsafe_allow_html=True)

c1,c2,c3 = st.columns([0.9,5,1.8])
with c1:
    if os.path.exists("logo.png"): st.image("logo.png", width=68)
with c2:
    st.markdown('<div class="header-card"><div style="color:white"><h2 style="margin:0;color:white;">Bea</h2><p style="margin:0;opacity:0.9;">BehaviorLab AI</p></div></div>', unsafe_allow_html=True)
with c3:
    b1,b2,b3 = st.columns(3)
    with b1: st.button("🌙" if not is_dark else "☀️", on_click=toggle_theme, key="th")
    with b2: st.button("FR", key="fr")
    with b3: st.button("EN", key="en")

# ===== APPLICATION UTILISABLE (APRES PAIEMENT) - SEULE AVEC GALERIE =====
if is_paid:
    st.success(f"✅ Accès actif : {query.get('email')} — Version utilisable")
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    # GALERIE UNIQUEMENT ICI
    if st.session_state.show_uploader:
        up = st.file_uploader("Glisse une image", type=["png","jpg","jpeg"], label_visibility="collapsed")
        if up: st.image(up, width=500)

    if st.button("🖼️ Glisse une image (galerie)"):
        st.session_state.show_uploader = not st.session_state.show_uploader
        st.rerun()

    prompt = st.chat_input("Décris une situation de ton entreprise...")
    if prompt:
        st.session_state.messages.append({"role":"user","content":prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Bea analyse..."):
                system_prompt = "Tu es Bea, IA comportementaliste experte. Structure: 1.Blocage 2.Levier 3.Script"
                comp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content":system_prompt},{"role":"user","content":prompt}])
                resp = comp.choices[0].message.content
                st.markdown(resp)
        st.session_state.messages.append({"role":"assistant","content":resp})
    st.stop()

# ===== VITRINE (SANS GALERIE) =====
hero_l, hero_r = st.columns([1.3,0.7], gap="large")
with hero_l:
    st.markdown('<div class="hero-title">Bea, ton IA<br>comportementaliste<br>pour ton entreprise.</div>', unsafe_allow_html=True)
    st.markdown("""
    <p class="hero-desc" style="margin-top:22px;">
    Bea n'est pas une IA qui rédige des pages de vente. <b>C'est une IA qui comprend pourquoi les gens n'achètent pas, pourquoi tes équipes ne performent pas, et quoi changer pour débloquer.</b><br><br>
    Elle analyse chaque situation avec les vrais modèles de psychologie comportementale : biais cognitifs, économie comportementale, neurosciences de la décision.<br><br>
    <b>Pour tes clients :</b> elle détecte les freins à l'achat, les doutes cachés, les déclencheurs qui les feront passer à l'action.<br>
    <b>Pour tes équipes :</b> elle t'aide à mieux communiquer, manager, négocier et fidéliser sans forcer.
    </p>
    """, unsafe_allow_html=True)

with hero_r:
    st.markdown('''
    <div style="background:#f5f3ff;border-radius:24px;padding:24px;border:1px solid #ede9fe;">
        <div style="font-size:11px;font-weight:800;color:#4c1d95;letter-spacing:0.8px">SITUATION</div><br>
        <div style="background:white;border-radius:16px;padding:20px;border:1px solid #e5e7eb;color:#111827;line-height:1.6;box-shadow:0 4px 12px rgba(0,0,0,0.05)">
            <div style="font-weight:700;color:#0f172a;margin-bottom:8px;">Exemple de question :</div>
            <i>"Une personne est intéressée par ce que je vends mais elle me dit qu'elle doit réfléchir"</i>
            <div style="height:1px;background:#f3f4f6;margin:16px 0;"></div>
            <div style="font-weight:800;color:#7c3aed;margin-bottom:8px;">Réponse de Bea :</div>
            <div style="font-size:14.5px;">
            <b>Blocage :</b> Biais du statu quo + aversion à la perte. Elle a peur de regretter.<br><br>
            <b>Levier :</b> Preuve sociale + projection mentale. Ne baisse pas ton prix.<br><br>
            <b>À dire :</b> "Je comprends. Justement, une cliente comme toi me disait la même chose la semaine dernière, elle a pris [produit] et m'a dit hier : j'aurais dû le prendre plus tôt."
            </div>
        </div>
    </div>
    ''', unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown('<h2 style="text-align:center;color:#0f172a;">Choisis ta version, même site</h2><p style="text-align:center;color:#6b7280;">Paiement Stripe et retour automatique sur l\'application utilisable</p><br>', unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")
with col1:
    st.markdown('<div style="background:white;border:1px solid #ede9fe;border-radius:24px;padding:32px;color:#111827;"><h3>Version Basique</h3><h1>14,90€</h1>/mois<br><br>✓ Chat illimité avec Bea<br>✓ Analyses comportementales<br>✓ Scripts de vente / management</div>', unsafe_allow_html=True)
    st.link_button("Choisir Version Basique →", STRIPE_BASIQUE, use_container_width=True)
with col2:
    st.markdown('<div style="background:white;border:2px solid #7c3aed;border-radius:24px;padding:32px;color:#111827;box-shadow:0 12px 32px rgba(124,58,237,0.15)"><span style="background:#7c3aed;color:white;padding:6px 14px;border-radius:20px;font-size:11px;font-weight:800">RECOMMANDÉ</span><br><br><h3>Version Pro</h3><h1>21€</h1>/mois<br><br>✓ Tout Basique inclus<br>✓ <b>Analyse d\'images depuis la galerie</b><br>✓ Générateur d\'images</div>', unsafe_allow_html=True)
    st.link_button("Choisir Version Pro →", STRIPE_PRO, use_container_width=True, type="primary")
