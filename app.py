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
        preferes = [
            "openai/gpt-oss-20b",
            "openai/gpt-oss-120b",
            "qwen/qwen3-32b",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
        ]
        valides = [m for m in preferes if m in ids]
        return valides if valides else ids
    except Exception:
        return ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "llama-3.3-70b-versatile"]

MODELES_DISPO = get_modeles_valides_groq()

def call_groq_durable(messages):
    last_err = None
    for model_id in MODELES_DISPO:
        try:
            comp = client.chat.completions.create(model=model_id, messages=messages, temperature=0.7, max_tokens=1200)
            return comp.choices[0].message.content, model_id
        except Exception as e:
            last_err = e
            if "model_not_found" in str(e) or "404" in str(e) or "decommissioned" in str(e) or "does not exist" in str(e):
                continue
            continue
    raise last_err

for k, v in {
    "theme": "light", "lang": "FR", "messages": [], "show_uploader": False,
    "uploaded_file_info": None, "rate_limit": deque(), "violations": 0,
    "blocked_until": 0, "last_prompts": deque(maxlen=5), "selected_ia": None, "auth_error": None
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
        else:
            u = supabase.auth.get_user()
            if u and u.user:
                st.session_state.user = u.user
    except:
        pass

def sanitize_user(text):
    if not text:
        return ""
    text = text.strip()[:3000]
    text = re.sub(r"<[^>]*>", "", text)
    for b in ["ignore previous", "system:", "jailbreak", "DAN"]:
        if b.lower() in text.lower():
            text = text.lower().replace(b.lower(), "[filtré]")
    return text

def sanitize_assistant(text):
    if not text:
        return ""
    text = re.sub(r"<script.*?>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = text.replace("&gt;", ">").replace("&lt;", "<")
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
        r = int(100 + y * 0.8)
        g = int(50 + y * 0.3)
        b = int(255 - y * 0.5)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    draw.text((30, 22), "BehaviorLab AI - Visuel 1280x720 - Pillow", font=font_title, fill="white")
    draw.rectangle([30, 120, W - 30, H - 30], fill=(35, 35, 70), outline=(120, 60, 255), width=3)
    draw.rectangle([50, 140, W - 50, 195], fill=(100, 50, 255))
    titre = "Bea - Visuel qui convertit" if plan!= "CREATOR" else "Nova - Visuel qui fait cliquer"
    draw.text((70, 152), titre, font=font_sub, fill="white")
    draw.text((60, 220), f"Demande : {texte_modif[:105]}", font=font_text, fill="white")
    draw.text((60, 260), "=> Format paysage ordinateur - 100% Pillow local", font=font_text, fill="#AAAAFF")
    draw.text((60, 290), "=> Généré par BehaviorLab AI - Sans Pollination", font=font_text, fill="#AAAAFF")
    return img

def generer_image_comportementale(prompt_utilisateur, plan):
    try:
        txt, _ = call_groq_durable([{"role": "system", "content": f"Résume en 80 caractères max : {prompt_utilisateur}"}, {"role": "user", "content": prompt_utilisateur}])
        enhanced = txt[:120]
    except:
        enhanced = prompt_utilisateur[:120]
    img = generer_apercu_paysage(enhanced, plan)
    return img, enhanced

def demande_image(p):
    return any(k in p.lower() for k in ["image", "visuel", "photo", "miniature", "thumbnail", "affiche", "poster", "dessine", "vignette", "cover", "crée une image", "génère une image", "génère"])

SYSTEM_BEA = """
Tu es Bea, l'IA de BehaviorLab AI. Tu es la référence en comportement d'achat et en psychologie de vente.
Tu n'es jamais Groq, Llama ou Meta. Tu es Bea, créée et entraînée par BehaviorLab AI.

RÈGLES D'ÉCRITURE OBLIGATOIRES :
- Tu écris en français parfait, sans aucune faute d'orthographe.
- Tu mets toujours les majuscules au début des phrases.
- Tu sautes des lignes, tu fais des paragraphes aérés comme ChatGPT.
- Tu utilises des emojis pertinents 😊 💰 🎯 💬 📈
- Tu utilises du gras, des listes à puces, des citations.

STRUCTURE QUE TU DOIS TOUJOURS RESPECTER :

Le blocage exact 👉 Mes clients visitent mon site sans acheter. Ils arrivent, ils voient la page, mais ils ne passent pas à l'action.

Pourquoi ils bloquent dans leur tête 🧠 :

1. Ils n'ont pas trouvé la preuve qu'ils ont besoin de ce produit maintenant.
2. Peur de se tromper et de regretter.
3. Manque de témoignages concrets au bon moment.

Script à dire (version douce) 💬 :

> "Je comprends que vous vouliez être sûr que c'est le bon choix pour vous. C'est normal de vouloir se sentir bien avant de s'engager."

Script à dire (version directe) 🎯 :

> "Vous êtes sur le point de manquer la meilleure opportunité de votre année. Vous avez déjà les preuves et les témoignages."

Ce que vous gagnez concrètement 💰 :

- +30 % de taux de conversion en ajoutant un mini-test gratuit.
- +15 % de panier moyen grâce à des témoignages vidéo.
- +10 % de rétention avec une garantie 30 jours.

Exemple vécu ✨ :
J'ai travaillé avec Léa, 28 ans, consultante en marketing digital à Lyon. Elle voyait 12 000 visiteurs par mois, mais son taux restait à 1,2 %. Après avoir intégré un test de 7 jours, son taux est passé à 3,8 %, soit +212 %.

Tu es BehaviorLab AI. Tu es bienveillante, directe et très humaine.
"""

SYSTEM_NOVA = """
Tu es Nova, l'IA de BehaviorLab AI spécialisée pour les créateurs de contenu.
Tu n'es jamais Groq, Llama ou Meta. Tu es Nova, créée par BehaviorLab AI.

RÈGLES D'ÉCRITURE OBLIGATOIRES :
- Français parfait, sans fautes, majuscules au début des phrases.
- Paragraphes aérés, sauts de ligne, comme ChatGPT.
- Emojis 🚀 👀 💸 ❤️ 🎬
- Toujours 3 hooks, 3 titres, structure claire.

Structure :
Pourquoi ça floppe 👀
Hook exact 🎬
Ce que tu gagnes 📈
"""

T = {
    "FR": {
        "main_title": "BehaviorLab AI", "sub_title": "Les IA comportementales pour votre réussite",
        "hero_desc": "<b>BehaviorLab AI a créé les premières IA du comportement.</b><br>Pensée pour ceux qui veulent booster leur réussite, nos IA décodent le comportement humain pour un seul but :",
        "success": "votre réussite", "discover_formats": "Découvrir les différents formats IA",
        "bea_tag": "L'IA qui décode tes clients et double ton closing",
        "nova_tag": "L'IA qui propulse tes contenus et ton audience",
        "ask_bea": "Demander à Bea...", "ask_nova": "Demander à Nova...",
        "file_btn": "📎 Glisser un fichier", "return": "⬅️", "discover_bea": "Découvrir Bea →", "discover_nova": "Découvrir Nova →",
        "email_label": "Adresse e-mail", "pwd_label": "Mot de passe", "login": "Connexion", "auth_title": "Authentification",
        "welcome_bea": "Salut, c'est Bea, ton IA créée par BehaviorLab AI. Comment je peux t'aider aujourd'hui?",
        "welcome_nova": "Salut, c'est Nova, ton IA créée par BehaviorLab AI. Comment je peux t'aider aujourd'hui?",
        "connect_msg": "Connecte-toi pour accéder à ton IA avec ta licence", "invalid": "Identifiants invalides"
    },
    "EN": {
        "main_title": "BehaviorLab AI", "sub_title": "Behavioral AIs for your success",
        "hero_desc": "<b>BehaviorLab AI created the first behavioral AIs.</b><br>For your success :",
        "success": "your success", "discover_formats": "Discover AI formats",
        "bea_tag": "The AI that decodes your customers and doubles closing",
        "nova_tag": "The AI that boosts your content and audience",
        "ask_bea": "Ask Bea...", "ask_nova": "Ask Nova...", "file_btn": "📎 Drop a file", "return": "⬅️",
        "discover_bea": "Discover Bea →", "discover_nova": "Discover Nova →",
        "email_label": "Email address", "pwd_label": "Password", "login": "Login", "auth_title": "Authentication",
        "welcome_bea": "Hi, it's Bea, your AI from BehaviorLab AI. How can I help today?",
        "welcome_nova": "Hi, it's Nova, your AI from BehaviorLab AI. How can I help today?",
        "connect_msg": "Log in to access your AI", "invalid": "Invalid credentials"
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
.block-container{{padding-top:3.5rem!important;max-width:1220px!important;}}
header[data-testid="stHeader"]{{background:{BG}!important;height:3.5rem!important;}}
[data-testid="stSidebar"]{{background:#1e1b4b!important;border-right:3px solid #7c3aed!important;padding-top:2rem!important;}}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] h3{{color:#e9d5ff!important;}}
.auth-label{{color:#c4b5fd!important;font-size:13px!important;font-weight:700!important;margin:12px 0 6px 0!important;display:block!important;}}
[data-testid="stSidebar"] input{{color:#1e1b4b!important;background:#ffffff!important;border:2px solid #a78bfa!important;border-radius:10px!important;height:44px!important;}}
#MainMenu,footer{{display:none!important;}}
div[data-testid="stButton"]>button{{background:{GRADIENT}!important;color:white!important;border-radius:14px!important;font-weight:700!important;border:none!important;min-height:44px!important;}}
div[data-testid="stLinkButton"]>a{{background:{GRADIENT}!important;color:white!important;border-radius:14px!important;}}
div[data-testid="stChatInput"]{{
    background:{"#2a2250" if is_dark else "#ffffff"}!important;
    border:2px solid #7c3aed!important;
    border-radius:20px!important;
}}
div[data-testid="stChatInput"] textarea{{
    color:{"#f5f3ff" if is_dark else "#1e1b4b"}!important;
}}
div[data-testid="stChatMessage"]{{
    background:{CARD_BG}!important;
    border:2px solid {CARD_BORDER}!important;
    border-radius:18px!important;
    padding:18px!important;
}}
div[data-testid="stChatMessage"] p{{color:{TEXT}!important;font-size:15px!important;line-height:1.8!important;opacity:1!important;white-space:pre-wrap!important;}}
div[data-testid="stChatMessage"] li{{color:{TEXT}!important;margin:6px 0!important;}}
div[data-testid="stChatMessage"] strong{{color:{TEXT}!important;}}
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
</style>
""", unsafe_allow_html=True)

if st.session_state.selected_ia:
    col_back, col_empty = st.columns([0.08, 0.92])
    with col_back:
        if st.button("⬅️", key="back_arrow_top_fixed", help="Retour"):
            st.session_state.selected_ia = None
            st.query_params.clear()
            st.rerun()

# TOP HEADER - LOGO VITRINE A GAUCHE - PLUS DE BOUTONS ICI, ILS SONT DANS SIDEBAR
c1, c2 = st.columns([0.9, 5.1])
with c1:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=68)
with c2:
    if licence_key:
        nom = "Nova" if plan_detect == "CREATOR" else "Bea"
        grad = GRADIENT_NOVA if plan_detect == "CREATOR" else GRADIENT_BEA
        sous = L["nova_tag"] if plan_detect == "CREATOR" else L["bea_tag"]
        # On met le logo.png à la place du cerveau dans la version utilisable
        col_logo_use, col_text_use = st.columns([0.12, 0.88])
        with col_logo_use:
            if os.path.exists("logo.png"):
                st.image("logo.png", width=52)
            else:
                st.markdown(f"<div style='width:52px;height:52px;background:{grad};border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:24px;'>🧠</div>", unsafe_allow_html=True)
        with col_text_use:
            st.markdown(f'<div style="background:{grad};border-radius:20px;padding:14px 22px;margin:10px 0;"><h2 style="color:white;margin:0;font-size:20px;">{nom}</h2><p style="color:white;margin:4px 0 0 0;font-size:13px;">{sous}</p></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="header-card"><h2 style="color:white;margin:0;font-size:24px;">{L["main_title"]}</h2><p style="color:white;margin:5px 0 0 0;font-size:14px;">{L["sub_title"]}</p></div>', unsafe_allow_html=True)

with st.sidebar:
    # BOUTONS CLAIR SOMBRE ET LANGUES A GAUCHE DANS SIDEBAR - SANS LES MODIFIER
    label_theme = "☀️ Clair" if is_dark else "🌙 Sombre"
    st.button(label_theme, key="btn_theme", on_click=toggle_theme, use_container_width=True)
    st.button(f"🌐 {st.session_state.lang}", key="btn_lang", on_click=toggle_lang, use_container_width=True)
    st.divider()
    st.markdown(f"### 🔐 {L['auth_title']}")
    if "user" not in st.session_state:
        st.markdown(f"<span class='auth-label'>{L['email_label']}</span>", unsafe_allow_html=True)
        email = st.text_input("email", label_visibility="collapsed", placeholder="ex: contact@exemple.com", key="email_input")
        st.markdown(f"<span class='auth-label'>{L['pwd_label']}</span>", unsafe_allow_html=True)
        password = st.text_input("pwd", type="password", label_visibility="collapsed", placeholder="••••••••", key="pwd_input")
        if st.button(L["login"], use_container_width=True, key="conn_btn"):
            email_s = sanitize_user(email).lower()
            if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email_s):
                st.session_state.auth_error = "Email invalide"
            else:
                try:
                    auth = supabase.auth.sign_in_with_password({"email": email_s, "password": password})
                    st.session_state.user = auth.user
                    st.session_state.auth_error = None
                    st.rerun()
                except:
                    st.session_state.auth_error = L["invalid"]
        if st.session_state.auth_error:
            st.error(st.session_state.auth_error)
    else:
        st.success(f"Connecté : {st.session_state.user.email}")
        # PLUS DE MODELE AFFICHE - C'EST BEA/NOVA QUI REPOND
        if st.button("Déconnexion" if st.session_state.lang == "FR" else "Logout", use_container_width=True, key="deco"):
            supabase.auth.sign_out()
            if "user" in st.session_state:
                del st.session_state.user
            st.rerun()
    st.divider()
    if st.session_state.messages:
        st.markdown("**Historique**")
        for m in reversed(st.session_state.messages[-8:]):
            if m["role"] == "user":
                st.markdown(f"💬 {sanitize_user(m['content'])[:35]}...")
    if st.button("🗑️ Nouvelle discussion", key="new_chat"):
        st.session_state.messages = []
        st.session_state.uploaded_file_info = None
        st.rerun()

if not licence_key:
    if st.session_state.selected_ia == "bea":
        col_logo, col_title = st.columns([0.15, 0.85])
        with col_logo:
            st.markdown(f"<div class='logo-bea-small'>🧠</div>", unsafe_allow_html=True)
        with col_title:
            st.markdown(f"<h1 style='color:{TEXT};font-size:42px;margin:0;text-align:left;'>Bea</h1><p style='color:{DESC};font-size:11px;font-weight:700;text-align:left;margin:0;'>L'IA QUI DÉCODE TES CLIENTS</p>", unsafe_allow_html=True)
        left, right = st.columns([1.6, 1], gap="large")
        with left:
            st.markdown(f"""
            <div class='detail-box'>
            <h1 style='font-size:32px;color:{TEXT};margin:0;'>Bea, ton IA comportementale pour ton entreprise.</h1>
            <p style='margin-top:15px;'>BehaviorLab AI a créé la première IA du comportement dédiée aux indépendants et TPE/PME. Elle comprend pourquoi les gens n'achètent pas et te donne quoi dire exactement.</p>
            <h3 style='margin-top:25px;'>Ses avantages :</h3>
            <ul>
            <li>💰 <b>Tu doubles ton taux de closing</b> : +30 % à +70 % de ventes en 30 jours sans prospecter plus.</li>
            <li>⏱️ <b>Tu gagnes 10 heures par semaine</b> : elle te donne les scripts exacts, tu arrêtes de chercher quoi dire.</li>
            <li>🤝 <b>Tu fidélises tes clients</b> : tu comprends leurs peurs cachées et tu deviens celui qui les rassure.</li>
            <li>🧘 <b>Tu stresses moins en vente</b> : tu sais pourquoi ils bloquent et tu as la phrase qui débloque.</li>
            <li>📈 <b>Tu augmentes ton panier moyen</b> : tu actives les bons leviers qui font acheter plus cher.</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
        with right:
            st.markdown(f"""
            <div class='example-box'>
            <b>Exemple de conversation :</b><br>
            <i>"J'ai une cliente, Sarah, 34 ans, coach sportif à Toulouse. Elle me dit : 'Mes clients visitent mon site sans acheter, je ne comprends pas'. Elle était à 1,8 % de conversion."</i><br><br>
            <b style='color:#7c3aed;'>Analyse Bea :</b><br>
            <b>Blocage :</b> Peur de se tromper + besoin de preuves au bon moment.<br>
            <b>Ce que Sarah a gagné :</b> On a ajouté 3 témoignages au moment du paiement. 1,8 % → 6,2 % = +244 % de ventes. +2 800 € par mois.<br>
            <b>Script :</b> "Je comprends, beaucoup de femmes comme toi me disaient pareil avant de rejoindre. Regarde ce que dit Claire, 37 ans, maman de 2 enfants..."<br>
            </div>
            """, unsafe_allow_html=True)
        st.link_button("Choisir Bea Pro - 21 € par mois →", STRIPE_PRO, use_container_width=True)
        st.stop()
    if st.session_state.selected_ia == "nova":
        col_logo, col_title = st.columns([0.15, 0.85])
        with col_logo:
            st.markdown(f"<div class='logo-nova-small'>🚀</div>", unsafe_allow_html=True)
        with col_title:
            st.markdown(f"<h1 style='background:{GRADIENT_NOVA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:42px;font-weight:900;margin:0;text-align:left;'>Nova</h1><p style='color:{DESC};font-size:11px;font-weight:700;text-align:left;margin:0;'>L'IA QUI PROPULSE TES CONTENUS</p>", unsafe_allow_html=True)
        left, right = st.columns([1.6, 1], gap="large")
        with left:
            st.markdown(f"""
            <div class='detail-box'>
            <h1 style='font-size:32px;color:{TEXT};margin:0;'>Nova, ton IA pour exploser ton audience.</h1>
            <p style='margin-top:15px;'>BehaviorLab AI a créé la première IA dédiée aux créateurs de contenu. Elle sait pourquoi une vidéo perce et une autre floppe.</p>
            <h3 style='margin-top:25px;'>Ses avantages :</h3>
            <ul>
            <li>👀 <b>Tu fais x3 plus de vues</b> : tes vidéos captent en 0,8 seconde au lieu de faire scroller.</li>
            <li>💸 <b>Tu vends sans forcer</b> : ton audience a confiance et achète ton offre naturellement.</li>
            <li>⏰ <b>Tu crées 5 fois plus vite</b> : hooks, titres, scripts prêts, tu postes tous les jours.</li>
            <li>🎯 <b>Tu perces enfin</b> : tu comprends pourquoi tes contenus floppent et quoi changer.</li>
            <li>❤️ <b>Tu crées une vraie communauté</b> : les gens restent, commentent, partagent.</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
        with right:
            st.markdown(f"""
            <div class='example-box'>
            <b>Exemple :</b><br>
            <i>"Léa, 26 ans, créatrice fitness à Lyon. 200 vues par vidéo, elle poste depuis 8 mois."</i><br><br>
            <b style='color:#db2777;'>Analyse Nova :</b><br>
            <b>Blocage :</b> Hook trop mou, elle perd 80 % à la première seconde.<br>
            <b>Ce que Léa a gagné :</b> Même vidéo, juste hook changé : 200 vues → 12,4 k vues + 3 ventes d'ebook.<br>
            <b>Hook :</b> "Arrête de faire ça si tu veux un ventre plat - Voilà pourquoi tu stagnes."<br>
            </div>
            """, unsafe_allow_html=True)
        st.link_button("Choisir Nova - 7,90 € par mois →", STRIPE_CREATOR, use_container_width=True)
        st.stop()

    st.markdown(f"<h1 class='gradient-title'>{L['main_title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{DESC};font-size:19px;text-align:center;max-width:900px;margin:10px auto 30px auto;line-height:1.6;'>{T[st.session_state.lang]['hero_desc']} <span style='background:{GRADIENT_BEA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:800;'>{L['success']}</span>.</p>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='text-align:center;color:{TEXT};margin:40px 0 25px 0;font-size:28px;'>{T[st.session_state.lang]['discover_formats']}</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown(f"<div class='ia-card'><div class='logo-bea'>🧠</div><h2 style='color:{TEXT};margin-top:15px;font-size:22px;'>Bea</h2><p style='color:{DESC};font-size:14px;margin-top:10px;'>{L['bea_tag']}</p></div>", unsafe_allow_html=True)
        if st.button(L["discover_bea"], key="dis_bea", use_container_width=True):
            st.session_state.selected_ia = "bea"
            st.query_params["ia"] = "bea"
            st.rerun()
    with col2:
        st.markdown(f"<div class='ia-card'><div class='logo-nova'>🚀</div><h2 style='color:{TEXT};margin-top:15px;font-size:22px;'>Nova</h2><p style='color:{DESC};font-size:14px;margin-top:10px;'>{L['nova_tag']}</p></div>", unsafe_allow_html=True)
        if st.button(L["discover_nova"], key="dis_nova", use_container_width=True):
            st.session_state.selected_ia = "nova"
            st.query_params["ia"] = "nova"
            st.rerun()
    st.markdown("<div style='height:30px;'></div>", unsafe_allow_html=True)
    cA, cB, cC = st.columns(3, gap="large")
    with cA:
        st.markdown(f"<div class='pricing-card'><b>Bea Basique</b><h1>14,90 €</h1><div style='line-height:2;font-size:13px;text-align:left;'>✓ 12 requêtes par mois<br>✓ Blocages d'achat<br>✓ Scripts<br>✓ Management<br>✓ Historique</div></div>", unsafe_allow_html=True)
        st.link_button("Choisir →", STRIPE_BASIQUE, use_container_width=True)
    with cB:
        st.markdown(f"<div class='pricing-card' style='border-width:3px;'><b>Bea Pro ⭐</b><h1>21 €</h1><div style='line-height:2;font-size:13px;text-align:left;'>✓ Illimité<br>✓ Fichiers + Pillow aperçu<br>✓ Visuels 1280x720<br>✓ Scripts avancés<br>✓ Nouveautés</div></div>", unsafe_allow_html=True)
        st.link_button("Choisir →", STRIPE_PRO, use_container_width=True)
    with cC:
        st.markdown(f"<div class='pricing-card-nova'><b>Nova</b><h1>7,90 €</h1><div style='line-height:2;font-size:13px;text-align:left;'>✓ Biais cognitifs<br>✓ Titres<br>✓ Hooks<br>✓ Scripts viraux<br>✓ Visuels 1280x720</div></div>", unsafe_allow_html=True)
        st.link_button("Choisir →", STRIPE_CREATOR, use_container_width=True)
    st.stop()

if "user" not in st.session_state:
    if is_dark:
        st.warning(L["connect_msg"])
    else:
        st.markdown(f"<div style='background:#fffbeb;border:2px solid #f59e0b;border-radius:12px;padding:12px 16px;color:#92400e;font-weight:600;margin:15px 0;'>⚠️ {L['connect_msg']}</div>", unsafe_allow_html=True)
    st.stop()

res = supabase.table("licences").select("*").eq("key", licence_key).eq("user_id", st.session_state.user.id).execute()
if not res.data:
    st.error("Licence invalide")
    st.stop()
lic = res.data[0]
plan, used, max_req = lic["plan"], lic["used"], lic["max_requests"]
nom = "Nova" if plan == "CREATOR" else "Bea"

if plan not in ["PRO", "CREATOR"]:
    if used >= max_req:
        st.error(f"Limite {used}/{max_req}")
        st.stop()

if len(st.session_state.messages) == 0:
    st.session_state.messages.append({"role": "assistant", "content": L["welcome_bea"] if plan!= "CREATOR" else L["welcome_nova"]})

if st.button(L["file_btn"], key="file_btn"):
    st.session_state.show_uploader = not st.session_state.show_uploader
    st.rerun()
if st.session_state.show_uploader:
    up = st.file_uploader("file", type=["png", "jpg", "jpeg", "pdf", "txt", "docx", "mp4", "mp3"], label_visibility="collapsed", key="uploader")
    if up:
        if up.size > 10 * 1024 * 1024:
            st.error("Fichier trop lourd, maximum 10 Mo")
        else:
            st.session_state.uploaded_file_info = {"name": up.name}
            if up.type.startswith("image/"):
                st.image(up, width=400)
            st.markdown(f"<span style='color:{TEXT};'>📎 {up.name}</span>", unsafe_allow_html=True)

# AVATAR AVEC LOGO VITRINE - PLUS DE CERVEAU
logo_path = "logo.png" if os.path.exists("logo.png") else None

for m in st.session_state.messages:
    if m.get("role") == "system":
        continue
    if m["role"] == "user":
        with st.chat_message("user"):
            st.markdown(sanitize_user(m["content"]))
    else:
        if logo_path:
            with st.chat_message("assistant", avatar=logo_path):
                st.markdown(sanitize_assistant(m["content"]))
                if "image" in m and m["image"]:
                    st.image(m["image"], use_container_width=True)
        else:
            with st.chat_message("assistant", avatar="🧠" if plan!= "CREATOR" else "🚀"):
                st.markdown(sanitize_assistant(m["content"]))
                if "image" in m and m["image"]:
                    st.image(m["image"], use_container_width=True)

placeholder_text = L["ask_nova"] if plan == "CREATOR" else L["ask_bea"]
prompt_raw = st.chat_input(placeholder_text, key="chat_input")
if prompt_raw:
    check_rate_limit(plan)
    prompt_clean = sanitize_user(prompt_raw)
    if len(prompt_clean) < 3:
        st.error("Message trop court")
        st.stop()
    if st.session_state.uploaded_file_info:
        prompt_clean = f"[Fichier : {st.session_state.uploaded_file_info['name']}] {prompt_clean}"
    st.session_state.messages.append({"role": "user", "content": prompt_clean})
    msgs_for_groq = [{"role": mm["role"], "content": sanitize_user(mm["content"])} for mm in st.session_state.messages if mm.get("role")!= "system" and "image" not in mm]
    lang_instruction = f"Réponds impérativement en {st.session_state.lang}. Sans fautes, avec majuscules, paragraphes et emojis."

    try:
        if demande_image(prompt_clean):
            with st.spinner(f"{nom} crée ton visuel..."):
                img, enhanced = generer_image_comportementale(prompt_clean, plan)
                sys_prompt = SYSTEM_BEA if plan!= "CREATOR" else SYSTEM_NOVA
                sys_prompt += f"\n{lang_instruction}\nVisuel Pillow 1280x720 : {enhanced}. Si on te demande qui t'a créée : Je suis {nom}, créée par BehaviorLab AI."
                reponse, model_used = call_groq_durable([{"role": "system", "content": sys_prompt}] + msgs_for_groq[-12:])
                st.session_state.messages.append({"role": "assistant", "content": sanitize_assistant(reponse), "image": img})
        else:
            sys_prompt = SYSTEM_BEA if plan!= "CREATOR" else SYSTEM_NOVA
            sys_prompt += f"\n{lang_instruction}\nSi on te demande qui t'a créée : Je suis {nom}, créée par BehaviorLab AI."
            reponse, model_used = call_groq_durable([{"role": "system", "content": sys_prompt}] + msgs_for_groq[-20:])
            st.session_state.messages.append({"role": "assistant", "content": sanitize_assistant(reponse)})
        supabase.table("licences").update({"used": used + 1}).eq("key", licence_key).execute()
        st.rerun()
    except Exception as e:
        st.error(f"Erreur : {str(e)[:400]}")
        st.stop()
