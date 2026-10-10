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
def toggle_lang():
    st.session_state.lang = "EN" if st.session_state.lang == "FR" else "FR"

is_dark = st.session_state.theme == "dark"
lang = st.session_state.lang

T = {
"FR": {
"hero_title": "Bea, ton IA<br>comportementaliste<br>pour ton entreprise.",
"hero_desc1": "<b>BehaviorLab a créé la première IA du comportement dédiée aux indépendants et TPE/PME.</b> Fini les pages de vente qui ne convertissent pas : Bea transforme chaque hésitation en vente et chaque tension d'équipe en performance.",
"hero_desc2": "C'est une IA qui comprend <b>pourquoi les gens n'achètent pas, pourquoi tes équipes ne performent pas, et quoi changer pour débloquer</b>.",
"hero_desc3": "Elle analyse avec : biais cognitifs, économie comportementale, neurosciences de la décision.",
"situation": "SITUATION",
"exemple": "Exemple :",
"exemple_text": "\"Une personne est intéressée mais me dit qu'elle doit réfléchir\"",
"reponse": "Réponse de Bea :",
"blocage": "Blocage : Biais du statu quo + aversion à la perte.",
"levier": "Levier : Preuve sociale + projection mentale.",
"adire": "À dire : \"Je comprends. Une cliente comme toi me disait pareil, elle a pris [produit] et m'a dit : j'aurais dû le prendre plus tôt.\"",
"choisis": "Choisis le format",
"paiement": "Paiement Stripe et retour automatique sur l'application utilisable",
"basique": "Version Basique",
"pro": "Version Pro",
"recommande": "RECOMMANDÉ",
"par_mois": "/mois",
"basique_1": "✓ <b>12 requêtes par mois</b>",
"basique_2": "✓ Analyses comportementales complètes",
"basique_3": "✓ Scripts de vente / management",
"basique_4": "✓ Historique de tes échanges",
"btn_basique": "Choisir Version Basique →",
"pro_1": "✓ <b>Chat illimité avec Bea</b>",
"pro_2": "✓ Analyse d'images depuis la galerie",
"pro_3": "✓ Générateur d'images publicitaires",
"pro_4": "✓ Scripts avancés + nouveautés",
"pro_5": "✓ Sans limite",
"btn_pro": "Choisir Version Pro →",
"chat_placeholder": "Décris une situation de ton entreprise...",
"licence_active": "Licence active",
"galerie_btn": "🖼️ Glisse une image (galerie) - Pro",
"mode_clair": "☀️ Mode clair",
"mode_sombre": "🌙 Mode sombre",
},
"EN": {
"hero_title": "Bea, your AI<br>behavioral expert<br>for your business.",
"hero_desc1": "<b>BehaviorLab created the first behavioral AI for freelancers and SMBs.</b> No more sales pages that don't convert: Bea turns every hesitation into a sale and every team tension into performance.",
"hero_desc2": "It's an AI that understands <b>why people don't buy, why your teams don't perform, and what to change to unblock</b>.",
"hero_desc3": "It analyzes with: cognitive biases, behavioral economics, decision neuroscience.",
"situation": "SITUATION",
"exemple": "Example:",
"exemple_text": "\"Someone is interested but tells me they need to think about it\"",
"reponse": "Bea's answer:",
"blocage": "Block: Status quo bias + loss aversion.",
"levier": "Lever: Social proof + mental projection.",
"adire": "Say: \"I understand. A client like you told me the same, she took [product] and told me: I should have taken it sooner.\"",
"choisis": "Choose your plan",
"paiement": "Stripe payment and automatic return to the usable app",
"basique": "Basic Version",
"pro": "Pro Version",
"recommande": "RECOMMENDED",
"par_mois": "/month",
"basique_1": "✓ <b>12 requests per month</b>",
"basique_2": "✓ Full behavioral analysis",
"basique_3": "✓ Sales / management scripts",
"basique_4": "✓ History of your chats",
"btn_basique": "Choose Basic Version →",
"pro_1": "✓ <b>Unlimited chat with Bea</b>",
"pro_2": "✓ Image analysis from gallery",
"pro_3": "✓ Ad image generator",
"pro_4": "✓ Advanced scripts + new features",
"pro_5": "✓ Unlimited",
"btn_pro": "Choose Pro Version →",
"chat_placeholder": "Describe a situation in your business...",
"licence_active": "Active license",
"galerie_btn": "🖼️ Drag an image (gallery) - Pro",
"mode_clair": "☀️ Light mode",
"mode_sombre": "🌙 Dark mode",
}
}
t = T[lang]

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
    st.button(t["mode_clair"] if is_dark else t["mode_sombre"], on_click=toggle_theme)
    st.button(f"🌐 Langue : {lang}", on_click=toggle_lang)

query = st.query_params
licence_key = query.get("key") or st.session_state.licence

if licence_key:
    res = supabase.table("licences").select("*").eq("key", licence_key).execute()
    if res.data:
        lic = res.data[0]
        plan, used, limit = lic["plan"], lic["used"], lic["limit"]
        if used >= limit:
            st.error(f"{used}/{limit} limit reached")
            st.stop()
        st.success(f"✅ {t['licence_active']} : {licence_key} — {plan} — {used}/{limit}")
        for m in st.session_state.messages:
            with st.chat_message(m["role"]): st.markdown(m["content"])
        if plan == "PRO":
            if st.session_state.show_uploader:
                up = st.file_uploader("Image", type=["png","jpg","jpeg"])
                if up: st.image(up, width=500)
            if st.button(t["galerie_btn"]):
                st.session_state.show_uploader = not st.session_state.show_uploader
                st.rerun()
        prompt = st.chat_input(t["chat_placeholder"])
        if prompt:
            st.session_state.messages.append({"role":"user","content":prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Bea analyse..." if lang=="FR" else "Bea is analyzing..."):
                    # --- SEULE MODIF : RELANCE CLIENT ---
                    system_prompt = f"""Tu es Bea, IA comportementaliste par BehaviorLab. Langue:{lang}.
                    Format obligatoire: 1. Blocage (biais cognitif) 2. Levier 3. Script exact à dire/faire.
                    A LA FIN DE CHAQUE REPONSE, tu dois OBLIGATOIREMENT relancer le client avec 2-3 propositions concrètes, par exemple:
                    - Veux-tu que je te rédige le message exact prêt à envoyer?
                    - Tu veux que je l'adapte à ton offre précise?
                    - Tu as une autre situation à débloquer maintenant?
                    Ne termine JAMAIS sans question de relance. Sois directe et utile."""
                    comp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content":system_prompt},{"role":"user","content":prompt}])
                    resp = comp.choices[0].message.content
                    st.markdown(resp)
            st.session_state.messages.append({"role":"assistant","content":resp})
            supabase.table("licences").update({"used": used+1}).eq("key", licence_key).execute()
        st.stop()

l,r = st.columns([1.3,0.7], gap="large")
with l:
    st.markdown(f"<div style='font-size:52px;font-weight:850;line-height:1.05;color:{text_color};'>{t['hero_title']}</div>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{desc_color};font-size:18px;line-height:1.7;margin-top:20px;'>{t['hero_desc1']}<br><br>{t['hero_desc2']}<br><br>{t['hero_desc3']}</p>", unsafe_allow_html=True)
with r:
    st.markdown(f"<div style='background:{"#1e293b" if is_dark else "#f5f3ff"};border-radius:24px;padding:22px;border:1px solid {"#334155" if is_dark else "#ede9fe"};'><div style='font-size:11px;font-weight:800;color:#7c3aed;'>{t['situation']}</div><br><div style='background:{"#0f172a" if is_dark else "white"};border-radius:16px;padding:18px;color:{text_color};line-height:1.6'><b>{t['exemple']}</b><br><i>{t['exemple_text']}</i><br><br><b style='color:#7c3aed;'>{t['reponse']}</b><br><b>{t['blocage']}</b><br>{t['levier']}<br>{t['adire']}</div></div>", unsafe_allow_html=True)

st.markdown(f"<h2 style='text-align:center;color:{text_color};margin-top:35px;'>{t['choisis']}</h2><p style='text-align:center;color:{desc_color};'>{t['paiement']}</p>", unsafe_allow_html=True)

cA,cB = st.columns(2, gap="large")
with cA:
    st.markdown(f"<div class='pricing-card'><h3 style='color:{text_color};'>{t['basique']}</h3><h1 style='color:{text_color};'>14,90€ <span style='font-size:16px;font-weight:400;'>{t['par_mois']}</span></h1><div style='line-height:2;color:{text_color};font-size:15px;'>{t['basique_1']}<br>{t['basique_2']}<br>{t['basique_3']}<br>{t['basique_4']}</div></div>", unsafe_allow_html=True)
    st.link_button(t["btn_basique"], STRIPE_BASIQUE, use_container_width=True)
with cB:
    st.markdown(f"<div class='pricing-card' style='border:2px solid #7c3aed;'><span style='background:{GRADIENT};color:white!important;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:800;'>{t['recommande']}</span><h3 style='margin-top:12px;color:{text_color};'>{t['pro']}</h3><h1 style='color:{text_color};'>21€ <span style='font-size:16px;font-weight:400;'>{t['par_mois']}</span></h1><div style='line-height:2;color:{text_color};font-size:15px;'>{t['pro_1']}<br>{t['pro_2']}<br>{t['pro_3']}<br>{t['pro_4']}<br>{t['pro_5']}</div></div>", unsafe_allow_html=True)
    st.link_button(t["btn_pro"], STRIPE_PRO, use_container_width=True)
