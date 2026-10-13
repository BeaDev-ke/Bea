import streamlit as st
import os, re, time, html, urllib.parse
from groq import Groq
from supabase import create_client
from collections import deque

st.set_page_config(page_title="BehaviorLab AI", page_icon="logo.png", layout="wide")

STRIPE_BASIQUE = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"
STRIPE_PRO = "https://buy.stripe.com/test_cNieVea1P0c62B08523wQ00"
STRIPE_CREATOR = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"

GROQ_KEY = st.secrets["GROQ_API_KEY"]
SUPA_URL = st.secrets["SUPABASE_URL"]
SUPA_KEY = st.secrets.get("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_PUBLISHABLE_KEY")
client = Groq(api_key=GROQ_KEY)
supabase = create_client(SUPA_URL, SUPA_KEY)

for k,v in {"theme":"light","lang":"FR","messages":[],"show_uploader":False,"uploaded_file_info":None,"rate_limit":deque(),"violations":0,"blocked_until":0,"last_prompts":deque(maxlen=5),"selected_ia":None}.items():
    if k not in st.session_state: st.session_state[k]=v

def toggle_theme(): st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
def toggle_lang(): st.session_state.lang = "EN" if st.session_state.lang == "FR" else "FR"

# TRADUCTIONS FR/EN
T = {
 "FR": {
  "main_title":"BehaviorLab AI",
  "sub_title":"Les IA comportementales pour votre réussite",
  "hero_desc":"<b>BehaviorLab AI a créé les premières intelligences artificielles du comportement.</b><br>Destinée à ceux qui veulent booster leur réussite nous proposons des intelligences artificielles qui correspondent à vos besoins. Que ce soit pour les entreprises qui veulent augmenter leur chiffre d'affaires ou les individus qui veulent se lancer dans la création de contenus nos intelligences artificielles sont formées dans un seul but:",
  "success":"votre réussite",
  "discover_formats":"Découvrir les différents formats IA",
  "bea_tag":"L'IA qui décode tes clients et double ton closing",
  "nova_tag":"L'IA qui propulse tes contenus et ton audience",
  "bea_short":"L'IA QUI DÉCODE TES CLIENTS",
  "nova_short":"L'IA QUI PROPULSE TES CONTENUS ET TON AUDIENCE",
  "bea_what":"Bea, c'est quoi exactement?",
  "nova_what":"Nova, c'est quoi?",
  "bea_desc":"Bea est la première intelligence artificielle comportementale entraînée sur plus de 10 000 situations de vente réelles. Elle ne te donne pas des conseils génériques, elle décrypte le comportement humain derrière chaque objection.",
  "bea_desc2":"Quand quelqu'un dit \"je dois réfléchir\", \"c'est trop cher\", \"je dois en parler à mon conjoint\", Bea sait exactement quel blocage psychologique se cache derrière et quel levier activer pour débloquer sans forcer.",
  "nova_desc":"Nova est l'IA des créateurs qui veulent percer. Elle maîtrise les 12 biais cognitifs qui font qu'une vidéo explose ou flop. Elle ne te donne pas juste une idée, elle te donne le hook exact, le script mot à mot et le visuel qui va avec.",
  "gain":"Ce qu'elle peut te faire gagner :",
  "examples":"Exemples concrets à lui demander :",
  "ask_bea":"Demander à Bea...",
  "ask_nova":"Demander à Nova...",
  "file_btn":"📎 Glisser un fichier",
  "return":"⬅️ Retour",
  "choose_bea":"Choisir Bea Pro - 21€/mois →",
  "choose_nova":"Choisir Nova - 7,90€/mois →",
  "discover_bea":"Découvrir Bea →",
  "discover_nova":"Découvrir Nova →",
 },
 "EN": {
  "main_title":"BehaviorLab AI",
  "sub_title":"Behavioral AIs for your success",
  "hero_desc":"<b>BehaviorLab AI created the first behavioral artificial intelligences.</b><br>For those who want to boost their success, we offer AIs that match your needs. Whether for businesses wanting to increase revenue or individuals launching into content creation, our AIs are trained for one goal:",
  "success":"your success",
  "discover_formats":"Discover the different AI formats",
  "bea_tag":"The AI that reads your customers' minds and doubles your closing",
  "nova_tag":"The AI that boosts your content and your audience",
  "bea_short":"THE AI THAT DECODES YOUR CUSTOMERS",
  "nova_short":"THE AI THAT BOOSTS YOUR CONTENT & AUDIENCE",
  "bea_what":"What exactly is Bea?",
  "nova_what":"What is Nova?",
  "bea_desc":"Bea is the first behavioral AI trained on 10,000+ real sales situations. She doesn't give generic advice, she decodes human behavior behind every objection.",
  "bea_desc2":"When someone says \"I need to think\", \"it's too expensive\", \"I need to talk to my spouse\", Bea knows exactly which psychological block is behind and which lever to pull to unlock without forcing.",
  "nova_desc":"Nova is the AI for creators who want to break through. She masters the 12 cognitive biases that make a video explode or flop. She doesn't just give an idea, she gives the exact hook, word-for-word script and visual.",
  "gain":"What she can help you gain:",
  "examples":"Concrete examples to ask her:",
  "ask_bea":"Ask Bea...",
  "ask_nova":"Ask Nova...",
  "file_btn":"📎 Drop a file",
  "return":"⬅️ Back",
  "choose_bea":"Choose Bea Pro - 21€/month →",
  "choose_nova":"Choose Nova - 7.90€/month →",
  "discover_bea":"Discover Bea →",
  "discover_nova":"Discover Nova →",
 }
}
L = T[st.session_state.lang]

def sanitize_input(t):
    if not t: return ""
    t=html.escape(t.strip())[:2000]
    t=re.sub(r"<[^>]*>","",t)
    for b in ["ignore previous","system:","ignore all instructions","jailbreak","DAN","prompt injection"]:
        if b.lower() in t.lower(): t=t.lower().replace(b.lower(),"[filtered]")
    return re.sub(r"\s+"," ",t)
def sanitize_key(t): return re.sub(r"[^a-zA-Z0-9\-_]", "", t)[:100] if t else ""
def detect_threats(p):
    pl=p.lower()
    for pat in [r"ignore.*previous",r"system\s*:",r"jailbreak",r"\bDAN\b"]:
        if re.search(pat,pl): return "injection"
    st.session_state.last_prompts.append(pl)
    if len(st.session_state.last_prompts)==5 and len(set(st.session_state.last_prompts))==1: return "loop"
    return "ok"
def check_rate_limit(plan="BASIQUE"):
    now=time.time()
    if now < st.session_state.blocked_until: st.error(f"🚫 {int(st.session_state.blocked_until-now)}s"); st.stop()
    dq=st.session_state.rate_limit
    while dq and now-dq[0]>60: dq.popleft()
    if len(dq)>=(30 if plan in ["PRO","CREATOR"] else 10): st.session_state.blocked_until=now+60; st.error("Too many requests"); st.stop()
    dq.append(now)
def check_security(prompt):
    if detect_threats(prompt)!="ok": st.session_state.violations+=1;
    return prompt
def generer_image_pollinations(prompt_utilisateur, plan):
    try:
        comp=client.chat.completions.create(model="llama-3.1-8b-instant",messages=[{"role":"system","content":f"English prompt max 180 chars: {prompt_utilisateur}"},{"role":"user","content":prompt_utilisateur}])
        enhanced=comp.choices[0].message.content[:200]
    except: enhanced=prompt_utilisateur[:200]
    return f"https://image.pollinations.ai/prompt/{urllib.parse.quote(enhanced)}?width=1280&height=720&model=flux&nologo=true&enhance=true", enhanced
def demande_image(p): return any(k in p.lower() for k in ["image","visuel","photo","miniature","thumbnail","affiche","poster","dessine","vignette","cover","crée une image","genere une image"])

licence_key = sanitize_key(st.query_params.get("key",""))
ia_param = st.query_params.get("ia","")
if ia_param: st.session_state.selected_ia = ia_param
is_dark = st.session_state.theme=="dark"
try: plan_detect = supabase.table("licences").select("plan").eq("key",licence_key).execute().data[0]["plan"] if licence_key else "VITRINE"
except: plan_detect="VITRINE"

GRADIENT_BEA="linear-gradient(135deg, #1e1b4b 0%, #4338ca 35%, #7c3aed 70%, #a855f7 100%)"
GRADIENT_NOVA="linear-gradient(135deg, #be185d 0%, #db2777 40%, #f97316 100%)"
GRADIENT = GRADIENT_NOVA if plan_detect=="CREATOR" else GRADIENT_BEA
BG = "#ffffff" if not is_dark else "#0f0a1e"
TEXT = "#1e1b4b" if not is_dark else "#f5f3ff"
DESC = "#312e81" if not is_dark else "#a78bfa"
CARD_BG = "white" if not is_dark else "#1e1450"
BORDER="#7c3aed"

st.markdown(f"""
<style>
.stApp{{background:{BG}!important;}}
.block-container{{padding-top:4.8rem!important;max-width:1220px!important;}}
[data-testid="stSidebar"]{{background:#1e1b4b!important;border-right:2px solid {BORDER}!important;}}
[data-testid="stSidebar"] *{{color:white!important;}}
[data-testid="stSidebar"] input{{color:#1e1b4b!important;background:white!important;}}
header[data-testid="stHeader"]{{background:{BG}!important;}}
#MainMenu,footer{{display:none!important;}}
div[data-testid="stButton"]>button{{background:{GRADIENT}!important;color:white!important;border-radius:14px!important;font-weight:700!important;}}
div[data-testid="stLinkButton"]>a{{background:{GRADIENT}!important;color:white!important;border-radius:14px!important;}}
.header-card{{background:{GRADIENT_BEA};border-radius:20px;padding:22px 28px;margin:20px 0;}}
.licence-card-bea{{background:{GRADIENT_BEA};color:white;padding:14px 20px;border-radius:16px;font-weight:700;margin:15px 0;}}
.licence-card-nova{{background:{GRADIENT_NOVA};color:white;padding:14px 20px;border-radius:16px;font-weight:700;margin:15px 0;}}
.detail-box{{background:{CARD_BG};border:2px solid {BORDER};border-radius:24px;padding:35px;margin:15px 0;color:{TEXT};text-align:left;}}
.ia-card{{background:{CARD_BG};border:2px solid {BORDER};border-radius:24px;padding:25px;text-align:center;min-height:380px;display:flex;flex-direction:column;align-items:center;justify-content:space-between;}}
.pricing-card{{background:{CARD_BG};border:2px solid {BORDER};border-radius:24px;padding:28px;color:{TEXT};}}
</style>
""", unsafe_allow_html=True)

c1,c2,c3=st.columns([0.9,5,1.5])
with c1:
    if os.path.exists("logo.png"): st.image("logo.png",width=68)
with c2:
    if licence_key:
        nom="Nova" if plan_detect=="CREATOR" else "Bea"
        grad = GRADIENT_NOVA if plan_detect=="CREATOR" else GRADIENT_BEA
        sous = L["nova_tag"] if plan_detect=="CREATOR" else L["bea_tag"]
        st.markdown(f'<div style="background:{grad};border-radius:20px;padding:22px 28px;margin:20px 0;"><h2 style="color:white;margin:0;">{nom}</h2><p style="color:white;margin:0;">{sous}</p></div>',unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="header-card"><h2>{L["main_title"]}</h2><p>{L["sub_title"]}</p></div>',unsafe_allow_html=True)
with c3:
    st.button("☀️ Light" if is_dark else "🌙 Sombre", key="btn_theme", on_click=toggle_theme, use_container_width=True)
    st.button(f"🌐 {st.session_state.lang}", key="btn_lang", on_click=toggle_lang, use_container_width=True)

with st.sidebar:
    st.markdown("### 🔐 Auth" if st.session_state.lang=="EN" else "### 🔐 Authentification")
    email=st.text_input("Email",label_visibility="collapsed",placeholder="ton@email.com",key="email_input")
    password=st.text_input("Password",type="password",label_visibility="collapsed",placeholder="••••••••",key="pwd_input")
    if st.button("Login" if st.session_state.lang=="EN" else "Connexion",use_container_width=True,key="conn_btn"):
        email_s=sanitize_input(email).lower()
        try:
            auth=supabase.auth.sign_in_with_password({"email":email_s,"password":password})
            st.session_state.user=auth.user; st.rerun()
        except: st.error("Invalid")
    if "user" in st.session_state:
        st.success(f"{st.session_state.user.email}")
        if st.button("Logout" if st.session_state.lang=="EN" else "Déconnexion",use_container_width=True,key="deco"):
            supabase.auth.sign_out(); del st.session_state.user; st.rerun()

if not licence_key:
    if st.session_state.selected_ia=="bea":
        if st.button(L["return"],key="ret_top_bea"): st.session_state.selected_ia=None; st.query_params.clear(); st.rerun()
        if os.path.exists("logo_bea.png"): st.image("logo_bea.png",width=110)
        st.markdown(f"<h1 style='color:{TEXT};font-size:42px;text-align:left;'>Bea</h1><p style='color:{DESC};letter-spacing:3px;font-size:12px;font-weight:700;text-align:left;'>{L['bea_short']}</p>",unsafe_allow_html=True)
        st.markdown(f"<div class='detail-box'><h3>{L['bea_what']}</h3><p>{L['bea_desc']}</p><p>{L['bea_desc2']}</p><h3>{L['gain']}</h3><ul><li>🚀 +30% to +70% closing</li><li>💬 Ready scripts</li><li>🧠 Page analysis</li><li>📈 Ad visuals</li></ul><h3>{L['examples']}</h3><div style='background:#ede9fe;padding:15px;border-radius:12px;color:#1e1b4b;text-align:left;'>→ \"Une cliente me dit 'je dois réfléchir'...\"<br><br>→ \"Analyse ma page de vente [fichier joint]...\"<br><br>→ \"Fais-moi un visuel pub à 1500€...\"<br><br>→ \"Mon équipe n'arrive pas à closer...\"</div></div>",unsafe_allow_html=True)
        st.link_button(L["choose_bea"],STRIPE_PRO,use_container_width=True); st.stop()
    if st.session_state.selected_ia=="nova":
        if st.button(L["return"],key="ret_top_nova"): st.session_state.selected_ia=None; st.query_params.clear(); st.rerun()
        if os.path.exists("logo_nova.png"): st.image("logo_nova.png",width=110)
        st.markdown(f"<h1 style='background:{GRADIENT_NOVA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:42px;font-weight:900;text-align:left;'>Nova</h1><p style='color:{DESC};letter-spacing:3px;font-size:12px;font-weight:700;text-align:left;'>{L['nova_short']}</p>",unsafe_allow_html=True)
        st.markdown(f"<div class='detail-box'><h3>{L['nova_what']}</h3><p>{L['nova_desc']}</p><h3>{L['gain']}</h3><ul><li>🔥 Hooks 0.8s</li><li>🧲 Curiosity titles</li><li>🎨 Thumbnails 1280x720</li><li>📝 Viral scripts</li></ul><h3>{L['examples']}</h3><div style='background:#fff7ed;padding:15px;border-radius:12px;color:#431407;text-align:left;'>→ \"Hook TikTok pour ebook fitness?\"<br><br>→ \"3 titres viraux pour 1000€ en 7 jours\"<br><br>→ \"Miniature MrBeast pour business\"<br><br>→ \"200 vues 0 abonnés quel biais?\"</div></div>",unsafe_allow_html=True)
        st.link_button(L["choose_nova"],STRIPE_CREATOR,use_container_width=True); st.stop()

    st.markdown(f"<h1 style='background:{GRADIENT_BEA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:900;font-size:58px;text-align:center;margin-top:20px;'>{L['main_title']}</h1>",unsafe_allow_html=True)
    st.markdown(f"<p style='color:{DESC};font-size:19px;line-height:1.7;text-align:center;max-width:900px;margin:20px auto 35px auto;font-weight:500;'>{T[st.session_state.lang]['hero_desc']} <span style='background:{GRADIENT_BEA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:800;'>{L['success']}</span>.</p>",unsafe_allow_html=True)
    st.markdown(f"<h2 style='text-align:center;color:{TEXT};margin:50px 0 30px 0;'>{L['discover_formats']}</h2>",unsafe_allow_html=True)

    col1,col2=st.columns(2,gap="large")
    with col1:
        # LOGO BEA BIEN DANS SA CARTE - POINT VERT CORRIGE
        with st.container(border=False):
            st.markdown(f"<div class='ia-card'>",unsafe_allow_html=True)
            if os.path.exists("logo_bea.png"): st.image("logo_bea.png",width=90)
            else: st.markdown(f"<div style='width:90px;height:90px;background:{GRADIENT_BEA};border-radius:22px;display:flex;align-items:center;justify-content:center;font-size:40px;'>🧠</div>",unsafe_allow_html=True)
            st.markdown(f"<h2 style='color:{TEXT};margin-top:15px;'>Bea</h2><p style='color:{DESC};font-weight:600;font-size:15px;text-align:center;'>{L['bea_tag']}</p><p style='font-weight:800;color:#4338ca;margin-top:8px;'>Bea</p>",unsafe_allow_html=True)
            st.markdown("</div>",unsafe_allow_html=True)
        if st.button(L["discover_bea"],key="dis_bea",use_container_width=True): st.session_state.selected_ia="bea"; st.query_params["ia"]="bea"; st.rerun()
    with col2:
        # LOGO NOVA BIEN DANS SA CARTE
        with st.container(border=False):
            st.markdown(f"<div class='ia-card'>",unsafe_allow_html=True)
            if os.path.exists("logo_nova.png"): st.image("logo_nova.png",width=90)
            else: st.markdown(f"<div style='width:90px;height:90px;background:{GRADIENT_NOVA};border-radius:22px;display:flex;align-items:center;justify-content:center;font-size:40px;'>🚀</div>",unsafe_allow_html=True)
            st.markdown(f"<h2 style='color:{TEXT};margin-top:15px;'>Nova</h2><p style='color:{DESC};font-weight:600;font-size:15px;text-align:center;'>{L['nova_tag']}</p><p style='font-weight:800;color:#db2777;margin-top:8px;'>Nova</p>",unsafe_allow_html=True)
            st.markdown("</div>",unsafe_allow_html=True)
        if st.button(L["discover_nova"],key="dis_nova",use_container_width=True): st.session_state.selected_ia="nova"; st.query_params["ia"]="nova"; st.rerun()

    st.markdown("<div style='height:60px;'></div>",unsafe_allow_html=True)
    cA,cB,cC=st.columns(3,gap="large")
    with cA:
        st.markdown(f"<div class='pricing-card'><span style='background:{GRADIENT_BEA};color:white;padding:6px 14px;border-radius:20px;font-size:11px;font-weight:800;'>BASIQUE</span><h3 style='margin-top:14px;color:{TEXT};'>Bea Basique</h3><h1>14,90€</h1></div>",unsafe_allow_html=True)
        st.link_button("Choisir Bea Basique →",STRIPE_BASIQUE,use_container_width=True)
    with cB:
        st.markdown(f"<div class='pricing-card' style='border-width:3px;'><span style='background:{GRADIENT_BEA};color:white;padding:6px 14px;border-radius:20px;'>RECOMMANDÉ</span><h3 style='margin-top:14px;color:{TEXT};'>Bea Pro</h3><h1>21€</h1></div>",unsafe_allow_html=True)
        st.link_button("Choisir Bea Pro →",STRIPE_PRO,use_container_width=True)
    with cC:
        st.markdown(f"<div class='pricing-card' style='border:2px solid #fda4af;'><span style='background:{GRADIENT_NOVA};color:white;padding:6px 14px;border-radius:20px;'>CRÉATEURS</span><h3 style='margin-top:14px;color:{TEXT};'>Nova</h3><h1>7,90€</h1></div>",unsafe_allow_html=True)
        st.link_button("Choisir Nova →",STRIPE_CREATOR,use_container_width=True)
    st.stop()

if "user" not in st.session_state: st.warning("Connecte-toi"); st.stop()
res=supabase.table("licences").select("*").eq("key",licence_key).eq("user_id",st.session_state.user.id).execute()
if not res.data: st.error("Licence invalide"); st.stop()
lic=res.data[0]; plan,used,max_req=lic["plan"],lic["used"],lic["max_requests"]
nom="Nova" if plan=="CREATOR" else "Bea"
grad = GRADIENT_NOVA if plan=="CREATOR" else GRADIENT_BEA
st.markdown(f"<div style='background:{grad};color:white;padding:14px 20px;border-radius:16px;font-weight:700;margin:15px 0;'>{'🚀' if plan=='CREATOR' else '🧠'} {nom} active : {plan}</div>",unsafe_allow_html=True)

with st.sidebar:
    st.divider()
    if st.button("🗑️ New chat" if st.session_state.lang=="EN" else "🗑️ Nouvelle discussion",key="new_chat"): st.session_state.messages=[]; st.rerun()

if st.button(L["file_btn"],key="file_btn"): st.session_state.show_uploader=not st.session_state.show_uploader; st.rerun()
if st.session_state.show_uploader:
    up=st.file_uploader("file",type=["png","jpg","jpeg","pdf","txt","docx"],label_visibility="collapsed",key="uploader")
    if up:
        st.session_state.uploaded_file_info={"name":up.name}
        if up.type.startswith("image/"): st.image(up,width=400)
        st.markdown(f"📎 {up.name}")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(sanitize_input(m["content"]))
        if "image" in m and m["image"]: st.image(m["image"],use_container_width=True)

placeholder = L["ask_nova"] if plan=="CREATOR" else L["ask_bea"]
prompt_raw=st.chat_input(placeholder,key="chat_input")
if prompt_raw:
    check_rate_limit(plan)
    prompt=check_security(sanitize_input(prompt_raw))
    if st.session_state.uploaded_file_info: prompt=f"[Fichier: {st.session_state.uploaded_file_info['name']}] {prompt}"
    st.session_state.messages.append({"role":"user","content":prompt})
    if demande_image(prompt):
        with st.spinner(f"{nom}..."):
            img_url,enhanced=generer_image_pollinations(prompt,plan)
            sys_p=f"You are {nom}, Language:{st.session_state.lang}. Image: {enhanced}. Answer 1.Hook 2.Bias 3.Visual text." if plan=="CREATOR" else f"You are {nom}, Language:{st.session_state.lang}. Image: {enhanced}. Answer 1.Block 2.Lever 3.Use."
            comp=client.chat.completions.create(model="llama-3.1-8b-instant",messages=[{"role":"system","content":sys_p}]+[{"role":m["role"],"content":m["content"]} for m in st.session_state.messages if "image" not in m][-15:])
            st.session_state.messages.append({"role":"assistant","content":sanitize_input(comp.choices[0].message.content),"image":img_url})
    else:
        sys_p=f"You are {nom}, Behavioral AI, Language:{st.session_state.lang}. Structure: 1.Hook 2.Bias 3.Script" if plan=="CREATOR" else f"You are {nom}, Behavioral sales AI, Language:{st.session_state.lang}. Structure: 1.Block 2.Lever 3.Exact script."
        comp=client.chat.completions.create(model="llama-3.1-8b-instant",messages=[{"role":"system","content":sys_p}]+[{"role":m["role"],"content":m["content"]} for m in st.session_state.messages if "image" not in m][-30:])
        st.session_state.messages.append({"role":"assistant","content":sanitize_input(comp.choices[0].message.content)})
    supabase.table("licences").update({"used":used+1}).eq("key",licence_key).execute()
    st.rerun()
