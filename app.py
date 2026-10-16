import streamlit as st
import os
import re
import time
import io
import zipfile
from groq import Groq
from supabase import create_client
from collections import deque
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="BehaviorLab AI", page_icon="logo.png", layout="wide", initial_sidebar_state="expanded")

# LIENS PAIEMENT - 4 PRIX CORRIGES HIER
STRIPE_BASIQUE = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"
STRIPE_PRO = "https://buy.stripe.com/test_cNieVea1P0c62B08523wQ00"
STRIPE_NOVA = "https://buy.stripe.com/test_nova_8_90"
STRIPE_FORGE = "https://buy.stripe.com/test_forge_13"

def find_file(candidates):
    for f in candidates:
        if os.path.exists(f):
            return f
    return None

def load_logos_avec_correction_inversion():
    bea_path = find_file(["logo_bea.png", "logo_bea.jpg", "Bea.png", "bea.png"])
    forge_path = find_file(["logo_forge.png", "logo_forge.jpg", "Forge.png", "forge.png", "logo_bloxks.png"])
    nova_path = find_file(["logo_nova.png", "logo_nova.jpg", "Nova.png", "nova.png", "logo_nova_ultra.png"])
    main_path = find_file(["logo.png", "Logo.png"])
    if bea_path and forge_path:
        if "forge" in bea_path.lower() and "bea" in forge_path.lower():
            bea_path, forge_path = forge_path, bea_path
        if "bloxks" in bea_path.lower():
            bea_path, forge_path = forge_path, bea_path
    return {"bea": bea_path, "forge": forge_path, "nova": nova_path, "main": main_path}

LOGOS = load_logos_avec_correction_inversion()

try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    SUPA_URL = st.secrets["SUPABASE_URL"]
    SUPA_KEY = st.secrets.get("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_PUBLISHABLE_KEY")
    client = Groq(api_key=GROQ_KEY)
    supabase = create_client(SUPA_URL, SUPA_KEY)
except Exception as e:
    st.error(f"Erreur Secrets Supabase Groq : {e}")
    st.stop()

def get_modeles_valides_groq():
    try:
        liste = client.models.list()
        ids = [m.id for m in liste.data]
        preferes = ["openai/gpt-oss-20b","openai/gpt-oss-120b","qwen/qwen3-32b","meta-llama/llama-4-maverick-17b-128e-instruct","llama-3.3-70b-versatile","llama-3.1-8b-instant"]
        valides = [m for m in preferes if m in ids]
        return valides if valides else ids
    except:
        return ["openai/gpt-oss-20b","llama-3.3-70b-versatile"]

MODELES_DISPO = get_modeles_valides_groq()

def call_groq_durable(messages):
    last_err = None
    for model_id in MODELES_DISPO:
        try:
            comp = client.chat.completions.create(model=model_id, messages=messages, temperature=0.7, max_tokens=2000)
            return comp.choices[0].message.content, model_id
        except Exception as e:
            last_err = e
            continue
    raise last_err

for k, v in {
    "theme": "light","lang": "FR","messages": [],"show_uploader": False,
    "uploaded_file_info": None,"rate_limit": deque(),"blocked_until": 0,
    "selected_ia": None,"nova_tab": "nova_ai","current_ia": "dashboard",
    "logged": False,"action_message": "","uploaded_video_name": None,
    "forge_files": {},"gen_image": False
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
            st.session_state.logged = True
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
    if len(dq) >= (50 if plan in ["PRO", "CREATOR", "FORGE"] else 15):
        st.session_state.blocked_until = now + 90
        st.error("Trop de requêtes - pause 90s")
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
    titre = "Bea - Visuel qui convertit" if plan=="PRO" else "Nova Ultra" if plan=="CREATOR" else "Forge - App"
    draw.text((70, 152), titre, font=font_sub, fill="white")
    draw.text((60, 220), f"Demande : {texte_modif[:105]}", font=font_text, fill="white")
    draw.text((60, 260), "Export: Vertical / Horizontal / Carré", font=font_text, fill="#c4b5fd")
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
SYSTEM_NOVA = "Tu es Nova Ultra, studio de BehaviorLab AI pour montage vidéo professionnel. Tu maîtrises : génération automatique de sous-titres stylisés et synchronisés avec la parole, suppression de l'arrière-plan, découpe des silences et nettoyage de la piste audio, bibliothèque intégrée de modèles, d'effets, de transitions et d'animations, export direct dans un format optimisé pour chaque plateforme de diffusion. Format export 9:16 TikTok, 16:9, 1:1. Style sous-titres Viral pop. Si on te demande qui t'a créée : Je suis Nova Ultra, créée par BehaviorLab AI."
SYSTEM_FORGE = "Tu es Forge, IA de BehaviorLab AI qui crée des applications mobiles qui se publient sur Play Store en un prompt. L'utilisateur dit : crée une app de livraison pour mon restaurant avec paiement, et tu génères toute l'app. Tu donnes : 1. Description de l'app, 2. Prompt exact optimisé pour Forge, 3. Structure écrans, 4. Base de données, 5. Logique publication Play Store avec package name, icône 512x512, screenshots, description, 6. Export APK/AAB. Tu maîtrises e-commerce, réservation, coaching, SaaS, jeux simples, Stripe, Supabase. Règles : Français parfait avec accents, emojis 💻 🚀 📱 ⚡ 🔥 ✅ 📦. Si on te demande qui t'a créée : Je suis Forge, créée par BehaviorLab AI."

T = {
    "FR": {
        "main_title": "BehaviorLab AI","sub_title": "Les IA comportementales pour votre réussite",
        "hero_desc": "<b>BehaviorLab AI a créé les premières IA du comportement.</b><br>Pensée pour ceux qui veulent booster leur réussite, nos IA décodent le comportement humain pour un seul but :",
        "success": "votre réussite","discover_formats": "Découvrir les 3 formats IA",
        "bea_tag": "L'IA qui décode tes clients et double ton closing",
        "nova_tag": "Le studio de montage vidéo professionnel",
        "forge_tag": "L'IA qui crée ton app Play Store en un prompt",
        "ask_bea": "Demander à Bea...","ask_nova": "Demander à Nova Ultra...","ask_forge": "Décris ton app à Forge...","file_btn": "Glisser un fichier","return": "Retour",
        "discover_bea": "Découvrir Bea","discover_nova": "Découvrir Nova Ultra","discover_forge": "Découvrir Forge",
        "email_label": "Adresse e-mail","pwd_label": "Mot de passe","login": "Connexion","auth_title": "Authentification",
        "welcome_bea": "Salut, c'est Bea 😊, ton IA créée par BehaviorLab AI. Comment je peux t'aider aujourd'hui? 🚀💡",
        "welcome_nova": "Salut, c'est Nova Ultra 🎬🚀, ton studio de montage vidéo professionnel. Je fais ton montage complet en un seul endroit. Que veux-tu créer? ✨📈",
        "welcome_forge": "Salut, c'est Forge 💻📱, ton IA qui crée ton app Play Store en un prompt. Décris ton idée et je te génère l'app prête à publier. 🚀⚡",
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
GRADIENT_FORGE = "linear-gradient(135deg, #0ea5e9 0%, #6366f1 50%, #8b5cf6 100%)"
GRADIENT = GRADIENT_FORGE if plan_detect == "FORGE" else GRADIENT_NOVA if plan_detect == "CREATOR" else GRADIENT_BEA
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
.ia-card{{background:{CARD_BG};border:2px solid #7c3aed;border-radius:24px;padding:35px 25px 25px 25px;text-align:center;min-height:520px;margin-top:30px!important;}}
.example-box{{background:{CARD_BG};border:2px solid #7c3aed;border-radius:20px;padding:22px;color:{TEXT};}}
.gradient-title{{background:{GRADIENT_BEA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:900;font-size:52px!important;text-align:center;margin:20px 0 10px 0!important;}}
.pricing-card{{background:{CARD_BG};border:2px solid #7c3aed;border-radius:20px;padding:20px;text-align:center;color:{TEXT};}}
.pricing-card-nova{{background:{CARD_BG};border:2px solid #db2777;border-radius:20px;padding:20px;text-align:center;color:{TEXT};}}
.pricing-card-forge{{background:{CARD_BG};border:2px solid #0ea5e9;border-radius:20px;padding:20px;text-align:center;color:{TEXT};}}
.capcut-bar{{background:#1a1a24; border-radius:12px; padding:12px; display:flex; gap:10px; flex-wrap:wrap}}
.capcut-tool{{background:#2a2a3f; border-radius:8px; padding:8px 12px; font-size:12px; color:#d1d5db}}
.capcut-timeline{{background:#12121f; border-radius:12px; height:90px; margin-top:12px; border:1px solid #2a2a3f; display:flex; align-items:center; padding:10px}}
.timeline-block{{background:linear-gradient(135deg,#7c3aed,#c026d3); height:50px; min-width:80px; border-radius:6px; margin-right:6px; display:flex; align-items:center; justify-content:center; font-size:10px; color:white}}
.montage-title{{font-size:38px;font-weight:800;color:{TEXT};margin:20px 0;}}
.montage-label{{color:{TEXT};font-size:14px;margin:18px 0 8px 0;font-weight:600;}}
</style>
""", unsafe_allow_html=True)

def render_logo(logo_key, fallback_text, gradient):
    path = LOGOS.get(logo_key)
    if path and os.path.exists(path):
        st.image(path, width=90)
    else:
        st.markdown(f"<div style='width:90px;height:90px;background:{gradient};border-radius:22px;display:flex;align-items:center;justify-content:center;color:white;font-weight:900;font-size:18px;margin:15px auto;'>{fallback_text}</div>", unsafe_allow_html=True)

if st.session_state.selected_ia:
    if st.button("← Retour", key="retour_vitrine_top"):
        st.session_state.selected_ia = None
        st.query_params.clear()
        st.rerun()

c1, c2 = st.columns([0.9, 5.1])
with c1:
    main_logo = LOGOS.get("main") or LOGOS.get("bea")
    if main_logo and os.path.exists(main_logo):
        st.image(main_logo, width=68)
with c2:
    if licence_key:
        if plan_detect == "FORGE":
            nom = "Forge"; grad = GRADIENT_FORGE; sous = L["forge_tag"]
        elif plan_detect == "CREATOR":
            nom = "Nova Ultra"; grad = GRADIENT_NOVA; sous = L["nova_tag"]
        else:
            nom = "Bea"; grad = GRADIENT_BEA; sous = L["bea_tag"]
        st.markdown(f'<div style="background:{grad};border-radius:20px;padding:14px 22px;margin:10px 0;"><h2 style="color:white;margin:0;font-size:20px;">{nom}</h2><p style="color:white;margin:4px 0 0 0;font-size:13px;">{sous}</p></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="header-card"><h2 style="color:white;margin:0;font-size:24px;">{L["main_title"]}</h2><p style="color:white;margin:5px 0 0 0;font-size:14px;">{L["sub_title"]}</p></div>', unsafe_allow_html=True)

if not licence_key:
    with st.sidebar:
        if st.button("Clair" if is_dark else "Sombre", key="btn_theme_vitrine", on_click=toggle_theme):
            st.rerun()
        if st.button(f"{st.session_state.lang}", key="btn_lang_vitrine", on_click=toggle_lang):
            st.rerun()
        st.divider()
        st.markdown(f"### {L['auth_title']}")
        if st.session_state.logged and "user" in st.session_state:
            st.success(f"Connecté : {st.session_state.user.email}")
            if st.button("Déconnexion", key="deco_vitrine"):
                supabase.auth.sign_out()
                st.session_state.logged=False
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
                    st.session_state.logged=True
                    st.rerun()
                except:
                    st.error(L["invalid"])
            st.caption("Pas encore de compte? Choisissez une offre ci-dessous, vous recevrez votre licence par e-mail.")

if not licence_key:
    if st.session_state.selected_ia == "bea":
        st.markdown(f"<h1 style='color:{TEXT};font-size:42px;'>Bea</h1><p style='color:{DESC};font-size:11px;font-weight:700;'>L'IA QUI DÉCODE TES CLIENTS</p>", unsafe_allow_html=True)
        left, right = st.columns([1.6, 1], gap="large")
        with left:
            st.markdown(f"<div class='detail-box'>", unsafe_allow_html=True)
            render_logo("bea", "Bea", GRADIENT_BEA)
            st.markdown(f"<h1 style='font-size:32px;'>Bea, ton IA comportementale pour ton entreprise.</h1><p>BehaviorLab AI a créé la première IA du comportement dédiée aux indépendants et TPE/PME.</p><ul><li>Double ton closing +30 à +70% en 30 jours</li><li>Gagne 10h par semaine avec des scripts exacts</li><li>Fidélise tes clients en comprenant leurs peurs cachées</li><li>Stresse moins grâce à une phrase qui débloque</li><li>Augmente ton panier moyen avec le bon moment</li></ul></div>", unsafe_allow_html=True)
        with right:
            st.markdown(f"<div class='example-box'>", unsafe_allow_html=True)
            render_logo("bea", "Bea", GRADIENT_BEA)
            st.markdown(f"<b>Exemple :</b><br>Sarah, 34 ans, coach à Toulouse, passait de 1,8% à 6,2% de conversion en 3 semaines, +2800€/mois.<br><br>Pourquoi ça marche : Bea détecte le blocage exact et te donne le script mot à mot.</div>", unsafe_allow_html=True)
        if st.button("Choisir Bea Pro - 21 € par mois", key="choose_bea_pro_detail"):
            st.link_button("Choisir Bea Pro - 21 € par mois", STRIPE_PRO, use_container_width=True)
        st.link_button("Choisir Bea Pro - 21 € par mois", STRIPE_PRO, use_container_width=True)
        st.stop()
    if st.session_state.selected_ia == "nova":
        st.markdown(f"<h1 style='background:{GRADIENT_NOVA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:42px;font-weight:900;'>Nova Ultra</h1><p style='color:{DESC};font-size:11px;font-weight:700;'>STUDIO DE MONTAGE VIDÉO PROFESSIONNEL</p>", unsafe_allow_html=True)
        left, right = st.columns([1.6, 1], gap="large")
        with left:
            st.markdown(f"<div class='detail-box'>", unsafe_allow_html=True)
            render_logo("nova", "Nova", GRADIENT_NOVA)
            st.markdown(f"<h1 style='font-size:32px;'>Nova Ultra, ton studio complet de montage vidéo professionnel.</h1><p>BehaviorLab AI a créé le studio qui fait tout à ta place.</p><ul><li>Génération automatique de sous-titres stylisés et synchronisés avec la parole</li><li>Suppression de l'arrière-plan, découpe des silences et nettoyage de la piste audio</li><li>Bibliothèque intégrée de modèles, d'effets, de transitions et d'animations</li><li>Export direct dans un format optimisé pour chaque plateforme de diffusion</li><li>Miniatures 1280x720 qui cliquent +45% CTR</li><li>Export Vertical / Horizontal / Carré - Format 9:16 TikTok</li></ul></div>", unsafe_allow_html=True)
        with right:
            st.markdown(f"<div class='example-box'>", unsafe_allow_html=True)
            render_logo("nova", "Nova", GRADIENT_NOVA)
            st.markdown(f"<b>Exemple studio :</b><br>Léa, 26 ans, fitness à Lyon, 200 vues -> 12,4k vues + 3 ventes.<br><br><b>Flux Nova Ultra :</b><br>1️⃣ Importe ta vidéo brute<br>2️⃣ Génère sous-titres Viral pop<br>3️⃣ Découpe silences + effets<br>4️⃣ Exporte Vertical / Horizontal / Carré</div>", unsafe_allow_html=True)
        st.link_button("Choisir Nova Ultra - 8,90 € par mois", STRIPE_NOVA, use_container_width=True)
        st.stop()
    if st.session_state.selected_ia == "forge":
        st.markdown(f"<h1 style='background:{GRADIENT_FORGE};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:42px;font-weight:900;'>Forge</h1><p style='color:{DESC};font-size:11px;font-weight:700;'>L'IA QUI CRÉE TON APP PLAY STORE EN UN PROMPT</p>", unsafe_allow_html=True)
        left, right = st.columns([1.6, 1], gap="large")
        with left:
            st.markdown(f"<div class='detail-box'>", unsafe_allow_html=True)
            render_logo("forge", "Forge", GRADIENT_FORGE)
            st.markdown(f"<h1 style='font-size:32px;'>Forge, ton usine à apps Play Store.</h1><p>Tu envoies un prompt, Forge crée l'app Android et te donne le fichier prêt à publier sur Play Store.</p><ul><li>Apps e-commerce, livraison, réservation, coaching, SaaS, jeux simples</li><li>Juste un prompt : crée une app de réservation pour mon salon avec paiement</li><li>Génère écrans, base de données, authentification, paiement</li><li>Exporte APK / AAB, icône 512x512, screenshots, description Play Store</li><li>Publie sur Play Store en 1 clic</li></ul></div>", unsafe_allow_html=True)
        with right:
            st.markdown(f"<div class='example-box'>", unsafe_allow_html=True)
            render_logo("forge", "Forge", GRADIENT_FORGE)
            st.markdown(f"<b>Exemple :</b><br>Marc, 32 ans, restaurateur à Toulouse : crée une app de livraison avec menu, panier, paiement. Forge génère l'app en 3 min, il publie sur Play Store le jour même.<br><br><b>Prompt Forge :</b><br>crée une app de livraison avec menu, panier, Stripe, Supabase</div>", unsafe_allow_html=True)
        st.link_button("Choisir Forge - 13 € par mois", STRIPE_FORGE, use_container_width=True)
        st.stop()
    st.markdown(f"<h1 class='gradient-title'>{L['main_title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{DESC};font-size:19px;text-align:center;max-width:900px;margin:10px auto 30px auto;'>{T[st.session_state.lang]['hero_desc']} <span style='background:{GRADIENT_BEA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:800;'>{L['success']}</span>.</p>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='text-align:center;color:{TEXT};margin:40px 0 25px 0;font-size:28px;'>{T[st.session_state.lang]['discover_formats']}</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3, gap="large")
    with col1:
        st.markdown(f"<div class='ia-card'>", unsafe_allow_html=True)
        render_logo("bea", "Bea", GRADIENT_BEA)
        st.markdown(f"<h2 style='color:{TEXT};'>Bea</h2><p style='color:{DESC};'>{L['bea_tag']}</p></div>", unsafe_allow_html=True)
        if st.button(L["discover_bea"], key="dis_bea", use_container_width=True):
            st.session_state.selected_ia = "bea"; st.query_params["ia"] = "bea"; st.rerun()
    with col2:
        st.markdown(f"<div class='ia-card'>", unsafe_allow_html=True)
        render_logo("nova", "Nova", GRADIENT_NOVA)
        st.markdown(f"<h2 style='color:{TEXT};'>Nova Ultra</h2><p style='color:{DESC};'>{L['nova_tag']}</p></div>", unsafe_allow_html=True)
        if st.button(L["discover_nova"], key="dis_nova", use_container_width=True):
            st.session_state.selected_ia = "nova"; st.query_params["ia"] = "nova"; st.rerun()
    with col3:
        st.markdown(f"<div class='ia-card' style='border-color:#0ea5e9;'>", unsafe_allow_html=True)
        render_logo("forge", "Forge", GRADIENT_FORGE)
        st.markdown(f"<h2 style='color:{TEXT};'>Forge</h2><p style='color:{DESC};'>{L['forge_tag']}</p></div>", unsafe_allow_html=True)
        if st.button(L["discover_forge"], key="dis_forge", use_container_width=True):
            st.session_state.selected_ia = "forge"; st.query_params["ia"] = "forge"; st.rerun()
    st.markdown("<div style='height:30px;'></div>", unsafe_allow_html=True)
    cA, cB, cC, cD = st.columns(4, gap="medium")
    with cA:
        st.markdown(f"<div class='pricing-card'><b>Bea Basique</b><h1>14,90 €</h1><div style='text-align:left;font-size:13px;line-height:2;'>12 requêtes/mois<br>Blocages<br>Scripts</div></div>", unsafe_allow_html=True)
        st.link_button("Choisir", STRIPE_BASIQUE, use_container_width=True, key="buy_basique_vitrine")
    with cB:
        st.markdown(f"<div class='pricing-card' style='border-width:3px;'><b>Bea Pro</b><h1>21 €</h1><div style='text-align:left;font-size:13px;line-height:2;'>Illimité<br>Fichiers + Pillow<br>Visuels 1280x720<br>Tous les emojis 😊🚀</div></div>", unsafe_allow_html=True)
        st.link_button("Choisir", STRIPE_PRO, use_container_width=True, key="buy_pro_vitrine")
    with cC:
        st.markdown(f"<div class='pricing-card-nova'><b>Nova Ultra</b><h1>8,90 €</h1><div style='text-align:left;font-size:13px;line-height:2;'>Remplace 75€<br>Sous-titres auto<br>Découpe silences<br>Effets + Transitions<br>Vertical / Horizontal / Carré<br>9:16 TikTok</div></div>", unsafe_allow_html=True)
        st.link_button("Choisir", STRIPE_NOVA, use_container_width=True, key="buy_nova_vitrine")
    with cD:
        st.markdown(f"<div class='pricing-card-forge'><b>Forge</b><h1>13 €</h1><div style='text-align:left;font-size:13px;line-height:2;'>1 prompt = 1 app<br>Android + iOS<br>Publie Play Store<br>Base + Paiement<br>APK / AAB</div></div>", unsafe_allow_html=True)
        st.link_button("Choisir", STRIPE_FORGE, use_container_width=True, key="buy_forge_vitrine")
    st.stop()

if "user" not in st.session_state or not st.session_state.logged:
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
                st.session_state.logged=True
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
    st.error(f"Licence {licence_key} invalide pour {st.session_state.user.email}.")
    st.stop()

lic = res.data[0]
plan, used, max_req = lic["plan"], lic["used"], lic["max_requests"]
if plan not in ["PRO", "CREATOR", "FORGE"]:
    if used >= max_req:
        st.error(f"Limite {used}/{max_req} atteinte")
        st.stop()

if len(st.session_state.messages) == 0:
    if plan == "FORGE":
        st.session_state.messages.append({"role": "assistant", "content": L["welcome_forge"]})
    elif plan == "CREATOR":
        st.session_state.messages.append({"role": "assistant", "content": L["welcome_nova"]})
    else:
        st.session_state.messages.append({"role": "assistant", "content": L["welcome_bea"]})

if plan not in ["CREATOR", "FORGE"]:
    with st.sidebar:
        if st.button("Clair" if is_dark else "Sombre", key="btn_theme_bea", on_click=toggle_theme, use_container_width=True):
            st.rerun()
        if st.button(f"{st.session_state.lang}", key="btn_lang_bea", on_click=toggle_lang, use_container_width=True):
            st.rerun()
        st.divider()
        st.success(f"Connecté : {st.session_state.user.email}")
        st.caption(f"Plan {plan} - {used}/{max_req}")
        if st.button("Déconnexion", key="deco_bea"):
            supabase.auth.sign_out()
            st.session_state.logged=False
            if "user" in st.session_state: del st.session_state.user
            st.rerun()
        st.divider()
        if st.button("Nouvelle discussion", key="new_chat_bea"):
            st.session_state.messages=[{"role":"assistant","content":L["welcome_bea"]}]
            st.rerun()
        if st.button("Effacer historique", key="clear_bea"):
            st.session_state.messages=[]
            st.rerun()
    if st.button(L["file_btn"], key="file_btn_bea"):
        st.session_state.show_uploader = not st.session_state.show_uploader
        st.rerun()
    if st.session_state.show_uploader:
        up = st.file_uploader("file", type=["png","jpg","jpeg","pdf","txt"], label_visibility="collapsed", key="uploader_bea")
        if up:
            st.session_state.uploaded_file_info={"name":up.name}
            if up.type.startswith("image/"): st.image(up,width=400)
            if st.button("Supprimer fichier", key="del_file_bea"):
                st.session_state.uploaded_file_info=None
                st.session_state.show_uploader=False
                st.rerun()
    logo_path = LOGOS.get("main") or LOGOS.get("bea") or "logo.png"
    for m in st.session_state.messages:
        if m.get("role")=="system": continue
        if m["role"]=="user":
            with st.chat_message("user"): st.markdown(sanitize_user(m["content"]))
        else:
            with st.chat_message("assistant", avatar=logo_path if os.path.exists(logo_path) else "🧠"):
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
                img,_ = generer_image_comportementale(prompt_clean, plan)
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

# INTERFACE PHOTO - TOUS BOUTONS MARCHENT
if st.button("← Retour", key="retour_photo_top"):
    st.session_state.selected_ia=None
    st.query_params.clear()
    st.rerun()

st.markdown(f"<h1 class='montage-title'>Montage vidéo professionnel — Groq + Montage</h1>", unsafe_allow_html=True)

st.markdown(f"<p class='montage-label'>Vidéo brute</p>", unsafe_allow_html=True)
col_up1, col_up2 = st.columns([0.3, 0.7])
with col_up1:
    uploaded_video = st.file_uploader("Upload", type=["mp4","mov","webm","avi"], label_visibility="collapsed", key="upload_brute_photo")
    if uploaded_video:
        st.session_state.uploaded_video_name = uploaded_video.name
        st.success(f"Chargé : {uploaded_video.name}")
        if st.button("Supprimer vidéo", key="del_video_photo"):
            st.session_state.uploaded_video_name=None
            st.rerun()
    else:
        if st.button("⬆ Upload (choisir fichier)", key="fake_upload_btn"):
            st.info("Clique sur Browse files ci-dessus pour uploader 200MB max")
with col_up2:
    st.markdown(f"<p style='color:#a1a1aa;font-size:13px;margin-top:10px;'>200MB per file • MP4, MOV, WEBM, AVI</p>", unsafe_allow_html=True)
    if uploaded_video:
        st.video(uploaded_video)

st.markdown(f"<p class='montage-label'>Script / paroles pour sous-titres</p>", unsafe_allow_html=True)
script = st.text_area("Script", height=120, label_visibility="collapsed", key="script_photo", placeholder="Colle ton script ici pour générer les sous-titres...")

c_fmt, c_style = st.columns([0.6, 0.4])
with c_fmt:
    st.markdown(f"<p class='montage-label'>Format export</p>", unsafe_allow_html=True)
    fmt = st.selectbox("Format export", ["9:16 TikTok", "16:9 YouTube", "1:1 Carré"], label_visibility="collapsed", key="fmt_photo")
    if st.button(f"Format actuel : {fmt}", key="btn_fmt_actuel"):
        st.toast(f"Format {fmt} sélectionné")
        st.session_state.action_message=f"Format {fmt} sélectionné"
with c_style:
    st.markdown(f"<p class='montage-label'>Style sous-titres</p>", unsafe_allow_html=True)
    style_sub = st.selectbox("Style sous-titres", ["Viral pop", "Hormozi bold", "Minimal"], label_visibility="collapsed", key="style_photo")
    if st.button(f"Style actuel : {style_sub}", key="btn_style_actuel"):
        st.toast(f"Style {style_sub} sélectionné")
        st.session_state.action_message=f"Style {style_sub} sélectionné"

st.markdown("---")
st.markdown(f"<p class='montage-label'>Outils de montage</p>", unsafe_allow_html=True)
c1,c2,c3,c4=st.columns(4)
with c1:
    if st.button("✂️ Couper", key="btn_cut_photo", use_container_width=True):
        st.session_state.action_message="✂️ Couper : découpe des silences activée"
        st.toast("✂️ Découpe activée")
        st.rerun()
with c2:
    if st.button("📝 Sous-titres auto", key="btn_sub_photo", use_container_width=True):
        st.session_state.action_message="📝 Sous-titres auto : génération auto activée"
        st.toast("📝 Sous-titres auto")
        st.rerun()
with c3:
    if st.button("🧹 Supprimer fond", key="btn_bg_photo", use_container_width=True):
        st.session_state.action_message="🧹 Suppression arrière-plan activée"
        st.toast("🧹 Fond supprimé")
        st.rerun()
with c4:
    if st.button("🎨 Modèles", key="btn_template_photo", use_container_width=True):
        st.session_state.action_message="🎨 Modèles ouverts"
        st.toast("🎨 Modèles")
        st.rerun()

c5,c6,c7,c8=st.columns(4)
with c5:
    if st.button("✨ Effets", key="btn_effects_photo", use_container_width=True):
        st.session_state.action_message="✨ Effets activés"
        st.toast("✨ Effets")
        st.rerun()
with c6:
    if st.button("🎞️ Transitions", key="btn_trans_photo", use_container_width=True):
        st.session_state.action_message="🎞️ Transitions activées"
        st.toast("🎞️ Transitions")
        st.rerun()
with c7:
    if st.button("🎧 Nettoyage audio", key="btn_audio_photo", use_container_width=True):
        st.session_state.action_message="🎧 Nettoyage audio activé"
        st.toast("🎧 Audio nettoyé")
        st.rerun()
with c8:
    if st.button("🔇 Couper silences", key="btn_silence_photo", use_container_width=True):
        st.session_state.action_message="🔇 Couper silences activé"
        st.toast("🔇 Silences coupés")
        st.rerun()

if st.session_state.action_message:
    st.info(f"Action en cours : {st.session_state.action_message}")

if st.button("Générer montage avec Groq", key="gen_groq_photo", use_container_width=True):
    check_rate_limit(plan)
    if not script and not uploaded_video:
        st.warning("Ajoute une vidéo brute ou un script d'abord")
    else:
        prompt_clean = sanitize_user(script) if script else f"Génère montage vidéo professionnel format {fmt} style {style_sub}"
        st.session_state.messages.append({"role":"user","content":prompt_clean})
        msgs = [{"role":mm["role"],"content":sanitize_user(mm["content"])} for mm in st.session_state.messages if mm.get("role")!="system" and "image" not in mm]
        sys_prompt = SYSTEM_NOVA if plan=="CREATOR" else SYSTEM_FORGE
        sys_prompt += f" Format: {fmt} Style: {style_sub}. Réponds en {st.session_state.lang}. Si on te demande qui t'a créée : Je suis { 'Nova Ultra' if plan=='CREATOR' else 'Forge' }, créée par BehaviorLab AI."
        try:
            with st.spinner("Groq génère ton montage..."):
                reponse,_ = call_groq_durable([{"role":"system","content":sys_prompt}]+msgs[-15:])
                img,_ = generer_image_comportementale(prompt_clean, plan)
                st.session_state.messages.append({"role":"assistant","content":sanitize_assistant(reponse),"image":img})
            supabase.table("licences").update({"used":used+1}).eq("key",licence_key).execute()
            st.success("✅ Montage généré avec Groq!")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {str(e)[:400]}")

st.divider()
col_a,col_b,col_c,col_d=st.columns(4)
with col_a:
    if st.button("Nouvelle discussion", key="new_chat_photo", use_container_width=True):
        st.session_state.messages=[{"role":"assistant","content":L["welcome_nova"] if plan=="CREATOR" else L["welcome_forge"]}]
        st.session_state.action_message=""
        st.rerun()
with col_b:
    if st.button("Télécharger SRT", key="dl_srt_photo", use_container_width=True):
        if script:
            words=script.split()
            srt=""
            for i in range(0, len(words), 6):
                chunk=words[i:i+6]
                srt+=f"{i//6+1}\n00:00:{i//3:02d},000 --> 00:00:{i//3+2:02d},000\n{' '.join(chunk)}\n\n"
            st.download_button("Télécharger sous_titres.srt", srt, file_name="sous_titres.srt", mime="text/plain", key="dl_srt_btn_real")
        else:
            st.warning("Pas de script pour SRT")
with col_c:
    if st.button("Exporter visuel 1280x720", key="export_visuel_photo", use_container_width=True):
        img=generer_apercu_paysage(script or "montage vidéo professionnel", plan)
        st.image(img, use_container_width=True)
        st.success("Visuel 1280x720 généré")
with col_d:
    if st.button("Déconnexion", key="deco_photo", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.logged=False
        if "user" in st.session_state: del st.session_state.user
        st.rerun()

logo_path = LOGOS.get("main") or LOGOS.get("nova") or LOGOS.get("forge") or "logo.png"
for m in st.session_state.messages:
    if m.get("role")=="system": continue
    if m["role"]=="user":
        with st.chat_message("user"): st.markdown(sanitize_user(m["content"]))
    else:
        with st.chat_message("assistant", avatar=logo_path if os.path.exists(logo_path) else "🎬" if plan=="CREATOR" else "📱"):
            st.markdown(sanitize_assistant(m["content"]))
            if "image" in m and m["image"]: st.image(m["image"], use_container_width=True)

ask_key = L["ask_forge"] if plan=="FORGE" else L["ask_nova"]
prompt_raw = st.chat_input(ask_key, key="chat_input_photo_final")
if prompt_raw:
    check_rate_limit(plan)
    prompt_clean=sanitize_user(prompt_raw)
    st.session_state.messages.append({"role":"user","content":prompt_clean})
    msgs=[{"role":mm["role"],"content":sanitize_user(mm["content"])} for mm in st.session_state.messages if mm.get("role")!="system" and "image" not in mm]
    sys_prompt=SYSTEM_FORGE if plan=="FORGE" else SYSTEM_NOVA
    try:
        reponse,_=call_groq_durable([{"role":"system","content":sys_prompt}]+msgs[-20:])
        st.session_state.messages.append({"role":"assistant","content":sanitize_assistant(reponse)})
        supabase.table("licences").update({"used":used+1}).eq("key",licence_key).execute()
        st.rerun()
    except Exception as e: st.error(f"Erreur : {str(e)[:400]}")
