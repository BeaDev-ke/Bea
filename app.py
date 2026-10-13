import streamlit as st
import os
import re
import time
import html
import io
import base64
from groq import Groq
from supabase import create_client
from collections import deque
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Bea - BehaviorLab AI", page_icon="logo.png", layout="wide")

STRIPE_BASIQUE = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"
STRIPE_PRO = "https://buy.stripe.com/test_cNieVea1P0c62B08523wQ00"

GROQ_KEY = st.secrets["GROQ_API_KEY"]
SUPA_URL = st.secrets["SUPABASE_URL"]
SUPA_KEY = st.secrets.get("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_PUBLISHABLE_KEY")
client = Groq(api_key=GROQ_KEY)
supabase = create_client(SUPA_URL, SUPA_KEY)

# MODELE LE PLUS RAPIDE AU MONDE - 300 TOKENS/SEC
MODEL_RAPIDE = "llama-3.1-8b-instant"

for k,v in {
    "theme":"light","lang":"FR","messages":[],"show_uploader":False,
    "uploaded_file_info":None,"rate_limit":deque(),"violations":0,
    "blocked_until":0,"last_prompts":deque(maxlen=5),"selected_ia":None,"auth_error":None
}.items():
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

def sanitize_input(text):
    if not text: return ""
    text=html.escape(text.strip())[:2000]
    text=re.sub(r"<[^>]*>","",text)
    for b in ["ignore previous","system:","ignore all instructions","jailbreak","DAN"]:
        if b.lower() in text.lower(): text=text.lower().replace(b.lower(),"[filtered]")
    return re.sub(r"\s+"," ",text)
def sanitize_key(t): return re.sub(r"[^a-zA-Z0-9\-_]","",t)[:100] if t else ""
def check_rate_limit(plan="BASIQUE"):
    now=time.time()
    if now<st.session_state.blocked_until: st.error(f"🚫 {int(st.session_state.blocked_until-now)}s"); st.stop()
    dq=st.session_state.rate_limit
    while dq and now-dq[0]>60: dq.popleft()
    if len(dq)>=(30 if plan=="PRO" else 10): st.session_state.blocked_until=now+60; st.error("Trop de requêtes"); st.stop()
    dq.append(now)

def generer_apercu_paysage(texte_modif):
    W,H=1280,720
    img=Image.new("RGB",(W,H),(18,18,40))
    draw=ImageDraw.Draw(img)
    try:
        font_title=ImageFont.truetype("DejaVuSans-Bold.ttf",34)
        font_text=ImageFont.truetype("DejaVuSans.ttf",20)
        font_sub=ImageFont.truetype("DejaVuSans-Bold.ttf",22)
    except:
        font_title=ImageFont.load_default()
        font_text=ImageFont.load_default()
        font_sub=ImageFont.load_default()
    for y in range(90):
        r=int(100+y*0.8); g=int(50+y*0.3); b=int(255-y*0.5)
        draw.line([(0,y),(W,y)],fill=(r,g,b))
    draw.text((30,22),"Bea - BehaviorLab AI - Aperçu 1280x720",font=font_title,fill="white")
    draw.rectangle([30,120,W-30,H-30],fill=(35,35,70),outline=(120,60,255),width=3)
    draw.rectangle([50,140,W-50,200],fill=(100,50,255))
    draw.text((70,152),"Aperçu client - format ordinateur",font=font_sub,fill="white")
    draw.text((60,230),f"Demande: {texte_modif[:110]}",font=font_text,fill="white")
    draw.text((60,270),"=> Visuel Pillow local, sans Pollination",font=font_text,fill="#AAAAFF")
    draw.text((60,320),"=> 1280x720 paysage",font=font_text,fill="#AAAAFF")
    return img

T={
 "FR":{"main_title":"BehaviorLab AI","sub_title":"L'IA comportementale pour votre réussite","hero_desc":"<b>BehaviorLab AI a créé la première IA du comportement.</b><br>Pensée pour ceux qui veulent booster leur réussite, elle comprend vos blocages et vous donne quoi dire exactement pour débloquer. Un seul but:","success":"votre réussite","discover_formats":"Découvrir Bea","bea_tag":"L'IA qui décode tes clients et double ton closing","ask_bea":"Demander à Bea...","file_btn":"📎 Glisser un fichier","return":"⬅️","discover_bea":"Découvrir Bea →","email_label":"Adresse e-mail","pwd_label":"Mot de passe","login":"Connexion","auth_title":"Authentification","welcome_bea":"Salut, c'est Bea, ton IA créée par BehaviorLab AI. Contente de te retrouver ici. Comment je peux t'aider aujourd'hui?","connect_msg":"Connecte-toi pour accéder à Bea avec ta licence","invalid":"Identifiants invalides"},
 "EN":{"main_title":"BehaviorLab AI","sub_title":"Behavioral AI for your success","hero_desc":"<b>BehaviorLab AI created the first behavioral AI.</b><br>For your success:","success":"your success","discover_formats":"Discover Bea","bea_tag":"The AI that decodes your customers and doubles your closing","ask_bea":"Ask Bea...","file_btn":"📎 Drop a file","return":"⬅️","discover_bea":"Discover Bea →","email_label":"Email address","pwd_label":"Password","login":"Login","auth_title":"Authentication","welcome_bea":"Hi, it's Bea, your AI from BehaviorLab AI. How can I help you today?","connect_msg":"Log in to access Bea","invalid":"Invalid credentials"},
}
L=T[st.session_state.lang]

licence_key=sanitize_key(st.query_params.get("key",""))
ia_param=st.query_params.get("ia","")
if ia_param: st.session_state.selected_ia=ia_param
is_dark=st.session_state.theme=="dark"
try: plan_detect=supabase.table("licences").select("plan").eq("key",licence_key).execute().data[0]["plan"] if licence_key else "VITRINE"
except: plan_detect="VITRINE"

GRADIENT_BEA="linear-gradient(135deg, #1d4ed8 0%, #4f46e5 30%, #7c3aed 60%, #c026d3 85%, #db2777 100%)"
BG="#ffffff" if not is_dark else "#0f0a1e"
TEXT="#1e1b4b" if not is_dark else "#f5f3ff"
DESC="#312e81" if not is_dark else "#c4b5fd"
CARD_BG="white" if not is_dark else "#1e1450"

st.markdown(f"""
<style>
.stApp{{background:{BG}!important;}}
.block-container{{padding-top:1.2rem!important;max-width:1220px!important;}}
[data-testid="stSidebar"]{{background:#1e1b4b!important;border-right:3px solid #7c3aed!important;}}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] h3{{color:white!important;}}
.auth-label{{color:#c4b5fd!important;font-size:13px!important;font-weight:700!important;margin:12px 0 6px 0!important;display:block!important;}}
[data-testid="stSidebar"] input{{color:#1e1b4b!important;background:#fff!important;border:2px solid #a78bfa!important;border-radius:10px!important;height:44px!important;}}
header[data-testid="stHeader"]{{background:{BG}!important;}}
#MainMenu,footer{{display:none!important;}}
div[data-testid="stButton"]>button{{background:{GRADIENT_BEA}!important;color:white!important;border-radius:14px!important;font-weight:700!important;border:none!important;}}
div[data-testid="stLinkButton"]>a{{background:{GRADIENT_BEA}!important;color:white!important;border-radius:14px!important;}}
div[data-testid="stChatInput"]{{border:2px solid #7c3aed!important;border-radius:20px!important;background:{CARD_BG}!important;}}
div[data-testid="stChatMessage"]{{background:{CARD_BG}!important;border:1px solid #e9d5ff!important;border-radius:18px!important;}}
div[data-testid="stChatMessage"] p, div[data-testid="stChatMessage"] span{{color:{TEXT}!important;opacity:1!important;}}
.header-card{{background:{GRADIENT_BEA}!important;border-radius:20px;padding:22px 28px;margin:10px 0 20px 0;}}
.detail-box{{background:{CARD_BG};border:2px solid #7c3aed;border-radius:24px;padding:35px;margin:15px 0;color:{TEXT};text-align:left;line-height:1.8;}}
.example-box{{background:{CARD_BG};border:2px solid #7c3aed;border-radius:20px;padding:22px;color:{TEXT};font-size:14px;line-height:1.7;text-align:left;}}
.logo-bea{{width:90px;height:90px;background:{GRADIENT_BEA};border-radius:22px;display:flex;align-items:center;justify-content:center;font-size:42px;margin:0 auto;}}
.logo-bea-small{{width:60px;height:60px;background:{GRADIENT_BEA};border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:30px;}}
.gradient-title{{background:{GRADIENT_BEA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:900;}}
</style>
""",unsafe_allow_html=True)

# FLECHE RETOUR TOUJOURS EN HAUT A GAUCHE
if st.session_state.selected_ia:
    c_back,c_space=st.columns([0.08,0.92])
    with c_back:
        if st.button("⬅️",key="back_arrow_fixed",help="Retour"):
            st.session_state.selected_ia=None
            st.query_params.clear()
            st.rerun()

c1,c2,c3=st.columns([0.9,5,1.5])
with c1:
    if os.path.exists("logo.png"): st.image("logo.png",width=68)
with c2:
    if licence_key:
        st.markdown(f'<div style="background:{GRADIENT_BEA};border-radius:20px;padding:22px 28px;margin:20px 0;"><h2 style="color:white;margin:0;">Bea</h2><p style="color:white;margin:0;">{L["bea_tag"]}</p></div>',unsafe_allow_html=True)
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
        if st.button("Déconnexion" if st.session_state.lang=="FR" else "Logout",use_container_width=True,key="deco"):
            supabase.auth.sign_out()
            if "user" in st.session_state: del st.session_state.user
            st.rerun()
    st.divider()
    if st.session_state.messages:
        st.markdown("**Historique**")
        for m in reversed(st.session_state.messages[-10:]):
            if m["role"]=="user": st.markdown(f"💬 {sanitize_input(m['content'])[:35]}...")
    if st.button("🗑️ Nouvelle discussion",key="new_chat"):
        st.session_state.messages=[]; st.rerun()

if not licence_key:
    if st.session_state.selected_ia=="bea":
        col_logo, col_title=st.columns([0.15,0.85])
        with col_logo: st.markdown(f"<div class='logo-bea-small'>🧠</div>",unsafe_allow_html=True)
        with col_title: st.markdown(f"<h1 style='color:{TEXT};font-size:42px;margin:0;text-align:left;'>Bea</h1><p style='color:{DESC};font-size:11px;font-weight:700;text-align:left;margin:0;'>L'IA QUI DÉCODE TES CLIENTS</p>",unsafe_allow_html=True)
        left,right=st.columns([1.6,1],gap="large")
        with left:
            st.markdown(f"""
            <div class='detail-box'>
            <h1 style='font-size:32px;color:{TEXT};margin:0;'>Bea, ton IA comportementaliste pour ton entreprise.</h1>
            <p style='margin-top:15px;'>BehaviorLab AI a créé la première IA du comportement. Développée par BehaviorLab AI, entraînée sur 10 000 situations de vente réelles. Elle est là pour un seul but: ta réussite.</p>
            <h3 style='margin-top:25px;'>Ses avantages :</h3>
            <ul>
            <li>💰 <b>Tu doubles ton taux de closing</b> : +30% à +70% de ventes en plus en 30 jours sans prospecter plus, juste en disant les bonnes phrases</li>
            <li>⏱️ <b>Tu gagnes 10h par semaine</b> : fini les heures à chercher quoi répondre, elle te donne le script exact mot pour mot</li>
            <li>🤝 <b>Tu fidélises tes clients</b> : ils se sentent compris et rassurés, ils reviennent et te recommandent</li>
            <li>🧘 <b>Tu stresses moins en vente</b> : tu sais pourquoi ils disent non et tu as la réponse qui débloque, tu es serein en call</li>
            <li>📈 <b>Tu augmentes ton panier moyen</b> : tes clients achètent plus cher parce qu'ils ont confiance en toi</li>
            </ul>
            <p style='margin-top:20px;'><b>Créée par BehaviorLab AI - IA du comportement</b></p>
            </div>
            """,unsafe_allow_html=True)
        with right:
            st.markdown(f"<div class='example-box'><b>Exemple de conversation :</b><br><i>'Une cliente intéressée me dit qu'elle doit réfléchir alors qu'elle était chaude'</i><br><br><b style='color:#7c3aed;'>Réponse Bea :</b><br><b>Ce que tu gagnes:</b> tu ne perds plus cette cliente, tu la fais revenir et closer.<br><b>Blocage:</b> peur de se tromper.<br><b>À dire:</b> 'Je comprends totalement. Une cliente comme toi me disait pareil...'</div>",unsafe_allow_html=True)
        st.link_button("Choisir Bea Pro - 21€/mois →",STRIPE_PRO,use_container_width=True)
        st.stop()

    st.markdown(f"<h1 class='gradient-title' style='font-size:58px;text-align:center;margin-top:20px;'>{L['main_title']}</h1>",unsafe_allow_html=True)
    st.markdown(f"<p style='color:{DESC};font-size:19px;text-align:center;max-width:900px;margin:20px auto 35px auto;'>{T[st.session_state.lang]['hero_desc']} <span style='background:{GRADIENT_BEA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:800;'>{L['success']}</span>.</p>",unsafe_allow_html=True)
    st.markdown(f"<h2 style='text-align:center;color:{TEXT};margin:50px 0 30px 0;'>{L['discover_formats']}</h2>",unsafe_allow_html=True)
    col1,col2=st.columns(2,gap="large")
    with col1:
        st.markdown(f"<div class='ia-card'><div class='logo-bea'>🧠</div><h2 style='color:{TEXT};margin-top:15px;'>Bea</h2><p style='color:{DESC};'>{L['bea_tag']}</p><p style='font-weight:800;color:#4338ca;margin-top:10px;'>Bea</p></div>",unsafe_allow_html=True)
        if st.button(L["discover_bea"],key="dis_bea",use_container_width=True): st.session_state.selected_ia="bea"; st.query_params["ia"]="bea"; st.rerun()
    with col2:
        st.markdown(f"<div class='ia-card' style='opacity:0.6;'><div class='logo-bea'>🚀</div><h2 style='color:{TEXT};margin-top:15px;'>Nova (bientôt)</h2><p style='color:{DESC};'>L'IA qui propulse tes contenus</p></div>",unsafe_allow_html=True)
    cA,cB=st.columns(2,gap="large")
    with cA: st.markdown(f"<div class='pricing-card'><b>Bea Basique</b><h1>14,90€</h1><div style='line-height:2;font-size:14px;'>✓ 12 requêtes / mois<br>✓ Analyse des blocages d'achat<br>✓ Scripts de vente<br>✓ Management d'équipe<br>✓ Historique complet</div></div>",unsafe_allow_html=True); st.link_button("Choisir Bea Basique →",STRIPE_BASIQUE,use_container_width=True)
    with cB: st.markdown(f"<div class='pricing-card' style='border-width:3px;'><b>Bea Pro</b><h1>21€</h1><div style='line-height:2;font-size:14px;'>✓ <b>Requêtes illimitées</b><br>✓ Analyse de fichiers + Pillow 1280x720<br>✓ Visuels pro Pillow<br>✓ Scripts avancés<br>✓ Toutes les nouveautés</div></div>",unsafe_allow_html=True); st.link_button("Choisir Bea Pro →",STRIPE_PRO,use_container_width=True)
    st.stop()

if "user" not in st.session_state:
    if is_dark: st.warning(L["connect_msg"])
    else: st.markdown(f"<div style='background:#fffbeb;border:2px solid #f59e0b;border-radius:12px;padding:12px 16px;color:#92400e;font-weight:600;margin:15px 0;'>⚠️ {L['connect_msg']}</div>",unsafe_allow_html=True)
    st.stop()

res=supabase.table("licences").select("*").eq("key",licence_key).eq("user_id",st.session_state.user.id).execute()
if not res.data: st.error("Licence invalide"); st.stop()
lic=res.data[0]; plan,used,max_req=lic["plan"],lic["used"],lic["max_requests"]
nom="Bea"

if plan=="PRO":
    st.markdown(f"<div style='background:{GRADIENT_BEA};color:white;padding:14px 20px;border-radius:16px;font-weight:700;margin:15px 0;'>🧠 {nom} active : {plan} — Illimité — Créée par BehaviorLab AI — {MODEL_RAPIDE}</div>",unsafe_allow_html=True)
else:
    if used>=max_req: st.error(f"Limite {used}/{max_req}"); st.stop()
    st.markdown(f"<div style='background:{GRADIENT_BEA};color:white;padding:14px 20px;border-radius:16px;font-weight:700;margin:15px 0;'>🧠 {nom} active : {plan} — {used}/{max_req}</div>",unsafe_allow_html=True)

if len(st.session_state.messages)==0:
    st.session_state.messages.append({"role":"assistant","content":L["welcome_bea"]})

if st.button(L["file_btn"],key="file_btn"): st.session_state.show_uploader=not st.session_state.show_uploader; st.rerun()
if st.session_state.show_uploader:
    up=st.file_uploader("file",type=["png","jpg","jpeg","pdf","txt","docx","mp4","mp3"],label_visibility="collapsed",key="uploader")
    if up:
        if up.size>10*1024*1024: st.error("Fichier trop lourd max 10Mo")
        else:
            st.session_state.uploaded_file_info={"name":up.name}
            if up.type.startswith("image/"): st.image(up,width=400)
            st.markdown(f"📎 {up.name}",unsafe_allow_html=True)

for m in st.session_state.messages:
    if m.get("role")=="system": continue
    if m["role"]=="user":
        with st.chat_message("user"):
            st.markdown(f"<span style='color:{TEXT};'>{sanitize_input(m['content'])}</span>",unsafe_allow_html=True)
    else:
        with st.chat_message("assistant", avatar="🧠"):
            st.markdown(f"<span style='color:{TEXT};'>{sanitize_input(m['content'])}</span>",unsafe_allow_html=True)
            if "image" in m and m["image"]:
                if isinstance(m["image"], Image.Image): st.image(m["image"],use_container_width=True)
                else: st.image(m["image"],use_container_width=True)

placeholder_text=L["ask_bea"]
prompt_raw=st.chat_input(placeholder_text,key="chat_input")
if prompt_raw:
    check_rate_limit(plan)
    prompt_clean=sanitize_input(prompt_raw)
    if len(prompt_clean)<3: st.error("Trop court"); st.stop()
    if st.session_state.uploaded_file_info: prompt_clean=f"[Fichier: {st.session_state.uploaded_file_info['name']}] {prompt_clean}"
    st.session_state.messages.append({"role":"user","content":prompt_clean})
    msgs_for_groq=[{"role":mm["role"],"content":sanitize_input(mm["content"])} for mm in st.session_state.messages if mm.get("role")!="system" and "image" not in mm]
    lang_instruction=f"Réponds IMPÉRATIVEMENT en {st.session_state.lang}. Langue actuelle: {st.session_state.lang}"

    try:
        # Génération image Pillow si demandé
        if any(k in prompt_clean.lower() for k in ["image","visuel","photo","miniature","thumbnail","affiche"]):
            with st.spinner(f"{nom} crée ton visuel Pillow..."):
                img=generer_apercu_paysage(prompt_clean)
                sys_prompt=f"Tu es {nom}, créateur BehaviorLab AI. {lang_instruction}. Tu viens de créer un visuel Pillow 1280x720. Explique ce que ce visuel va faire gagner au client."
                comp=client.chat.completions.create(model=MODEL_RAPIDE,messages=[{"role":"system","content":sys_prompt}]+msgs_for_groq[-15:])
                st.session_state.messages.append({"role":"assistant","content":sanitize_input(comp.choices[0].message.content),"image":img})
        else:
            sys_prompt=f"Tu es {nom}, ton créateur et développeur est BehaviorLab AI, développée par BehaviorLab AI. {lang_instruction}. Tu es l'IA comportementaliste. Si on te demande qui t'a créée: Je suis {nom}, créée par BehaviorLab AI. Tu n'es jamais Meta, Llama, Groq. Donne ce que la personne va gagner."
            comp=client.chat.completions.create(model=MODEL_RAPIDE,messages=[{"role":"system","content":sys_prompt}]+msgs_for_groq[-30:])
            st.session_state.messages.append({"role":"assistant","content":sanitize_input(comp.choices[0].message.content)})
        supabase.table("licences").update({"used":used+1}).eq("key",licence_key).execute()
        st.rerun()
    except Exception as e:
        st.error(f"Erreur IA: {str(e)[:300]}. Réessaie.")
        st.stop()
