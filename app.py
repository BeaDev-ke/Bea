import streamlit as st
import os
import re
import time
import html
import urllib.parse
import base64
from groq import Groq
from supabase import create_client
from collections import deque

st.set_page_config(page_title="BehaviorLab AI", page_icon="logo.png", layout="wide")

STRIPE_BASIQUE="https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"
STRIPE_PRO="https://buy.stripe.com/test_cNieVea1P0c62B08523wQ00"
STRIPE_CREATOR="https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"

# SECRETS AVEC VERIF
try:
    GROQ_KEY=st.secrets["GROQ_API_KEY"]
    SUPA_URL=st.secrets["SUPABASE_URL"]
    SUPA_KEY=st.secrets.get("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_PUBLISHABLE_KEY")
    if not GROQ_KEY or len(GROQ_KEY)<20:
        st.error("⚠️ GROQ_API_KEY manquante ou invalide dans Secrets"); st.stop()
    client=Groq(api_key=GROQ_KEY)
    supabase=create_client(SUPA_URL,SUPA_KEY)
except Exception as e:
    st.error(f"Erreur Secrets: {e} - Vérifie GROQ_API_KEY, SUPABASE_URL, SUPABASE_ANON_KEY dans Manage app > Secrets")
    st.stop()

MODEL_GROQ="llama-3.3-70b-versatile" # modèle valide 2025-2026, plus de 3.1-8b-instant

for k,v in {"theme":"light","lang":"FR","messages":[],"show_uploader":False,"uploaded_file_info":None,"rate_limit":deque(),"violations":0,"blocked_until":0,"last_prompts":deque(maxlen=5),"selected_ia":None,"auth_error":None}.items():
    if k not in st.session_state: st.session_state[k]=v

def toggle_theme(): st.session_state.theme="light" if st.session_state.theme=="dark" else "dark"
def toggle_lang(): st.session_state.lang="EN" if st.session_state.lang=="FR" else "FR"

if "user" not in st.session_state:
    try:
        sess=supabase.auth.get_session()
        if sess and sess.session and sess.session.user: st.session_state.user=sess.session.user
        else:
            u=supabase.auth.get_user()
            if u and u.user: st.session_state.user=u.user
    except: pass

def get_logo_base64(path):
    if not os.path.exists(path): return None
    try:
        with open(path,"rb") as f: return base64.b64encode(f.read()).decode()
    except: return None

def sanitize_input(text):
    if not text: return ""
    text=html.escape(text.strip())[:2000]
    text=re.sub(r"<[^>]*>","",text)
    for b in ["ignore previous","system:","ignore all instructions","jailbreak","DAN","prompt injection"]:
        if b.lower() in text.lower(): text=text.lower().replace(b.lower(),"[filtered]")
    return re.sub(r"\s+"," ",text)
def sanitize_key(t): return re.sub(r"[^a-zA-Z0-9\-_]","",t)[:100] if t else ""
def detect_threats(p):
    pl=p.lower()
    for pat in [r"ignore.*previous",r"system\s*:",r"jailbreak",r"\bDAN\b"]:
        if re.search(pat,pl): return "injection"
    st.session_state.last_prompts.append(pl)
    if len(st.session_state.last_prompts)==5 and len(set(st.session_state.last_prompts))==1: return "loop"
    return "ok"
def check_rate_limit(plan="BASIQUE"):
    now=time.time()
    if now<st.session_state.blocked_until: st.error(f"🚫 {int(st.session_state.blocked_until-now)}s"); st.stop()
    dq=st.session_state.rate_limit
    while dq and now-dq[0]>60: dq.popleft()
    if len(dq)>=(30 if plan in ["PRO","CREATOR"] else 10): st.session_state.blocked_until=now+60; st.error("Trop de requêtes"); st.stop()
    dq.append(now)
def check_security(prompt):
    if detect_threats(prompt)!="ok":
        st.session_state.violations+=1
        if st.session_state.violations>=3: st.session_state.blocked_until=time.time()+300; st.error("🚫 blocage 5 min"); st.stop()
    return prompt

def generer_image_pollinations(prompt_utilisateur, plan):
    try:
        sys_en=f"English viral thumbnail prompt max 180 chars: {prompt_utilisateur}" if plan=="CREATOR" else f"English business marketing visual prompt max 180 chars: {prompt_utilisateur}"
        comp=client.chat.completions.create(model=MODEL_GROQ,messages=[{"role":"system","content":sys_en},{"role":"user","content":prompt_utilisateur}])
        enhanced=comp.choices[0].message.content[:200]
    except Exception as e:
        # si Groq fail, on utilise prompt brut pour ne pas crasher
        enhanced=prompt_utilisateur[:200]
    url=f"https://image.pollinations.ai/prompt/{urllib.parse.quote(enhanced)}?width=1280&height=720&model=flux&nologo=true&enhance=true"
    return url, enhanced

def demande_image(p): return any(k in p.lower() for k in ["image","visuel","photo","miniature","thumbnail","affiche","poster","dessine","vignette","cover","crée une image","genere une image","génère"])

T={
 "FR":{"main_title":"BehaviorLab AI","sub_title":"Les IA comportementales pour votre réussite","hero_desc":"<b>BehaviorLab AI a créé les premières IA du comportement.</b><br>Destinée à ceux qui veulent booster leur réussite nous proposons des IA qui correspondent à vos besoins. Formées dans un seul but:","success":"votre réussite","discover_formats":"Découvrir les différents formats IA","bea_tag":"L'IA qui décode tes clients et double ton closing","nova_tag":"L'IA qui propulse tes contenus et ton audience","ask_bea":"Demander à Bea...","ask_nova":"Demander à Nova...","file_btn":"📎 Glisser un fichier","return":"⬅️ Retour","discover_bea":"Découvrir Bea →","discover_nova":"Découvrir Nova →","email_label":"Adresse e-mail","pwd_label":"Mot de passe","login":"Connexion","auth_title":"Authentification","welcome_bea":"Salut, c'est Bea, ton IA de BehaviorLab AI. Contente de te retrouver. Comment je peux t'aider aujourd'hui?","welcome_nova":"Salut, c'est Nova, ton IA de BehaviorLab AI. Ravie de te voir. Comment je peux t'aider aujourd'hui?","connect_msg":"Connecte-toi pour accéder à ton IA avec ta licence","invalid":"Identifiants invalides"},
 "EN":{"main_title":"BehaviorLab AI","sub_title":"Behavioral AIs for your success","hero_desc":"<b>BehaviorLab AI created the first behavioral AIs.</b><br>For your success:","success":"your success","discover_formats":"Discover the different AI formats","bea_tag":"The AI that decodes your customers and doubles your closing","nova_tag":"The AI that boosts your content and your audience","ask_bea":"Ask Bea...","ask_nova":"Ask Nova...","file_btn":"📎 Drop a file","return":"⬅️ Back","discover_bea":"Discover Bea →","discover_nova":"Discover Nova →","email_label":"Email address","pwd_label":"Password","login":"Login","auth_title":"Authentication","welcome_bea":"Hi, it's Bea, your AI from BehaviorLab AI. Happy to see you. How can I help you today?","welcome_nova":"Hi, it's Nova, your AI from BehaviorLab AI. Happy to see you. How can I help you today?","connect_msg":"Log in to access your AI with your license","invalid":"Invalid credentials"},
}
L=T[st.session_state.lang]

licence_key=sanitize_key(st.query_params.get("key",""))
ia_param=st.query_params.get("ia","")
if ia_param: st.session_state.selected_ia=ia_param
is_dark=st.session_state.theme=="dark"
try: plan_detect=supabase.table("licences").select("plan").eq("key",licence_key).execute().data[0]["plan"] if licence_key else "VITRINE"
except: plan_detect="VITRINE"

GRADIENT_BEA="linear-gradient(135deg, #1d4ed8 0%, #4f46e5 30%, #7c3aed 60%, #c026d3 85%, #db2777 100%)"
GRADIENT_NOVA="linear-gradient(135deg, #7c3aed 0%, #db2777 50%, #f97316 100%)"
GRADIENT=GRADIENT_NOVA if plan_detect=="CREATOR" else GRADIENT_BEA

BG="#ffffff" if not is_dark else "#0f0a1e"
TEXT="#1e1b4b" if not is_dark else "#f5f3ff"
DESC="#312e81" if not is_dark else "#c4b5fd"
CARD_BG="white" if not is_dark else "#1e1450"

st.markdown(f"""
<style>
.stApp{{background:{BG}!important;}}
.block-container{{padding-top:4.8rem!important;max-width:1220px!important;}}
[data-testid="stSidebar"]{{background:#1e1b4b!important;border-right:3px solid #7c3aed!important;}}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] h3{{color:white!important;}}
.auth-label{{color:#c4b5fd!important;font-size:13px!important;font-weight:700!important;margin:12px 0 6px 0!important;display:block!important;}}
[data-testid="stSidebar"] input{{color:#1e1b4b!important;background:#fff!important;border:2px solid #a78bfa!important;border-radius:10px!important;height:44px!important;}}
header[data-testid="stHeader"]{{background:{BG}!important;}}
#MainMenu,footer{{display:none!important;}}
div[data-testid="stButton"]>button{{background:{GRADIENT}!important;color:white!important;border-radius:14px!important;font-weight:700!important;border:none!important;}}
div[data-testid="stLinkButton"]>a{{background:{GRADIENT}!important;color:white!important;border-radius:14px!important;}}
div[data-testid="stChatInput"]{{border:2px solid #7c3aed!important;border-radius:20px!important;background:{CARD_BG}!important;}}
.header-card{{background:{GRADIENT_BEA}!important;border-radius:20px;padding:22px 28px;margin:20px 0;}}
.detail-box{{background:{CARD_BG};border:2px solid #7c3aed;border-radius:24px;padding:35px;margin:15px 0;color:{TEXT};text-align:left;line-height:1.8;}}
.ia-card{{background:{CARD_BG};border:2px solid #7c3aed;border-radius:24px;padding:25px;text-align:center;min-height:400px;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;}}
.example-box{{background:{CARD_BG};border:2px solid #7c3aed;border-radius:20px;padding:22px;color:{TEXT};font-size:14px;line-height:1.7;text-align:left;}}
.logo-bea{{width:90px;height:90px;background:{GRADIENT_BEA};border-radius:22px;display:flex;align-items:center;justify-content:center;font-size:42px;margin:0 auto;}}
.logo-nova{{width:90px;height:90px;background:{GRADIENT_NOVA};border-radius:22px;display:flex;align-items:center;justify-content:center;font-size:42px;margin:0 auto;}}
.logo-bea-small{{width:60px;height:60px;background:{GRADIENT_BEA};border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:30px;}}
.logo-nova-small{{width:60px;height:60px;background:{GRADIENT_NOVA};border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:30px;}}
.gradient-title{{background:{GRADIENT_BEA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:900;}}
</style>
""",unsafe_allow_html=True)

c1,c2,c3=st.columns([0.9,5,1.5])
with c1:
    if os.path.exists("logo.png"): st.image("logo.png",width=68)
with c2:
    if licence_key:
        nom="Nova" if plan_detect=="CREATOR" else "Bea"
        grad=GRADIENT_NOVA if plan_detect=="CREATOR" else GRADIENT_BEA
        sous=L["nova_tag"] if plan_detect=="CREATOR" else L["bea_tag"]
        st.markdown(f'<div style="background:{grad};border-radius:20px;padding:22px 28px;margin:20px 0;"><h2 style="color:white;margin:0;">{nom}</h2><p style="color:white;margin:0;">{sous}</p></div>',unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="header-card"><h2>{L["main_title"]}</h2><p>{L["sub_title"]}</p></div>',unsafe_allow_html=True)
with c3:
    label_theme="☀️ Clair" if is_dark else "🌙 Sombre"
    st.button(label_theme,key="btn_theme",on_click=toggle_theme,use_container_width=True)
    st.button(f"🌐 {st.session_state.lang}",key="btn_lang",on_click=toggle_lang,use_container_width=True)

with st.sidebar:
    st.markdown(f"### 🔐 {L['auth_title']}")
    if "user" not in st.session_state:
        st.markdown(f"<span class='auth-label'>{L['email_label']}</span>",unsafe_allow_html=True)
        email=st.text_input("email",label_visibility="collapsed",placeholder="ex: contact@exemple.com",key="email_input")
        st.markdown(f"<span class='auth-label'>{L['pwd_label']}</span>",unsafe_allow_html=True)
        password=st.text_input("pwd",type="password",label_visibility="collapsed",placeholder="••••••••",key="pwd_input")
        if st.button(L["login"],use_container_width=True,key="conn_btn"):
            email_s=sanitize_input(email).lower()
            if not re.match(r"^[^@]+@[^@]+\.[^@]+$",email_s):
                st.session_state.auth_error="Email invalide"
            else:
                try:
                    auth=supabase.auth.sign_in_with_password({"email":email_s,"password":password})
                    st.session_state.user=auth.user
                    st.session_state.auth_error=None
                    st.rerun()
                except:
                    st.session_state.auth_error=L["invalid"]
        if st.session_state.auth_error: st.error(st.session_state.auth_error)
    else:
        st.success(f"Connecté: {st.session_state.user.email}")
        st.session_state.auth_error=None
        if st.button("Déconnexion" if st.session_state.lang=="FR" else "Logout",use_container_width=True,key="deco"):
            supabase.auth.sign_out()
            if "user" in st.session_state: del st.session_state.user
            st.rerun()
    st.divider()
    if st.button("🗑️ Nouvelle discussion",key="new_chat"):
        st.session_state.messages=[]; st.session_state.uploaded_file_info=None; st.rerun()

if not licence_key:
    if st.session_state.selected_ia=="bea":
        if st.button(L["return"],key="ret_top_bea"): st.session_state.selected_ia=None; st.query_params.clear(); st.rerun()
        col_logo, col_title=st.columns([0.15,0.85])
        with col_logo: st.markdown(f"<div class='logo-bea-small'>🧠</div>",unsafe_allow_html=True)
        with col_title: st.markdown(f"<h1 style='color:{TEXT};font-size:42px;margin:0;text-align:left;'>Bea</h1><p style='color:{DESC};font-size:11px;font-weight:700;text-align:left;margin:0;'>L'IA QUI DÉCODE TES CLIENTS</p>",unsafe_allow_html=True)
        left,right=st.columns([1.6,1],gap="large")
        with left: st.markdown(f"<div class='detail-box'><h1 style='font-size:32px;color:{TEXT};margin:0;'>Bea, ton IA comportementaliste pour ton entreprise.</h1><h3 style='margin-top:30px;'>Ses avantages :</h3><ul><li>🧠 Décode le non-dit</li><li>👁️ Lit le comportement humain</li><li>🎯 Active les bons leviers psycho</li><li>🗣️ Corrige ton ton de voix</li><li>📈 Double ton closing</li></ul></div>",unsafe_allow_html=True)
        with right: st.markdown(f"<div class='example-box'><b>Exemple:</b><br><i>'Je dois réfléchir'</i><br><br><b style='color:#7c3aed;'>Réponse Bea:</b><br>Blocage statu quo</div>",unsafe_allow_html=True)
        st.link_button("Choisir Bea Pro - 21€/mois →",STRIPE_PRO,use_container_width=True); st.stop()
    if st.session_state.selected_ia=="nova":
        if st.button(L["return"],key="ret_top_nova"): st.session_state.selected_ia=None; st.query_params.clear(); st.rerun()
        col_logo, col_title=st.columns([0.15,0.85])
        with col_logo: st.markdown(f"<div class='logo-nova-small'>🚀</div>",unsafe_allow_html=True)
        with col_title: st.markdown(f"<h1 style='background:{GRADIENT_NOVA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:42px;font-weight:900;margin:0;text-align:left;'>Nova</h1><p style='color:{DESC};font-size:11px;font-weight:700;text-align:left;margin:0;'>L'IA QUI PROPULSE TES CONTENUS</p>",unsafe_allow_html=True)
        left,right=st.columns([1.6,1],gap="large")
        with left: st.markdown(f"<div class='detail-box'><h1 style='font-size:32px;color:{TEXT};margin:0;'>Nova, ton IA pour exploser ton audience.</h1><h3 style='margin-top:30px;'>Ses avantages :</h3><ul><li>💡 Lumière 45° +40% watch time</li><li>👀 Contact visuel 0.8s</li><li>🎥 Cadrage qui capte</li><li>🧠 Hooks qui hackent le cerveau</li><li>🎨 Miniatures 1280x720</li></ul></div>",unsafe_allow_html=True)
        with right: st.markdown(f"<div class='example-box'><b>Exemple:</b><br><i>'Hook TikTok ebook?'</i></div>",unsafe_allow_html=True)
        st.link_button("Choisir Nova - 7,90€/mois →",STRIPE_CREATOR,use_container_width=True); st.stop()
    st.markdown(f"<h1 class='gradient-title' style='font-size:58px;text-align:center;margin-top:20px;'>{L['main_title']}</h1>",unsafe_allow_html=True)
    st.markdown(f"<p style='color:{DESC};font-size:19px;text-align:center;max-width:900px;margin:20px auto 35px auto;'>{T[st.session_state.lang]['hero_desc']} <span style='background:{GRADIENT_BEA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:800;'>{L['success']}</span>.</p>",unsafe_allow_html=True)
    st.markdown(f"<h2 style='text-align:center;color:{TEXT};margin:50px 0 30px 0;'>{T[st.session_state.lang]['discover_formats']}</h2>",unsafe_allow_html=True)
    col1,col2=st.columns(2,gap="large")
    with col1:
        st.markdown(f"<div class='ia-card'><div class='logo-bea'>🧠</div><h2 style='color:{TEXT};margin-top:15px;'>Bea</h2><p style='color:{DESC};'>{L['bea_tag']}</p></div>",unsafe_allow_html=True)
        if st.button(L["discover_bea"],key="dis_bea",use_container_width=True): st.session_state.selected_ia="bea"; st.query_params["ia"]="bea"; st.rerun()
    with col2:
        st.markdown(f"<div class='ia-card'><div class='logo-nova'>🚀</div><h2 style='color:{TEXT};margin-top:15px;'>Nova</h2><p style='color:{DESC};'>{L['nova_tag']}</p></div>",unsafe_allow_html=True)
        if st.button(L["discover_nova"],key="dis_nova",use_container_width=True): st.session_state.selected_ia="nova"; st.query_params["ia"]="nova"; st.rerun()
    cA,cB,cC=st.columns(3,gap="large")
    with cA: st.markdown(f"<div class='pricing-card'><b>Bea Basique</b><h1>14,90€</h1></div>",unsafe_allow_html=True); st.link_button("Choisir →",STRIPE_BASIQUE,use_container_width=True)
    with cB: st.markdown(f"<div class='pricing-card' style='border-width:3px;'><b>Bea Pro</b><h1>21€</h1></div>",unsafe_allow_html=True); st.link_button("Choisir →",STRIPE_PRO,use_container_width=True)
    with cC: st.markdown(f"<div class='pricing-card-nova'><b>Nova</b><h1>7,90€</h1></div>",unsafe_allow_html=True); st.link_button("Choisir →",STRIPE_CREATOR,use_container_width=True)
    st.stop()

if "user" not in st.session_state:
    if is_dark: st.warning(L["connect_msg"])
    else: st.markdown(f"<div style='background:#fffbeb;border:2px solid #f59e0b;border-radius:12px;padding:12px 16px;color:#92400e;font-weight:600;margin:15px 0;'>⚠️ {L['connect_msg']}</div>",unsafe_allow_html=True)
    st.stop()

res=supabase.table("licences").select("*").eq("key",licence_key).eq("user_id",st.session_state.user.id).execute()
if not res.data: st.error("Licence invalide"); st.stop()
lic=res.data[0]; plan,used,max_req=lic["plan"],lic["used"],lic["max_requests"]
nom="Nova" if plan=="CREATOR" else "Bea"
grad=GRADIENT_NOVA if plan=="CREATOR" else GRADIENT_BEA
welcome_key="welcome_nova" if plan=="CREATOR" else "welcome_bea"

if plan in ["PRO","CREATOR"]:
    st.markdown(f"<div style='background:{grad};color:white;padding:14px 20px;border-radius:16px;font-weight:700;margin:15px 0;'>{'🚀' if plan=='CREATOR' else '🧠'} {nom} active : {plan} — Illimité — Créée par BehaviorLab AI</div>",unsafe_allow_html=True)
else:
    if used>=max_req: st.error(f"Limite {used}/{max_req}"); st.stop()
    st.markdown(f"<div style='background:{grad};color:white;padding:14px 20px;border-radius:16px;font-weight:700;margin:15px 0;'>🧠 {nom} active : {plan} — {used}/{max_req}</div>",unsafe_allow_html=True)

if len(st.session_state.messages)==0:
    st.session_state.messages.append({"role":"assistant","content":L[welcome_key]})

if st.button(L["file_btn"],key="file_btn"): st.session_state.show_uploader=not st.session_state.show_uploader; st.rerun()
if st.session_state.show_uploader:
    up=st.file_uploader("file",type=["png","jpg","jpeg","pdf","txt","docx","mp4","mp3"],label_visibility="collapsed",key="uploader")
    if up:
        if up.size>10*1024*1024: st.error("Fichier trop lourd max 10Mo")
        else:
            st.session_state.uploaded_file_info={"name":up.name}
            if up.type.startswith("image/"): st.image(up,width=400)
            st.markdown(f"📎 {up.name}",unsafe_allow_html=True)

# AVATAR FIXE NON INVERSABLE - LOGO SEUL SANS TEXTE
for m in st.session_state.messages:
    if m.get("role")=="system": continue
    if m["role"]=="user":
        with st.chat_message("user"): st.markdown(sanitize_input(m["content"]))
    else:
        if plan=="CREATOR":
            with st.chat_message("assistant", avatar="🚀"):
                st.markdown(sanitize_input(m["content"]))
                if "image" in m and m["image"]: st.image(m["image"],use_container_width=True)
        else:
            with st.chat_message("assistant", avatar="🧠"):
                st.markdown(sanitize_input(m["content"]))
                if "image" in m and m["image"]: st.image(m["image"],use_container_width=True)

placeholder_text=L["ask_nova"] if plan=="CREATOR" else L["ask_bea"]
prompt_raw=st.chat_input(placeholder_text,key="chat_input")
if prompt_raw:
    check_rate_limit(plan)
    prompt_clean=sanitize_input(prompt_raw)
    if len(prompt_clean)<3: st.error("Trop court"); st.stop()
    prompt=check_security(prompt_clean)
    if st.session_state.uploaded_file_info: prompt=f"[Fichier: {st.session_state.uploaded_file_info['name']}] {prompt}"
    st.session_state.messages.append({"role":"user","content":prompt})
    msgs_for_groq=[{"role":mm["role"],"content":sanitize_input(mm["content"])} for mm in st.session_state.messages if mm.get("role")!="system" and "image" not in mm]
    lang_instruction=f"Réponds IMPÉRATIVEMENT en {st.session_state.lang}. Langue actuelle: {st.session_state.lang}"

    try:
        if demande_image(prompt):
            with st.spinner(f"{nom} crée ton visuel..."):
                img_url,enhanced=generer_image_pollinations(prompt,plan)
                sys_prompt=f"Tu es {nom}, ton créateur est BehaviorLab AI. {lang_instruction}. Image: {enhanced}. Si on te demande qui t'a créée: Je suis {nom}, créée par BehaviorLab AI."
                comp=client.chat.completions.create(model=MODEL_GROQ,messages=[{"role":"system","content":sys_prompt}]+msgs_for_groq[-15:])
                st.session_state.messages.append({"role":"assistant","content":sanitize_input(comp.choices[0].message.content),"image":img_url})
        else:
            sys_prompt=f"Tu es {nom}, ton créateur et développeur est BehaviorLab AI. {lang_instruction}. Tu es experte en comportement humain. Si on te demande qui t'a créée: Je suis {nom}, créée par BehaviorLab AI."
            comp=client.chat.completions.create(model=MODEL_GROQ,messages=[{"role":"system","content":sys_prompt}]+msgs_for_groq[-30:])
            st.session_state.messages.append({"role":"assistant","content":sanitize_input(comp.choices[0].message.content)})
        supabase.table("licences").update({"used":used+1}).eq("key",licence_key).execute()
        st.rerun()
    except Exception as e:
        # NE CRASH PLUS EN ROUGE - MESSAGE PROPRE
        err_str=str(e)
        if "AuthenticationError" in err_str or "401" in err_str or "api_key" in err_str.lower():
            st.error("🔑 Clé Groq invalide ou expirée. Va dans Manage app > Secrets et vérifie GROQ_API_KEY. Va sur console.groq.com pour en générer une nouvelle.")
        else:
            st.error(f"Erreur IA: {err_str[:300]}. Réessaie dans quelques secondes.")
        st.stop()
