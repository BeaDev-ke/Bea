import streamlit as st
import os
from groq import Groq
from supabase import create_client
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Bea - BehaviorLab AI", page_icon="logo.png", layout="wide", initial_sidebar_state="expanded")

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
if "gen_image" not in st.session_state: st.session_state.gen_image = False

is_dark = st.session_state.theme == "dark"

def generer_apercu_paysage(texte):
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), (15, 15, 45))
    draw = ImageDraw.Draw(img)
    try:
        ft = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
        fs = ImageFont.truetype("DejaVuSans.ttf", 20)
    except:
        ft = ImageFont.load_default()
        fs = ImageFont.load_default()
    draw.rectangle([0,0,W,90], fill=(67,56,202))
    draw.text((30,25), "Bea - Illustration 1280x720", font=ft, fill="white")
    draw.rectangle([30,120,W-30,H-30], fill=(30,30,60), outline=(124,58,237), width=2)
    draw.text((60,150), f"Illustration pour: {texte[:110]}", font=fs, fill="white")
    return img

GRADIENT = "linear-gradient(135deg, #4338ca 0%, #7c3aed 50%, #db2777 100%)"
bg_color = "#0f172a" if is_dark else "#ffffff"
text_color = "#f8fafc" if is_dark else "#0f172a"
desc_color = "#cbd5e1" if is_dark else "#475569"

st.markdown(f"""
<style>
.stApp {{ background:{bg_color}; }}
header[data-testid="stHeader"] {{ background: transparent!important; }}
.block-container {{ max-width:1240px!important; padding-top:1.2rem!important; }}
.pricing-card {{ background:{"#1e293b" if is_dark else "white"}; border:1px solid {"#334155" if is_dark else "#e2e8f0"}; border-radius:24px; padding:28px; }}
.header-card {{ background:{GRADIENT}; border-radius:20px; padding:18px 28px; }}
.header-card h2,.header-card p {{ color:white!important; margin:0; }}
</style>
""", unsafe_allow_html=True)

c1,c2,c3 = st.columns([0.9,5,2.2])
with c1:
    if os.path.exists("logo.png"): st.image("logo.png", width=68)
with c2:
    st.markdown('<div class="header-card"><h2>Bea</h2><p>BehaviorLab AI</p></div>', unsafe_allow_html=True)
with c3:
    if st.button("☀️ Mode clair" if is_dark else "🌙 Mode sombre", key="btn_theme"):
        st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
        st.rerun()
    if st.button(f"🌐 Langue : {st.session_state.lang}", key="btn_lang"):
        st.session_state.lang = "EN" if st.session_state.lang == "FR" else "FR"
        st.rerun()

query = st.query_params
licence_key = query.get("key") or st.session_state.licence

if licence_key:
    res = supabase.table("licences").select("*").eq("key", licence_key).execute()
    if res.data:
        lic = res.data[0]
        plan, used, limit = lic["plan"], lic["used"], lic["limit"]
        if used >= limit:
            st.error(f"Limite {used}/{limit} atteinte")
            st.stop()
        masked_key = f"****{licence_key[-4:]}" if len(licence_key) > 4 else "****"
        st.success(f"✅ Licence active : {masked_key} — {plan} — {used}/{limit}")

        with st.sidebar:
            if os.path.exists("logo.png"): st.image("logo.png", width=50)
            st.markdown("### Bea")
            st.caption("BehaviorLab AI")
            st.caption(f"Plan {plan} - {used}/{limit}")
            st.divider()
            st.markdown("**Historique**")
            for m in reversed(st.session_state.messages[-15:]):
                if m["role"] == "user":
                    st.markdown(f"💬 {m['content'][:35]}...")
            if st.button("🗑️ Nouvelle discussion"):
                st.session_state.messages = []
                st.rerun()

        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
                if "image" in m and m["image"] is not None:
                    st.image(m["image"], use_container_width=True)

        if plan == "PRO":
            if st.session_state.show_uploader:
                up = st.file_uploader("Glisse une image", type=["png","jpg","jpeg"])
                if up: st.image(up, width=500)
            if st.button("🖼️ Glisse une image (galerie) - Pro"):
                st.session_state.show_uploader = not st.session_state.show_uploader
                st.rerun()

        st.checkbox("🖼️ Générer une image d'illustration", key="gen_image")
        prompt = st.chat_input("Décris une situation de ton entreprise et ton état d'esprit actuel...")
        if prompt:
            st.session_state.messages.append({"role":"user","content":prompt})
            if plan!= "PRO" and len(st.session_state.messages) > 30:
                st.session_state.messages = st.session_state.messages[-30:]
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                if st.session_state.gen_image:
                    img = generer_apercu_paysage(prompt)
                    st.image(img, caption="Illustration 1280x720", use_container_width=True)
                    st.session_state.messages.append({"role":"assistant","content":f"Illustration générée pour : {prompt}", "image": img})
                else:
                    comp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content":f"Tu es Bea, IA comportementaliste par BehaviorLab. Langue:{st.session_state.lang}. Structure: 1.Blocage 2.Levier 3.Script"}] + [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if "image" not in m][-30:])
                    resp = comp.choices[0].message.content
                    st.markdown(resp)
                    st.session_state.messages.append({"role":"assistant","content":resp})
            supabase.table("licences").update({"used": used+1}).eq("key", licence_key).execute()
        st.stop()

# VITRINE
l,r = st.columns([1.3,0.7], gap="large")
with l:
    st.markdown(f"<div style='font-size:52px;font-weight:850;line-height:1.05;color:{text_color};'>Bea, ton IA<br>comportementaliste<br>pour ton entreprise.</div>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{desc_color};font-size:18px;line-height:1.7;margin-top:20px;'><b style='color:{text_color};'>BehaviorLab a créé la première IA du comportement dédiée aux indépendants et TPE/PME.</b> Fini les pages de vente qui ne convertissent pas : Bea transforme chaque hésitation en vente et chaque tension d'équipe en performance.<br><br>C'est une IA qui comprend <b style='color:{text_color};'>pourquoi les gens n'achètent pas, pourquoi tes équipes ne performent pas, et quoi changer pour débloquer</b>.<br><br>Elle analyse avec : biais cognitifs, économie comportementale, neurosciences de la décision.</p>", unsafe_allow_html=True)
with r:
    st.markdown(f"<div style='background:{"#1e293b" if is_dark else "#f5f3ff"};border-radius:24px;padding:22px;'><div style='background:{"#0f172a" if is_dark else "white"};border-radius:16px;padding:18px;color:{text_color};'>Exemple: \"doit réfléchir\" → Biais statu quo → Script preuve sociale</div></div>", unsafe_allow_html=True)

cA,cB = st.columns(2, gap="large")
with cA:
    st.markdown(f"<div class='pricing-card'><h3>Basique</h3><h1>14,90€</h1>12 requêtes / mois</div>", unsafe_allow_html=True)
    st.link_button("Choisir Basique →", STRIPE_BASIQUE, use_container_width=True)
with cB:
    st.markdown(f"<div class='pricing-card' style='border:2px solid #7c3aed;'>PRO - 21€ - Illimité</div>", unsafe_allow_html=True)
    st.link_button("Choisir Pro →", STRIPE_PRO, use_container_width=True)
