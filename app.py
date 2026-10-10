import streamlit as st
import os
from groq import Groq
from supabase import create_client

st.set_page_config(page_title="Bea - BehaviorLab AI", page_icon="logo.png", layout="wide", initial_sidebar_state="collapsed")

STRIPE_BASIQUE = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"
STRIPE_PRO = "https://buy.stripe.com/test_cNieVea1P0c62B08523wQ00"

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

# --- CSS QUI MARCHE VRAIMENT EN CLAIR / SOMBRE ---
bg_color = "#0f172a" if is_dark else "#ffffff"
text_color = "#f8fafc" if is_dark else "#0f172a"
desc_color = "#cbd5e1" if is_dark else "#334155"
card_bg = "#1e293b" if is_dark else "#ffffff"
card_border = "#334155" if is_dark else "#ede9fe"

st.markdown(f"""
<style>
.stApp {{ background-color: {bg_color}; }}
header[data-testid="stHeader"] {{ background: transparent!important; }}
.block-container {{ max-width: 1240px!important; padding-top: 1.5rem!important; }}
h1,h2,h3,p,div,span,li {{ color: {text_color}!important; }}
.header-card {{ background: linear-gradient(135deg, #4338ca 0%, #7c3aed 50%, #db2777 100%); border-radius: 20px; padding: 18px 28px; }}
.desc-text {{ color: {desc_color}!important; font-size:18px; line-height:1.7; margin-top:22px; }}
.pricing-card {{ background:{card_bg}; border:1px solid {card_border}; border-radius:24px; padding:32px; min-height:360px; }}
.example-card {{ background:{"#1e293b" if is_dark else "#f5f3ff"}; border-radius:24px; padding:24px; border:1px solid {card_border}; }}
.example-inner {{ background:{card_bg}; border-radius:16px; padding:20px; border:1px solid {card_border}; color:{text_color}; line-height:1.6 }}
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
c1,c2,c3 = st.columns([0.9,5,2.2])
with c1:
    if os.path.exists("logo.png"): st.image("logo.png", width=68)
with c2:
    st.markdown('<div class="header-card"><div style="color:white!important"><h2 style="margin:0;color:white!important;">Bea</h2><p style="margin:0;opacity:0.9;color:white!important;">BehaviorLab AI</p></div></div>', unsafe_allow_html=True)
with c3:
    b1,b2 = st.columns(2)
    with b1:
        st.button("☀️ Mode clair" if is_dark else "🌙 Mode sombre", on_click=toggle_theme)
    with b2:
        st.button(f"🌐 Langue : {st.session_state.lang}", on_click=lambda: st.session_state.__setitem__("lang","EN" if st.session_state.lang=="FR" else "FR"))

# --- VERIF LICENCE = MODE APP ---
query = st.query_params
licence_key = query.get("key") or st.session_state.licence

if licence_key:
    res = supabase.table("licences").select("*").eq("key", licence_key).execute()
    if res.data:
        lic = res.data[0]
        st.session_state.licence = licence_key
        plan = lic["plan"]; used = lic["used"]; limit = lic["limit"]
        if used >= limit:
            st.error(f"⚠️ Licence {licence_key} : limite atteinte ({used}/{limit}) - Passe en Pro")
            st.stop()
        st.success(f"✅ Licence active : {licence_key} — {plan} — {used}/{limit} — Application utilisable")
        st.markdown(f"<h3 style='color:{text_color}!important;'>Parle à Bea, ton IA comportementaliste</h3>", unsafe_allow_html=True)

        for m in st.session_state.messages:
            with st.chat_message(m["role"]): st.markdown(m["content"])

        # ICI SEULEMENT EN MODE PRO : LA GALERIE
        if plan == "PRO":
            if st.session_state.show_uploader:
                up = st.file_uploader("Glisse une image de ta galerie", type=["png","jpg","jpeg"])
                if up: st.image(up, width=500)
            if st.button("🖼️ Glisse une image (galerie) - Pro uniquement"):
                st.session_state.show_uploader = not st.session_state.show_uploader
                st.rerun()

        # ICI LA VRAIE CASE TEXTE DE DISCUSSION
        prompt = st.chat_input("Décris une situation de ton entreprise...")
        if prompt:
            st.session_state.messages.append({"role":"user","content":prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Bea analyse..."):
                    comp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content":f"Tu es Bea, IA comportementaliste. Langue: {st.session_state.lang}. Réponds en 3 parties: 1.Blocage (biais) 2.Levier 3.Script exact"},{"role":"user","content":prompt}])
                    resp = comp.choices[0].message.content
                    st.markdown(resp)
            st.session_state.messages.append({"role":"assistant","content":resp})
            supabase.table("licences").update({"used": used+1}).eq("key", licence_key).execute()
        st.stop()

# --- VITRINE (SANS GALERIE) ---
hero_l, hero_r = st.columns([1.3,0.7], gap="large")
with hero_l:
    st.markdown(f"<div style='font-size:52px;font-weight:850;line-height:1.05;color:{text_color};'>Bea, ton IA<br>comportementaliste<br>pour ton entreprise.</div>", unsafe_allow_html=True)
    st.markdown(f"<p class='desc-text'>Bea n'est pas une IA qui rédige des pages de vente. <b>C'est une IA qui comprend pourquoi les gens n'achètent pas, pourquoi tes équipes ne performent pas, et quoi changer pour débloquer.</b><br><br>Elle analyse avec : biais cognitifs, économie comportementale, neurosciences de la décision.</p>", unsafe_allow_html=True)
with hero_r:
    st.markdown(f'<div class="example-card"><div style="font-size:11px;font-weight:800;color:#4c1d95;">SITUATION</div><br><div class="example-inner"><div style="font-weight:700;">Exemple :</div><i>"Une personne est intéressée mais me dit qu\'elle doit réfléchir"</i><div style="height:1px;background:#334155;margin:16px 0;"></div><div style="font-weight:800;color:#7c3aed;">Réponse de Bea :</div><b>Blocage :</b> Biais du statu quo + aversion à la perte.<br><br><b>Levier :</b> Preuve sociale + projection mentale.<br><br><b>À dire :</b> "Je comprends. Une cliente comme toi me disait pareil, elle a pris [produit] et m\'a dit : j\'aurais dû le prendre plus tôt."</div></div>', unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(f'<h2 style="text-align:center;font-size:36px;color:{text_color};">Choisis le format</h2><p style="text-align:center;color:{desc_color};">Paiement Stripe et retour automatique sur l\'application utilisable</p><br>', unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")
with col1:
    st.markdown(f'<div class="pricing-card"><h3>Version Basique</h3><div style="display:flex;align-items:baseline;gap:8px;margin:12px 0;"><h1 style="margin:0;font-size:42px;">14,90€</h1><span>/mois</span></div><div style="line-height:2.1;font-size:15px;">✓ <b>12 requêtes par mois</b><br>✓ Analyses comportementales<br>✓ Scripts de vente<br>✓ Historique<br><span style="color:#9ca3af;">✗ Pas d\'analyse d\'images</span></div></div>', unsafe_allow_html=True)
    st.link_button("Choisir Version Basique →", STRIPE_BASIQUE, use_container_width=True)
with col2:
    st.markdown(f'<div class="pricing-card" style="border:2px solid #7c3aed;box-shadow:0 12px 32px rgba(124,58,237,0.12)"><span style="background:#7c3aed;color:white!important;padding:6px 14px;border-radius:20px;font-size:11px;font-weight:800">RECOMMANDÉ</span><br><br><h3>Version Pro</h3><div style="display:flex;align-items:baseline;gap:8px;margin:12px 0;"><h1 style="margin:0;font-size:42px;">21€</h1><span>/mois</span></div><div style="line-height:2.1;font-size:15px;">✓ <b>Chat illimité avec Bea</b><br>✓ Analyse d\'images galerie<br>✓ Générateur d\'images pub<br>✓ Scripts avancés<br>✓ Sans limite</div></div>', unsafe_allow_html=True)
    st.link_button("Choisir Version Pro →", STRIPE_PRO, use_container_width=True, type="primary")
