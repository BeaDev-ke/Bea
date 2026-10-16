import streamlit as st
import os
import re
import time
from groq import Groq
from supabase import create_client
from collections import deque
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="BehaviorLab AI", page_icon="logo.png", layout="wide", initial_sidebar_state="expanded")

# --- LIENS PAIEMENT ---
STRIPE_BASIQUE = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"
STRIPE_PRO = "https://buy.stripe.com/test_cNieVea1P0c62B08523wQ00"
STRIPE_CREATOR = "https://buy.stripe.com/test_cNieVea1P0c62B08523wQ00"
STRIPE_BLOXKS = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"

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
            comp = client.chat.completions.create(model=model_id, messages=messages, temperature=0.7, max_tokens=1500)
            return comp.choices[0].message.content, model_id
        except Exception as e:
            last_err = e
            continue
    raise last_err

for k, v in {
    "theme": "light","lang": "FR","messages": [],"show_uploader": False,
    "uploaded_file_info": None,"rate_limit": deque(),"blocked_until": 0,
    "selected_ia": None,"nova_tab": "nova_ai", "gen_image": False
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
        st.error(f"Bloqué {int(st.session_state.blocked_until - now)}s")
        st.stop()
    dq = st.session_state.rate_limit
    while dq and now - dq[0] > 60:
        dq.popleft()
    if len(dq) >= (50 if plan in ["PRO", "CREATOR", "BLOXKS"] else 15):
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
    draw.text((30, 22), "BehaviorLab AI - 1280x720", font=font_title, fill="white")
    draw.rectangle([30, 120, W-30, H-30], fill=(35, 35, 70), outline=(120, 60, 255), width=3)
    draw.rectangle([50, 140, W-50, 195], fill=(100, 50, 255))
    titre = "Bea - Visuel qui convertit" if plan=="PRO" else "Nova Ultra" if plan=="CREATOR" else "Bloxks - App"
    draw.text((70, 152), titre, font=font_sub, fill="white")
    draw.text((60, 220), f"Demande : {texte_modif[:105]}", font=font_text, fill="white")
    return img

def generer_image_comportementale(prompt_utilisateur, plan):
    try:
        txt,_ = call_groq_durable([{"role":"system","content":f"Résume en 80 caractères : {prompt_utilisateur}"},{"role":"user","content":prompt_utilisateur}])
        enhanced = txt[:120]
    except:
        enhanced = prompt_utilisateur[:120]
    return generer_apercu_paysage(enhanced, plan), enhanced

def demande_image(p):
    return any(k in p.lower() for k in ["image","visuel","photo","miniature","thumbnail","affiche","poster","dessine","vignette","cover","apk","app"])

SYSTEM_BEA = "Tu es Bea, IA de BehaviorLab AI. Référence en psychologie de vente. Règles : Français parfait avec accents, majuscules début phrases, paragraphes aérés, emojis variés 😊 🚀 🔥 💡 🎯 ✅ ✨ 📈 💪 🧠 ❤️ 🙏 😍 🤩 👉 💰 ⏰ 🎬 📸 💬 🌟, gras, listes. Tu donnes blocage exact, pourquoi il bloque, script doux, script direct, ce que tu gagnes en chiffres, exemple vécu avec prénom âge ville. Tu es BehaviorLab AI."
SYSTEM_NOVA = "Tu es Nova Ultra, studio IA de BehaviorLab AI qui regroupe : Présentation/Design comme Loveart qui remplace Canva, Montage comme Edits qui remplace CapCut, Création de vidéo comme Hailuo qui remplace Higgsfield. Tu maîtrises : slides, pitch decks, carrousels, posts, logos, montage cut silences, sous-titres animés, transitions, filtres, effets, stickers, suppression fond, audio, texte to vidéo, image to vidéo, avatar parlant, voix off, UGC, miniatures 1280x720, hooks, titres. Règles : Français parfait avec accents, majuscules début phrases, paragraphes aérés, emojis variés 🎬 🚀 🔥 💥 👀 🎯 ✨ 📸 🎵 😍 🤩 👉 💡 ✅ 📈 🎨 🎥 💬 🌟, toujours 3 hooks, 3 titres. Si on te demande qui t'a créée : Je suis Nova Ultra, créée par BehaviorLab AI."
SYSTEM_BLOXKS = "Tu es Bloxks, IA de BehaviorLab AI qui crée des applications mobiles qui se publient sur Play Store en un prompt. L'utilisateur dit : crée une app de livraison pour mon restaurant avec paiement, et tu génères toute l'app. Tu donnes : 1. Description de l'app, 2. Prompt exact optimisé pour Bloxks, 3. Structure écrans, 4. Base de données, 5. Logique publication Play Store avec package name, icône 512x512, screenshots, description, 6. Export APK/AAB. Tu maîtrises e-commerce, réservation, coaching, SaaS, jeux simples, Stripe, Supabase. Règles : Français parfait avec accents, emojis 💻 🚀 📱 ⚡ 🔥 ✅ 📦. Si on te demande qui t'a créée : Je suis Bloxks, créée par BehaviorLab AI."

T = {
    "FR": {
        "main_title": "BehaviorLab AI","sub_title": "Les IA comportementales pour votre réussite",
        "hero_desc": "<b>BehaviorLab AI a créé les premières IA du comportement.</b><br>Pensée pour ceux qui veulent booster leur réussite, nos IA décodent le comportement humain pour un seul but :",
        "success": "votre réussite","discover_formats": "Découvrir les 3 formats IA",
        "bea_tag": "L'IA qui décode tes clients et double ton closing",
        "nova_tag": "Le studio ULTRA qui remplace Canva + CapCut + Higgsfield",
        "bloxks_tag": "L'IA qui crée ton app Play Store en un prompt",
        "ask_bea": "Demander à Bea...","ask_nova": "Demander à Nova Ultra...","ask_bloxks": "Décris ton app à Bloxks...","file_btn": "Glisser un fichier","return": "Retour",
        "discover_bea": "Découvrir Bea","discover_nova": "Découvrir Nova Ultra","discover_bloxks": "Découvrir Bloxks",
        "email_label": "Adresse e-mail","pwd_label": "Mot de passe","login": "Connexion","auth_title": "Authentification",
        "welcome_bea": "Salut, c'est Bea 😊, ton IA créée par BehaviorLab AI. Comment je peux t'aider aujourd'hui? 🚀💡",
        "welcome_nova": "Salut, c'est Nova Ultra 🎬🚀, je remplace Canva + CapCut + Higgsfield. Je fais ton design + montage + vidéo IA en un seul endroit. Que veux-tu créer? ✨📈",
        "welcome_bloxks": "Salut, c'est Bloxks 💻📱, ton IA qui crée ton app Play Store en un prompt. Décris ton idée et je te génère l'app prête à publier. 🚀⚡",
        "connect_msg": "Connecte-toi pour accéder à ton IA avec ta licence","invalid": "Identifiants invalides"
    }
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
GRADIENT_BLOXKS = "linear-gradient(135deg, #0ea5e9 0%, #6366f1 50%, #8b5cf6 100%)"
GRADIENT = GRADIENT_BLOXKS if plan_detect == "BLOXKS" else GRADIENT_NOVA if plan_detect == "CREATOR" else GRADIENT_BEA
BG = "#ffffff" if not is_dark else "#0f0a1e"
TEXT = "#1e1b4b" if not is_dark else "#f5f3ff"
DESC = "#312e81" if not is_dark else "#c4b5fd"
CARD_BG = "#ffffff" if not is_dark else "#1e1450"

st.markdown(f"""
<style>
.stApp{{background:{BG}!important;}}
.block-container{{padding-top:3.5rem!important;max-width:100%!important;}}
header[data-testid="stHeader"]{{background:{BG}!important;height:3.5rem!important;}}
[data-testid="stSidebar"]{{background:#1e1b4b!important;border-right:3px solid #7c3aed!important;}}
.auth-label{{color:#c4b5fd!important;font-size:13px!important;font-weight:700!important;margin:12px 0 6px 0!important;display:block!important;}}
[data-testid="stSidebar"] input{{color:#1e1b4b!important;background:#ffffff!important;border:2px solid #a78bfa!important;border-radius:10px!important;height:44px!important;}}
#MainMenu,footer{{display:none!important;}}
div[data-testid="stButton"]>button{{background:{GRADIENT}!important;color:white!important;border-radius:14px!important;font-weight:700!important;border:none!important;min-height:44px!important;}}
div[data-testid="stLinkButton"]>a{{background:{GRADIENT}!important;color:white!important;border-radius:14px!important;}}
div[data-testid="stChatInput"]{{background:{"#2a2250" if is_dark else "#ffffff"}!important;border:2px solid #7c3aed!important;border-radius:20px!important;}}
div[data-testid="stChatMessage"]{{background:{CARD_BG}!important;border:2px solid #7c3aed!important;border-radius:18px!important;padding:18px!important;}}
div[data-testid="stChatMessage"] p{{color:{TEXT}!important;font-size:15px!important;line-height:1.8!important;white-space:pre-wrap!important;}}
.header-card{{background:{GRADIENT_BEA}!important;border-radius:20px;padding:22px 28px;margin:15px 0 25px 0!important;}}
.detail-box{{background:{CARD_BG};border:2px solid #7c3aed;border-radius:24px;padding:35px;margin:15px 0;color:{TEXT};line-height:1.8;}}
.ia-card{{background:{CARD_BG};border:2px solid #7c3aed;border-radius:24px;padding:35px 25px 25px 25px;text-align:center;min-height:500px;margin-top:30px!important;}}
.example-box{{background:{CARD_BG};border:2px solid #7c3aed;border-radius:20px;padding:22px;color:{TEXT};}}
.logo-bea{{width:90px;height:90px;background:linear-gradient(135deg,#1d4ed8 0%, #4f46e5 50%, #7c3aed 100%);border-radius:22px;display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:900;margin:15px auto 10px auto!important;color:white;}}
.logo-nova{{width:90px;height:90px;background:linear-gradient(135deg,#7c3aed 0%, #db2777 50%, #f97316 100%);border-radius:22px;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:900;margin:15px auto 10px auto!important;color:white;}}
.logo-bloxks{{width:90px;height:90px;background:linear-gradient(135deg,#0ea5e9 0%, #6366f1 50%, #8b5cf6 100%);border-radius:22px;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:900;margin:15px auto 10px auto!important;color:white;}}
.gradient-title{{background:{GRADIENT_BEA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:900;font-size:52px!important;text-align:center;margin:20px 0 10px 0!important;}}
.pricing-card{{background:{CARD_BG};border:2px solid #7c3aed;border-radius:20px;padding:20px;text-align:center;color:{TEXT};}}
.pricing-card-nova{{background:{CARD_BG};border:2px solid #db2777;border-radius:20px;padding:20px;text-align:center;color:{TEXT};}}
.pricing-card-bloxks{{background:{CARD_BG};border:2px solid #0ea5e9;border-radius:20px;padding:20px;text-align:center;color:{TEXT};}}
.capcut-bar{{background:#1a1a24; border-radius:12px; padding:12px; display:flex; gap:10px; flex-wrap:wrap}}
.capcut-tool{{background:#2a2a3f; border-radius:8px; padding:8px 12px; font-size:12px; color:#d1d5db}}
.capcut-timeline{{background:#12121f; border-radius:12px; height:90px; margin-top:12px; border:1px solid #2a2a3f; display:flex; align-items:center; padding:10px}}
.timeline-block{{background:linear-gradient(135deg,#7c3aed,#c026d3); height:50px; min-width:80px; border-radius:6px; margin-right:6px; display:flex; align-items:center; justify-content:center; font-size:10px; color:white}}
</style>
""", unsafe_allow_html=True)

if st.session_state.selected_ia:
    col_back, col_empty = st.columns([0.08, 0.92])
    with col_back:
        if st.button("Retour", key="back_arrow_top_fixed"):
            st.session_state.selected_ia = None
            st.query_params.clear()
            st.rerun()

c1, c2 = st.columns([0.9, 5.1])
with c1:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=68)
with c2:
    if licence_key:
        if plan_detect == "BLOXKS":
            nom = "Bloxks"; grad = GRADIENT_BLOXKS; sous = L["bloxks_tag"]
        elif plan_detect == "CREATOR":
            nom = "Nova Ultra"; grad = GRADIENT_NOVA; sous = L["nova_tag"]
        else:
            nom = "Bea"; grad = GRADIENT_BEA; sous = L["bea_tag"]
        st.markdown(f'<div style="background:{grad};border-radius:20px;padding:14px 22px;margin:10px 0;"><h2 style="color:white;margin:0;font-size:20px;">{nom}</h2><p style="color:white;margin:4px 0 0 0;font-size:13px;">{sous}</p></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="header-card"><h2 style="color:white;margin:0;font-size:24px;">{L["main_title"]}</h2><p style="color:white;margin:5px 0 0 0;font-size:14px;">{L["sub_title"]}</p></div>', unsafe_allow_html=True)

if not licence_key:
    with st.sidebar:
        st.button("Clair" if is_dark else "Sombre", key="btn_theme_vitrine", on_click=toggle_theme, use_container_width=True)
        st.button(f"{st.session_state.lang}", key="btn_lang_vitrine", on_click=toggle_lang, use_container_width=True)
        st.divider()
        st.markdown(f"### {L['auth_title']}")
        if "user" in st.session_state:
            st.success(f"Connecté : {st.session_state.user.email}")
            if st.button("Déconnexion", key="deco_vitrine"):
                supabase.auth.sign_out()
                if "user" in st.session_state: del st.session_state.user
                st.rerun()
        else:
            st.markdown(f"<span class='auth-label'>{L['email_label']}</span>", unsafe_allow_html=True)
            email = st.text_input("email_v", label_visibility="collapsed", placeholder="email@exemple.com", key="email_vitrine")
            st.markdown(f"<span class='auth-label'>{L['pwd_label']}</span>", unsafe_allow_html=True)
            pwd = st.text_input("pwd_v", type="password", label_visibility="collapsed", placeholder="••••••••", key="pwd_vitrine")
            if st.button(L["login"], key="login_vitrine", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": pwd})
                    st.session_state.user = res.user
                    st.rerun()
                except:
                    st.error(L["invalid"])
            st.caption("Pas encore de compte? Choisissez une offre ci-dessous, vous recevrez votre licence par e-mail.")

if not licence_key:
    if st.session_state.selected_ia == "bea":
        st.markdown(f"<h1 style='color:{TEXT};font-size:42px;'>Bea</h1><p style='color:{DESC};font-size:11px;font-weight:700;'>L'IA QUI DÉCODE TES CLIENTS</p>", unsafe_allow_html=True)
        left, right = st.columns([1.6, 1], gap="large")
        with left:
            st.markdown(f"<div class='detail-box'><div class='logo-bea'>Bea</div><h1 style='font-size:32px;'>Bea, ton IA comportementale pour ton entreprise.</h1><p>BehaviorLab AI a créé la première IA du comportement dédiée aux indépendants et TPE/PME.</p><ul><li>Double ton closing +30 à +70% en 30 jours</li><li>Gagne 10h par semaine avec des scripts exacts</li><li>Fidélise tes clients en comprenant leurs peurs cachées</li><li>Stresse moins grâce à une phrase qui débloque</li><li>Augmente ton panier moyen avec le bon moment</li></ul></div>", unsafe_allow_html=True)
        with right:
            st.markdown(f"<div class='example-box'><div class='logo-bea'>Bea</div><b>Exemple :</b><br>Sarah, 34 ans, coach à Toulouse, passait de 1,8% à 6,2% de conversion en 3 semaines, +2800€/mois.<br><br>Pourquoi ça marche : Bea détecte le blocage exact et te donne le script mot à mot.</div>", unsafe_allow_html=True)
        st.link_button("Choisir Bea Pro - 21 € par mois", STRIPE_PRO, use_container_width=True)
        st.stop()
    if st.session_state.selected_ia == "nova":
        st.markdown(f"<h1 style='background:{GRADIENT_NOVA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:42px;font-weight:900;'>Nova Ultra</h1><p style='color:{DESC};font-size:11px;font-weight:700;'>REMPLACE CANVA + CAPCUT + HIGGSFIELD</p>", unsafe_allow_html=True)
        left, right = st.columns([1.6, 1], gap="large")
        with left:
            st.markdown(f"<div class='detail-box'><div class='logo-nova'>Nova Ultra</div><h1 style='font-size:32px;'>Nova Ultra, ton studio complet qui remplace 75€ d'outils.</h1><p>BehaviorLab AI a créé le premier studio IA qui fait tout à ta place.</p><ul><li>🎨 Présentation/Design comme Loveart qui remplace Canva : slides, pitch, carrousels, posts, logos, 1280x720</li><li>✂️ Montage comme Edits qui remplace CapCut : importe, coupe, sous-titres animés, transitions, filtres, effets, stickers, suppression fond, audio</li><li>🎥 Création vidéo comme Hailuo qui remplace Higgsfield : texte to vidéo, image to vidéo, avatar parlant, voix off, UGC</li><li>📈 Titres, hooks, miniatures 1280x720 qui cliquent +45% CTR</li></ul></div>", unsafe_allow_html=True)
        with right:
            st.markdown(f"<div class='example-box'><div class='logo-nova'>Nova Ultra</div><b>Exemple studio :</b><br>Léa, 26 ans, fitness à Lyon, 200 vues -> 12,4k vues + 3 ventes.<br><br><b>Flux Nova Ultra :</b><br>1️⃣ Design ton visuel<br>2️⃣ Monte ta vidéo<br>3️⃣ Génère vidéo IA<br>4️⃣ Exporte Vertical / Horizontal / Carré</div>", unsafe_allow_html=True)
        st.link_button("Choisir Nova Ultra - 19,90 € par mois", STRIPE_CREATOR, use_container_width=True)
        st.stop()
    if st.session_state.selected_ia == "bloxks":
        st.markdown(f"<h1 style='background:{GRADIENT_BLOXKS};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:42px;font-weight:900;'>Bloxks</h1><p style='color:{DESC};font-size:11px;font-weight:700;'>L'IA QUI CRÉE TON APP PLAY STORE EN UN PROMPT</p>", unsafe_allow_html=True)
        left, right = st.columns([1.6, 1], gap="large")
        with left:
            st.markdown(f"<div class='detail-box'><div class='logo-bloxks'>Bloxks</div><h1 style='font-size:32px;'>Bloxks, ton usine à apps Play Store.</h1><p>Tu envoies un prompt, Bloxks crée l'app Android et te donne le fichier prêt à publier sur Play Store.</p><ul><li>📱 Apps e-commerce, livraison, réservation, coaching, SaaS, jeux simples</li><li>💬 Juste un prompt : crée une app de réservation pour mon salon avec paiement</li><li>⚡ Génère écrans, base de données, authentification, paiement</li><li>📦 Exporte APK / AAB, icône 512x512, screenshots, description Play Store</li><li>🚀 Publie sur Play Store en 1 clic</li></ul></div>", unsafe_allow_html=True)
        with right:
            st.markdown(f"<div class='example-box'><div class='logo-bloxks'>Bloxks</div><b>Exemple :</b><br>Marc, 32 ans, restaurateur à Toulouse : crée une app de livraison avec menu, panier, paiement. Bloxks génère l'app en 3 min, il publie sur Play Store le jour même.<br><br><b>Prompt Bloxks :</b><br>crée une app de livraison avec menu, panier, Stripe, Supabase</div>", unsafe_allow_html=True)
        st.link_button("Choisir Bloxks - 29 € par mois", STRIPE_BLOXKS, use_container_width=True)
        st.stop()
    st.markdown(f"<h1 class='gradient-title'>{L['main_title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{DESC};font-size:19px;text-align:center;max-width:900px;margin:10px auto 30px auto;'>{T[st.session_state.lang]['hero_desc']} <span style='background:{GRADIENT_BEA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:800;'>{L['success']}</span>.</p>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='text-align:center;color:{TEXT};margin:40px 0 25px 0;font-size:28px;'>{T[st.session_state.lang]['discover_formats']}</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3, gap="large")
    with col1:
        st.markdown(f"<div class='ia-card'><div class='logo-bea'>Bea</div><h2 style='color:{TEXT};'>Bea</h2><p style='color:{DESC};'>{L['bea_tag']}</p></div>", unsafe_allow_html=True)
        if st.button(L["discover_bea"], key="dis_bea", use_container_width=True):
            st.session_state.selected_ia = "bea"; st.query_params["ia"] = "bea"; st.rerun()
    with col2:
        st.markdown(f"<div class='ia-card'><div class='logo-nova'>Nova Ultra</div><h2 style='color:{TEXT};'>Nova Ultra</h2><p style='color:{DESC};'>{L['nova_tag']}</p></div>", unsafe_allow_html=True)
        if st.button(L["discover_nova"], key="dis_nova", use_container_width=True):
            st.session_state.selected_ia = "nova"; st.query_params["ia"] = "nova"; st.rerun()
    with col3:
        st.markdown(f"<div class='ia-card' style='border-color:#0ea5e9;'><div class='logo-bloxks'>Bloxks</div><h2 style='color:{TEXT};'>Bloxks</h2><p style='color:{DESC};'>{L['bloxks_tag']}</p></div>", unsafe_allow_html=True)
        if st.button(L["discover_bloxks"], key="dis_bloxks", use_container_width=True):
            st.session_state.selected_ia = "bloxks"; st.query_params["ia"] = "bloxks"; st.rerun()
    st.markdown("<div style='height:30px;'></div>", unsafe_allow_html=True)
    cA, cB, cC, cD = st.columns(4, gap="medium")
    with cA:
        st.markdown(f"<div class='pricing-card'><b>Bea Basique</b><h1>14,90 €</h1><div style='text-align:left;font-size:13px;line-height:2;'>12 requêtes/mois<br>Blocages<br>Scripts</div></div>", unsafe_allow_html=True)
        st.link_button("Choisir", STRIPE_BASIQUE, use_container_width=True)
    with cB:
        st.markdown(f"<div class='pricing-card' style='border-width:3px;'><b>Bea Pro</b><h1>21 €</h1><div style='text-align:left;font-size:13px;line-height:2;'>Illimité<br>Fichiers + Pillow<br>Visuels 1280x720<br>Tous les emojis 😊🚀</div></div>", unsafe_allow_html=True)
        st.link_button("Choisir", STRIPE_PRO, use_container_width=True)
    with cC:
        st.markdown(f"<div class='pricing-card-nova'><b>Nova Ultra</b><h1>19,90 €</h1><div style='text-align:left;font-size:13px;line-height:2;'>Remplace 75€<br>Loveart + Canva<br>Edits + CapCut<br>Hailuo + Higgsfield<br>Design + Montage + Vidéo</div></div>", unsafe_allow_html=True)
        st.link_button("Choisir", STRIPE_CREATOR, use_container_width=True)
    with cD:
        st.markdown(f"<div class='pricing-card-bloxks'><b>Bloxks</b><h1>29 €</h1><div style='text-align:left;font-size:13px;line-height:2;'>1 prompt = 1 app<br>Android + iOS<br>Publie Play Store<br>Base + Paiement<br>APK / AAB</div></div>", unsafe_allow_html=True)
        st.link_button("Choisir", STRIPE_BLOXKS, use_container_width=True)
    st.stop()

if "user" not in st.session_state:
    with st.sidebar:
        st.button("Clair" if is_dark else "Sombre", key="btn_theme_lic", on_click=toggle_theme, use_container_width=True)
        st.button(f"{st.session_state.lang}", key="btn_lang_lic", on_click=toggle_lang, use_container_width=True)
        st.divider()
        st.markdown(f"### {L['auth_title']}")
        st.markdown(f"<span class='auth-label'>{L['email_label']}</span>", unsafe_allow_html=True)
        email = st.text_input("email_lic", label_visibility="collapsed", placeholder="email@exemple.com", key="email_lic")
        st.markdown(f"<span class='auth-label'>{L['pwd_label']}</span>", unsafe_allow_html=True)
        pwd = st.text_input("pwd_lic", type="password", label_visibility="collapsed", placeholder="••••••••", key="pwd_lic")
        if st.button(L["login"], key="login_lic", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": pwd})
                st.session_state.user = res.user
                st.rerun()
            except:
                st.error(L["invalid"])
    st.warning(L["connect_msg"])
    st.stop()

try:
    res = supabase.table("licences").select("*").eq("key", licence_key).eq("user_id", st.session_state.user.id).execute()
except Exception as e:
    st.error(f"Erreur licence : {e}")
    st.stop()

if not res.data:
    st.error(f"Licence {licence_key} invalide pour {st.session_state.user.email}. Dans Supabase vérifiez que user_id = {st.session_state.user.id}")
    st.stop()

lic = res.data[0]
plan, used, max_req = lic["plan"], lic["used"], lic["max_requests"]
if plan not in ["PRO", "CREATOR", "BLOXKS"]:
    if used >= max_req:
        st.error(f"Limite {used}/{max_req} atteinte")
        st.stop()

if len(st.session_state.messages) == 0:
    if plan == "BLOXKS":
        st.session_state.messages.append({"role": "assistant", "content": L["welcome_bloxks"]})
    elif plan == "CREATOR":
        st.session_state.messages.append({"role": "assistant", "content": L["welcome_nova"]})
    else:
        st.session_state.messages.append({"role": "assistant", "content": L["welcome_bea"]})

if plan not in ["CREATOR", "BLOXKS"]:
    with st.sidebar:
        st.button("Clair" if is_dark else "Sombre", key="btn_theme_bea", on_click=toggle_theme, use_container_width=True)
        st.button(f"{st.session_state.lang}", key="btn_lang_bea", on_click=toggle_lang, use_container_width=True)
        st.divider()
        st.success(f"Connecté : {st.session_state.user.email}")
        st.caption(f"Plan {plan} - {used}/{max_req}")
        if st.button("Déconnexion", key="deco_bea"):
            supabase.auth.sign_out()
            if "user" in st.session_state: del st.session_state.user
            st.rerun()
        st.divider()
        if st.button("Nouvelle discussion", key="new_chat_bea"):
            st.session_state.messages=[{"role":"assistant","content":L["welcome_bea"]}]; st.rerun()
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

# --- NOVA & BLOXKS STUDIO CAPCUT STYLE ---
col_icon, col_tools, col_editor = st.columns([0.08, 0.24, 0.68], gap="small")
with col_icon:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=56)
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    if st.button("💬", key="nav_nova_ai", use_container_width=True):
        st.session_state.nova_tab="nova_ai"; st.rerun()
    st.caption("Nova" if plan=="CREATOR" else "Bloxks")
    if st.button("🖼️", key="nav_montage", use_container_width=True):
        st.session_state.nova_tab="montage"; st.rerun()
    st.caption("Montage" if plan=="CREATOR" else "Écrans")
    if st.button("⚙️", key="nav_params", use_container_width=True):
        st.session_state.nova_tab="params"; st.rerun()
    st.caption("Params")
    st.divider()
    if st.button("🚪", key="nav_logout_nova", use_container_width=True):
        supabase.auth.sign_out()
        if "user" in st.session_state: del st.session_state.user
        st.rerun()

with col_tools:
    c_theme, c_lang = st.columns(2)
    with c_theme:
        st.button("Clair" if is_dark else "Sombre", key="btn_theme_nova", on_click=toggle_theme, use_container_width=True)
    with c_lang:
        st.button(f"{st.session_state.lang}", key="btn_lang_nova", on_click=toggle_lang, use_container_width=True)
    st.divider()
    if st.session_state.nova_tab == "nova_ai":
        st.markdown(f"### { 'Nova Ultra' if plan=='CREATOR' else 'Bloxks App' }")
        if st.button("Nouvelle discussion", key="new_chat_nova_side"):
            msg = L["welcome_bloxks"] if plan=="BLOXKS" else L["welcome_nova"]
            st.session_state.messages=[{"role":"assistant","content":msg}]; st.rerun()
    elif st.session_state.nova_tab == "montage":
        if plan=="CREATOR":
            st.markdown("### Montage ULTRA - Style CapCut")
            st.markdown('<div class="capcut-bar"><div class="capcut-tool">✂️ Couper</div><div class="capcut-tool">📝 Sous-titres auto</div><div class="capcut-tool">🧹 Fond</div><div class="capcut-tool">🔇 Silences</div><div class="capcut-tool">✨ Effets</div><div class="capcut-tool">🎞️ Transitions</div></div>', unsafe_allow_html=True)
            with st.expander("📁 Média", expanded=True):
                st.file_uploader("Importer", type=["png","jpg","jpeg","mp4"], key="media_up_nova")
            with st.expander("🎨 Présentation/Design Loveart + Canva"):
                st.button("Slides / Carrousels / Logos", use_container_width=True)
            with st.expander("✂️ Montage Edits + CapCut"):
                st.button("Cut + Sous-titres + Effets + Stickers", use_container_width=True)
            with st.expander("🎥 Création vidéo Hailuo + Higgsfield"):
                st.button("Texte to Vidéo + Image to Vidéo + Avatar", use_container_width=True)
        else:
            st.markdown("### App Bloxks")
            with st.expander("📱 Écrans", expanded=True):
                st.button("Login / Accueil / Profil / Panier", use_container_width=True)
            with st.expander("🗄️ Base de données"):
                st.button("Tables Supabase + Auth", use_container_width=True)
            with st.expander("💳 Paiement"):
                st.button("Stripe + Play Billing", use_container_width=True)
            with st.expander("📦 Publication Play Store"):
                st.button("APK / AAB + Icône 512 + Screenshots", use_container_width=True)
    else:
        st.markdown("### Paramètres")
        st.success(f"{st.session_state.user.email}")
        st.caption(f"Plan {plan} - {used}/{max_req}")

with col_editor:
    if st.session_state.nova_tab == "nova_ai":
        grad = GRADIENT_BLOXKS if plan=="BLOXKS" else GRADIENT_NOVA
        titre = "Bloxks App - 1 Prompt = Play Store" if plan=="BLOXKS" else "Nova Ultra - Remplace Canva + CapCut + Higgsfield - 1280x720"
        st.markdown(f"<div style='background:{grad};border-radius:16px;padding:16px;color:white;'><b>{titre}</b></div>", unsafe_allow_html=True)
        logo_path = "logo.png" if os.path.exists("logo.png") else None
        for m in st.session_state.messages:
            if m.get("role")=="system": continue
            if m["role"]=="user":
                with st.chat_message("user"): st.markdown(sanitize_user(m["content"]))
            else:
                with st.chat_message("assistant", avatar=logo_path if logo_path else "🎬" if plan=="CREATOR" else "📱"):
                    st.markdown(sanitize_assistant(m["content"]))
                    if "image" in m and m["image"]: st.image(m["image"], use_container_width=True)
    else:
        grad = GRADIENT_BLOXKS if plan=="BLOXKS" else GRADIENT_NOVA
        titre = "Studio Bloxks - App Preview Play Store" if plan=="BLOXKS" else "Studio Nova Ultra - Canvas 1280x720 - Design + Montage + Vidéo IA - Export Vertical / Horizontal / Carré"
        st.markdown(f"<div style='background:{grad};border-radius:16px;padding:16px;color:white;'><b>{titre}</b></div>", unsafe_allow_html=True)
        if plan=="BLOXKS":
            st.markdown(f"<div style='background:{CARD_BG};border:2px solid #0ea5e9;border-radius:16px;height:360px;display:flex;align-items:center;justify-content:center;color:{TEXT};'>📱 Aperçu App Bloxks - Écrans + Base + Paiement</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='background:#1e1b4b;border-radius:12px;padding:12px;color:#c4b5fd;margin-top:12px;'><b>Flux Bloxks Play Store</b><div style='background:#2a2250;height:45px;border-radius:8px;margin:8px 0;padding:8px;'>📱 Écran 1 - Accueil</div><div style='background:#3a2a60;height:35px;border-radius:8px;margin:8px 0;padding:8px;'>🗄️ Base Supabase</div><div style='background:#4a3560;height:30px;border-radius:8px;margin:8px 0;padding:8px;'>💳 Stripe + Play Billing</div><div style='background:#5a4080;height:30px;border-radius:8px;margin:8px 0;padding:8px;'>📦 APK prêt Play Store</div></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='background:{CARD_BG};border:2px solid #db2777;border-radius:16px;height:360px;display:flex;align-items:center;justify-content:center;color:{TEXT};'>Aperçu 1280x720 - Glisse ton média - Design + Montage + Vidéo IA</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='background:#1e1b4b;border-radius:12px;padding:12px;color:#c4b5fd;margin-top:12px;'><b>Timeline Nova Ultra - Style CapCut</b><div class='capcut-timeline'><div class='timeline-block'>Design</div><div class='timeline-block' style='min-width:120px'>Montage Cut</div><div class='timeline-block'>Audio</div><div class='timeline-block' style='background:#1a1a24'>Sous-titres</div></div></div>", unsafe_allow_html=True)
        if st.button("Générer visuel IA" if plan=="CREATOR" else "Générer APK Preview", key="gen_mini_editor"):
            img,_ = generer_image_comportementale("app mobile play store" if plan=="BLOXKS" else "miniature qui clique design montage video", plan)
            st.image(img, use_container_width=True)

if (plan=="CREATOR" or plan=="BLOXKS") and st.session_state.nova_tab=="nova_ai":
    if st.button(L["file_btn"], key="file_btn_nova_out"):
        st.session_state.show_uploader = not st.session_state.show_uploader; st.rerun()
    if st.session_state.show_uploader:
        up = st.file_uploader("file", type=["png","jpg","jpeg","pdf","txt","mp4"], label_visibility="collapsed", key="uploader_nova_fix")
        if up:
            st.session_state.uploaded_file_info={"name":up.name}
            if up.type.startswith("image/"): st.image(up,width=250)
    ask_key = L["ask_bloxks"] if plan=="BLOXKS" else L["ask_nova"]
    prompt_raw = st.chat_input(ask_key, key="chat_input_nova_final")
    if prompt_raw:
        check_rate_limit(plan)
        prompt_clean = sanitize_user(prompt_raw)
        if st.session_state.uploaded_file_info:
            prompt_clean = f"[Fichier : {st.session_state.uploaded_file_info['name']}] {prompt_clean}"
        st.session_state.messages.append({"role":"user","content":prompt_clean})
        msgs_for_groq = [{"role":mm["role"],"content":sanitize_user(mm["content"])} for mm in st.session_state.messages if mm.get("role")!="system" and "image" not in mm]
        if plan=="BLOXKS":
            sys_prompt = SYSTEM_BLOXKS + f"\nRéponds en {st.session_state.lang}. Si on te demande qui t'a créée : Je suis Bloxks, créée par BehaviorLab AI."
        else:
            sys_prompt = SYSTEM_NOVA + f"\nRéponds en {st.session_state.lang}. Si on te demande qui t'a créée : Je suis Nova Ultra, créée par BehaviorLab AI."
        try:
            if demande_image(prompt_clean):
                with st.spinner("Nova Ultra crée ton visuel..." if plan=="CREATOR" else "Bloxks génère ton app Play Store..."):
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
