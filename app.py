import streamlit as st
import os
from groq import Groq

st.set_page_config(page_title="Bea - BehaviorLab AI", page_icon="logo.png", layout="wide")

# --- CONFIG STRIPE & APP ---
STRIPE_BASIQUE = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"
STRIPE_PRO = "https://buy.stripe.com/test_cNieVea1P0c62B08523wQ00"
APP_URL = "https://qwstmazvzucznyer8bbqte.streamlit.app"

# Client Groq - clé dans Streamlit Secrets
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
txt = "#f8fafc" if is_dark else "#1e1b4b"
card = "#1e293b" if is_dark else "#ffffff"
border = "#334155" if is_dark else "#ede9fe"
muted = "#94a3b8" if is_dark else "#6b7280"

st.markdown(f"""
<style>
.stApp {{ background:{bg}; color:{txt}; }}
.block-container {{ max-width: 1240px!important; padding-top: 1.2rem; padding-bottom: 5rem; }}
.header-card {{ background: linear-gradient(135deg, #4338ca 0%, #7c3aed 50%, #db2777 100%); border-radius: 20px; padding: 18px 28px; display:flex; align-items:center; gap:16px; }}
.header-card h2 {{ margin:0; color:white; font-size:22px; }}
.header-card p {{ margin:0; color:white; opacity:0.9; font-size:13px; }}
.stButton > button {{ background:{card}!important; color:{txt}!important; border:1px solid {border}!important; border-radius:12px!important; font-weight:600!important; }}
.stButton > button:hover {{ border-color:#7c3aed!important; color:#4c1d95!important; background:#f5f3ff!important; }}
.pricing-card {{ background:{card}; border:1px solid {border}; border-radius:24px; padding:32px; min-height:360px; }}
.pricing-card.reco {{ border:2px solid #7c3aed; box-shadow: 0 12px 32px rgba(124,58,237,0.15); }}
.hero-title {{ font-size:54px; line-height:1.05; font-weight:850; letter-spacing:-1.2px; }}
.feature-pill {{ background:{card}; border:1px solid {border}; border-radius:16px; padding:16px 18px; display:flex; gap:12px; align-items:center; }}
</style>
""", unsafe_allow_html=True)

# HEADER
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

# ========== APP PAYEE ==========
if is_paid:
    email = query.get("email")
    st.success(f"✅ Accès actif : {email} — Version utilisable")

    # Affichage historique
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    # Galerie uniquement ici
    if st.session_state.show_uploader:
        up = st.file_uploader("Glisse une image (analyse comportementale)", type=["png","jpg","jpeg"], label_visibility="collapsed")
        if up: st.image(up, width=500)

    if st.button("🖼️ Glisse une image"):
        st.session_state.show_uploader = not st.session_state.show_uploader
        st.rerun()

    prompt = st.chat_input("Décris une situation client, équipe, vente... Bea analyse le comportement")

    if prompt:
        st.session_state.messages.append({"role":"user","content":prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Bea analyse le comportement..."):
                if client is None:
                    resp = "⚠️ Clé Groq manquante dans Streamlit Secrets. Ajoute GROQ_API_KEY."
                else:
                    system_prompt = f"""
Tu es Bea, IA comportementaliste experte pour entreprises et PME.
Tu n'es PAS une IA de rédaction de pages de vente.
Tu es une psychologue comportementale qui transforme une PME en entreprise de renom grâce aux biais cognitifs.

Règles:
- Analyse avec biais cognitifs (statu quo, aversion perte, preuve sociale, autorité, rareté, ancrage, etc)
- Structure obligatoire:
1. Blocage réel (psychologique)
2. Levier à activer
3. Script exact à dire / action concrète
- Tu es directe, premium, actionable.
- Langue de réponse: {st.session_state.lang}
"""
                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            *st.session_state.messages[-6:],
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=1000
                    )
                    resp = completion.choices[0].message.content

                st.markdown(resp)
        st.session_state.messages.append({"role":"assistant","content":resp})
    st.stop()

# ========== LANDING PAGE ==========
hero_l, hero_r = st.columns([1.3,0.7], gap="large")
with hero_l:
    st.markdown('<div class="hero-title">Bea, ton IA comportementaliste<br>pour ton entreprise.</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <p style="font-size:18px;color:{muted};margin-top:22px;line-height:1.6">
    Bea n'est pas une IA qui rédige des pages de vente. <b style="color:{txt}">C'est une IA qui comprend pourquoi les gens n'achètent pas, pourquoi tes équipes ne performent pas, et quoi changer pour débloquer.</b><br><br>
    Elle analyse chaque situation avec les vrais modèles de psychologie comportementale : biais cognitifs, économie comportementale, neurosciences de la décision.<br><br>
    <b>Pour tes clients :</b> elle détecte les freins à l'achat, les doutes cachés, les déclencheurs qui les feront passer à l'action.<br>
    <b>Pour tes équipes :</b> elle t'aide à mieux communiquer, manager, négocier et fidéliser sans forcer.
    </p>
    """, unsafe_allow_html=True)

with hero_r:
    st.markdown(f'<div style="background:linear-gradient(180deg,#ede9fe,#fff);border-radius:24px;padding:24px;border:1px solid {border}"><div style="font-size:12px;font-weight:800;color:#4c1d95;letter-spacing:0.5px">EXEMPLE EN LIVE</div><br><div style="background:white;border-radius:16px;padding:16px;border:1px solid #e5e7eb;color:#1e1b4b"><b>Client :</b> "Mon prospect dit qu\'il va réfléchir"<br><br><b>Bea :</b> "Il est en dissonance cognitive. Ne relance pas avec une remise. Envoie une preuve sociale d\'un client comme lui + une question qui le projette après achat."</div></div>', unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(f'<h2 style="text-align:center;font-size:32px;">Choisis ta version, même site</h2><p style="text-align:center;color:{muted}">Paiement Stripe et retour auto sur l\'app utilisable</p><br>', unsafe_allow_html=True)

col_p1, col_p2 = st.columns(2, gap="large")
with col_p1:
    st.markdown(f'<div class="pricing-card"><h3>Version Basique</h3><div style="display:flex;align-items:baseline;gap:8px"><h1 style="margin:0">14,90€</h1><span style="color:{muted}">/mois</span></div><br><div style="line-height:1.9">✓ Chat illimité avec Bea<br>✓ Analyses comportementales complètes<br>✓ Scripts de vente / management<br>✓ Suivi de tes situations</div></div>', unsafe_allow_html=True)
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.link_button("Choisir Version Basique →", STRIPE_BASIQUE, use_container_width=True)

with col_p2:
    st.markdown(f'<div class="pricing-card reco"><span style="background:#7c3aed;color:white;padding:6px 14px;border-radius:20px;font-size:11px;font-weight:800">RECOMMANDÉ</span><br><br><h3>Version Pro</h3><div style="display:flex;align-items:baseline;gap:8px"><h1 style="margin:0">21€</h1><span style="color:{muted}">/mois</span></div><br><div style="line-height:1.9">✓ Tout Basique inclus<br>✓ <b>Analyse d\'images galerie</b><br>✓ Générateur d\'images pub<br>✓ Priorité nouveautés</div></div>', unsafe_allow_html=True)
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.link_button("Choisir Version Pro →", STRIPE_PRO, use_container_width=True, type="primary")
