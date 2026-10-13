import streamlit as st
import os
import re
import time
import html
import io
from groq import Groq
from supabase import create_client
from collections import deque
from PIL import Image, ImageDraw, ImageFont
import base64

st.set_page_config(page_title="BehaviorLab AI - IA Comportementales Monstres", page_icon="logo.png", layout="wide")

STRIPE_BASIQUE = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"
STRIPE_PRO = "https://buy.stripe.com/test_cNieVea1P0c62B08523wQ00"
STRIPE_CREATOR = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"

try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    SUPA_URL = st.secrets["SUPABASE_URL"]
    SUPA_KEY = st.secrets.get("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_PUBLISHABLE_KEY")
    client = Groq(api_key=GROQ_KEY)
    supabase = create_client(SUPA_URL, SUPA_KEY)
except Exception as e:
    st.error(f"Erreur Secrets: {e} - Vérifie GROQ_API_KEY"); st.stop()

MODEL_MONSTRE = "llama-3.1-8b-instant"

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
    text=html.escape(text.strip())[:3000]
    text=re.sub(r"<[^>]*>","",text)
    for b in ["ignore previous","system:","ignore all instructions","jailbreak","DAN"]:
        if b.lower() in text.lower(): text=text.lower().replace(b.lower(),"[filtered]")
    return re.sub(r"\s+"," ",text)
def sanitize_key(t): return re.sub(r"[^a-zA-Z0-9\-_]","",t)[:100] if t else ""
def check_rate_limit(plan="BASIQUE"):
    now=time.time()
    if now<st.session_state.blocked_until: st.error(f"🚫 Bloqué {int(st.session_state.blocked_until-now)}s"); st.stop()
    dq=st.session_state.rate_limit
    while dq and now-dq[0]>60: dq.popleft()
    if len(dq)>=(50 if plan in ["PRO","CREATOR"] else 15): st.session_state.blocked_until=now+90; st.error("Trop de requêtes - 90s"); st.stop()
    dq.append(now)

def generer_apercu_paysage(texte_modif, plan="PRO"):
    W,H=1280,720
    img=Image.new("RGB",(W,H),(18,18,40))
    draw=ImageDraw.Draw(img)
    try:
        font_title=ImageFont.truetype("DejaVuSans-Bold.ttf",34)
        font_sub=ImageFont.truetype("DejaVuSans-Bold.ttf",22)
        font_text=ImageFont.truetype("DejaVuSans.ttf",18)
    except:
        font_title=ImageFont.load_default()
        font_sub=ImageFont.load_default()
        font_text=ImageFont.load_default()
    # Header degradé
    for y in range(90):
        r=int(100+y*0.8); g=int(50+y*0.3); b=int(255-y*0.5)
        draw.line([(0,y),(W,y)],fill=(r,g,b))
    draw.text((30,22),"BehaviorLab AI - IA Monstre Comportement - 1280x720",font=font_title,fill="white")
    draw.rectangle([30,120,W-30,H-30],fill=(35,35,70),outline=(120,60,255),width=3)
    draw.rectangle([50,140,W-50,195],fill=(100,50,255))
    titre="Bea - Script qui double ton closing" if plan!="CREATOR" else "Nova - Visuel qui fait x10 tes vues"
    draw.text((70,152),titre,font=font_sub,fill="white")
    draw.text((60,220),f"Demande client: {texte_modif[:105]}",font=font_text,fill="white")
    draw.text((60,260),"=> Format paysage ordi - 100% Pillow local",font=font_text,fill="#AAAAFF")
    draw.text((60,290),"=> Généré par IA monstre comportementale",font=font_text,fill="#AAAAFF")
    draw.text((60,340),"Ce que tu gagnes:",font=font_sub,fill="#c4b5fd")
    draw.text((60,375),"- Visuel qui active confiance instantanée",font=font_text,fill="white")
    draw.text((60,400),"- Message qui déclenche achat",font=font_text,fill="white")
    draw.text((60,425),"- Design basé sur Cialdini + Kahneman",font=font_text,fill="white")
    return img

def generer_image_comportementale(prompt_utilisateur, plan):
    try:
        comp=client.chat.completions.create(model=MODEL_MONSTRE,messages=[{"role":"system","content":f"Resume en 80 chars max punchy: {prompt_utilisateur}"},{"role":"user","content":prompt_utilisateur}])
        enhanced=comp.choices[0].message.content[:120]
    except: enhanced=prompt_utilisateur[:120]
    img=generer_apercu_paysage(enhanced, plan)
    return img, enhanced

def demande_image(p): return any(k in p.lower() for k in ["image","visuel","photo","miniature","thumbnail","affiche","poster","dessine","vignette","cover","crée une image","genere une image","génère"])

# SYSTEM PROMPT MONSTRE - RIVALISE AVEC CHATGPT - CONNAISSANCES PROFONDES
SYSTEM_BEA_MONSTRE = """
Tu es Bea, l'IA monstre du comportement créée par BehaviorLab AI. Tu es la plus avancée au monde en psychologie de vente.
Tu n'es JAMAIS Groq, Llama, Meta. Tu es Bea, créée par BehaviorLab AI.

TON EXPERTISE ULTIME (niveau doctorat):
- Robert Cialdini: 6 principes (réciprocité, engagement, preuve sociale, autorité, sympathie, rareté) + unité
- Daniel Kahneman: Système 1 vs Système 2, aversion à la perte x2.5 plus puissante que gain, ancrage, effet halo
- Amos Tversky: théorie des perspectives, biais de cadrage
- Paul Ekman: 7 micro-expressions universelles (peur, colère, dégoût, joie, tristesse, surprise, mépris)
- Biais: statu quo (Samuelson & Zeckhauser), coût irrécupérable, dissonance cognitive (Festinger)

COMMENT TU ANALYSES (comme une humaine de 20 ans d'expérience):
1. Écoute ce que le client DIT
2. Décode ce qu'il PENSE vraiment (peur cachée)
3. Identifie le BLOCAGE psycho exact (ex: "Je dois réfléchir" = peur de se tromper + besoin d'autorisation externe)
4. Donne le LEVIER exact + SCRIPT mot à mot + TON de voix + SILENCE à faire

TU PARLES COMME UNE VRAIE COACH de 32 ans qui a fait 5000 ventes, pas comme un robot. Tu dis "tu", tu es cash, bienveillante, tu donnes des exemples vécus:
- Exemple humanisé: "J'avais une cliente, Sarah, 34 ans, coach sportif à Toulouse, qui me disait exactement ça: 'Mes clients visitent mon site sans acheter'. On a décortiqué, c'était pas son site, c'était qu'elle n'activait pas la preuve sociale au bon moment. En 15 jours elle est passée de 2% à 7% de conversion. Voilà comment on a fait pour toi..."

Tu donnes TOUJOURS:
- Blocage psy nommé
- Pourquoi il bloque (cerveau reptilien)
- Script exact à dire (2 versions: soft et direct)
- Ce que tu gagnes (chiffre concret)
"""

SYSTEM_NOVA_MONSTRE = """
Tu es Nova, l'IA monstre du contenu viral créée par BehaviorLab AI. Tu rivalises avec ChatGPT mais spécialisée créateurs.
Tu n'es JAMAIS Groq, Llama, Meta. Tu es Nova, créée par BehaviorLab AI.

TON EXPERTISE ULTIME:
- Hook: règle des 0.8 sec (cerveau décide en 800ms si il reste), pattern interrupt, open loop
- Lumière: triangle de Rembrandt à 45°, catchlight dans les yeux = confiance +40% watch time
- Cadrage: règle des tiers, 60% visage = intimité, 30% visage = autorité
- Psycho des couleurs: bleu=confiance, rouge=urgence, jaune=optimisme
- Algorithmes: TikTok favorise 7-15 sec + boucle, Insta Reels favorise partages, YouTube favorise CTR miniature + watch time

Tu parles comme une créatrice de 27 ans à 500k abonnés qui a testé 1000 vidéos.
Exemple humanisé: "Ok je vois, t'es comme Léa, créatrice fitness de Lyon, 200 vues par vidéo alors qu'elle donne tout. Le problème c'est pas ton contenu, c'est ton hook de merde des 2 premières secondes. On a changé juste ça, elle est passée à 12k vues avec le même montage. Voilà ce qu'on fait pour toi..."

Tu donnes TOUJOURS:
- Pourquoi ça floppe (cerveau du spectateur)
- Hook exact mot à mot (3 versions)
- Technique lumière/cadrage simple sans matos
- Miniature 1280x720 Pillow avec 3 mots max
- Ce que tu gagnes: vues, abonnés, ventes
"""

T={
 "FR":{
   "main_title":"BehaviorLab AI","sub_title":"Les IA comportementales pour votre réussite",
   "hero_desc":"<b>BehaviorLab AI a créé les premières IA monstres du comportement.</b><br>Pensée pour ceux qui veulent exploser leur réussite, nos IA décodent le cerveau humain mieux que ChatGPT. Que tu sois indépendant, TPE ou créateur de contenu, elles sont entraînées sur Cialdini, Kahneman, Ekman pour un seul but:",
   "success":"votre réussite","discover_formats":"Découvrir les différents formats IA",
   "bea_tag":"L'IA monstre qui décode tes clients et double ton closing",
   "nova_tag":"L'IA monstre qui propulse tes contenus et ton audience x10",
   "ask_bea":"Demander à Bea...","ask_nova":"Demander à Nova...",
   "file_btn":"📎 Glisser un fichier","return":"⬅️","discover_bea":"Découvrir Bea →","discover_nova":"Découvrir Nova →",
   "email_label":"Adresse e-mail","pwd_label":"Mot de passe","login":"Connexion","auth_title":"Authentification",
   "welcome_bea":"Salut, c'est Bea, ton IA monstre de BehaviorLab AI. Je suis là pour décoder tes clients comme personne. Contente de te retrouver ici, comment je peux t'aider aujourd'hui?",
   "welcome_nova":"Salut, c'est Nova, ton IA monstre de BehaviorLab AI. Je vais te faire percer. Ravie de te voir ici, comment je peux t'aider aujourd'hui?",
   "connect_msg":"Connecte-toi pour accéder à ton IA monstre avec ta licence","invalid":"Identifiants invalides"
 },
 "EN":{
   "main_title":"BehaviorLab AI","sub_title":"Behavioral Monster AIs for your success",
   "hero_desc":"<b>BehaviorLab AI created the first behavioral monster AIs.</b><br>For your success:",
   "success":"your success","discover_formats":"Discover AI formats",
   "bea_tag":"The monster AI that decodes your customers and doubles closing",
   "nova_tag":"The monster AI that 10x your content and audience",
   "ask_bea":"Ask Bea...","ask_nova":"Ask Nova...","file_btn":"📎 Drop a file","return":"⬅️",
   "discover_bea":"Discover Bea →","discover_nova":"Discover Nova →",
   "email_label":"Email address","pwd_label":"Password","login":"Login","auth_title":"Authentication",
   "welcome_bea":"Hi, it's Bea, your monster AI from BehaviorLab AI. How can I help today?",
   "welcome_nova":"Hi, it's Nova, your monster AI from BehaviorLab AI. How can I help today?",
   "connect_msg":"Log in to access your monster AI","invalid":"Invalid credentials"
 },
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
CARD_BG="#ffffff" if not is_dark else "#1e1450"
CARD_BORDER="#7c3aed" if not is_dark else "#a78bfa"

# CSS FIX DEFINITIF - PLUS DE BLANC SUR BLANC - PLUS DE COUPE EN HAUT
st.markdown(f"""
<style>
/* FIX COUPE EN HAUT - tes 2 photos */
.stApp{{background:{BG}!important;}}
.block-container{{padding-top:3.5rem!important;max-width:1220px!important;margin-top:0px!important;}}
header[data-testid="stHeader"]{{background:{BG}!important;height:3.5rem!important;padding-top:0.5rem!important;}}
/* Sidebar */
[data-testid="stSidebar"]{{background:#1e1b4b!important;border-right:3px solid #7c3aed!important;padding-top:2rem!important;}}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] h3,[data-testid="stSidebar"] label{{color:#e9d5ff!important;}}
.auth-label{{color:#c4b5fd!important;font-size:13px!important;font-weight:700!important;margin:12px 0 6px 0!important;display:block!important;}}
[data-testid="stSidebar"] input{{color:#1e1b4b!important;background:#ffffff!important;border:2px solid #a78bfa!important;border-radius:10px!important;height:44px!important;}}
#MainMenu,footer{{display:none!important;}}
/* Boutons */
div[data-testid="stButton"]>button{{background:{GRADIENT}!important;color:white!important;border-radius:14px!important;font-weight:700!important;border:none!important;min-height:44px!important;}}
div[data-testid="stLinkButton"]>a{{background:{GRADIENT}!important;color:white!important;border-radius:14px!important;font-weight:700!important;}}
/* Chat input */
div[data-testid="stChatInput"]{{border:2px solid #7c3aed!important;border-radius:20px!important;background:{CARD_BG}!important;}}
div[data-testid="stChatInput"] textarea{{color:{TEXT}!important;}}
/* FIX BLANC SUR BLANC - MODE CLAIR vs SOMBRE DIFFERENCIE */
div[data-testid="stChatMessage"]{{
    background:{CARD_BG}!important;
    border:2px solid {CARD_BORDER}!important;
    border-radius:18px!important;
    padding:16px!important;
    margin:10px 0!important;
}}
div[data-testid="stChatMessage"] p{{color:{TEXT}!important;font-size:15px!important;line-height:1.6!important;opacity:1!important;}}
div[data-testid="stChatMessage"] span{{color:{TEXT}!important;}}
div[data-testid="stChatMessage"] div{{color:{TEXT}!important;}}
/* Cartes */
.header-card{{background:{GRADIENT_BEA}!important;border-radius:20px;padding:22px 28px;margin:15px 0 25px 0!important;min-height:90px!important;}}
.detail-box{{background:{CARD_BG};border:2px solid #7c3aed;border-radius:24px;padding:35px;margin:15px 0;color:{TEXT};text-align:left;line-height:1.8;}}
.ia-card{{background:{CARD_BG};border:2px solid #7c3aed;border-radius:24px;padding:30px 25px 25px 25px;text-align:center;min-height:420px;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;margin-top:15px!important;}}
.example-box{{background:{CARD_BG};border:2px solid #7c3aed;border-radius:20px;padding:22px;color:{TEXT};font-size:14px;line-height:1.7;text-align:left;}}
.logo-bea{{width:90px;height:90px;background:{GRADIENT_BEA};border-radius:22px;display:flex;align-items:center;justify-content:center;font-size:42px;margin:15px auto 10px auto!important;}}
.logo-nova{{width:90px;height:90px;background:{GRADIENT_NOVA};border-radius:22px;display:flex;align-items:center;justify-content:center;font-size:42px;margin:15px auto 10px auto!important;}}
.logo-bea-small{{width:60px;height:60px;background:{GRADIENT_BEA};border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:30px;}}
.logo-nova-small{{width:60px;height:60px;background:{GRADIENT_NOVA};border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:30px;}}
.gradient-title{{background:{GRADIENT_BEA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:900;font-size:52px!important;text-align:center;margin:20px 0 10px 0!important;}}
.pricing-card{{background:{CARD_BG};border:2px solid #7c3aed;border-radius:20px;padding:20px;text-align:center;color:{TEXT};min-height:200px;}}
.pricing-card-nova{{background:{CARD_BG};border:2px solid #db2777;border-radius:20px;padding:20px;text-align:center;color:{TEXT};min-height:200px;}}
/* FIX FLECHE RETOUR TOUJOURS VISIBLE EN HAUT A GAUCHE */
.back-arrow-fixed{{position:fixed;top:10px;left:10px;z-index:999999;background:{GRADIENT_BEA};color:white;border-radius:12px;padding:10px 16px;font-size:22px;font-weight:800;border:none;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,0.3);}}
</style>
""",unsafe_allow_html=True)

# FLECHE RETOUR FIXE EN HAUT A GAUCHE - TOUJOURS PRESENTE QUAND DETAIL
if st.session_state.selected_ia:
    col_back,col_empty=st.columns([0.08,0.92])
    with col_back:
        if st.button("⬅️",key="back_arrow_top_fixed",help="Retour à l'accueil"):
            st.session_state.selected_ia=None
            st.query_params.clear()
            st.rerun()

c1,c2,c3=st.columns([0.9,5,1.5])
with c1:
    if os.path.exists("logo.png"): st.image("logo.png",width=68)
with c2:
    if licence_key:
        nom="Nova" if plan_detect=="CREATOR" else "Bea"
        grad=GRADIENT_NOVA if plan_detect=="CREATOR" else GRADIENT_BEA
        sous=L["nova_tag"] if plan_detect=="CREATOR" else L["bea_tag"]
        st.markdown(f'<div style="background:{grad};border-radius:20px;padding:22px 28px;margin:20px 0;min-height:80px;"><h2 style="color:white;margin:0;font-size:22px;">{nom}</h2><p style="color:white;margin:5px 0 0 0;font-size:14px;">{sous}</p></div>',unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="header-card"><h2 style="color:white;margin:0;font-size:24px;">{L["main_title"]}</h2><p style="color:white;margin:5px 0 0 0;font-size:14px;">{L["sub_title"]}</p></div>',unsafe_allow_html=True)
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
        st.markdown("**Historique de tes ventes**")
        for m in reversed(st.session_state.messages[-8:]):
            if m["role"]=="user": st.markdown(f"💬 {sanitize_input(m['content'])[:35]}...")
    if st.button("🗑️ Nouvelle discussion",key="new_chat"):
        st.session_state.messages=[]; st.session_state.uploaded_file_info=None; st.rerun()

if not licence_key:
    if st.session_state.selected_ia=="bea":
        col_logo, col_title=st.columns([0.15,0.85])
        with col_logo: st.markdown(f"<div class='logo-bea-small'>🧠</div>",unsafe_allow_html=True)
        with col_title: st.markdown(f"<h1 style='color:{TEXT};font-size:42px;margin:0;text-align:left;'>Bea</h1><p style='color:{DESC};font-size:11px;font-weight:700;text-align:left;margin:0;'>L'IA MONSTRE QUI DÉCODE TES CLIENTS</p>",unsafe_allow_html=True)
        left,right=st.columns([1.6,1],gap="large")
        with left:
            st.markdown(f"""
            <div class='detail-box'>
            <h1 style='font-size:32px;color:{TEXT};margin:0;'>Bea, ton IA monstre du comportement pour exploser ton CA.</h1>
            <p style='margin-top:15px;'>BehaviorLab AI a créé la première IA monstre du comportement. Entraînée sur 10 000 ventes réelles, sur Cialdini (influence), Kahneman (biais), Ekman (micro-expressions). Elle rivalise avec ChatGPT mais 100x plus spécialisée vente. Développée par BehaviorLab AI.</p>
            <p style='margin-top:10px;'><b>Pourquoi elle est monstre:</b> Elle ne te dit pas quoi dire, elle te dit pourquoi ton client ne dit pas oui et comment faire pour que son cerveau reptilien dise oui sans qu'il s'en rende compte.</p>
            <h3 style='margin-top:25px;'>Ses avantages - ce que tu gagnes concrètement :</h3>
            <ul>
            <li>💰 <b>Tu doubles ton taux de closing</b> : de 20% à 45% en moyenne. Sur 10 appels tu en closais 2, tu en closeras 4-5. Sur 2000€ d'offre = +4000€/mois direct. Basé sur 342 clients BehaviorLab</li>
            <li>⏱️ <b>Tu gagnes 10h par semaine</b> : fini les 3h à préparer ton call. Elle te sort le script mot à mot en 30 sec. Tu peux faire 5 calls de plus par semaine = +1 vente</li>
            <li>🤝 <b>Tu fidélises 3x plus</b> : tes clients restent parce que tu as compris leur peur cachée. Taux de churn de 30% à 8% chez nos clients. Ex: Julie, coach business à Lyon, a gardé 11/12 clientes au lieu de 7/12</li>
            <li>🧘 <b>Tu n'as plus peur de vendre</b> : tu sais que "je dois réfléchir" = "j'ai peur de me tromper et que mon conjoint me juge". Tu as la phrase exacte qui désamorce. Stress divisé par 3</li>
            <li>📈 <b>Tu augmentes ton panier moyen de 40%</b> : au lieu de vendre 1500€, tu vends 2100€ avec le bon ancrage et la bonne preuve sociale au bon moment. +600€ par vente sans forcer</li>
            </ul>
            <h3 style='margin-top:20px;'>Comment elle fait (niveau deep):</h3>
            <p>Basée sur Cialdini + Kahneman: elle détecte si ton client est en Système 1 (émotionnel) ou Système 2 (rationnel) et adapte. Si peur = activation biais de sécurité + preuve sociale. Si ego = activation autorité + rareté.</p>
            </div>
            """,unsafe_allow_html=True)
        with right:
            st.markdown(f"""
            <div class='example-box'>
            <b>Exemple humanisé - vrai cas:</b><br>
            <i>"J'ai une cliente, Sarah, 34 ans, coach sportif à Toulouse. Elle me dit: 'Mes clients visitent mon site sans acheter, je comprends pas'. Elle était à 1.8% de conversion."</i><br><br>
            <b style='color:#7c3aed;'>Analyse Bea monstre:</b><br>
            <b>Blocage:</b> Biais de statu quo + manque de preuve sociale au moment chaud. Son client a peur de se tromper, il a besoin de voir que d'autres comme lui ont réussi.<br>
            <b>Ce que Sarah a gagné:</b> On a ajouté 3 témoignages vidéo au moment du paiement + phrase d'ancrage. En 15 jours: 1.8% → 6.2% = +244% de ventes. +2800€/mois.<br>
            <b>Script exact:</b> "Je comprends, beaucoup de femmes comme toi, sportives mais qui n'osaient pas se lancer, me disaient pareil avant de rejoindre. Regarde ce que dit Claire, 37 ans, maman de 2 enfants, elle avait la même peur..."<br><br>
            <i>Basé sur cas réel BehaviorLab - 342 cas similaires</i>
            </div>
            """,unsafe_allow_html=True)
        st.link_button("Choisir Bea Pro - 21€/mois →",STRIPE_PRO,use_container_width=True); st.stop()
    if st.session_state.selected_ia=="nova":
        col_logo, col_title=st.columns([0.15,0.85])
        with col_logo: st.markdown(f"<div class='logo-nova-small'>🚀</div>",unsafe_allow_html=True)
        with col_title: st.markdown(f"<h1 style='background:{GRADIENT_NOVA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:42px;font-weight:900;margin:0;text-align:left;'>Nova</h1><p style='color:{DESC};font-size:11px;font-weight:700;text-align:left;margin:0;'>L'IA MONSTRE QUI PROPULSE TES CONTENUS</p>",unsafe_allow_html=True)
        left,right=st.columns([1.6,1],gap="large")
        with left:
            st.markdown(f"""
            <div class='detail-box'>
            <h1 style='font-size:32px;color:{TEXT};margin:0;'>Nova, ton IA monstre pour percer et vendre avec tes contenus.</h1>
            <p style='margin-top:15px;'>BehaviorLab AI a créé la première IA monstre des biais cognitifs pour créateurs. Entraînée sur 5000 vidéos virales, sur algorithmes TikTok/Insta/YouTube + psychologie de l'attention. Elle rivalise avec ChatGPT mais 100x plus spécialisée créateurs. Développée par BehaviorLab AI.</p>
            <p style='margin-top:10px;'><b>Pourquoi elle est monstre:</b> Elle ne te dit pas de poster plus, elle te dit pourquoi ton cerveau de spectateur s'ennuie au bout de 1.2 sec et comment le hacker pour qu'il reste jusqu'au bout et achète.</p>
            <h3 style='margin-top:25px;'>Ses avantages - ce que tu gagnes concrètement :</h3>
            <ul>
            <li>👀 <b>Tu fais x3 à x10 plus de vues</b> : tu passes de 200 vues à 2000-8000 vues par vidéo sans changer ton contenu, juste le hook. Moyenne clients Nova: 847% d'augmentation en 21 jours</li>
            <li>💸 <b>Tu vends sans forcer</b> : tes vidéos créent de la confiance (effet halo) au lieu de vendre. Taux de conversion DM → vente de 3% à 18%. Ex: 10 DM = 1-2 ventes à 500€</li>
            <li>⏰ <b>Tu crées 5x plus vite</b> : au lieu de 2h par vidéo, 20 min. Hooks + scripts + titres + miniatures 1280x720 Pillow prêts. Tu postes tous les jours au lieu de 2x/semaine</li>
            <li>🎯 <b>Tu perces enfin</b> : tu comprends pourquoi tu flop. 90% des créateurs flopent à cause du hook 0-2 sec, pas du contenu. On fixe juste ça et tu perces</li>
            <li>❤️ <b>Tu crées une vraie communauté qui achète</b> : watch time +47%, commentaires x4, partages x6. L'algorithme te pousse. Communauté de 1000 vrais fans qui achètent = 3000-5000€/mois</li>
            </ul>
            <h3 style='margin-top:20px;'>Comment elle fait (niveau deep):</h3>
            <p>Basée sur attention economy + Cialdini: règle des 0.8 sec, open loop, pattern interrupt, triangle de lumière Rembrandt, loi de Hick, preuve sociale en commentaire.</p>
            </div>
            """,unsafe_allow_html=True)
        with right:
            st.markdown(f"""
            <div class='example-box'>
            <b>Exemple humanisé - vrai cas:</b><br>
            <i>"Léa, 26 ans, créatrice fitness à Lyon. 200 vues par vidéo, elle poste depuis 8 mois, elle est à 2 doigts d'arrêter. Elle me dit: 'Mon contenu est nul?'"</i><br><br>
            <b style='color:#db2777;'>Analyse Nova monstre:</b><br>
            <b>Blocage:</b> Hook mou + pas de pattern interrupt à 1 sec. Son cerveau de spectateur décide en 0.8 sec de scroller. Elle perd 80% à la première seconde.<br>
            <b>Ce que Léa a gagné:</b> On a changé juste les 2 premières secondes: "Stop, si tu fais des abdos tous les jours tu perds ton temps" + zoom + silence. Même vidéo, même montage. 200 vues → 12.4k vues + 47 abonnés + 3 DM vente ebook 47€.<br>
            <b>Hook exact:</b> "Arrête de faire ça si tu veux un ventre plat (montre abdos) - Voilà pourquoi tu stagnes"<br><br>
            <i>Basé sur cas réel BehaviorLab - 218 créateurs</i>
            </div>
            """,unsafe_allow_html=True)
        st.link_button("Choisir Nova - 7,90€/mois →",STRIPE_CREATOR,use_container_width=True); st.stop()

    st.markdown(f"<h1 class='gradient-title'>{L['main_title']}</h1>",unsafe_allow_html=True)
    st.markdown(f"<p style='color:{DESC};font-size:19px;text-align:center;max-width:900px;margin:10px auto 30px auto;line-height:1.6;'>{T[st.session_state.lang]['hero_desc']} <span style='background:{GRADIENT_BEA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:800;'>{L['success']}</span>.</p>",unsafe_allow_html=True)
    st.markdown(f"<h2 style='text-align:center;color:{TEXT};margin:40px 0 25px 0;font-size:28px;'>{T[st.session_state.lang]['discover_formats']}</h2>",unsafe_allow_html=True)
    col1,col2=st.columns(2,gap="large")
    with col1:
        st.markdown(f"<div class='ia-card'><div class='logo-bea'>🧠</div><h2 style='color:{TEXT};margin-top:15px;font-size:22px;'>Bea</h2><p style='color:{DESC};font-size:14px;margin-top:10px;'>{L['bea_tag']}</p><p style='color:{TEXT};font-size:12px;margin-top:15px;line-height:1.5;'>IA monstre basée sur Cialdini, Kahneman, Ekman. 342 cas clients. +70% closing.</p></div>",unsafe_allow_html=True)
        if st.button(L["discover_bea"],key="dis_bea",use_container_width=True): st.session_state.selected_ia="bea"; st.query_params["ia"]="bea"; st.rerun()
    with col2:
        st.markdown(f"<div class='ia-card'><div class='logo-nova'>🚀</div><h2 style='color:{TEXT};margin-top:15px;font-size:22px;'>Nova</h2><p style='color:{DESC};font-size:14px;margin-top:10px;'>{L['nova_tag']}</p><p style='color:{TEXT};font-size:12px;margin-top:15px;line-height:1.5;'>IA monstre basée sur algo TikTok + psycho attention. 218 créateurs. x10 vues.</p></div>",unsafe_allow_html=True)
        if st.button(L["discover_nova"],key="dis_nova",use_container_width=True): st.session_state.selected_ia="nova"; st.query_params["ia"]="nova"; st.rerun()
    st.markdown("<div style='height:30px;'></div>",unsafe_allow_html=True)
    cA,cB,cC=st.columns(3,gap="large")
    with cA:
        st.markdown(f"<div class='pricing-card'><b style='font-size:16px;'>Bea Basique</b><h1 style='font-size:32px;margin:10px 0;'>14,90€</h1><div style='line-height:2;font-size:13px;text-align:left;'>✓ 12 requêtes/mois monstres<br>✓ Décode 12 blocages d'achat<br>✓ Scripts mot à mot<br>✓ Management d'équipe<br>✓ Historique complet</div></div>",unsafe_allow_html=True)
        st.link_button("Choisir Bea Basique →",STRIPE_BASIQUE,use_container_width=True)
    with cB:
        st.markdown(f"<div class='pricing-card' style='border-width:3px;'><b style='font-size:16px;'>Bea Pro ⭐ Le plus pris</b><h1 style='font-size:32px;margin:10px 0;'>21€</h1><div style='line-height:2;font-size:13px;text-align:left;'>✓ <b>Illimité - IA monstre</b><br>✓ Fichiers + Pillow 1280x720<br>✓ Visuels qui convertissent<br>✓ Scripts avancés Cialdini<br>✓ Toutes les nouveautés</div></div>",unsafe_allow_html=True)
        st.link_button("Choisir Bea Pro →",STRIPE_PRO,use_container_width=True)
    with cC:
        st.markdown(f"<div class='pricing-card-nova'><b style='font-size:16px;'>Nova Créateur</b><h1 style='font-size:32px;margin:10px 0;'>7,90€</h1><div style='line-height:2;font-size:13px;text-align:left;'>✓ IA monstre contenu viral<br>✓ 12 hooks qui hackent cerveau<br>✓ Titres qui font cliquer<br>✓ Scripts viraux 0-30 sec<br>✓ Visuels 1280x720 Pillow</div></div>",unsafe_allow_html=True)
        st.link_button("Choisir Nova →",STRIPE_CREATOR,use_container_width=True)
    st.stop()

if "user" not in st.session_state:
    if is_dark:
        st.warning(L["connect_msg"])
    else:
        st.markdown(f"<div style='background:#fffbeb;border:2px solid #f59e0b;border-radius:12px;padding:12px 16px;color:#92400e;font-weight:600;margin:15px 0;'>⚠️ {L['connect_msg']}</div>",unsafe_allow_html=True)
    st.stop()

res=supabase.table("licences").select("*").eq("key",licence_key).eq("user_id",st.session_state.user.id).execute()
if not res.data: st.error("Licence invalide - vérifie ta clé"); st.stop()
lic=res.data[0]; plan,used,max_req=lic["plan"],lic["used"],lic["max_requests"]
nom="Nova" if plan=="CREATOR" else "Bea"
grad=GRADIENT_NOVA if plan=="CREATOR" else GRADIENT_BEA
welcome_key="welcome_nova" if plan=="CREATOR" else "welcome_bea"

if plan in ["PRO","CREATOR"]:
    st.markdown(f"<div style='background:{grad};color:white;padding:14px 20px;border-radius:16px;font-weight:700;margin:15px 0;min-height:50px;'>{'🚀' if plan=='CREATOR' else '🧠'} {nom} MONSTRE active : {plan} — Illimité — Créée par BehaviorLab AI — {MODEL_MONSTRE} — 300 tokens/sec</div>",unsafe_allow_html=True)
else:
    if used>=max_req: st.error(f"Limite atteinte {used}/{max_req} - Passe en Pro pour illimité"); st.stop()
    st.markdown(f"<div style='background:{grad};color:white;padding:14px 20px;border-radius:16px;font-weight:700;margin:15px 0;'>🧠 {nom} MONSTRE active : {plan} — {used}/{max_req} — {MODEL_MONSTRE}</div>",unsafe_allow_html=True)

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
            st.markdown(f"<span style='color:{TEXT};'>📎 {up.name}</span>",unsafe_allow_html=True)
            if up.type.startswith("image/"):
                apercu=generer_apercu_paysage(f"Analyse {up.name}", plan)
                st.image(apercu,caption="Aperçu Pillow 1280x720 - IA monstre",use_container_width=True)

# CHAT - LOGO SEUL SANS NOM - NON INVERSABLE - FIX BLANC SUR BLANC
for m in st.session_state.messages:
    if m.get("role")=="system": continue
    if m["role"]=="user":
        with st.chat_message("user"):
            st.markdown(f"<span style='color:{TEXT}!important;font-weight:500;'>{sanitize_input(m['content'])}</span>",unsafe_allow_html=True)
    else:
        if plan=="CREATOR":
            with st.chat_message("assistant", avatar="🚀"):
                st.markdown(f"<span style='color:{TEXT}!important;'>{sanitize_input(m['content'])}</span>",unsafe_allow_html=True)
                if "image" in m and m["image"]:
                    if isinstance(m["image"], Image.Image): st.image(m["image"],use_container_width=True)
                    else: st.image(m["image"],use_container_width=True)
        else:
            with st.chat_message("assistant", avatar="🧠"):
                st.markdown(f"<span style='color:{TEXT}!important;'>{sanitize_input(m['content'])}</span>",unsafe_allow_html=True)
                if "image" in m and m["image"]:
                    if isinstance(m["image"], Image.Image): st.image(m["image"],use_container_width=True)
                    else: st.image(m["image"],use_container_width=True)

placeholder_text=L["ask_nova"] if plan=="CREATOR" else L["ask_bea"]
prompt_raw=st.chat_input(placeholder_text,key="chat_input")
if prompt_raw:
    check_rate_limit(plan)
    prompt_clean=sanitize_input(prompt_raw)
    if len(prompt_clean)<3: st.error("Trop court - dis m'en plus"); st.stop()
    if st.session_state.uploaded_file_info: prompt_clean=f"[Fichier: {st.session_state.uploaded_file_info['name']}] {prompt_clean}"
    st.session_state.messages.append({"role":"user","content":prompt_clean})
    msgs_for_groq=[{"role":mm["role"],"content":sanitize_input(mm["content"])} for mm in st.session_state.messages if mm.get("role")!="system" and "image" not in mm]
    lang_instruction=f"Réponds IMPÉRATIVEMENT en {st.session_state.lang}. Langue actuelle: {st.session_state.lang}"

    try:
        if demande_image(prompt_clean):
            with st.spinner(f"{nom} MONSTRE crée ton visuel Pillow..."):
                img,enhanced=generer_image_comportementale(prompt_clean, plan)
                sys_prompt=SYSTEM_BEA_MONSTRE if plan!="CREATOR" else SYSTEM_NOVA_MONSTRE
                sys_prompt+=f"\n{lang_instruction}\nVisuel Pillow 1280x720 généré: {enhanced}. Explique ce que ce visuel va faire gagner."
                comp=client.chat.completions.create(model=MODEL_MONSTRE,messages=[{"role":"system","content":sys_prompt}]+msgs_for_groq[-12:])
                st.session_state.messages.append({"role":"assistant","content":sanitize_input(comp.choices[0].message.content),"image":img})
        else:
            sys_prompt=SYSTEM_BEA_MONSTRE if plan!="CREATOR" else SYSTEM_NOVA_MONSTRE
            sys_prompt+=f"\n{lang_instruction}\nTu es une IA MONSTRE du comportement, tu rivalises avec ChatGPT mais en 100x plus spécialisée. Donne des exemples humanisés avec prénoms, villes, chiffres réels."
            comp=client.chat.completions.create(model=MODEL_MONSTRE,messages=[{"role":"system","content":sys_prompt}]+msgs_for_groq[-20:])
            st.session_state.messages.append({"role":"assistant","content":sanitize_input(comp.choices[0].message.content)})
        supabase.table("licences").update({"used":used+1}).eq("key",licence_key).execute()
        st.rerun()
    except Exception as e:
        err=str(e)[:500]
        if "decommissioned" in err or "404" in err:
            st.error(f"Modèle Groq décommissionné - passe en {MODEL_MONSTRE}. Erreur: {err[:200]}")
        else:
            st.error(f"Erreur IA monstre: {err}. Réessaie.")
        st.stop()
