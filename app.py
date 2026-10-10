import streamlit as st
import os
from groq import Groq
from supabase import create_client

st.set_page_config(page_title="Bea - BehaviorLab AI", page_icon="logo.png", layout="wide", initial_sidebar_state="collapsed")

STRIPE_BASIQUE = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"
STRIPE_PRO = "https://buy.stripe.com/test_cNieVea1P0c62B08523wQ00"

# CONNEXION
GROQ_KEY = st.secrets["GROQ_API_KEY"]
SUPA_URL = st.secrets["SUPABASE_URL"]
SUPA_KEY = st.secrets.get("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_PUBLISHABLE_KEY")
client = Groq(api_key=GROQ_KEY)
supabase = create_client(SUPA_URL, SUPA_KEY)

if "theme" not in st.session_state: st.session_state.theme = "light"
if "lang" not in st.session_state: st.session_state.lang = "FR"
if "show_uploader" not in st.session_state: st.session_state.show_uploader = False
if "messages" not in st.session_state: st.session_state.messages = []
if "licence" not in st.session_state: st.session_state.licence = None

def toggle_theme():
    st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
is_dark = st.session_state.theme == "dark"

GRADIENT = "linear-gradient(135deg, #4338ca 0%, #7c3aed 50%, #db2777 100%)"
bg_color = "#0f172a" if is_dark else "#ffffff"
text_color = "#f8fafc" if is_dark else "#0f172a"
desc_color = "#cbd5e1" if is_dark else "#475569"

st.markdown(f"""
<style>
.stApp {{ background:{bg_color}; }}
header[data-testid="stHeader"] {{ background: transparent!important; }}
.block-container {{ max-width:1240px!important; padding-top:1.2rem!important; padding-bottom:1rem!important; }}
div[data-testid="stButton"] > button, div[data-testid="stLinkButton"] > a {{
    background:{GRADIENT}!important; color:white!important; border:none!important;
    border-radius:12px!important; font-weight:700!important; }}
div[data-testid="stButton"] > button p, div[data-testid="stLinkButton"] > a p {{ color:white!important; }}
.header-card {{ background:{GRADIENT}; border-radius:20px; padding:18px 28px; }}
.header-card h2,.header-card p {{ color:white!important; margin:0; }}
.pricing-card {{ background:{"#1e293b" if is_dark else "white"}; border:1px solid {"#334155" if is_dark else "#e2e8f0"}; border-radius:24px; padding:28px; }}
</style>
""", unsafe_allow_html=True)

c1,c2,c3 = st.columns([0.9,5,2.2])
with c1:
    if os.path.exists("logo.png"): st.image("logo.png", width=68)
with c2:
    st.markdown('<div class="header-card"><h2>Bea</h2><p>BehaviorLab AI</p></div>', unsafe_allow_html=True)
with c3:
    st.button("☀️ Mode clair" if is_dark else "🌙 Mode sombre", on_click=toggle_theme)
    st.button(f"🌐 Langue : {st.session_state.lang}", on_click=lambda: st.session_state.__setitem__("lang","EN" if st.session_state.lang=="FR" else "FR"))

query = st.query_params
licence_key = query.get("key") or st.session_state.licence

if licence_key:
    res = supabase.table("licences").select("*").eq("key", licence_key).execute()
    if res.data:
        lic = res.data[0]
        plan, used, limit = lic["plan"], lic["used"], lic["limit"]
        if used >= limit:
            st.error(f"Licence {licence_key} : limite {used}/{limit} atteinte - Passe en Pro")
            st.stop()
        st.success(f"✅ Licence active : {licence_key} — {plan} — {used}/{limit}")
        for m in st.session_state.messages:
            with st.chat_message(m["role"]): st.markdown(m["content"])
        if plan == "PRO":
            if st.session_state.show_uploader:
                up = st.file_uploader("Glisse une image", type=["png","jpg","jpeg"])
                if up: st.image(up, width=500)
            if st.button("🖼️ Glisse une image (galerie) - Pro"):
                st.session_state.show_uploader = not st.session_state.show_uploader
                st.rerun()
        prompt = st.chat_input("Décris une situation de ton entreprise...")
        if prompt:
            st.session_state.messages.append({"role":"user","content":prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Bea analyse..."):
                    comp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content":f"Tu es Bea, IA comportementaliste par BehaviorLab. Langue:{st.session_state.lang}. Structure: 1.Blocage avec biais cognitifs 2.Levier 3.Script exact à dire"},{"role":"user","content":prompt}])
                    resp = comp.choices[0].message.content
                    st.markdown(resp)
            st.session_state.messages.append({"role":"assistant","content":resp})
            supabase.table("licences").update({"used": used+1}).eq("key", licence_key).execute()
        st.stop()
    else:
        st.error("❌ Clé invalide")

# VITRINE
l,r = st.columns([1.3,0.7], gap="large")
with l:
    st.markdown(f"<div style='font-size:52px;font-weight:850;line-height:1.05;color:{text_color};'>Bea, ton IA<br>comportementaliste<br>pour ton entreprise.</div>", unsafe_allow_html=True)
    # NOUVELLE DESCRIPTION
    st.markdown(f"<p style='color:{desc_color};font-size:18px;line-height:1.7;margin-top:20px;'><b style='color:{text_color};'>BehaviorLab a créé la première IA du comportement dédiée aux indépendants et TPE/PME.</b> Fini les pages de vente qui ne convertissent pas : Bea transforme chaque hésitation en vente et chaque tension d'équipe en performance.<br><br>C'est une IA qui comprend <b style='color:{text_color};'>pourquoi les gens n'achètent pas, pourquoi tes équipes ne performent pas, et quoi changer pour débloquer des résultats concrets</b>.<br><br>Elle analyse avec : biais cognitifs, économie comportementale, neurosciences de la décision.</p>", unsafe_allow_html=True)
with r:
    st.markdown(f"<div style='background:{"#1e293b" if is_dark else "#f5f3ff"};border-radius:24px;padding:22px;border:1px solid {"#334155" if is_dark else "#ede9fe"};'><div style='font-size:11px;font-weight:800;color:#7c3aed;'>SITUATION</div><br><div style='background:{"#0f172a" if is_dark else "white"};border-radius:16px;padding:18px;color:{text_color};line-height:1.6'><b>Exemple :</b><br><i>\"Une personne est intéressée mais me dit qu'elle doit réfléchir\"</i><br><br><b style='color:#7c3aed;'>Réponse de Bea :</b><br><b>Blocage :</b> Biais du statu quo + aversion à la perte.<br><b>Levier :</b> Preuve sociale + projection mentale.<br><b>À dire :</b> \"Je comprends. Une cliente comme toi me disait pareil, elle a pris [produit] et m'a dit : j'aurais dû le prendre plus tôt.\"</div></div>", unsafe_allow_html=True)

st.markdown(f"<h2 style='text-align:center;color:{text_color};margin-top:35px;'>Choisis le format</h2><p style='text-align:center;color:{desc_color};'>Paiement Stripe et retour automatique sur l'application utilisable</p>", unsafe_allow_html=True)

cA,cB = st.columns(2, gap="large")
with cA:
    st.markdown(f"<div class='pricing-card'><h3 style='color:{text_color};'>Version Basique</h3><h1 style='color:{text_color};'>14,90€ <span style='font-size:16px;font-weight:400;'>/mois</span></h1><div style='line-height:2;color:{text_color};font-size:15px;'>✓ <b>12 requêtes par mois</b><br>✓ Analyses comportementales complètes<br>✓ Scripts de vente / management<br>✓ Historique de tes échanges</div></div>", unsafe_allow_html=True)
    st.link_button("Choisir Version Basique →", STRIPE_BASIQUE, use_container_width=True)
with cB:
    st.markdown(f"<div class='pricing-card' style='border:2px solid #7c3aed;'><span style='background:{GRADIENT};color:white!important;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:800;'>RECOMMANDÉ</span><h3 style='margin-top:12px;color:{text_color};'>Version Pro</h3><h1 style='color:{text_color};'>21€ <span style='font-size:16px;font-weight:400;'>/mois</span></h1><div style='line-height:2;color:{text_color};font-size:15px;'>✓ <b>Chat illimité avec Bea</b><br>✓ Analyse d'images depuis la galerie<br>✓ Générateur d'images publicitaires<br>✓ Scripts avancés + nouveautés<br>✓ Sans limite</div></div>", unsafe_allow_html=True)
    st.link_button("Choisir Version Pro →", STRIPE_PRO, use_container_width=True)
