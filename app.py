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

st.set_page_config(page_title="BehaviorLab AI", page_icon="logo.png", layout="wide")

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
    st.error(f"Erreur Secrets : {e}")
    st.stop()

def get_modeles_valides_groq():
    try:
        liste = client.models.list()
        ids = [m.id for m in liste.data]
        preferes = ["openai/gpt-oss-20b","openai/gpt-oss-120b","qwen/qwen3-32b","meta-llama/llama-4-maverick-17b-128e-instruct","llama-3.3-70b-versatile"]
        valides = [m for m in preferes if m in ids]
        return valides if valides else ids
    except:
        return ["openai/gpt-oss-20b","openai/gpt-oss-120b"]

MODELES_DISPO = get_modeles_valides_groq()

def call_groq_durable(messages):
    last_err = None
    for model_id in MODELES_DISPO:
        try:
            comp = client.chat.completions.create(model=model_id, messages=messages, temperature=0.7, max_tokens=1200)
            return comp.choices[0].message.content, model_id
        except Exception as e:
            last_err = e
            continue
    raise last_err

for k, v in {
    "theme": "light","lang": "FR","messages": [],"show_uploader": False,
    "uploaded_file_info": None,"rate_limit": deque(),"blocked_until": 0,
    "selected_ia": None,"auth_error": None,"auth_success": None,"nova_tab": "nova_ai"
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

def toggle_lang():
    st.session_state.lang = "EN" if st.session_state.lang == "FR" else "FR"

if "user" not in st.session_state:
    try:
        sess = supabase.auth.get_session()
        if sess and sess.session and sess.session.user:
            st.session_state.user = sess.session.user
    except:
        pass

def sanitize_user(text):
    if not text: return ""
    text = text.strip()[:3000]
    text = re.sub(r"<[^>]*>", "", text)
    return text

def sanitize_assistant(text):
    if not text: return ""
    text = re.sub(r"<script.*?>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]*>", "", text)
    return text.strip()[:6000]

def sanitize_key(t):
    return re.sub(r"[^a-zA-Z0-9\-_]", "", t)[:100] if t else ""

def check_rate_limit(plan="BASIQUE"):
    now = time.time()
    if now < st.session_state.blocked_until:
        st.error(f"🚫 Bloqué {int(st.session_state.blocked_until - now)}s")
        st.stop()
    dq = st.session_state.rate_limit
    while dq and now - dq[0] > 60:
        dq.popleft()
    if len(dq) >= (50 if plan in ["PRO", "CREATOR"] else 15):
        st.session_state.blocked_until = now + 90
        st.error("Trop de requêtes - 90s")
        st.stop()
    dq.append(now)

def generer_apercu_paysage(texte_modif, plan="PRO"):
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), (18, 18, 40))
    draw = ImageDraw.Draw(img)
    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
        font_sub = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
        font_text = ImageFont.truetype("DejaVuSans.ttf", 18)
    except:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_text = ImageFont.load_default()
    for y in range(90):
        draw.line([(0, y), (W, y)], fill=(int(100+y*0.8), int(50+y*0.3), int(255-y*0.5)))
    draw.text((30, 22), "BehaviorLab AI - 1280x720 - Pillow", font=font_title, fill="white")
    draw.rectangle([30, 120, W-30, H-30], fill=(35, 35, 70), outline=(120, 60, 255), width=3)
    draw.rectangle([50, 140, W-50, 195], fill=(100, 50, 255))
    titre = "Bea - Visuel qui convertit" if plan!="CREATOR" else "Nova - Visuel qui fait cliquer"
    draw.text((70, 152), titre, font=font_sub, fill="white")
    draw.text((60, 220), f"Demande : {texte_modif[:105]}", font=font_text, fill="white")
    draw.text((60, 260), "=> Format paysage - 100% Pillow local", font=font_text, fill="#AAAAFF")
    draw.text((60, 340), "Aperçu client :", font=font_sub, fill="#c4b5fd")
    return img

def generer_image_comportementale(prompt_utilisateur, plan):
    try:
        txt,_ = call_groq_durable([{"role":"system","content":f"Résume en 80 caractères : {prompt_utilisateur}"},{"role":"user","content":prompt_utilisateur}])
        enhanced = txt[:120]
    except:
        enhanced = prompt_utilisateur[:120]
    return generer_apercu_paysage(enhanced, plan), enhanced

def demande_image(p):
    return any(k in p.lower() for k in ["image","visuel","photo","miniature","thumbnail","affiche","poster","dessine","vignette","cover"])

SYSTEM_BEA = """
Tu es Bea, l'IA de BehaviorLab AI. Tu es la référence en psychologie de vente.
Règles : Français parfait sans fautes, majuscules début phrases, paragraphes aérés, emojis 😊 💰 🎯 💬 📈, gras, listes.
Tu donnes blocage exact, pourquoi il bloque, script doux, script direct, ce que tu gagnes en chiffres, exemple vécu avec prénom âge ville.
Tu es BehaviorLab AI.
"""

SYSTEM_NOVA = """
Tu es Nova, l'IA studio de montage de BehaviorLab AI pour créateurs de contenu.
Tu es experte en montage, hooks, titres, miniatures, rétention, algorithmes.
Règles : Français parfait sans fautes, majuscules début phrases, paragraphes aérés, emojis 🚀 👀 💸 ❤️ 🎬, toujours 3 hooks, 3 titres.
Tu maîtrises CapCut : média, audio, texte, stickers, effets, transitions, filtres, suppression fond.
Tu donnes pourquoi ça floppe, hook exact mot à mot, technique sans matériel cher, miniature 1280x720, ce que tu gagnes en vues abonnés ventes.
Tu es BehaviorLab AI.
"""

T = {
    "FR": {
        "main_title": "BehaviorLab AI","sub_title": "Les IA comportementales pour votre réussite",
        "hero_desc": "<b>BehaviorLab AI a créé les premières IA du comportement.</b><br>Pensée pour ceux qui veulent booster leur réussite, nos IA décodent le comportement humain pour un seul but :",
        "success": "votre réussite","discover_formats": "Découvrir les différents formats IA",
        "bea_tag": "L'IA qui décode tes clients et double ton closing",
        "nova_tag": "Le studio IA qui monte, titre et fait percer tes contenus",
        "ask_bea": "Demander à Bea...","ask_nova": "Demander à Nova...","file_btn": "📎 Glisser un fichier","return": "⬅️",
        "discover_bea": "Découvrir Bea →","discover_nova": "Découvrir Nova →",
        "email_label": "Adresse e-mail","pwd_label": "Mot de passe","login": "Connexion","signup": "Créer mon compte","auth_title": "Authentification",
        "welcome_bea": "Salut, c'est Bea, ton IA créée par BehaviorLab AI. Comment je peux t'aider aujourd'hui?",
        "welcome_nova": "Salut, c'est Nova, ton studio IA créé par BehaviorLab AI. Comment je peux t'aider aujourd'hui? Monte, titre, génère ton visuel et perce.",
        "connect_msg": "Connecte-toi pour accéder à ton IA avec ta licence","invalid": "Identifiants invalides",
        "welcome_email": "Bienvenue sur BehaviorLab AI - Vérifie ton e-mail pour confirmer que c'était bien toi."
    },
    "EN": {
        "main_title": "BehaviorLab AI","sub_title": "Behavioral AIs for your success",
        "hero_desc": "<b>BehaviorLab AI created the first behavioral AIs.</b><br>For your success :",
        "success": "your success","discover_formats": "Discover AI formats",
        "bea_tag": "The AI that decodes your customers","nova_tag": "The AI studio that edits and makes your content viral",
        "ask_bea": "Ask Bea...","ask_nova": "Ask Nova...","file_btn": "📎 Drop a file","return": "⬅️",
        "discover_bea": "Discover Bea →","discover_nova": "Discover Nova →",
        "email_label": "Email","pwd_label": "Password","login": "Login","signup": "Create account","auth_title": "Authentication",
        "welcome_bea": "Hi, it's Bea, your AI from BehaviorLab AI. How can I help today?",
        "welcome_nova": "Hi, it's Nova, your AI studio from BehaviorLab AI. How can I help today?",
        "connect_msg": "Log in to access your AI","invalid": "Invalid credentials","welcome_email": "Welcome to BehaviorLab AI - Check your email."
    },
}

L = T[st.session_state.lang]
licence_key = sanitize_key(st.query_params.get("key", ""))
ia_param = st.query_params.get("ia", "")
if ia_param:
    st.session_state.selected_ia = ia_param
is_dark = st.session_state.theme == "dark"
try:
    plan_detect = supabase.table("licences").select("plan").eq("key", licence_key).execute().data[0]["plan"] if licence_key else "VITRINE"
except:
    plan_detect = "VITRINE"

GRADIENT_BEA = "linear-gradient(135deg, #1d4ed8 0%, #4f46e5 30%, #7c3aed 60%, #c026d3 85%, #db2777 100%)"
GRADIENT_NOVA = "linear-gradient(135deg, #7c3aed 0%, #db2777 50%, #f97316 100%)"
GRADIENT = GRADIENT_NOVA if plan_detect == "CREATOR" else GRADIENT_BEA
BG = "#ffffff" if not is_dark else "#0f0a1e"
TEXT = "#1e1b4b" if not is_dark else "#f5f3ff"
DESC = "#312e81" if not is_dark else "#c4b5fd"
CARD_BG = "#ffffff" if not is_dark else "#1e1450"
CARD_BORDER = "#7c3aed"

st.markdown(f"""
<style>
.stApp{{background:{BG}!important;}}
.block-container{{padding-top:3.5rem!important;max-width:100%!important;}}
header[data-testid="stHeader"]{{background:{BG}!important;height:3.5rem!important;}}
[data-testid="stSidebar"]{{background:#1e1b4b!important;border-right:3px solid #7c3aed!important;padding-top:2rem!important;}}
.auth-label{{color:#c4b5fd!important;font-size:13px!important;font-weight:700!important;margin:12px 0 6px 0!important;display:block!important;}}
[data-testid="stSidebar"] input{{color:#1e1b4b!important;background:#ffffff!important;border:2px solid #a78bfa!important;border-radius:10px!important;height:44px!important;}}
#MainMenu,footer{{display:none!important;}}
div[data-testid="stButton"]>button{{background:{GRADIENT}!important;color:white!important;border-radius:14px!important;font-weight:700!important;border:none!important;min-height:44px!important;}}
div[data-testid="stLinkButton"]>a{{background:{GRADIENT}!important;color:white!important;border-radius:14px!important;}}
div[data-testid="stChatInput"]{{background:{"#2a2250" if is_dark else "#ffffff"}!important;border:2px solid #7c3aed!important;border-radius:20px!important;}}
div[data-testid="stChatMessage"]{{background:{CARD_BG}!important;border:2px solid {CARD_BORDER}!important;border-radius:18px!important;padding:18px!important;}}
div[data-testid="stChatMessage"] p{{color:{TEXT}!important;font-size:15px!important;line-height:1.8!important;white-space:pre-wrap!important;}}
.header-card{{background:{GRADIENT_BEA}!important;border-radius:20px;padding:22px 28px;margin:15px 0 25px 0!important;}}
.detail-box{{background:{CARD_BG};border:2px solid #7c3aed;border-radius:24px;padding:35px;margin:15px 0;color:{TEXT};line-height:1.8;}}
.ia-card{{background:{CARD_BG};border:2px solid #7c3aed;border-radius:24px;padding:35px 25px 25px 25px;text-align:center;min-height:420px;margin-top:30px!important;}}
.example-box{{background:{CARD_BG};border:2px solid #7c3aed;border-radius:20px;padding:22px;color:{TEXT};}}
.logo-bea{{width:90px;height:90px;background:{GRADIENT_BEA};border-radius:22px;display:flex;align-items:center;justify-content:center;font-size:42px;margin:15px auto 10px auto!important;}}
.logo-nova{{width:90px;height:90px;background:{GRADIENT_NOVA};border-radius:22px;display:flex;align-items:center;justify-content:center;font-size:42px;margin:15px auto 10px auto!important;}}
.gradient-title{{background:{GRADIENT_BEA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:900;font-size:52px!important;text-align:center;margin:20px 0 10px 0!important;}}
.pricing-card{{background:{CARD_BG};border:2px solid #7c3aed;border-radius:20px;padding:20px;text-align:center;color:{TEXT};}}
.pricing-card-nova{{background:{CARD_BG};border:2px solid #db2777;border-radius:20px;padding:20px;text-align:center;color:{TEXT};}}
.icon-bar{{background:#0f0a1e;border-right:2px solid #7c3aed;padding:15px 5px;height:100vh;}}
</style>
""", unsafe_allow_html=True)

if st.session_state.selected_ia:
    col_back, col_empty = st.columns([0.08, 0.92])
    with col_back:
        if st.button("⬅️", key="back_arrow_top_fixed"):
            st.session_state.selected_ia = None
            st.query_params.clear()
            st.rerun()

c1, c2 = st.columns([0.9, 5.1])
with c1:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=68)
with c2:
    if licence_key:
        nom = "Nova" if plan_detect == "CREATOR" else "Bea"
        grad = GRADIENT_NOVA if plan_detect == "CREATOR" else GRADIENT_BEA
        sous = L["nova_tag"] if plan_detect == "CREATOR" else L["bea_tag"]
        col_logo_use, col_text_use = st.columns([0.12, 0.88])
        with col_logo_use:
            if os.path.exists("logo.png"):
                st.image("logo.png", width=52)
        with col_text_use:
            st.markdown(f'<div style="background:{grad};border-radius:20px;padding:14px 22px;margin:10px 0;"><h2 style="color:white;margin:0;font-size:20px;">{nom}</h2><p style="color:white;margin:4px 0 0 0;font-size:13px;">{sous}</p></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="header-card"><h2 style="color:white;margin:0;font-size:24px;">{L["main_title"]}</h2><p style="color:white;margin:5px 0 0 0;font-size:14px;">{L["sub_title"]}</p></div>', unsafe_allow_html=True)

# VITRINE
if not licence_key:
    if st.session_state.selected_ia == "bea":
        st.markdown(f"<h1 style='color:{TEXT};font-size:42px;text-align:left;'>Bea</h1><p style='color:{DESC};font-size:11px;font-weight:700;'>L'IA QUI DÉCODE TES CLIENTS</p>", unsafe_allow_html=True)
        left, right = st.columns([1.6, 1], gap="large")
        with left:
            st.markdown(f"<div class='detail-box'><h1 style='font-size:32px;color:{TEXT};margin:0;'>Bea, ton IA comportementale pour ton entreprise.</h1><p>BehaviorLab AI a créé la première IA du comportement dédiée aux indépendants et TPE/PME.</p><h3>Ses avantages :</h3><ul><li>💰 Double ton closing +30 à +70% en 30 jours</li><li>⏱️ Gagne 10h par semaine scripts exacts</li><li>🤝 Fidélise tes clients peurs cachées</li><li>🧘 Stresses moins phrase qui débloque</li><li>📈 Augmente panier moyen</li></ul></div>", unsafe_allow_html=True)
        with right:
            st.markdown(f"<div class='example-box'>Exemple Sarah 34 ans coach Toulouse 1.8% → 6.2% +2800€/mois</div>", unsafe_allow_html=True)
        st.link_button("Choisir Bea Pro - 21 € par mois →", STRIPE_PRO, use_container_width=True)
        st.stop()
    if st.session_state.selected_ia == "nova":
        st.markdown(f"<h1 style='background:{GRADIENT_NOVA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:42px;font-weight:900;text-align:left;'>Nova</h1><p style='color:{DESC};font-size:11px;font-weight:700;'>LE STUDIO IA QUI FAIT PERCER TES CONTENUS</p>", unsafe_allow_html=True)
        left, right = st.columns([1.6, 1], gap="large")
        with left:
            st.markdown(f"""
            <div class='detail-box'>
            <h1 style='font-size:32px;color:{TEXT};margin:0;'>Nova, ton studio complet pour exploser ton audience.</h1>
            <p>BehaviorLab AI a créé le premier studio IA qui monte à ta place. Plus besoin de 5 logiciels.</p>
            <h3 style='margin-top:25px;'>Ses avantages studio :</h3>
            <ul>
            <li>🎬 <b>Montage photo / vidéo auto</b> : importe, coupe, ajoute musique en 1 clic</li>
            <li>👀 <b>x3 plus de vues</b> : hooks qui captent en 0,8 seconde</li>
            <li>💸 <b>Miniatures qui cliquent</b> : visuels 1280x720 générés Pillow qui font +45% CTR</li>
            <li>📝 <b>Titres & scripts viraux</b> : 3 hooks, 3 titres, sous-titres auto</li>
            <li>🎵 <b>Audio & effets</b> : musiques libres, transitions, filtres, stickers</li>
            <li>✂️ <b>Suppression fond & auto-cut</b> : détoure et recadre comme un pro</li>
            <li>📈 <b>Tu postes tous les jours</b> : 5x plus vite, audience qui explose</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
        with right:
            st.markdown(f"""
            <div class='example-box'>
            <b>Exemple studio :</b><br>
            Léa, 26 ans, fitness Lyon. 200 vues → 12,4 k vues + 3 ventes.<br><br>
            <b style='color:#db2777;'>Flux Nova :</b><br>
                        1. Import vidéo<br>2. Nova coupe les blancs<br>3. Ajoute hook + sous-titres<br>4. Génère miniature 1280x720<br>5. Exporte<br><br>
            Hook : "Arrête ça si tu veux un ventre plat"
            </div>
            """, unsafe_allow_html=True)
        st.link_button("Choisir Nova Studio - 7,90 € par mois →", STRIPE_CREATOR, use_container_width=True)
        st.stop()

    st.markdown(f"<h1 class='gradient-title'>{L['main_title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{DESC};font-size:19px;text-align:center;max-width:900px;margin:10px auto 30px auto;'>{T[st.session_state.lang]['hero_desc']} <span style='background:{GRADIENT_BEA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:800;'>{L['success']}</span>.</p>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='text-align:center;color:{TEXT};margin:40px 0 25px 0;font-size:28px;'>{T[st.session_state.lang]['discover_formats']}</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown(f"<div class='ia-card'><div class='logo-bea'>🧠</div><h2 style='color:{TEXT};'>Bea</h2><p style='color:{DESC};'>{L['bea_tag']}</p></div>", unsafe_allow_html=True)
        if st.button(L["discover_bea"], key="dis_bea", use_container_width=True):
            st.session_state.selected_ia = "bea"; st.query_params["ia"] = "bea"; st.rerun()
    with col2:
        st.markdown(f"<div class='ia-card'><div class='logo-nova'>🚀</div><h2 style='color:{TEXT};'>Nova</h2><p style='color:{DESC};'>{L['nova_tag']}</p></div>", unsafe_allow_html=True)
        if st.button(L["discover_nova"], key="dis_nova", use_container_width=True):
            st.session_state.selected_ia = "nova"; st.query_params["ia"] = "nova"; st.rerun()
    st.markdown("<div style='height:30px;'></div>", unsafe_allow_html=True)
    cA, cB, cC = st.columns(3, gap="large")
    with cA:
        st.markdown(f"<div class='pricing-card'><b>Bea Basique</b><h1>14,90 €</h1><div style='text-align:left;font-size:13px;line-height:2;'>✓ 12 requêtes/mois<br>✓ Blocages<br>✓ Scripts</div></div>", unsafe_allow_html=True)
        st.link_button("Choisir →", STRIPE_BASIQUE, use_container_width=True)
    with cB:
        st.markdown(f"<div class='pricing-card' style='border-width:3px;'><b>Bea Pro ⭐</b><h1>21 €</h1><div style='text-align:left;font-size:13px;line-height:2;'>✓ Illimité<br>✓ Fichiers + Pillow<br>✓ Visuels 1280x720</div></div>", unsafe_allow_html=True)
        st.link_button("Choisir →", STRIPE_PRO, use_container_width=True)
    with cC:
        st.markdown(f"<div class='pricing-card-nova'><b>Nova Studio</b><h1>7,90 €</h1><div style='text-align:left;font-size:13px;line-height:2;'>✓ Montage photo<br>✓ Miniatures 1280x720<br>✓ Hooks + Titres<br>✓ Audio + Effets</div></div>", unsafe_allow_html=True)
        st.link_button("Choisir →", STRIPE_CREATOR, use_container_width=True)
    st.stop()

# VERSION UTILISABLE AVEC LICENCE
if "user" not in st.session_state:
    st.warning(L["connect_msg"]); st.stop()

res = supabase.table("licences").select("*").eq("key", licence_key).eq("user_id", st.session_state.user.id).execute()
if not res.data:
    st.error("Licence invalide"); st.stop()
lic = res.data[0]
plan, used, max_req = lic["plan"], lic["used"], lic["max_requests"]
nom = "Nova" if plan == "CREATOR" else "Bea"

if plan not in ["PRO", "CREATOR"]:
    if used >= max_req:
        st.error(f"Limite {used}/{max_req}"); st.stop()

if len(st.session_state.messages) == 0:
    st.session_state.messages.append({"role": "assistant", "content": L["welcome_bea"] if plan!="CREATOR" else L["welcome_nova"]})

# SI BEA = ANCIEN CHAT SIMPLE AVEC LOGO
if plan!= "CREATOR":
    with st.sidebar:
        st.button("☀️ Clair" if is_dark else "🌙 Sombre", key="btn_theme", on_click=toggle_theme, use_container_width=True)
        st.button(f"🌐 {st.session_state.lang}", key="btn_lang", on_click=toggle_lang, use_container_width=True)
        st.divider()
        st.success(f"Connecté : {st.session_state.user.email}")
        if st.button("Déconnexion", key="deco"):
            supabase.auth.sign_out()
            if "user" in st.session_state: del st.session_state.user
            st.rerun()
        st.divider()
        if st.session_state.messages:
            st.markdown("**Historique**")
            for m in reversed(st.session_state.messages[-8:]):
                if m["role"]=="user": st.markdown(f"💬 {sanitize_user(m['content'])[:35]}...")
        if st.button("🗑️ Nouvelle discussion", key="new_chat_bea"):
            st.session_state.messages=[]; st.rerun()
    if st.button(L["file_btn"], key="file_btn_bea"):
        st.session_state.show_uploader = not st.session_state.show_uploader; st.rerun()
    if st.session_state.show_uploader:
        up = st.file_uploader("file", type=["png","jpg","jpeg","pdf","txt"], label_visibility="collapsed", key="uploader_bea")
        if up:
            st.session_state.uploaded_file_info={"name":up.name}
            if up.type.startswith("image/"): st.image(up,width=400)
    logo_path = "logo.png" if os.path.exists("logo.png") else None
    for m in st.session_state.messages:
        if m.get("role")=="system": continue
        if m["role"]=="user":
            with st.chat_message("user"): st.markdown(sanitize_user(m["content"]))
        else:
            with st.chat_message("assistant", avatar=logo_path if logo_path else "🧠"):
                st.markdown(sanitize_assistant(m["content"]))
                if "image" in m and m["image"]: st.image(m["image"], use_container_width=True)
    prompt_raw = st.chat_input(L["ask_bea"], key="chat_input_bea")
    if prompt_raw:
        check_rate_limit(plan)
        prompt_clean = sanitize_user(prompt_raw)
        if st.session_state.uploaded_file_info: prompt_clean = f"[Fichier : {st.session_state.uploaded_file_info['name']}] {prompt_clean}"
        st.session_state.messages.append({"role":"user","content":prompt_clean})
        msgs_for_groq = [{"role":mm["role"],"content":sanitize_user(mm["content"])} for mm in st.session_state.messages if mm.get("role")!="system" and "image" not in mm]
        sys_prompt = SYSTEM_BEA + f"\nRéponds en {st.session_state.lang}. Si on te demande qui t'a créée : Je suis Bea, créée par BehaviorLab AI."
        try:
            if demande_image(prompt_clean):
                img,enhanced = generer_image_comportementale(prompt_clean, plan)
                reponse,_ = call_groq_durable([{"role":"system","content":sys_prompt}]+msgs_for_groq[-12:])
                st.session_state.messages.append({"role":"assistant","content":sanitize_assistant(reponse),"image":img})
            else:
                reponse,_ = call_groq_durable([{"role":"system","content":sys_prompt}]+msgs_for_groq[-20:])
                st.session_state.messages.append({"role":"assistant","content":sanitize_assistant(reponse)})
            supabase.table("licences").update({"used":used+1}).eq("key",licence_key).execute()
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {str(e)[:400]}")
    st.stop()

# SI NOVA = NOUVEAU STUDIO CAPCUT AVEC DOUBLE SIDEBAR
# PREMIER SIDEBAR FIN + SECOND SIDEBAR + EDITEUR
col_icon, col_tools, col_editor = st.columns([0.08, 0.24, 0.68], gap="small")

with col_icon:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=56)
    else:
        st.markdown("<div style='width:56px;height:56px;background:linear-gradient(135deg,#7c3aed,#db2777);border-radius:14px;display:flex;align-items:center;justify-content:center;color:white;font-size:22px;'>🚀</div>", unsafe_allow_html=True)
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    if st.button("💬", key="nav_nova_ai", help="Nova AI Chat", use_container_width=True):
        st.session_state.nova_tab="nova_ai"; st.rerun()
    st.caption("Nova AI")
    if st.button("🖼️", key="nav_montage", help="Montage photo", use_container_width=True):
        st.session_state.nova_tab="montage"; st.rerun()
    st.caption("Montage")
    if st.button("⚙️", key="nav_params", help="Paramètres", use_container_width=True):
        st.session_state.nova_tab="params"; st.rerun()
    st.caption("Paramètres")
    st.divider()
    if st.button("🚪", key="nav_logout_nova"):
        supabase.auth.sign_out()
        if "user" in st.session_state: del st.session_state.user
        st.rerun()

with col_tools:
    # BOUTONS LANGUES ET CLAIR/SOMBRE EN HAUT A GAUCHE JUSTE A DROITE DU PREMIER SIDEBAR
    c_theme, c_lang = st.columns(2)
    with c_theme:
        st.button("☀️ Clair" if is_dark else "🌙 Sombre", key="btn_theme_nova", on_click=toggle_theme, use_container_width=True)
    with c_lang:
        st.button(f"🌐 {st.session_state.lang}", key="btn_lang_nova", on_click=toggle_lang, use_container_width=True)
    st.divider()
    if st.session_state.nova_tab == "nova_ai":
        st.markdown("### 💬 Nova AI - Chat")
        st.caption("Ton studio IA qui répond comme un chat")
        # LOGOS DU SCREEN DANS NOVA AI CHAT
        logo_path = "logo.png" if os.path.exists("logo.png") else None
        for m in st.session_state.messages[-10:]:
            if m.get("role")=="system": continue
            if m["role"]=="user":
                with st.chat_message("user"): st.markdown(sanitize_user(m["content"])[:120])
            else:
                with st.chat_message("assistant", avatar=logo_path if logo_path else "🚀"):
                    st.markdown(sanitize_assistant(m["content"])[:200])
                    if "image" in m and m["image"]: st.image(m["image"], use_container_width=True)
        if st.button("🗑️ Nouvelle discussion", key="new_chat_nova"):
            st.session_state.messages=[{"role":"assistant","content":L["welcome_nova"]}]; st.rerun()
    elif st.session_state.nova_tab == "montage":
        st.markdown("### 🖼️ Montage photo")
        st.caption("Tout ce qu'il y a dans CapCut")
        with st.expander("📁 Média", expanded=True):
            st.file_uploader("Importer média", type=["png","jpg","jpeg","mp4"], key="media_up")
            st.button("Stock vidéos", use_container_width=True)
            st.button("Mes projets", use_container_width=True)
        with st.expander("🎵 Audio"):
            st.button("Musiques libres", use_container_width=True)
            st.button("Effets sonores", use_container_width=True)
            st.button("Extraire audio", use_container_width=True)
            st.button("Voix off IA", use_container_width=True)
        with st.expander("🔤 Texte"):
            st.button("Titres animés", use_container_width=True)
            st.button("Sous-titres auto", use_container_width=True)
            st.button("Animations texte", use_container_width=True)
        with st.expander("😃 Stickers"):
            st.button("Emoji", use_container_width=True)
            st.button("Formes", use_container_width=True)
        with st.expander("✨ Effets"):
            st.button("Effets vidéo", use_container_width=True)
            st.button("Effets corps", use_container_width=True)
        with st.expander("🔀 Transitions"):
            st.button("Fondu", use_container_width=True)
            st.button("Zoom", use_container_width=True)
            st.button("Glitch", use_container_width=True)
        with st.expander("🎨 Filtres"):
            st.button("Cinématique", use_container_width=True)
            st.button("Vintage", use_container_width=True)
        with st.expander("🪄 Outils IA"):
            st.button("Supprimer arrière-plan", use_container_width=True)
            st.button("Auto-cut silences", use_container_width=True)
            st.button("Upscale 4K", use_container_width=True)
            st.button("Générer miniature 1280x720", use_container_width=True)
    else:
        st.markdown("### ⚙️ Paramètres")
        st.success(f"Connecté : {st.session_state.user.email}")
        st.markdown(f"Plan : {plan}")
        st.markdown(f"Utilisé : {used}/{max_req}")
        st.divider()
        st.button("Déconnexion", key="deco_nova", use_container_width=True)

with col_editor:
    if st.session_state.nova_tab == "nova_ai":
        st.markdown(f"<div style='background:{GRADIENT_NOVA};border-radius:16px;padding:16px;color:white;'><b>Nova Studio - Chat IA</b> - {L['nova_tag']}</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:15px;'></div>", unsafe_allow_html=True)
        logo_path = "logo.png" if os.path.exists("logo.png") else None
        for m in st.session_state.messages:
            if m.get("role")=="system": continue
            if m["role"]=="user":
                with st.chat_message("user"): st.markdown(sanitize_user(m["content"]))
            else:
                with st.chat_message("assistant", avatar=logo_path if logo_path else "🚀"):
                    st.markdown(sanitize_assistant(m["content"]))
                    if "image" in m and m["image"]: st.image(m["image"], use_container_width=True)
        if st.button(L["file_btn"], key="file_btn_nova"):
            st.session_state.show_uploader = not st.session_state.show_uploader; st.rerun()
        if st.session_state.show_uploader:
            up = st.file_uploader("file", type=["png","jpg","jpeg","pdf","txt","mp4","mp3"], label_visibility="collapsed", key="uploader_nova")
            if up:
                st.session_state.uploaded_file_info={"name":up.name}
                if up.type.startswith("image/"): st.image(up,width=400)
        prompt_raw = st.chat_input(L["ask_nova"], key="chat_input_nova")
        if prompt_raw:
            check_rate_limit(plan)
            prompt_clean = sanitize_user(prompt_raw)
            if st.session_state.uploaded_file_info: prompt_clean = f"[Fichier : {st.session_state.uploaded_file_info['name']}] {prompt_clean}"
            st.session_state.messages.append({"role":"user","content":prompt_clean})
            msgs_for_groq = [{"role":mm["role"],"content":sanitize_user(mm["content"])} for mm in st.session_state.messages if mm.get("role")!="system" and "image" not in mm]
            sys_prompt = SYSTEM_NOVA + f"\nRéponds en {st.session_state.lang}. Si on te demande qui t'a créée : Je suis Nova, créée par BehaviorLab AI."
            try:
                if demande_image(prompt_clean):
                    with st.spinner("Nova crée ton visuel studio..."):
                        img,enhanced = generer_image_comportementale(prompt_clean, plan)
                        reponse,_ = call_groq_durable([{"role":"system","content":sys_prompt}]+msgs_for_groq[-12:])
                        st.session_state.messages.append({"role":"assistant","content":sanitize_assistant(reponse),"image":img})
                else:
                    reponse,_ = call_groq_durable([{"role":"system","content":sys_prompt}]+msgs_for_groq[-20:])
                    st.session_state.messages.append({"role":"assistant","content":sanitize_assistant(reponse)})
                supabase.table("licences").update({"used":used+1}).eq("key",licence_key).execute()
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {str(e)[:400]}")
    else:
        st.markdown(f"<div style='background:{GRADIENT_NOVA};border-radius:16px;padding:16px;color:white;display:flex;justify-content:space-between;align-items:center;'><span><b>Studio Nova - 1280x720</b> - Montage photo</span><span>● REC</span></div>", unsafe_allow_html=True)
        st.markdown("<div style='height:15px;'></div>", unsafe_allow_html=True)
        # CANVAS STYLE CANVA
        st.markdown(f"<div style='background:{CARD_BG};border:2px solid #db2777;border-radius:16px;height:360px;display:flex;align-items:center;justify-content:center;color:{TEXT};'>Aperçu 1280x720 - Glisse ton média ici<br>Génère avec Nova AI</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:15px;'></div>", unsafe_allow_html=True)
        # TIMELINE STYLE CAPCUT
        st.markdown(f"""
        <div style='background:#1e1b4b;border-radius:12px;padding:12px;color:#c4b5fd;'>
        <b>Timeline</b><br>
        <div style='background:#2a2250;height:45px;border-radius:8px;margin:8px 0;display:flex;align-items:center;padding:0 12px;'>🎬 Vidéo 1 - 00:00:05</div>
        <div style='background:#3a2a60;height:35px;border-radius:8px;margin:8px 0;display:flex;align-items:center;padding:0 12px;'>🎵 Audio - Musique libre</div>
        <div style='background:#4a3560;height:30px;border-radius:8px;margin:8px 0;display:flex;align-items:center;padding:0 12px;'>🔤 Texte - Hook</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:15px;'></div>", unsafe_allow_html=True)
        c_exp1, c_exp2, c_exp3 = st.columns(3)
        with c_exp1:
            if st.button("Exporter 1080p", use_container_width=True): st.success("Export simulé 1280x720 Pillow OK")
        with c_exp2:
            if st.button("Générer miniature IA", use_container_width=True):
                img, _ = generer_image_comportementale("miniature qui clique", plan)
                st.image(img, use_container_width=True)
        with c_exp3:
            if st.button("Demander à Nova AI", use_container_width=True):
                st.session_state.nova_tab="nova_ai"; st.rerun()
