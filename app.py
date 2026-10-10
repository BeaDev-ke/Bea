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
bg = "#0f172a" if is_dark else "#ffffff"
txt = "#0f172a" if not is_dark else "#f8fafc"
card = "#1e293b" if is_dark else "#ffffff"
border = "#334155" if is_dark else "#ede9fe"

st.markdown(f"""
<style>
header[data-testid="stHeader"] {{ display: none!important; }}
.stApp {{ background:{bg}; color:{txt}; margin-top: -75px; }}
.block-container {{ max-width: 1240px!important; padding-top: 3rem!important; padding-bottom: 5rem; }}
.header-card {{ background: linear-gradient(135deg, #4338ca 0%, #7c3aed 50%, #db2777 100%); border-radius: 20px; padding: 18px 28px; display:flex; align-items:center; gap:16px; margin-top: 15px; }}
.hero-title {{ font-size:52px; line-height:1.05; font-weight:850; color:{txt}!important; }}
.hero-desc {{ font-size:18px; line-height:1.7; color:#111827!important; }}
.hero-desc b {{ color:#000000!important; font-weight:700; }}
.pricing-card {{ background:{card}; border:1px solid {border}; border-radius:24px; padding:32px; min-height:360px; color:#111827!important; }}
.pricing-card.reco {{ border:2px solid #7c3aed; box-shadow: 0 12px 32px rgba(124,58,237,0.15); }}
</style>
""", unsafe_allow_html=True)

c1,c2,c3 = st.columns([0.9,5,1.8])
with c1:
    if os.path.exists("logo.png"): st.image("logo.png", width=68)
with c2:
    st.markdown('<div class="header-card"><div><h2>Bea</h2><p>BehaviorLab AI</p></div></div>', unsafe_allow_html=True)
with c3:
    b1,b2,b3 = st.columns(3)
    with b1: st.button("🌙" if not is_dark else "☀️", on_click=toggle_theme, key="th")
    with b2: st.button("FR", on_click=lambda: st.session_state.__setitem__("lang","FR"))
    with b3: st.button("EN", on_click=lambda: st.session_state.__setitem__("lang","EN"))

# APPLICATION PAYANTE
if is_paid:
    email = query.get("email")
    st.success(f"✅ Accès actif : {email} — Version utilisable")
    st.markdown("### Parle à Bea, ton IA comportementaliste")

    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if st.session_state.show_uploader:
        up = st.file_uploader("Glisse une image", type=["png","jpg","jpeg"], label_visibility="collapsed")
        if up: st.image(up, width=500)

    if st.button("🖼️ Glisse une image"):
        st.session_state.show_uploader = not st.session_state.show_uploader
        st.rerun()

    prompt = st.chat_input("Décris une situation de ton entreprise...")

    if prompt:
        st.session_state.messages.append({"role":"user","content":prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Bea analyse..."):
                if client is None:
                    resp = "⚠️ Clé Groq manquante dans Secrets."
                else:
                    system_prompt = f"""Tu es Bea, IA comportementaliste experte pour les entreprises.
                    Structure: 1. Blocage 2. Levier 3. Script. Langue: {st.session_state.lang}"""
                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "system", "content": system_prompt}, *st.session_state.messages[-6:], {"role": "user", "content": prompt}],
                        temperature=0.7
                    )
                    resp = completion.choices[0].message.content
                st.markdown(resp)
        st.session_state.messages.append({"role":"assistant","content":resp})
    st.stop()

# VITRINE
hero_l, hero_r = st.columns([1.3,0.7], gap="large")
with hero_l:
    st.markdown('<div class="hero-title">Bea, ton IA comportementaliste<br>pour ton entreprise.</div>', unsafe_allow_html=True)
    st.markdown("""
    <p class="hero-desc" style="margin-top:22px;">
    Bea n'est pas une IA qui rédige des pages de vente. <b>C'est une IA qui comprend pourquoi les gens n'achètent pas, pourquoi tes équipes ne performent pas, et quoi changer pour débloquer.</b><br><br>
    Elle analyse chaque situation avec les vrais modèles de psychologie comportementale : biais cognitifs, économie comportementale, neurosciences de la décision.<br><br>
    <b>Pour tes clients :</b> elle détecte les freins à l'achat, les doutes cachés, les déclencheurs qui les feront passer à l'action.<br>
    <b>Pour tes équipes :</b> elle t'aide à mieux communiquer, manager, négocier et fidéliser sans forcer.
    </p>
    """, unsafe_allow_html=True)

with hero_r:
    st.markdown(f'''
    <div style="background:linear-gradient(180deg,#ede9fe,#fff);border-radius:24px;padding:24px;border:1px solid {border}">
        <div style="font-size:12px;font-weight:800;color:#4c1d95;letter-spacing:0.5px">SITUATION</div><br>
        <div style="background:white;border-radius:16px;padding:18px;border:1px solid #e5e7eb;color:#111827;line-height:1.6">
            <div style="font-weight:700;color:#0f172a;margin-bottom:6px;">Exemple de question :</div>
            "Une personne est intéressée par ce que je vends mais elle me dit qu'elle doit réfléchir"
            <br><br>
            <div style="height:1px;background:#f3f4f6;margin:12px 0;"></div>
            <div style="font-weight:700;color:#7c3aed;">Réponse de Bea :</div>
            "C'est normal, elle a peur de se tromper. Ne baisse pas ton prix. Montre-lui qu'une autre personne comme elle a déjà dit oui, et pose-lui une question qui l'aide à s'imaginer après l'achat."
        </div>
    </div>
    ''', unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown('<h2 style="text-align:center;font-size:32px;color:#0f172a;">Choisis ta version, même site</h2><p style="text-align:center;color:#6b7280;">Paiement Stripe et retour automatique sur l\'application utilisable</p><br>', unsafe_allow_html=True)

col_p1, col_p2 = st.columns(2, gap="large")
with col_p1:
    st.markdown('<div class="pricing-card"><h3>Version Basique</h3><div style="display:flex;align-items:baseline;gap:8px"><h1 style="margin:0;color:#0f172a;">14,90€</h1><span style="color:#6b7280;">/mois</span></div><br><div style="line-height:1.9;color:#111827;">✓ Chat illimité avec Bea<br>✓ Analyses comportementales complètes<br>✓ Scripts de vente / management<br>✓ Suivi de tes situations</div></div>', unsafe_allow_html=True)
    st.link_button("Choisir Version Basique →", STRIPE_BASIQUE, use_container_width=True)
with col_p2:
    st.markdown('<div class="pricing-card reco"><span style="background:#7c3aed;color:white;padding:6px 14px;border-radius:20px;font-size:11px;font-weight:800">RECOMMANDÉ</span><br><br><h3>Version Pro</h3><div style="display:flex;align-items:baseline;gap:8px"><h1 style="margin:0;color:#0f172a;">21€</h1><span style="color:#6b7280;">/mois</span></div><br><div style="line-height:1.9;color:#111827;">✓ Tout Basique inclus<br>✓ <b>Analyse d\'images depuis la galerie</b><br>✓ Générateur d\'images<br>✓ Priorité nouveautés</div></div>', unsafe_allow_html=True)
    st.link_button("Choisir Version Pro →", STRIPE_PRO, use_container_width=True, type="primary")
