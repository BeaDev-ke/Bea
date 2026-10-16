import streamlit as st
import os
import re
import time
from groq import Groq
from supabase import create_client
from collections import deque
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="BehaviorLab AI", page_icon="logo.png", layout="wide", initial_sidebar_state="expanded")

STRIPE_BASIQUE = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"
STRIPE_PRO = "https://buy.stripe.com/test_cNieVea1P0c62B08523wQ00"
STRIPE_NOVA = "https://buy.stripe.com/test_nova_8_90"
STRIPE_FORGE = "https://buy.stripe.com/test_forge_13"

def find_file(cands):
    for f in cands:
        if os.path.exists(f):
            return f
    return None

def load_logos():
    bea = find_file(["logo_bea.png"])
    forge = find_file(["logo_forge.png", "logo_bloxks.png"])
    nova = find_file(["logo_nova.png"])
    main = find_file(["logo.png"])
    if bea and forge and "forge" in bea.lower():
        bea, forge = forge, bea
    return {"bea": bea, "forge": forge, "nova": nova, "main": main}

LOGOS = load_logos()

try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    SUPA_URL = st.secrets["SUPABASE_URL"]
    SUPA_KEY = st.secrets.get("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_PUBLISHABLE_KEY")
    client = Groq(api_key=GROQ_KEY)
    supabase = create_client(SUPA_URL, SUPA_KEY)
except Exception as e:
    st.error(f"Erreur Secrets : {e}")
    st.stop()

def get_modeles():
    try:
        ids = [m.id for m in client.models.list().data]
        pref = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "llama-3.3-70b-versatile"]
        return [m for m in pref if m in ids] or ids
    except:
        return ["openai/gpt-oss-20b"]

MODELES = get_modeles()

def call_groq(messages):
    last = None
    for mid in MODELES:
        try:
            c = client.chat.completions.create(model=mid, messages=messages, temperature=0.7, max_tokens=1800)
            return c.choices[0].message.content, mid
        except Exception as e:
            last = e
            continue
    raise last

for k, v in {"theme": "light", "lang": "FR", "messages": [], "show_uploader": False, "uploaded_file_info": None, "rate_limit": deque(), "blocked_until": 0, "selected_ia": None, "logged": False, "action_message": "", "uploaded_video_name": None}.items():
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

def sanitize_user(t):
    if not t:
        return ""
    return re.sub(r"<[^>]*>", "", t.strip()[:3000])

def sanitize_assistant(t):
    if not t:
        return ""
    t = re.sub(r"<script.*?>.*?</script>", "", t, flags=re.DOTALL | re.IGNORECASE)
    return re.sub(r"<[^>]*>", "", t).strip()[:6000]

def sanitize_key(t):
    return re.sub(r"[^a-zA-Z0-9-_]", "", t)[:100] if t else ""

def check_rate(plan):
    now = time.time()
    if now < st.session_state.blocked_until:
        st.error(f"Bloque {int(st.session_state.blocked_until - now)}s")
        st.stop()
    dq = st.session_state.rate_limit
    while dq and now - dq[0] > 60:
        dq.popleft()
    if len(dq) >= (50 if plan in ["PRO", "CREATOR", "FORGE"] else 15):
        st.session_state.blocked_until = now + 90
        st.error("Trop de requetes - 90s")
        st.stop()
    dq.append(now)

def generer_apercu(texte, plan="PRO"):
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), (18, 18, 40))
    draw = ImageDraw.Draw(img)
    try:
        ft = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
        fs = ImageFont.truetype("DejaVuSans.ttf", 18)
    except:
        ft = ImageFont.load_default()
        fs = ImageFont.load_default()
    for y in range(90):
        draw.line([(0, y), (W, y)], fill=(int(100+y*0.8), int(50+y*0.3), int(255-y*0.5)))
    draw.text((30, 22), "BehaviorLab AI - 1280x720", font=ft, fill="white")
    draw.rectangle([30, 120, W-30, H-30], fill=(35, 35, 70), outline=(120, 60, 255), width=3)
    draw.text((60, 160), f"{texte[:110]}", font=fs, fill="white")
    return img

SYSTEM_BEA = "Tu es Bea, IA de BehaviorLab AI."
SYSTEM_NOVA = "Tu es Nova Ultra, studio de BehaviorLab AI pour montage video professionnel. Format 9:16 TikTok. Style Viral pop."
SYSTEM_FORGE = "Tu es Forge, IA de BehaviorLab AI qui cree des apps Play Store en un prompt."

T = {"FR": {"main_title": "BehaviorLab AI", "sub_title": "Les IA comportementales pour votre reussite", "hero_desc": "BehaviorLab AI a cree les premieres IA du comportement. Pensee pour ceux qui veulent booster leur reussite, nos IA decodent le comportement humain pour un seul but :", "success": "votre reussite", "discover": "Decouvrir les 3 formats IA", "bea_tag": "L'IA qui decode tes clients et double ton closing", "nova_tag": "Le studio de montage video professionnel", "forge_tag": "L'IA qui cree ton app Play Store en un prompt", "ask_bea": "Demander a Bea...", "ask_nova": "Demander a Nova Ultra...", "ask_forge": "Decris ton app a Forge...", "dis_bea": "Decouvrir Bea", "dis_nova": "Decouvrir Nova Ultra", "dis_forge": "Decouvrir Forge", "email": "Adresse e-mail", "pwd": "Mot de passe", "login": "Connexion", "auth": "Authentification", "welcome_bea": "Salut, c'est Bea.", "welcome_nova": "Salut, c'est Nova Ultra.", "welcome_forge": "Salut, c'est Forge.", "connect": "Connecte-toi pour acceder a ton IA avec ta licence", "invalid": "Identifiants invalides"}}

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

GRAD_BEA = "linear-gradient(135deg, #1d4ed8 0%, #4f46e5 30%, #7c3aed 60%, #c026d3 85%, #db2777 100%)"
GRAD_NOVA = "linear-gradient(135deg, #7c3aed 0%, #db2777 50%, #f97316 100%)"
GRAD_FORGE = "linear-gradient(135deg, #0ea5e9 0%, #6366f1 50%, #8b5cf6 100%)"
GRAD = GRAD_FORGE if plan_detect == "FORGE" else GRAD_NOVA if plan_detect == "CREATOR" else GRAD_BEA
BG = "#ffffff" if not is_dark else "#0f0a1e"
TEXT = "#1e1b4b" if not is_dark else "#f5f3ff"
DESC = "#312e81" if not is_dark else "#c4b5fd"
CARD = "#ffffff" if not is_dark else "#1e1450"

st.markdown(f"""
<style>
.stApp{{background:{BG}!important;}}
.block-container{{padding-top:3.5rem!important;max-width:100%!important;}}
header[data-testid="stHeader"]{{background:{BG}!important;height:3.5rem!important;}}
[data-testid="stSidebar"]{{background:#1e1b4b!important;border-right:3px solid #7c3aed!important;}}
.auth-label{{color:#c4b5fd!important;font-size:13px!important;font-weight:700!important;margin:12px 0 6px 0!important;display:block!important;}}
#MainMenu,footer{{display:none!important;}}
div[data-testid="stButton"]>button{{background:{GRAD}!important;color:white!important;border-radius:14px!important;font-weight:700!important;border:none!important;min-height:44px!important;}}
div[data-testid="stLinkButton"]>a{{background:{GRAD}!important;color:white!important;border-radius:14px!important;}}
div[data-testid="stChatInput"]{{background:{"#2a2250" if is_dark else "#ffffff"}!important;border:2px solid #7c3aed!important;border-radius:20px!important;}}
div[data-testid="stChatMessage"]{{background:{CARD}!important;border:2px solid #7c3aed!important;border-radius:18px!important;padding:18px!important;}}
.montage-title{{font-size:38px;font-weight:800;color:{TEXT};margin:20px 0;}}
.montage-label{{color:{TEXT};font-size:14px;margin:18px 0 8px 0;font-weight:600;}}
</style>
""", unsafe_allow_html=True)

def vitrine_card(logo_key, title, tag, grad):
    path = LOGOS.get(logo_key)
    with st.container(border=True):
        if path and os.path.exists(path):
            st.image(path, width=80)
        else:
            st.markdown(f"<div style='width:80px;height:80px;background:{grad};border-radius:18px;display:flex;align-items:center;justify-content:center;color:white;font-weight:900;margin-bottom:12px;'>{title[0]}</div>", unsafe_allow_html=True)
        st.markdown(f"### {title}")
        st.caption(tag)

if st.session_state.selected_ia:
    if st.button("Retour", key="retour_vitrine_top"):
        st.session_state.selected_ia = None
        st.query_params.clear()
        st.rerun()

c1, c2 = st.columns([0.9, 5.1])
with c1:
    ml = LOGOS.get("main") or LOGOS.get("bea")
    if ml and os.path.exists(ml):
        st.image(ml, width=68)
with c2:
    if licence_key:
        nom = "Forge" if plan_detect == "FORGE" else "Nova Ultra" if plan_detect == "CREATOR" else "Bea"
        grad = GRAD_FORGE if plan_detect == "FORGE" else GRAD_NOVA if plan_detect == "CREATOR" else GRAD_BEA
        sous = L["forge_tag"] if plan_detect == "FORGE" else L["nova_tag"] if plan_detect == "CREATOR" else L["bea_tag"]
        st.markdown(f'<div style="background:{grad};border-radius:20px;padding:14px 22px;margin:10px 0;"><h2 style="color:white;margin:0;font-size:20px;">{nom}</h2><p style="color:white;margin:4px 0 0 0;font-size:13px;">{sous}</p></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="background:{GRAD_BEA};border-radius:20px;padding:22px 28px;margin:15px 0 25px 0;"><h2 style="color:white;margin:0;font-size:24px;">{L["main_title"]}</h2><p style="color:white;margin:5px 0 0 0;font-size:14px;">{L["sub_title"]}</p></div>', unsafe_allow_html=True)

# VITRINE LIBRE SANS CONNEXION OBLIGATOIRE
if not licence_key:
    with st.sidebar:
        if st.button("Clair" if is_dark else "Sombre", key="theme_vitrine", on_click=toggle_theme):
            st.rerun()
        if st.button(f"{st.session_state.lang}", key="lang_vitrine", on_click=toggle_lang):
            st.rerun()
        st.divider()
        st.markdown(f"### {L['auth']}")
        st.caption("Optionnel - uniquement si vous avez une licence")
        if st.session_state.logged and "user" in st.session_state:
            st.success(f"Connecte : {st.session_state.user.email}")
            if st.button("Deconnexion", key="deco_vitrine"):
                supabase.auth.sign_out()
                st.session_state.logged = False
                if "user" in st.session_state:
                    del st.session_state.user
                st.rerun()
        else:
            email = st.text_input("email_v", label_visibility="collapsed", placeholder="email@exemple.com", key="email_v")
            pwd = st.text_input("pwd_v", type="password", label_visibility="collapsed", placeholder="********", key="pwd_v")
            if st.button(L["login"], use_container_width=True, key="login_vitrine"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": pwd})
                    st.session_state.user = res.user
                    st.session_state.logged = True
                    st.rerun()
                except:
                    st.error(L["invalid"])
            st.caption("Pas encore de compte? Choisissez une offre ci-dessous, vous recevrez votre licence par e-mail.")

if not licence_key:
    if st.session_state.selected_ia == "bea":
        with st.container(border=True):
            st.markdown("## Bea - L'IA qui decode tes clients et double ton closing")
            st.markdown("**Transformer une intention en resultats concrets**")
            st.markdown("A partir d'une situation de vente, construire le blocage exact, le levier et le script qui debloque.")
            st.markdown("**Avantages**")
            st.markdown("- Detection du blocage exact qui freine la vente\n- Script doux et script direct prets a l'emploi\n- Chiffrage de ce que tu gagnes\n- Exemple vecu avec prenom age ville")
            st.caption("Pourquoi payer : Bea remplace des mois de tests par un script qui convertit immediatement.")
        st.link_button("Choisir Bea Pro - 21 / mois", STRIPE_PRO, use_container_width=True)
        st.stop()
    if st.session_state.selected_ia == "nova":
        with st.container(border=True):
            st.markdown("## Nova Ultra - Studio de montage video professionnel")
            st.markdown("**L'ensemble des fonctions de montage video professionnel reuni dans un seul outil.**")
            st.markdown("Production de videos pretes a diffuser : sous-titrage, decoupe, effets et mise en forme sont automatises.")
            st.markdown("**Avantages**")
            st.markdown("- Generation automatique de sous-titres stylises et synchronises avec la parole\n- Suppression de l'arriere-plan, decoupe des silences et nettoyage de la piste audio\n- Bibliotheque integree de modeles, d'effets, de transitions et d'animations\n- Export direct dans un format optimise pour chaque plateforme de diffusion")
            st.caption("Pourquoi payer : un seul outil remplace plusieurs logiciels et des heures de montage manuel.")
        st.link_button("Choisir Nova Ultra - 8,90 / mois", STRIPE_NOVA, use_container_width=True)
        st.stop()
    if st.session_state.selected_ia == "forge":
        with st.container(border=True):
            st.markdown("## Forge - L'IA qui cree ton app Play Store en un prompt")
            st.markdown("**De l'idee au projet executable**")
            st.markdown("A partir d'une intention de depart, construire un plan, des systemes et des outils qui fonctionnent.")
            st.markdown("**Avantages**")
            st.markdown("- Generation d'un plan d'action complet et ordonne\n- Creation de systemes reutilisables et de routines stables\n- Passage direct de la conception a l'execution, sans etape intermediaire inutile\n- Export APK/AAB, icone 512x512, screenshots, description Play Store")
            st.caption("Pourquoi payer : acces a une methode de construction qui evite des mois de dispersion et livre un resultat utilisable tout de suite.")
        st.link_button("Choisir Forge - 13 / mois", STRIPE_FORGE, use_container_width=True)
        st.stop()

    st.markdown(f"<h1 style='background:{GRAD_BEA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:900;font-size:52px;text-align:center;margin:20px 0 10px 0;'>{L['main_title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{DESC};font-size:19px;text-align:center;max-width:900px;margin:10px auto 30px auto;'>{T[st.session_state.lang]['hero_desc']} <span style='background:{GRAD_BEA};-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:800;'>{L['success']}</span>.</p>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='text-align:center;color:{TEXT};margin:40px 0 25px 0;font-size:28px;'>{L['discover']}</h2>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3, gap="large")
    with col1:
        vitrine_card("bea", "Bea", L["bea_tag"], GRAD_BEA)
        if st.button(L["dis_bea"], use_container_width=True, key="dis_bea"):
            st.session_state.selected_ia = "bea"
            st.query_params["ia"] = "bea"
            st.rerun()
    with col2:
        vitrine_card("nova", "Nova Ultra", L["nova_tag"], GRAD_NOVA)
        if st.button(L["dis_nova"], use_container_width=True, key="dis_nova"):
            st.session_state.selected_ia = "nova"
            st.query_params["ia"] = "nova"
            st.rerun()
    with col3:
        vitrine_card("forge", "Forge", L["forge_tag"], GRAD_FORGE)
        if st.button(L["dis_forge"], use_container_width=True, key="dis_forge"):
            st.session_state.selected_ia = "forge"
            st.query_params["ia"] = "forge"
            st.rerun()

    st.markdown("<div style='height:30px;'></div>", unsafe_allow_html=True)
    cA, cB, cC, cD = st.columns(4, gap="medium")
    with cA:
        with st.container(border=True):
            st.markdown("**Bea Basique** # 14,90")
            st.caption("12 requetes/mois")
            st.link_button("Choisir", STRIPE_BASIQUE, use_container_width=True, key="buy_basique_v")
    with cB:
        with st.container(border=True):
            st.markdown("**Bea Pro** # 21")
            st.caption("Illimite - Fichiers + Visuels 1280x720")
            st.link_button("Choisir", STRIPE_PRO, use_container_width=True, key="buy_pro_v")
    with cC:
        with st.container(border=True):
            st.markdown("**Nova Ultra** # 8,90")
            st.caption("Sous-titres auto - Decoupe silences - Effets")
            st.link_button("Choisir", STRIPE_NOVA, use_container_width=True, key="buy_nova_v")
    with cD:
        with st.container(border=True):
            st.markdown("**Forge** # 13")
            st.caption("1 prompt = 1 app - Publie Play Store")
            st.link_button("Choisir", STRIPE_FORGE, use_container_width=True, key="buy_forge_v")

    # DESCRIPTIONS BEHAVIORLAB AI AVEC FORMATS EN BAS - CE QUE TU DEMANDAIS
    st.markdown("<div style='height:50px;'></div>", unsafe_allow_html=True)
    st.divider()
    st.markdown(f"<h2 style='text-align:center;color:{TEXT};font-size:32px;margin:40px 0 20px 0;'>BehaviorLab AI - Les 3 formats</h2>", unsafe_allow_html=True)

    col_f1, col_f2, col_f3 = st.columns(3, gap="large")
    with col_f1:
        with st.container(border=True):
            if LOGOS.get("bea") and os.path.exists(LOGOS.get("bea")):
                st.image(LOGOS.get("bea"), width=60)
            st.markdown("#### De l'idee au projet - Bea")
            st.markdown("**Transformer une idee vague en projet structure et executable.**")
            st.caption("A partir d'une intention de depart, construire un plan, des systemes et des outils qui fonctionnent.")
            st.markdown("**Avantages**\n- Generation d'un plan d'action complet et ordonne\n- Creation de systemes reutilisables et de routines stables\n- Passage direct de la conception a l'execution")
            st.caption("Pourquoi payer : acces a une methode qui evite des mois de dispersion et livre un resultat utilisable tout de suite.")
            st.link_button("Payer - Bea 21€", STRIPE_PRO, use_container_width=True, key="pay_bea_bottom")
            if st.button("Ouvrir Bea", key="open_bea_bottom", use_container_width=True):
                st.session_state.selected_ia = "bea"
                st.query_params["ia"] = "bea"
                st.rerun()
    with col_f2:
        with st.container(border=True):
            if LOGOS.get("nova") and os.path.exists(LOGOS.get("nova")):
                st.image(LOGOS.get("nova"), width=60)
            st.markdown("#### Montage video professionnel - Nova Ultra")
            st.markdown("**L'ensemble des fonctions de montage video professionnel reuni dans un seul outil.**")
            st.caption("Production de videos pretes a diffuser : sous-titrage, decoupe, effets et mise en forme sont automatises.")
            st.markdown("**Avantages**\n- Generation automatique de sous-titres stylises et synchronises\n- Suppression de l'arriere-plan, decoupe des silences et nettoyage audio\n- Bibliotheque integree de modeles, d'effets, de transitions et d'animations\n- Export direct dans un format optimise pour chaque plateforme")
            st.caption("Pourquoi payer : un seul outil remplace plusieurs logiciels et des heures de montage manuel.")
            st.link_button("Payer - Nova 8,90€", STRIPE_NOVA, use_container_width=True, key="pay_nova_bottom")
            if st.button("Ouvrir Nova", key="open_nova_bottom", use_container_width=True):
                st.session_state.selected_ia = "nova"
                st.query_params["ia"] = "nova"
                st.rerun()
    with col_f3:
        with st.container(border=True):
            if LOGOS.get("forge") and os.path.exists(LOGOS.get("forge")):
                st.image(LOGOS.get("forge"), width=60)
            st.markdown("#### De l'idee au projet - Forge")
            st.markdown("**L'IA qui cree ton app Play Store en un prompt**")
            st.caption("De l'idee vague a l'app publiee sur Play Store en un prompt.")
            st.markdown("**Avantages**\n- 1 prompt = 1 app Android + iOS\n- Ecrans + Base de donnees + Paiement\n- Export APK/AAB, icone 512x512, screenshots\n- Publie Play Store en 1 clic")
            st.caption("Pourquoi payer : Forge evite des mois de dev et livre une app prete a publier.")
            st.link_button("Payer - Forge 13€", STRIPE_FORGE, use_container_width=True, key="pay_forge_bottom")
            if st.button("Ouvrir Forge", key="open_forge_bottom", use_container_width=True):
                st.session_state.selected_ia = "forge"
                st.query_params["ia"] = "forge"
                st.rerun()

    st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
    st.caption("BehaviorLab AI - Acces complet aux 3 IA")
    st.link_button("Acces complet aux 3 IA - Payer maintenant", STRIPE_PRO, use_container_width=True, key="buy_all_bottom")
    st.stop()

# Si licence presente, on demande connexion uniquement la
if "user" not in st.session_state or not st.session_state.logged:
    with st.sidebar:
        st.button("Clair" if is_dark else "Sombre", on_click=toggle_theme, use_container_width=True, key="theme_lic")
        st.divider()
        st.markdown(f"### {L['auth']}")
        st.caption("Connexion requise pour utiliser votre licence")
        email = st.text_input("email_lic", label_visibility="collapsed", placeholder="email@exemple.com", key="email_lic")
        pwd = st.text_input("pwd_lic", type="password", label_visibility="collapsed", placeholder="********", key="pwd_lic")
        if st.button(L["login"], use_container_width=True, key="login_lic"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": pwd})
                st.session_state.user = res.user
                st.session_state.logged = True
                st.rerun()
            except:
                st.error(L["invalid"])
    st.warning(L["connect"])
    st.stop()

try:
    res = supabase.table("licences").select("*").eq("key", licence_key).eq("user_id", st.session_state.user.id).execute()
except Exception as e:
    st.error(f"Erreur licence : {e}")
    st.stop()

if not res.data:
    st.error("Licence invalide")
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

if st.button("Retour", key="retour_photo"):
    st.session_state.selected_ia = None
    st.query_params.clear()
    st.rerun()

st.markdown(f"<h1 class='montage-title'>Montage video professionnel - Groq + Montage</h1>", unsafe_allow_html=True)

st.markdown(f"<p class='montage-label'>Video brute</p>", unsafe_allow_html=True)
col_up1, col_up2 = st.columns([0.3, 0.7])
with col_up1:
    uploaded_video = st.file_uploader("Upload", type=["mp4", "mov", "webm", "avi"], label_visibility="collapsed", key="upload_brute")
    if uploaded_video:
        st.session_state.uploaded_video_name = uploaded_video.name
        st.success(f"Charge : {uploaded_video.name}")
        if st.button("Supprimer video", key="del_video"):
            st.session_state.uploaded_video_name = None
            st.rerun()
with col_up2:
    st.markdown(f"<p style='color:#a1a1aa;font-size:13px;margin-top:10px;'>200MB per file - MP4, MOV, WEBM, AVI</p>", unsafe_allow_html=True)
    if uploaded_video:
        st.video(uploaded_video)

st.markdown(f"<p class='montage-label'>Script / paroles pour sous-titres</p>", unsafe_allow_html=True)
script = st.text_area("Script", height=120, label_visibility="collapsed", key="script_photo")

c_fmt, c_style = st.columns([0.6, 0.4])
with c_fmt:
    st.markdown(f"<p class='montage-label'>Format export</p>", unsafe_allow_html=True)
    fmt = st.selectbox("Format export", ["9:16 TikTok", "16:9 YouTube", "1:1 Carre"], label_visibility="collapsed", key="fmt_photo")
    if st.button(f"Format : {fmt}", key="btn_fmt"):
        st.toast(f"Format {fmt} selectionne")
        st.session_state.action_message = f"Format {fmt}"
with c_style:
    st.markdown(f"<p class='montage-label'>Style sous-titres</p>", unsafe_allow_html=True)
    style_sub = st.selectbox("Style sous-titres", ["Viral pop", "Hormozi bold", "Minimal"], label_visibility="collapsed", key="style_photo")
    if st.button(f"Style : {style_sub}", key="btn_style"):
        st.toast(f"Style {style_sub}")
        st.session_state.action_message = f"Style {style_sub}"

st.markdown("---")
c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("Couper", key="btn_cut", use_container_width=True):
        st.session_state.action_message = "Couper"
        st.toast("Couper")
        st.rerun()
with c2:
    if st.button("Sous-titres auto", key="btn_sub", use_container_width=True):
        st.session_state.action_message = "Sous-titres auto"
        st.toast("Sous-titres auto")
        st.rerun()
with c3:
    if st.button("Supprimer fond", key="btn_bg", use_container_width=True):
        st.session_state.action_message = "Supprimer fond"
        st.toast("Fond supprime")
        st.rerun()
with c4:
    if st.button("Modeles", key="btn_template", use_container_width=True):
        st.session_state.action_message = "Modeles"
        st.toast("Modeles")
        st.rerun()

c5, c6, c7, c8 = st.columns(4)
with c5:
    if st.button("Effets", key="btn_eff", use_container_width=True):
        st.session_state.action_message = "Effets"
        st.toast("Effets")
        st.rerun()
with c6:
    if st.button("Transitions", key="btn_trans", use_container_width=True):
        st.session_state.action_message = "Transitions"
        st.toast("Transitions")
        st.rerun()
with c7:
    if st.button("Nettoyage audio", key="btn_audio", use_container_width=True):
        st.session_state.action_message = "Nettoyage audio"
        st.toast("Audio")
        st.rerun()
with c8:
    if st.button("Couper silences", key="btn_sil", use_container_width=True):
        st.session_state.action_message = "Couper silences"
        st.toast("Silences")
        st.rerun()

if st.session_state.action_message:
    st.info(f"Action : {st.session_state.action_message}")

if st.button("Generer montage avec Groq", key="gen_groq", use_container_width=True):
    check_rate(plan)
    if not script and not uploaded_video:
        st.warning("Ajoute video ou script")
    else:
        prompt_clean = sanitize_user(script) if script else f"Genere montage {fmt} {style_sub}"
        st.session_state.messages.append({"role": "user", "content": prompt_clean})
        msgs = [{"role": mm["role"], "content": sanitize_user(mm["content"])} for mm in st.session_state.messages if mm.get("role")!= "system" and "image" not in mm]
        sys_prompt = SYSTEM_NOVA if plan == "CREATOR" else SYSTEM_FORGE
        sys_prompt += f" Format: {fmt} Style: {style_sub}."
        try:
            with st.spinner("Groq genere..."):
                reponse, _ = call_groq([{"role": "system", "content": sys_prompt}] + msgs[-15:])
                img = generer_apercu(prompt_clean, plan)
                st.session_state.messages.append({"role": "assistant", "content": sanitize_assistant(reponse), "image": img})
            supabase.table("licences").update({"used": used+1}).eq("key", licence_key).execute()
            st.success("Montage genere!")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {str(e)[:400]}")

st.divider()
col_a, col_b, col_c, col_d = st.columns(4)
with col_a:
    if st.button("Nouvelle discussion", key="new_chat", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": L["welcome_nova"] if plan == "CREATOR" else L["welcome_forge"]}]
        st.rerun()
with col_b:
    if st.button("Telecharger SRT", key="dl_srt", use_container_width=True):
        if script:
            words = script.split()
            srt = ""
            for i in range(0, len(words), 6):
                chunk = words[i:i+6]
                srt += f"{i//6+1}\n00:00:{i//3:02d},000 --> 00:00:{i//3+2:02d},000\n{' '.join(chunk)}\n\n"
            st.download_button("Telecharger sous_titres.srt", srt, file_name="sous_titres.srt", key="dl_btn")
        else:
            st.warning("Pas de script")
with col_c:
    if st.button("Exporter visuel", key="export_vis", use_container_width=True):
        img = generer_apercu(script or "montage", plan)
        st.image(img, use_container_width=True)
with col_d:
    if st.button("Deconnexion", key="deco", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.logged = False
        if "user" in st.session_state:
            del st.session_state.user
        st.rerun()

logo_path = LOGOS.get("main") or LOGOS.get("nova") or "logo.png"
for m in st.session_state.messages:
    if m.get("role") == "system":
        continue
    if m["role"] == "user":
        with st.chat_message("user"):
            st.markdown(sanitize_user(m["content"]))
    else:
        with st.chat_message("assistant", avatar=logo_path if os.path.exists(logo_path) else "assistant"):
            st.markdown(sanitize_assistant(m["content"]))
            if "image" in m and m["image"]:
                st.image(m["image"], use_container_width=True)

ask_key = L["ask_forge"] if plan == "FORGE" else L["ask_nova"]
prompt_raw = st.chat_input(ask_key, key="chat_input_final")
if prompt_raw:
    check_rate(plan)
    prompt_clean = sanitize_user(prompt_raw)
    st.session_state.messages.append({"role": "user", "content": prompt_clean})
    msgs = [{"role": mm["role"], "content": sanitize_user(mm["content"])} for mm in st.session_state.messages if mm.get("role")!= "system" and "image" not in mm]
    sys_prompt = SYSTEM_FORGE if plan == "FORGE" else SYSTEM_NOVA
    try:
        reponse, _ = call_groq([{"role": "system", "content": sys_prompt}] + msgs[-20:])
        st.session_state.messages.append({"role": "assistant", "content": sanitize_assistant(reponse)})
        supabase.table("licences").update({"used": used+1}).eq("key", licence_key).execute()
        st.rerun()
    except Exception as e:
        st.error(f"Erreur : {str(e)[:400]}")
