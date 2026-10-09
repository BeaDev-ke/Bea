import streamlit as st
import os

st.set_page_config(page_title="Bea - BehaviorLab AI", page_icon="logo.png", layout="centered")

if "theme" not in st.session_state: st.session_state.theme = "light"
if "lang" not in st.session_state: st.session_state.lang = "FR"
if "show_uploader" not in st.session_state: st.session_state.show_uploader = False
if "messages" not in st.session_state: st.session_state.messages = []
if "show_landing" not in st.session_state: st.session_state.show_landing = True

def toggle_theme():
    st.session_state.theme = "dark" if st.session_state.theme=="light" else "light"
def set_lang(l): st.session_state.lang = l

is_dark = st.session_state.theme=="dark"
bg = "#0f172a" if is_dark else "#f8f9ff"
text_color = "#ffffff" if is_dark else "#1a1a2e"
card_bg = "#1e293b" if is_dark else "#ffffff"
border = "#334155" if is_dark else "#e2e8f0"

st.markdown(f"""
<style>
.stApp {{ background-color: {bg}; color: {text_color}; }}
.header-card {{
    background: linear-gradient(90deg, #4f46e5 0%, #a855f7 50%, #ec4899 100%);
    border-radius: 16px; padding: 18px 24px; margin-bottom: 10px;
}}
.header-card h1 {{ color: white; margin:0; font-size:24px; }}
.header-card p {{ color: white; margin:4px 0 0 0; opacity:0.9; font-size:14px; }}
.pricing-card {{ background: {card_bg}; border: 1px solid {border}; border-radius: 16px; padding: 20px; }}
</style>
""", unsafe_allow_html=True)

# HEADER
c_logo, c_title, c_btns = st.columns([1,5,3])
with c_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=60)
with c_title:
    st.markdown('<div class="header-card"><div><h1>Bea</h1><p>BehaviorLab AI</p></div></div>', unsafe_allow_html=True)
with c_btns:
    b1,b2,b3 = st.columns(3)
    with b1: st.button("☀️" if is_dark else "🌙", on_click=toggle_theme)
    with b2: st.button("FR", on_click=set_lang, args=("FR",))
    with b3: st.button("EN", on_click=set_lang, args=("EN",))

# --- LANDING PAGE ---
if st.session_state.show_landing:
    if st.session_state.lang=="FR":
        st.title("Bea, ton IA comportementaliste pour ton entreprise.")
        st.write("Bea analyse les comportements de tes clients et de tes équipes pour améliorer tes décisions, ta communication et tes performances.")
    else:
        st.title("Bea, your behavioral AI for your business.")
        st.write("Bea analyzes your customers and teams behaviors to improve decisions, communication and performance.")

    # PRIX - sans les 3 cartes entourées
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="pricing-card"><h3>Version Basique</h3><h2>14,90€ <span style="font-size:14px">/mois</span></h2><p>✓ Chat illimité<br>✓ Analyse comportementale</p></div>', unsafe_allow_html=True)
        if st.button("Version Basique", key="basique", use_container_width=True):
            st.session_state.show_landing=False
            st.rerun()
    with col2:
        st.markdown(f'<div class="pricing-card" style="border: 2px solid #6366f1;"><span style="background:#6366f1;color:white;padding:4px 8px;border-radius:8px;font-size:12px">RECOMMANDÉ</span><h3>Version Pro</h3><h2>21€ <span style="font-size:14px">/mois</span></h2><p>✓ Tout Basique<br>✓ Générateur d\'images<br>✓ Analyse d\'images galerie</p></div>', unsafe_allow_html=True)
        if st.button("Version Pro →", key="pro", use_container_width=True):
            st.session_state.show_landing=False
            st.rerun()
    st.stop()

# --- CHAT ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if st.session_state.show_uploader:
    up = st.file_uploader("Glisse une image", type=["png","jpg","jpeg"], label_visibility="collapsed")
    if up: st.image(up, width=300)

if st.button("🖼️"):
    st.session_state.show_uploader = not st.session_state.show_uploader
    st.rerun()

ph = "Parle à Bea, ton IA comportementaliste..." if st.session_state.lang=="FR" else "Talk to Bea, your behavioral AI..."
prompt = st.chat_input(ph)

if prompt:
    st.session_state.messages.append({"role":"user","content":prompt})
    with st.chat_message("user"): st.markdown(prompt)
    resp = f"Analyse comportementale : **{prompt}**\n\nVoici les biais et leviers pour ton entreprise..." if st.session_state.lang=="FR" else f"Behavioral analysis: **{prompt}**..."
    st.session_state.messages.append({"role":"assistant","content":resp})
    with st.chat_message("assistant"): st.markdown(resp)
