import streamlit as st
import os
from groq import Groq
from supabase import create_client

st.set_page_config(page_title="Bea - BehaviorLab AI", page_icon="logo.png", layout="wide")

STRIPE_BASIQUE = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"
STRIPE_PRO = "https://buy.stripe.com/test_cNieVea1P0c62B08523wQ00"

client = Groq(api_key=st.secrets["GROQ_API_KEY"])
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])

if "theme" not in st.session_state: st.session_state.theme = "light"
if "lang" not in st.session_state: st.session_state.lang = "FR"
if "show_uploader" not in st.session_state: st.session_state.show_uploader = False
if "messages" not in st.session_state: st.session_state.messages = []
if "licence" not in st.session_state: st.session_state.licence = None

def toggle_theme():
    st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
is_dark = st.session_state.theme == "dark"

st.markdown(f"""
<style>
header[data-testid="stHeader"] {{ background: transparent!important; }}
.block-container {{ max-width: 1240px!important; padding-top: 1.5rem!important; }}
.header-card {{ background: linear-gradient(135deg, #4338ca 0%, #7c3aed 50%, #db2777 100%); border-radius: 20px; padding: 18px 28px; }}
</style>
""", unsafe_allow_html=True)

c1,c2,c3 = st.columns([0.9,5,2.2])
with c1:
    if os.path.exists("logo.png"): st.image("logo.png", width=68)
with c2:
    st.markdown('<div class="header-card"><div style="color:white"><h2 style="margin:0;color:white;">Bea</h2><p style="margin:0;opacity:0.9;">BehaviorLab AI</p></div></div>', unsafe_allow_html=True)
with c3:
    b1,b2 = st.columns(2)
    with b1: st.button("🌙 Mode sombre" if not is_dark else "☀️ Mode clair", on_click=toggle_theme, help="Changer le thème clair / sombre")
    with b2: st.button(f"🌐 Langue : {st.session_state.lang}", on_click=lambda: st.session_state.__setitem__("lang","EN" if st.session_state.lang=="FR" else "FR"), help="Passer en Français / Anglais")

# ===== VERIF LICENCE SUPABASE =====
query = st.query_params
licence_key = query.get("key") or st.session_state.licence

if licence_key:
    res = supabase.table("licences").select("*").eq("key", licence_key).execute()
    if res.data:
        lic = res.data[0]
        st.session_state.licence = licence_key
        plan = lic["plan"] # BASIC ou PRO
        used = lic["used"]
        limit = lic["limit"]

        if used >= limit:
            st.error(f"⚠️ Licence {licence_key} : limite de {limit} requêtes atteinte. Utilisé : {used}")
            st.stop()

        st.success(f"✅ Licence active : {licence_key} — {plan} — {used}/{limit}")

        for m in st.session_state.messages:
            with st.chat_message(m["role"]): st.markdown(m["content"])

        if plan == "PRO":
            if st.session_state.show_uploader:
                up = st.file_uploader("Glisse une image", type=["png","jpg","jpeg"], label_visibility="collapsed")
                if up: st.image(up, width=500)
            if st.button("🖼️ Glisse une image (galerie)", help="Analyse d'images - uniquement en version Pro"):
                st.session_state.show_uploader = not st.session_state.show_uploader
                st.rerun()

        prompt = st.chat_input("Décris une situation de ton entreprise...")
        if prompt:
            st.session_state.messages.append({"role":"user","content":prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                comp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content":"Tu es Bea, IA comportementaliste. Structure: 1. Blocage (avec biais) 2. Levier 3. Script"},{"role":"user","content":prompt}])
                resp = comp.choices[0].message.content
                st.markdown(resp)
            st.session_state.messages.append({"role":"assistant","content":resp})
            # Incrémente used
            supabase.table("licences").update({"used": used+1}).eq("key", licence_key).execute()
        st.stop()
    else:
        st.error("Clé licence invalide")

# ===== VITRINE SI PAS DE LICENCE =====
hero_l, hero_r = st.columns([1.3,0.7], gap="large")
with hero_l:
    st.markdown(f'<div style="font-size:52px;font-weight:850;line-height:1.05;color:{"#f8fafc" if is_dark else "#0f172a"}">Bea, ton IA<br>comportementaliste<br>pour ton entreprise.</div>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:18px;line-height:1.7;color:#111827;margin-top:22px;">Bea n\'est pas une IA qui rédige des pages de vente. <b>C\'est une IA qui comprend pourquoi les gens n\'achètent pas, pourquoi tes équipes ne performent pas, et quoi changer pour débloquer.</b></p>', unsafe_allow_html=True)
with hero_r:
    st.markdown('''
    <div style="background:#f5f3ff;border-radius:24px;padding:24px;border:1px solid #ede9fe;">
        <div style="font-size:11px;font-weight:800;color:#4c1d95;">SITUATION</div><br>
        <div style="background:white;border-radius:16px;padding:20px;border:1px solid #e5e7eb;color:#111827;line-height:1.6">
            <div style="font-weight:700;">Exemple de question :</div>
            <i>"Une personne est intéressée mais me dit qu'elle doit réfléchir"</i>
            <div style="height:1px;background:#f3f4f6;margin:16px 0;"></div>
            <div style="font-weight:800;color:#7c3aed;">Réponse de Bea :</div>
            <b>Blocage :</b> Biais du statu quo + aversion à la perte.<br><br>
            <b>Levier :</b> Preuve sociale + projection mentale.<br><br>
            <b>À dire :</b> "Je comprends. Une cliente comme toi me disait pareil, elle a pris [produit] et m'a dit : j'aurais dû le prendre plus tôt."
        </div>
    </div>
    ''', unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown('<h2 style="text-align:center;color:#0f172a;font-size:36px;">Choisis le format</h2><p style="text-align:center;color:#6b7280;">Paiement Stripe et retour automatique sur l\'application utilisable</p><br>', unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")
with col1:
    st.markdown('''
    <div style="background:white;border:1px solid #ede9fe;border-radius:24px;padding:32px;min-height:340px;color:#111827;">
        <h3>Version Basique</h3><h1 style="font-size:42px;">14,90€</h1>/mois
        <div style="line-height:2.1;margin-top:12px;">✓ <b>12 requêtes par mois</b> avec Bea<br>✓ Analyses comportementales complètes<br>✓ Scripts de vente / management<br><span style="color:#9ca3af;">✗ Pas d'analyse d'images</span></div>
    </div>''', unsafe_allow_html=True)
    st.link_button("Choisir Version Basique →", STRIPE_BASIQUE, use_container_width=True, help="12 requêtes par mois")

with col2:
    st.markdown('''
    <div style="background:white;border:2px solid #7c3aed;border-radius:24px;padding:32px;min-height:340px;color:#111827;box-shadow:0 12px 32px rgba(124,58,237,0.12)">
        <span style="background:#7c3aed;color:white;padding:6px 14px;border-radius:20px;font-size:11px;font-weight:800">RECOMMANDÉ</span><br><br>
        <h3>Version Pro</h3><h1 style="font-size:42px;">21€</h1>/mois
        <div style="line-height:2.1;margin-top:12px;">✓ <b>Chat illimité avec Bea</b><br>✓ Analyse d'images depuis la galerie<br>✓ Générateur d'images publicitaires<br>✓ Scripts avancés + priorité nouveautés</div>
    </div>''', unsafe_allow_html=True)
    st.link_button("Choisir Version Pro →", STRIPE_PRO, use_container_width=True, type="primary", help="Illimité + galerie images")

st.markdown("<br><br>", unsafe_allow_html=True)
with st.expander("🔑 J'ai déjà une clé licence"):
    k = st.text_input("Entre ta clé", placeholder="TEST-BASIC-123 ou TEST-PRO-123", help="Clé stockée dans Supabase table licences")
    if st.button("Activer", help="Vérifie la clé dans Supabase"):
        st.session_state.licence = k
        st.rerun()
