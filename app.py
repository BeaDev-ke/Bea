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

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
def toggle_lang():
    st.session_state.lang = "EN" if st.session_state.lang == "FR" else "FR"

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
    for pat in [r"ignore.*previous",r"system\s*:",r"jailbreak",r"\bDAN\b",r"prompt injection"]:
        if re.search(pat,pl): return "injection"
    st.session_state.last_prompts.append(pl)
    if len(st.session_state.last_prompts)==5 and len(set(st.session_state.last_prompts))==1: return "loop"
    return "ok"

def check_rate_limit(plan="BASIQUE"):
    now=time.time()
    if now < st.session_state.blocked_until:
        st.error(f"🚫 Blocage {int(st.session_state.blocked_until-now)}s"); st.stop()
    dq=st.session_state.rate_limit
    while dq and now-dq[0]>60: dq.popleft()
    if len(dq)>=(30 if plan in ["PRO","CREATOR"] else 10):
        st.session_state.blocked_until=now+60; st.error("Trop de requêtes"); st.stop()
    dq.append(now)

def check_security(prompt):
    threat=detect_threats(prompt)
    if threat!="ok":
        st.session_state.violations+=1
        if st.session_state.violations>=3:
            st.session_state.blocked_until=time.time()+300; st.error(f"🚫 {threat} blocage 5 min"); st.stop()
    return prompt

def generer_image_pollinations(prompt_utilisateur, plan):
    try:
        sys_en = f"English viral thumbnail prompt max 180 chars: {prompt_utilisateur}" if plan=="CREATOR" else f"English business marketing visual prompt max 180 chars: {prompt_utilisateur}"
        comp=client.chat.completions.create(model="llama-3.1-8b-instant",messages=[{"role":"system","content":sys_en},{"role":"user","content":prompt_utilisateur}])
        enhanced=comp.choices[0].message.content[:200]
    except: enhanced=prompt_utilisateur[:200]
    url=f"https://image.pollinations.ai/prompt/{urllib.parse.quote(enhanced)}?width=1280&height=720&model=flux&nologo=true&enhance=true"
    return url, enhanced

def demande_image(p): return any(k in p.lower() for k in ["image","visuel","photo","miniature","thumbnail","affiche","poster","dessine","vignette","cover","crée une image","genere une image","génère","fais une image"])

licence_key = sanitize_key(st.query_params.get("key",""))
ia_param = st.query_params.get("ia","")
if ia_param: st.session_state.selected_ia = ia_param

is_dark = st.session_state.theme=="dark"
try: plan_detect = supabase.table("licences").select("plan").eq("key",licence_key).execute().data[0]["plan"] if licence_key else "VITRINE"
except: plan_detect="VITRINE"

# VIOLET DEGRADE DU LOGO - PLUS DE BLEU
GRADIENT_BEA="linear-gradient(135deg, #1e1b4b 0%, #4338ca 35%, #7c3aed 70%, #a855f7 100%)"
GRADIENT_NOVA="linear-gradient(135deg, #be185d 0%, #db2777 40%, #f97316 100%)"
GRADIENT = GRADIENT_NOVA if plan_detect=="CREATOR" else GRADIENT_BEA

if plan_detect in ["BASIQUE","PRO"]:
    BG = "#120c24" if is_dark else "#ffffff"
    TEXT = "#f5f3ff" if is_dark else "#1e1b4b"
    DESC = "#a78bfa" if is_dark else "#312e81"
    CARD_BG = "#1e1450" if is_dark else "white"
elif plan_detect=="CREATOR":
    BG = "#1a0f0a" if is_dark else "#fff7ed"
    TEXT = "#fff7ed" if is_dark else "#431407"
    DESC = "#fda4af" if is_dark else "#9f1239"
    CARD_BG = "#2a1508" if is_dark else "white"
else:
    BG = "#0f0a1e" if is_dark else "#ffffff"
    TEXT = "#f5f3ff" if is_dark else "#1e1b4b"
    DESC = "#a78bfa" if is_dark else "#312e81"
    CARD_BG = "#1e1450" if is_dark else "white"

BORDER = "#7c3aed"

st.markdown(f"""
<style>
.stApp{{background:{BG}!important;}}
.block-container{{padding-top:4.8rem!important;max-width:1220px!important;}}
[data-testid="stSidebar"]{{background:#1e1b4b!important;border-right:2px solid {BORDER}!important;padding-top:2rem!important;}}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] span{{color:white!important;opacity:1!important;font-weight:600!important;}}
[data-testid="stSidebar"] input{{color:#1e1b4b!important;background:white!important;font-weight:600!important;}}
[data-testid="stSidebar"] div[data-testid="stTextInput"] > div > div{{background:white!important;border:2px solid #a78bfa!important;border-radius:12px!important;}}
header[data-testid="stHeader"]{{background:{BG}!important;}}
#MainMenu,footer,div[data-testid="stDecoration"],div[data-testid="stToolbar"],div[data-testid="manage-app-button"]{{display:none!important;visibility:hidden!important;}}
div[data-testid="stButton"]>button{{background:{GRADIENT}!important;color:white!important;border:none!important;border-radius:14px!important;font-weight:700!important;}}
div[data-testid="stLinkButton"]>a{{background:{GRADIENT}!important;color:white!important;border-radius:14px!important;font-weight:700!important;}}
div[data-testid="stChatInput"]{{border:2px solid #7c3aed!important;border-radius:20px!important;background:{CARD_BG}!important;}}
.header-card{{background:{GRADIENT_BEA};border-radius:20px;padding:22px 28px;margin:20px 0;}}
.header-card h2,.header-card p{{color:white!important;margin:0;}}
.licence-card-bea{{background:{GRADIENT_BEA};color:white;padding:14px 20px;border-radius:16px;font-weight:700;margin:15px 0;}}
.licence-card-nova{{background:{GRADIENT_NOVA};color:white;padding:14px 20px;border-radius:16px;font-weight:700;margin:15px 0;}}
.pricing-card{{background:{CARD_BG};border:2px solid {BORDER};border-radius:24px;padding:28px;color:{TEXT};box-shadow:0 4px 20px rgba(124,58,237,0.15);}}
.pricing-card-nova{{background:{CARD_BG};border:2px solid #fda4af;border-radius:24px;padding:28px;color:{TEXT};box-shadow:0 4px 20px rgba(219,39,119,0.15);}}
.gradient-title{{background:{GRADIENT_BEA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:900;}}
.badge-bea{{background:{GRADIENT_BEA};color:white;padding:6px 14px;border-radius:20px;font-size:11px;font-weight:800;}}
.badge-nova{{background:{GRADIENT_NOVA};color:white;padding:6px 14px;border-radius:20px;font-size:11px;font-weight:800;}}
.file-card{{background:{CARD_BG};border:2px dashed #7c3aed;border-radius:16px;padding:12px 16px;margin:10px 0;color:{TEXT};}}
.detail-box{{background:{CARD_BG};border:2px solid {BORDER};border-radius:24px;padding:35px;margin:30px 0;color:{TEXT};line-height:1.8;text-align:left;}}
.ia-card{{background:{CARD_BG};border:2px solid {BORDER};border-radius:24px;padding:30px;text-align:center;min-height:320px;}}
.ia-card p.desc{{color:{DESC}!important;font-weight:600!important;opacity:1!important;font-size:15px!important;margin-top:10px!important;}}
</style>
""", unsafe_allow_html=True)

c1,c2,c3=st.columns([0.9,5,1.5])
with c1:
    if os.path.exists("logo.png"): st.image("logo.png",width=68)
with c2:
    if licence_key:
        nom="Nova" if plan_detect=="CREATOR" else "Bea"
        css="header-card" if plan_detect!="CREATOR" else "header-card"
        sous="L'IA qui propulse tes contenus et ton audience" if plan_detect=="CREATOR" else "L'IA qui décode le comportement de tes clients"
        grad = GRADIENT_NOVA if plan_detect=="CREATOR" else GRADIENT_BEA
        st.markdown(f'<div style="background:{grad};border-radius:20px;padding:22px 28px;margin:20px 0;"><h2 style="color:white;margin:0;">{nom}</h2><p style="color:white;margin:0;">{sous}</p></div>',unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="header-card"><h2>BehaviorLab AI</h2><p>Les IA comportementales pour votre réussite</p></div>',unsafe_allow_html=True)
with c3:
    st.button("☀️ Mode clair" if is_dark else "🌙 Mode sombre", key="btn_theme", on_click=toggle_theme, use_container_width=True)
    st.button(f"🌐 {st.session_state.lang}", key="btn_lang", on_click=toggle_lang, use_container_width=True)

with st.sidebar:
    st.markdown("### 🔐 Authentification")
    st.markdown("<p style='color:white;font-size:13px;'>Email</p>",unsafe_allow_html=True)
    email=st.text_input("Email",label_visibility="collapsed",placeholder="ton@email.com",key="email_input")
    st.markdown("<p style='color:white;font-size:13px;margin-top:10px;'>Mot de passe</p>",unsafe_allow_html=True)
    password=st.text_input("Mot de passe",type="password",label_visibility="collapsed",placeholder="••••••••",key="pwd_input")
    if st.button("Connexion",use_container_width=True,key="conn_btn"):
        email_s=sanitize_input(email).lower()
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$",email_s): st.error("Email invalide")
        else:
            try:
                auth=supabase.auth.sign_in_with_password({"email":email_s,"password":password})
                st.session_state.user=auth.user; st.rerun()
            except: st.error("Identifiants invalides")
    if "user" in st.session_state:
        st.success(f"Connecté: {st.session_state.user.email}")
        if st.button("Déconnexion",use_container_width=True,key="deco"):
            supabase.auth.sign_out(); del st.session_state.user; st.rerun()

if not licence_key:
    if st.session_state.selected_ia=="bea":
        c = st.columns([1,6])[0]
        if os.path.exists("logo_bea.png"): c.image("logo_bea.png",width=110)
        else: c.markdown(f"<div style='width:100px;height:100px;background:{GRADIENT_BEA};border-radius:22px;display:flex;align-items:center;justify-content:center;font-size:45px;'>🧠</div>",unsafe_allow_html=True)
        st.markdown(f"<h1 style='text-align:left;color:{TEXT};font-size:42px;'>Bea</h1><p style='text-align:left;color:{DESC};letter-spacing:3px;font-size:12px;font-weight:700;'>L'IA QUI DÉCODE TES CLIENTS</p>",unsafe_allow_html=True)
        st.markdown(f"""
        <div class='detail-box'>
        <h3>Bea, c'est quoi exactement?</h3>
        <p>Bea est la première intelligence artificielle comportementale entraînée sur plus de 10 000 situations de vente réelles. Elle ne te donne pas des conseils génériques, elle décrypte le comportement humain derrière chaque objection.</p>
        <h3 style='margin-top:25px;'>Ce qu'elle peut te faire gagner :</h3>
        <ul style='text-align:left;'>
        <li>🚀 +30% à +70% de taux de closing en 30 jours</li>
        <li>💬 Scripts prêts à l'emploi pour chaque objection</li>
        <li>🧠 Analyse de tes pages, messages, vocaux clients</li>
        <li>📈 Visuels publicitaires qui activent les biais cognitifs</li>
        <li>🔒 Tu arrêtes de douter en vente</li>
        </ul>
        <h3>Exemples concrets à lui demander :</h3>
        <div style='background:{"#1e1b4b" if is_dark else "#ede9fe"};padding:15px;border-radius:12px;color:{TEXT};text-align:left;font-weight:500;'>
        → "Une cliente me dit 'je dois réfléchir' alors qu'elle était chaude, que répondre?"<br><br>
        → "Analyse ma page de vente [fichier joint], pourquoi ça ne convertit pas?"<br><br>
        → "Fais-moi un visuel pub pour mon offre à 1500€ qui stoppe le scroll"<br><br>
        → "Mon équipe n'arrive pas à closer, quel management mettre en place?"
        </div>
        </div>
        """,unsafe_allow_html=True)
        if st.button("⬅️ Retour",key="ret_bea"): st.session_state.selected_ia=None; st.query_params.clear(); st.rerun()
        st.link_button("Choisir Bea Pro - 21€/mois →",STRIPE_PRO,use_container_width=True); st.stop()

    if st.session_state.selected_ia=="nova":
        c = st.columns([1,6])[0]
        if os.path.exists("logo_nova.png"): c.image("logo_nova.png",width=110)
        else: c.markdown(f"<div style='width:100px;height:100px;background:{GRADIENT_NOVA};border-radius:22px;display:flex;align-items:center;justify-content:center;font-size:45px;'>🚀</div>",unsafe_allow_html=True)
        st.markdown(f"<h1 style='text-align:left;background:{GRADIENT_NOVA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:42px;font-weight:900;'>Nova</h1><p style='text-align:left;color:{DESC};letter-spacing:3px;font-size:12px;font-weight:700;'>L'IA QUI PROPULSE TES CONTENUS ET TON AUDIENCE</p>",unsafe_allow_html=True)
        st.markdown(f"""
        <div class='detail-box'>
        <h3>Nova, c'est quoi?</h3>
        <p>Nova est l'IA des créateurs qui veulent percer. Elle maîtrise les 12 biais cognitifs qui font qu'une vidéo explose ou flop. Elle ne te donne pas juste une idée, elle te donne le hook exact, le script mot à mot et le visuel qui va avec.</p>
        <h3 style='margin-top:25px;'>Ce qu'elle peut te faire gagner :</h3>
        <ul style='text-align:left;'>
        <li>🔥 Hooks TikTok / Reels qui captent en 0.8s</li>
        <li>🧲 Titres qui déclenchent le biais de curiosité</li>
        <li>🎨 Miniatures YouTube 1280x720 Pollinations ultra réalistes</li>
        <li>📝 Scripts viraux prêts à poster</li>
        <li>💸 Transformer tes vues en abonnés et en clients</li>
        </ul>
        <h3>Exemples concrets à lui demander :</h3>
        <div style='background:{"#2a1508" if is_dark else "#fff7ed"};padding:15px;border-radius:12px;color:{TEXT};text-align:left;font-weight:500;'>
        → "Comment faire un hook TikTok qui explose pour vendre mon ebook fitness?"<br><br>
        → "Donne-moi 3 titres viraux pour ma vidéo 'comment gagner 1000€ en 7 jours'"<br><br>
        → "Génère-moi une miniature YouTube style MrBeast pour ma vidéo business"<br><br>
        → "J'ai 200 vues, 0 abonnés, quel biais cognitif activer?"
        </div>
        </div>
        """,unsafe_allow_html=True)
        if st.button("⬅️ Retour",key="ret_nova"): st.session_state.selected_ia=None; st.query_params.clear(); st.rerun()
        st.link_button("Choisir Nova - 7,90€/mois →",STRIPE_CREATOR,use_container_width=True); st.stop()

    st.markdown(f"<h1 class='gradient-title' style='font-size:58px;text-align:center;margin-top:20px;'>BehaviorLab AI</h1>",unsafe_allow_html=True)
    st.markdown(f"<p style='color:{DESC};font-size:19px;line-height:1.7;text-align:center;max-width:900px;margin:20px auto 35px auto;font-weight:500;'><b style='color:{TEXT};'>BehaviorLab AI a créé les premières intelligences artificielles du comportement.</b><br>Destinée à ceux qui veulent booster leur réussite nous proposons des intelligences artificielles qui correspondent à vos besoins. Que ce soit pour les entreprises qui veulent augmenter leur chiffre d'affaires ou les individus qui veulent se lancer dans la création de contenus nos intelligences artificielles sont formées dans un seul but: <span style='background:{GRADIENT_BEA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:800;'>votre réussite</span>.</p>",unsafe_allow_html=True)
    st.markdown(f"<h2 style='text-align:center;color:{TEXT};margin:50px 0 30px 0;'>Découvrir les différents formats IA</h2>",unsafe_allow_html=True)
    col1,col2=st.columns(2,gap="large")
    with col1:
        if os.path.exists("logo_bea.png"): st.image("logo_bea.png",width=90)
        else: st.markdown(f"<div style='width:90px;height:90px;background:{GRADIENT_BEA};border-radius:22px;margin:0 auto;display:flex;align-items:center;justify-content:center;font-size:40px;'>🧠</div>",unsafe_allow_html=True)
        st.markdown(f"<div class='ia-card'><h2 style='color:{TEXT};'>Bea</h2><p class='desc'>L'IA qui décode tes clients et double ton closing</p><p style='font-weight:800;color:#4338ca;margin-top:12px;'>Bea</p></div>",unsafe_allow_html=True)
        if st.button("Découvrir Bea →",key="dis_bea",use_container_width=True): st.session_state.selected_ia="bea"; st.query_params["ia"]="bea"; st.rerun()
    with col2:
        if os.path.exists("logo_nova.png"): st.image("logo_nova.png",width=90)
        else: st.markdown(f"<div style='width:90px;height:90px;background:{GRADIENT_NOVA};border-radius:22px;margin:0 auto;display:flex;align-items:center;justify-content:center;font-size:40px;'>🚀</div>",unsafe_allow_html=True)
        st.markdown(f"<div class='ia-card'><h2 style='color:{TEXT};'>Nova</h2><p class='desc'>L'IA qui propulse tes contenus et ton audience</p><p style='font-weight:800;color:#db2777;margin-top:12px;'>Nova</p></div>",unsafe_allow_html=True)
        if st.button("Découvrir Nova →",key="dis_nova",use_container_width=True): st.session_state.selected_ia="nova"; st.query_params["ia"]="nova"; st.rerun()
    st.markdown("<div style='height:60px;'></div>",unsafe_allow_html=True)
    cA,cB,cC=st.columns(3,gap="large")
    with cA:
        st.markdown(f"<div class='pricing-card'><span class='badge-bea'>BASIQUE</span><h3 style='margin-top:14px;color:{TEXT};'>Bea Basique</h3><h1 style='color:{TEXT};'>14,90€</h1><div style='line-height:2;font-size:14px;margin-top:10px;color:{TEXT};'>✓ 12 requêtes / mois<br>✓ Blocages d'achat<br>✓ Scripts comportementaux<br>✓ Management<br>✓ Historique</div></div>",unsafe_allow_html=True)
        st.link_button("Choisir Bea Basique →",STRIPE_BASIQUE,use_container_width=True)
    with cB:
        st.markdown(f"<div class='pricing-card' style='border-width:3px;'><span class='badge-bea'>RECOMMANDÉ</span><h3 style='margin-top:14px;color:{TEXT};'>Bea Pro</h3><h1 style='color:{TEXT};'>21€</h1><div style='line-height:2;font-size:14px;margin-top:10px;color:{TEXT};'>✓ Requêtes illimitées<br>✓ Analyse de fichiers<br>✓ Visuels pub Pollinations<br>✓ Scripts avancés<br>✓ Nouveautés</div></div>",unsafe_allow_html=True)
        st.link_button("Choisir Bea Pro →",STRIPE_PRO,use_container_width=True)
    with cC:
        st.markdown(f"<div class='pricing-card-nova'><span class='badge-nova'>CRÉATEURS</span><h3 style='margin-top:14px;color:{TEXT};'>Nova</h3><h1 style='color:{TEXT};'>7,90€</h1><div style='line-height:2;font-size:14px;margin-top:10px;color:{TEXT};'>✓ Biais cognitifs<br>✓ Titres qui captent<br>✓ Hooks TikTok<br>✓ Scripts viraux<br>✓ Visuels 1280x720</div></div>",unsafe_allow_html=True)
        st.link_button("Choisir Nova →",STRIPE_CREATOR,use_container_width=True)
    st.stop()

if "user" not in st.session_state: st.warning("Connecte-toi pour accéder à ton IA"); st.stop()
res=supabase.table("licences").select("*").eq("key",licence_key).eq("user_id",st.session_state.user.id).execute()
if not res.data: st.error("Licence invalide"); st.stop()
lic=res.data[0]; plan,used,max_req=lic["plan"],lic["used"],lic["max_requests"]
nom="Nova" if plan=="CREATOR" else "Bea"
card_class="licence-card-nova" if plan=="CREATOR" else "licence-card-bea"
grad = GRADIENT_NOVA if plan=="CREATOR" else GRADIENT_BEA
st.markdown(f"<div style='background:{grad};color:white;padding:14px 20px;border-radius:16px;font-weight:700;margin:15px 0;'>{'🚀' if plan=='CREATOR' else '🧠'} {nom} active : {plan} — {'illimité' if plan in ['PRO','CREATOR'] else f'{used}/{max_req}'}</div>",unsafe_allow_html=True)

with st.sidebar:
    st.divider(); st.markdown(f"**Historique {nom}**")
    for m in reversed(st.session_state.messages[-15:]):
        if m["role"]=="user": st.markdown(f"💬 {sanitize_input(m['content'])[:35]}...")
    if st.button("🗑️ Nouvelle discussion",key="new_chat"): st.session_state.messages=[]; st.session_state.uploaded_file_info=None; st.rerun()

if st.button("📎 Glisser un fichier",key="file_btn"): st.session_state.show_uploader=not st.session_state.show_uploader; st.rerun()
if st.session_state.show_uploader:
    up=st.file_uploader("Glisse un fichier",type=["png","jpg","jpeg","pdf","txt","docx","mp4","mp3"],label_visibility="collapsed",key="uploader")
    if up:
        if up.size>10*1024*1024: st.error("Fichier trop lourd max 10Mo")
        else:
            st.session_state.uploaded_file_info={"name":up.name,"type":up.type}
            if up.type.startswith("image/"): st.image(up,width=400)
            st.markdown(f"<div class='file-card'>📎 {up.name} - Demande à {nom} de l'analyser</div>",unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(sanitize_input(m["content"]))
        if "image" in m and m["image"]: st.image(m["image"],use_container_width=True)

prompt_raw=st.chat_input(f"Demander à {nom}...",key="chat_input")
if prompt_raw:
    check_rate_limit(plan)
    prompt_clean=sanitize_input(prompt_raw)
    if len(prompt_clean)<3: st.error("Trop court"); st.stop()
    prompt=check_security(prompt_clean)
    if st.session_state.uploaded_file_info: prompt=f"[Fichier: {st.session_state.uploaded_file_info['name']}] {prompt}"
    st.session_state.messages.append({"role":"user","content":prompt})
    if demande_image(prompt):
        with st.spinner(f"{nom} crée ton visuel..."):
            img_url,enhanced=generer_image_pollinations(prompt,plan)
            sys_p=f"Tu es {nom}, IA BehaviorLab. Image générée: {enhanced}. Réponds avec 1.Hook 2.Biais 3.Texte visuel." if plan=="CREATOR" else f"Tu es {nom}, IA comportementaliste. Image: {enhanced}. Réponds 1.Blocage 2.Levier 3.Utilisation."
            comp=client.chat.completions.create(model="llama-3.1-8b-instant",messages=[{"role":"system","content":sys_p}]+[{"role":m["role"],"content":sanitize_input(m["content"])} for m in st.session_state.messages if "image" not in m][-15:])
            st.session_state.messages.append({"role":"assistant","content":sanitize_input(comp.choices[0].message.content),"image":img_url})
    else:
        sys_p=f"Tu es {nom}, IA créateur. Langue:{st.session_state.lang}. Structure: 1.Hook 2.Biais 3.Script exact." if plan=="CREATOR" else f"Tu es {nom}, IA comportementaliste. Langue:{st.session_state.lang}. Structure: 1.Blocage 2.Levier 3.Script exact."
        comp=client.chat.completions.create(model="llama-3.1-8b-instant",messages=[{"role":"system","content":sys_p}]+[{"role":m["role"],"content":sanitize_input(m["content"])} for m in st.session_state.messages if "image" not in m][-30:])
        st.session_state.messages.append({"role":"assistant","content":sanitize_input(comp.choices[0].message.content)})
    supabase.table("licences").update({"used":used+1}).eq("key",licence_key).execute()
    st.rerun()
