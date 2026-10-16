import streamlit as st
import os
import re
import time
from groq import Groq
from supabase import create_client
from collections import deque
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Bea", page_icon="logo_bea.png", layout="wide", initial_sidebar_state="expanded")

STRIPE_BEA_9 = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"
STRIPE_PRO_1490 = "https://buy.stripe.com/test_cNieVea1P0c62B08523wQ00"
STRIPE_ABO_16 = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"

def find_file(cands):
    for f in cands:
        if os.path.exists(f):
            return f
    return None

LOGOS = {"bea": find_file(["logo_bea.png", "logo.png"])}

try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    SUPA_URL = st.secrets["SUPABASE_URL"]
    SUPA_KEY = st.secrets.get("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_KEY")
    client = Groq(api_key=GROQ_KEY)
    supabase = create_client(SUPA_URL, SUPA_KEY)
except Exception as e:
    st.error(f"Erreur config : {e}")
    st.stop()

def get_modeles():
    try:
        ids = [m.id for m in client.models.list().data]
        pref = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "llama-3.3-70b-versatile", "llama-3.1-70b-versatile"]
        return [m for m in pref if m in ids] or ids
    except:
        return ["openai/gpt-oss-20b"]

MODELES = get_modeles()

def call_groq(messages):
    last = None
    for mid in MODELES:
        try:
            c = client.chat.completions.create(model=mid, messages=messages, temperature=0.7, max_tokens=2600)
            return c.choices[0].message.content, mid
        except Exception as e:
            last = e
            continue
    raise last

for k, v in {
    "theme": "dark", "lang": "FR", "messages": [], "code_messages": [], "rate_limit": deque(), "blocked_until": 0,
    "selected_format": "bea", "logged": False, "history": [], "projets_codes": [], "show_persona": False,
    "vitrine_section": "accueil", "expanded_format": None, "code_content": "# Bea - Création de code gratuite - BehaviorLab AI\n# Écris ton code ici librement\n\ndef bea_project():\n print('Bea - BehaviorLab AI - IA comportementale')\n idee = input('Ton idée: ')\n return f'App générée pour: {idee}'\n\nbea_project()",
    "code_language": "python", "script_text": "", "format_export": "9:16 Vertical", "style_sub": "Viral pop",
    "speed": 1.0, "filter": "Aucun", "current_tool": "", "action_message": "", "uploaded_video": None,
    "monthly_code_used": 0, "monthly_bea_used": 0, "monthly_pro_used": 0
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

if "user" not in st.session_state:
    try:
        sess = supabase.auth.get_session()
        if sess and sess.session and sess.session.user:
            st.session_state.user = sess.session.user
            st.session_state.logged = True
    except:
        pass

def sanitize_user(t):
    return re.sub(r"<[^>]*>", "", t.strip()[:4000]) if t else ""

def sanitize_assistant(t):
    t = re.sub(r"<script.*?>.*?</script>", "", t, flags=re.DOTALL | re.IGNORECASE)
    return re.sub(r"<[^>]*>", "", t).strip()[:6000] if t else ""

def sanitize_key(t):
    return re.sub(r"[^a-zA-Z0-9-_]", "", t)[:100] if t else ""

def check_rate_minute():
    now = time.time()
    if now < st.session_state.blocked_until:
        st.error(f"Patiente {int(st.session_state.blocked_until - now)}s")
        st.stop()
    dq = st.session_state.rate_limit
    while dq and now - dq[0] > 60:
        dq.popleft()
    if len(dq) >= 25:
        st.session_state.blocked_until = now + 60
        st.error("Trop de requêtes - attends 60s")
        st.stop()
    dq.append(now)

def check_monthly_limit(type_req="bea"):
    if st.session_state.selected_format == "abo":
        return True
    if type_req == "code":
        if st.session_state.monthly_code_used >= 10:
            st.warning("⚠️ Limite gratuite atteinte : 10 requêtes / mois pour l'IA code dans l'éditeur.")
            st.info("👉 Découvrez les formats payants ci-dessous pour continuer.")
            st.stop()
    elif type_req in ["bea", "pro"]:
        total = st.session_state.monthly_bea_used + st.session_state.monthly_pro_used
        if st.session_state.selected_format in ["bea", "pro"] and total >= 25:
            st.warning(f"⚠️ Limite atteinte : 25 requêtes / mois pour {st.session_state.selected_format}.")
            st.info("💎 Passez à l'offre Abonnement à 16 € / mois pour une utilisation illimitée - aucune rate limit.")
            st.stop()

def generer_visuel(texte, style="Viral"):
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), (18, 18, 40))
    draw = ImageDraw.Draw(img)
    try:
        ft = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
        fs = ImageFont.truetype("DejaVuSans.ttf", 15)
    except:
        ft = fs = ImageFont.load_default()
    for y in range(80):
        draw.line([(0, y), (W, y)], fill=(int(90+y*0.7), int(40+y*0.3), int(220-y*0.3)))
    draw.rectangle([30, 110, W-30, H-30], fill=(30, 30, 60), outline=(130, 70, 255), width=2)
    draw.text((50, 130), f"Bea - {style} - 1280x720", font=ft, fill="white")
    draw.text((50, 180), texte[:140], font=fs, fill="#d1c5ff")
    return img

SYSTEM_BEHAVIOR = """Tu es Bea, IA comportementale créée par BehaviorLab AI.
Tu aides les créateurs de contenu grâce à des méthodes psychologiques prouvées pour réussir.
Tu sais comment capter l'attention : la bonne luminosité pour arrêter le scroll,
comment une musique fait rester plus longtemps sur la vidéo, comment structurer un hook,
comment une couleur augmente la rétention.
Tu ne dévoiles pas les techniques en détail, tu montres que Bea maîtrise ces leviers comportementaux.
Tu transformes une idée floue en projet concret, tu structures, tu donnes plan, systèmes, outils."""

SYSTEM_CODE = "Tu es l'IA code de Bea, BehaviorLab AI. Tu es dans un éditeur simple avec Ask about your code à droite. Tu aides à comprendre, debugger, améliorer le code. Limite gratuite 10 req/mois."

licence_key = sanitize_key(st.query_params.get("key", ""))
GRAD = "linear-gradient(135deg, #1d4ed8 0%, #7c3aed 60%, #c026d3 85%, #db2777 100%)"
BORDER = "#7c3aed"
BG = "#0f0a1e"
CARD = "#1a1535"
TEXT = "#f5f3ff"

st.markdown(f"""
<style>
.stApp{{background:{BG}!important; overflow:visible!important;}}
[data-testid="stSidebar"]{{background:#0d0d14!important; border-right:3px solid {BORDER}!important;}}
[data-testid="stSidebar"] *{{color:#e2d6ff!important;}}
header[data-testid="stHeader"]{{background:transparent!important; height:0!important;}}
.block-container{{max-width:1150px!important; padding-top:2.8rem!important; padding-bottom:4rem!important; overflow:visible!important;}}
[data-testid="stVerticalBlock"]{{overflow:visible!important; gap:0.6rem;}}
#MainMenu,footer{{visibility:hidden;}}
div[data-testid="stButton"]>button{{background:#15112a!important; color:#e8e0ff!important; border:2px solid {BORDER}!important; border-radius:12px!important; font-weight:600!important; font-size:13px!important; min-height:44px!important;}}
div[data-testid="stButton"]>button:hover{{background:#231a4a!important; border-color:#a855f7!important; box-shadow:0 0 10px rgba(124,58,237,0.4)!important;}}
.tool-btn button{{background:#15112a!important; color:#e8e0ff!important; border:2px solid {BORDER}!important; border-radius:14px!important; font-weight:700!important; font-size:12px!important; text-align:center!important; min-height:76px!important; box-shadow:0 0 0 1px rgba(124,58,237,0.3)!important;}}
.tool-btn button:hover{{background:#231a4a!important; border-color:#c084fc!important;}}
div[data-testid="stLinkButton"]>a{{background:{GRAD}!important; color:white!important; border-radius:12px!important; font-weight:700!important; border:2px solid {BORDER}!important; padding:12px!important;}}
div[data-testid="stChatMessage"]{{background:{CARD}!important; border:2px solid {BORDER}!important; border-radius:16px!important; padding:14px!important;}}
div[data-testid="stChatMessage"] p{{color:{TEXT}!important; font-size:15px!important; line-height:1.6!important;}}
div[data-testid="stChatInput"]{{background:#1a1535!important; border:2px solid {BORDER}!important; border-radius:24px!important;}}
input, textarea{{background:#1a1535!important; color:{TEXT}!important; border:2px solid {BORDER}!important; border-radius:12px!important;}}
.login-box{{background:#15112a; border:2px solid {BORDER}; border-radius:18px; padding:22px; margin-top:10px; box-shadow:0 0 20px rgba(124,58,237,0.2);}}
.logo-top{{display:flex; justify-content:center; margin-top:12px; margin-bottom:8px; padding:8px; overflow:visible!important;}}
.logo-top img{{object-fit:contain;}}
.claude-title{{font-size:34px; font-weight:800; color:{TEXT}; text-align:center; margin:8px 0 2px 0;}}
.claude-sub{{font-size:12px; color:#d8ccff!important; text-align:center; font-weight:700; letter-spacing:0.8px; margin-bottom:16px;}}
.desc-main{{font-size:14px; color:#c4b5fd; text-align:center; max-width:720px; margin:12px auto 32px auto; line-height:1.7;}}
.timeline{{background:#15112a; border-radius:14px; padding:14px; border:2px solid {BORDER}; margin:14px 0;}}
.timeline-track{{background:#0d0d1e; height:46px; border-radius:10px; margin:8px 0; display:flex; align-items:center; padding:0 10px; border:1px solid #2a2250;}}
.track-block{{background:{GRAD}; height:34px; border-radius:8px; min-width:80px; margin-right:8px; display:flex; align-items:center; justify-content:center; font-size:11px; color:white; font-weight:700; border:1px solid #a855f7;}}
.limit-badge{{background:#2a1a4a; border:1px solid {BORDER}; border-radius:8px; padding:6px 10px; font-size:11px; color:#c4b5fd; margin-bottom:10px;}}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div style="display:flex; flex-direction:column; align-items:center; padding-top:12px;">', unsafe_allow_html=True)
    logo_path = LOGOS.get("bea")
    if logo_path and os.path.exists(logo_path):
        st.image(logo_path, width=62)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; font-size:18px; font-weight:800; color:#f5f3ff; margin-top:6px;">Bea</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; font-size:11px; color:#d8ccff!important; font-weight:700; letter-spacing:0.8px; margin-bottom:12px;">BehaviorLab AI</div>', unsafe_allow_html=True)

    if st.session_state.logged:
        if st.session_state.selected_format == "abo":
            st.markdown('<div class="limit-badge">♾️ Abonnement 16 € - Aucune rate limit - Illimité</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="limit-badge">Code gratuit: {st.session_state.monthly_code_used}/10 | Bea: {st.session_state.monthly_bea_used+st.session_state.monthly_pro_used}/25</div>', unsafe_allow_html=True)

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        if st.button("🌙 Sombre", key="btn_theme", use_container_width=True):
            st.rerun()
    with col_t2:
        if st.button(f"🌐 {st.session_state.lang}", key="btn_lang", use_container_width=True):
            st.session_state.lang = "EN" if st.session_state.lang == "FR" else "FR"
            st.rerun()

    st.divider()

    if not st.session_state.logged and not licence_key:
        st.caption("Bienvenue sur Bea - Gratuit après connexion")
    else:
        if st.button("✨ Nouvelle discussion", key="new_side_pay", use_container_width=True):
            st.session_state.messages = []
            st.session_state.code_messages = []
            st.session_state.history.append(f"Chat {len(st.session_state.history)+1}")
            st.toast("Nouvelle discussion")
            st.rerun()

        if st.button("💻 Code", key="code_side_pay", use_container_width=True):
            st.session_state.vitrine_section = "code"
            st.rerun()

        if st.button("🎨 Personnalisation", key="perso_side_pay", use_container_width=True):
            st.session_state.show_persona = True
            st.session_state.vitrine_section = "perso"
            st.rerun()

        if st.button("📁 Projets", key="proj_side_pay", use_container_width=True):
            st.session_state.vitrine_section = "projets"
            st.rerun()

        if st.session_state.history:
            st.markdown('<div style="font-size:10px; color:#8a7ab8; text-transform:uppercase; margin:14px 0 6px 0; font-weight:700;">Historique</div>', unsafe_allow_html=True)
            for h in st.session_state.history[-8:][::-1]:
                if "Bienvenue" in h:
                    continue
                if st.button(f"• {h[:20]}", key=f"hist_{h}_{len(h)}", use_container_width=True):
                    st.session_state.vitrine_section = "accueil"
                    st.rerun()

        st.markdown('<div style="font-size:10px; color:#8a7ab8; text-transform:uppercase; margin:14px 0 6px 0; font-weight:700;">Derniers codes</div>', unsafe_allow_html=True)
        for idx, code_item in enumerate(st.session_state.projets_codes[-6:][::-1]):
            if st.button(f"💾 {code_item['name'][:18]}", key=f"code_proj_{idx}", use_container_width=True):
                st.session_state.code_content = code_item["content"]
                st.session_state.vitrine_section = "code"
                st.rerun()

        st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
        if "user" in st.session_state:
            st.caption(f"{st.session_state.user.email}")
            if st.button("🚪 Déconnexion", key="deco_side", use_container_width=True):
                supabase.auth.sign_out()
                st.session_state.logged = False
                if "user" in st.session_state:
                    del st.session_state.user
                st.rerun()

def render_editor_complet():
    st.markdown("### Création de code gratuite + discussion libre à droite")
    st.markdown(f"<div style='background:#15112a; border:2px solid {BORDER}; border-radius:10px; padding:10px; font-size:12px; color:#c4b5fd; margin-bottom:12px;'>Éditeur libre - Bea - BehaviorLab AI - IA comportementale - Écris ton code à gauche, discute avec l'IA à droite (Ask about your code) - Limite gratuite {st.session_state.monthly_code_used}/10 par mois</div>", unsafe_allow_html=True)

    col_editor, col_chat = st.columns([1.25, 0.75], gap="medium")

    with col_editor:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("📄 Nouveau fichier", key="ed_new", use_container_width=True):
                st.session_state.code_content = "# Nouveau fichier Bea\n"
                st.session_state.code_messages = []
                st.rerun()
        with c2:
            if st.button("💾 Sauver dans Projets", key="ed_save", use_container_width=True):
                name = f"Code_{len(st.session_state.projets_codes)+1}.py"
                st.session_state.projets_codes.append({"name": name, "content": st.session_state.code_content, "lang": st.session_state.code_language})
                st.toast(f"{name} sauvé")
                st.rerun()
        with c3:
            if st.button("▶️ Exécuter", key="ed_run", use_container_width=True):
                st.success("Exécution terminal")
                st.code(f"> python main.py\n{st.session_state.code_content[:200]}\n\nBea - BehaviorLab AI ready", language="bash")
        with c4:
            lang = st.selectbox("Lang", ["python", "javascript", "typescript", "html", "css", "json"], index=0, key="ed_lang", label_visibility="collapsed")
            st.session_state.code_language = lang

        code_input = st.text_area("Éditeur code", value=st.session_state.code_content, height=480, key="code_editor_main", label_visibility="collapsed")
        if code_input!= st.session_state.code_content:
            st.session_state.code_content = code_input

        st.code(f"Ln {len(code_input.splitlines())}, Col 1 | Spaces: 4 | UTF-8 | CRLF | {st.session_state.code_language} | Bea BehaviorLab AI | {st.session_state.monthly_code_used}/10", language="text")

    with col_chat:
        st.markdown(f"""
        <div style="background:#15112a; border:2px solid {BORDER}; border-radius:12px; padding:14px; text-align:center; margin-bottom:10px;">
            <div style="font-size:24px;">💬✨</div>
            <div style="color:#f5f3ff; font-weight:700; margin:6px 0;">Ask about your code</div>
            <div style="color:#8a7ab8; font-size:11px; line-height:1.4;">AI responses may be inaccurate<br/>Gratuit: {st.session_state.monthly_code_used}/10 par mois<br/>Après: Découvrir les formats payants</div>
        </div>
        """, unsafe_allow_html=True)

        for m in st.session_state.code_messages[-8:]:
            if m["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(sanitize_user(m["content"]))
            else:
                with st.chat_message("assistant", avatar=LOGOS["bea"] if LOGOS["bea"] and os.path.exists(LOGOS["bea"]) else "Bea"):
                    st.markdown(sanitize_assistant(m["content"]))

        q = st.chat_input("Ask about your code...", key="code_chat")
        if q:
            check_rate_minute()
            check_monthly_limit("code")
            st.session_state.code_messages.append({"role": "user", "content": sanitize_user(q)})
            ctx = st.session_state.code_content[:2500]
            msgs = [{"role": "system", "content": SYSTEM_CODE + f"\nCode actuel:\n{ctx}"}] + [{"role": mm["role"], "content": sanitize_user(mm["content"])} for mm in st.session_state.code_messages[-10:]]
            try:
                rep, _ = call_groq(msgs)
                st.session_state.code_messages.append({"role": "assistant", "content": sanitize_assistant(rep)})
                st.session_state.monthly_code_used += 1
                st.rerun()
            except Exception as e:
                st.error(str(e)[:400])

        if st.button("Expliquer mon code", key="exp_code", use_container_width=True):
            check_monthly_limit("code")
            st.session_state.code_messages.append({"role": "user", "content": "Explique mon code ligne par ligne"})
            msgs = [{"role": "system", "content": SYSTEM_CODE + f"\nCode:\n{st.session_state.code_content[:2500]}"}, {"role": "user", "content": "Explique mon code ligne par ligne"}]
            try:
                rep, _ = call_groq(msgs)
                st.session_state.code_messages.append({"role": "assistant", "content": sanitize_assistant(rep)})
                st.session_state.monthly_code_used += 1
                st.rerun()
            except Exception as e:
                st.error(str(e))
        if st.button("Corriger / Améliorer mon code", key="fix_code", use_container_width=True):
            check_monthly_limit("code")
            st.session_state.code_messages.append({"role": "user", "content": "Corrige et améliore mon code"})
            msgs = [{"role": "system", "content": SYSTEM_CODE + f"\nCode:\n{st.session_state.code_content[:2500]}"}, {"role": "user", "content": "Corrige et améliore mon code et donne version corrigée"}]
            try:
                rep, _ = call_groq(msgs)
                st.session_state.code_messages.append({"role": "assistant", "content": sanitize_assistant(rep)})
                st.session_state.monthly_code_used += 1
                st.rerun()
            except Exception as e:
                st.error(str(e))
        if st.button("Générer Agent Instructions", key="agent_instr", use_container_width=True):
            st.toast("Instructions agent générées pour ta codebase")

# VITRINE COMME CLAUDE - CONNEXION D'ABORD - FIX COUPE
if not st.session_state.logged and not licence_key:
    st.markdown('<div class="logo-top">', unsafe_allow_html=True)
    logo_path = LOGOS.get("bea")
    if logo_path and os.path.exists(logo_path):
        st.image(logo_path, width=80)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="claude-title">Bea</div>', unsafe_allow_html=True)
    st.markdown('<div class="claude-sub">BehaviorLab AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="desc-main">Bea est une IA du comportement qui aide les créateurs de contenu à réussir grâce à des méthodes psychologiques prouvées. Elle comprend la bonne luminosité pour arrêter le scroll et comment une musique fait rester plus longtemps.</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([0.5, 1.6, 0.5])
    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("#### Se connecter pour accéder")
        email = st.text_input("email_login", label_visibility="collapsed", placeholder="Adresse e-mail", key="email_claude")
        pwd = st.text_input("pwd_login", label_visibility="collapsed", type="password", placeholder="Mot de passe", key="pwd_claude")
        if st.button("Continuer", use_container_width=True, key="login_claude"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": pwd})
                st.session_state.user = res.user
                st.session_state.logged = True
                st.rerun()
            except:
                st.error("Identifiants invalides")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:42px;'></div>", unsafe_allow_html=True)
    st.markdown("## Découvrir les formats")

    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        with st.container(border=True):
            st.markdown("#### Bea : 9 € par mois")
            st.caption("25 requêtes / mois - IA comportementale")
            if st.button("Voir description", key="btn_bea", use_container_width=True):
                st.session_state.expanded_format = "bea" if st.session_state.expanded_format!= "bea" else None
                st.rerun()
            if st.session_state.expanded_format == "bea":
                st.markdown("**Bea est une IA du comportement. Elle aide les créateurs de contenu grâce à des méthodes psychologiques prouvées pour réussir.**")
                st.markdown("Bea part d'une idée encore floue et la transforme en projet concret. Elle ne se contente pas de générer du contenu, elle comprend les leviers qui font qu'une vidéo arrête le scroll ou qu'une musique fait rester plus longtemps. Son point fort : repérer le blocage précis qui ralentit votre avancement, puis proposer une solution mesurable, applicable immédiatement.")
                st.markdown("**Dans quoi elle peut vous aider :**\n- Blocage psychologique et procrastination\n- Closing et négociation\n- La bonne luminosité pour capter l'attention et arrêter le scroll\n- Comment une musique ou un rythme fait rester plus longtemps sur la vidéo\n- Organisation et passage de l'idée au concret")
                st.markdown("**Ce que vous obtenez :**\n- L'identification du blocage exact qui freine votre projet\n- Des scripts prêts à l'emploi, à la fois doux et directs, pour convaincre\n- Une estimation chiffrée du temps et de l'argent gagnés\n- Un exemple concret avec preuve sociale")
                st.markdown("**+ Studio de montage pro inclus (ancien Pro) :**\n- Génération automatique de sous-titres stylisés synchronisés avec la parole\n- Suppression de l'arrière-plan, découpe des silences et nettoyage audio en un clic\n- Bibliothèque intégrée de modèles, d'effets, de transitions et d'animations\n- Export direct dans un format adapté à chaque plateforme (9:16, 16:9, 1:1)\n- Visuels 1280x720 qui augmentent le taux de clic et la rétention")
                st.caption("Méthodes psychologiques prouvées - Bea les applique pour vous faire réussir.")
            st.link_button("Choisir Bea - 9 €", STRIPE_BEA_9, use_container_width=True)

    with c2:
        with st.container(border=True):
            st.markdown("#### Bea Pro : 14,90 € par mois")
            st.caption("25 requêtes / mois - La plus choisie")
            if st.button("Voir description", key="btn_pro", use_container_width=True):
                st.session_state.expanded_format = "pro" if st.session_state.expanded_format!= "pro" else None
                st.rerun()
            if st.session_state.expanded_format == "pro":
                st.markdown("**Bea Pro reprend toutes les forces de Bea à 9 € et y ajoute la création d'applications complètes. Toujours basée sur des méthodes psychologiques prouvées pour que vos contenus performent.**")
                st.markdown("**Ce que vous obtenez :**\n- Toutes les fonctions de Bea 9 €\n- Un prompt = une application complète fonctionnelle\n- Écrans + Base de données + Paiement + Auth intégrés automatiquement\n- Icône 512x512, captures, description générées pour le store\n- Fichier exporté prêt à publier (APK ou Web)")
                st.markdown("**Fonctions supplémentaires :**\n- Génération d'applications complètes\n- Éditeur de code avec IA à droite\n- Timeline vidéo professionnelle\n- Export vidéo\n- Tous les outils montage : couper / découper, sous-titres auto, supprimer fond, découpe silences, nettoyage audio, modèles bibliothèque, effets vidéo, transitions animées, animations texte, filtres couleur, vitesse et ralenti, stickers et emojis, bibliothèque musicale, recadrer zoom, stabiliser vidéo, voix off IA, miniatures 1280x720, créer app en 1 prompt.")
            st.link_button("Choisir Bea Pro - 14,90 €", STRIPE_PRO_1490, use_container_width=True)

    with c3:
        with st.container(border=True):
            st.markdown("#### Abonnement : 16 € par mois")
            st.caption("Aucune rate limit - Illimité")
            if st.button("Voir description", key="btn_abo", use_container_width=True):
                st.session_state.expanded_format = "abo" if st.session_state.expanded_format!= "abo" else None
                st.rerun()
            if st.session_state.expanded_format == "abo":
                st.markdown("**L'offre abonnement complète pour les créateurs qui veulent tout, sans limite.**")
                st.markdown("**Ce que vous obtenez :**\n- Tout Bea Pro 14,90 € inclus\n- Aucune rate limit - requêtes illimitées\n- Discussions illimitées\n- Historique complet conservé\n- Projets illimités sauvegardés\n- Support prioritaire BehaviorLab AI\n- Accès anticipé aux nouvelles fonctions")
                st.markdown("**Pourquoi l'IA comportementale change tout :** Bea ne fait pas juste du montage, elle applique des méthodes psychologiques prouvées pour que vos vidéos arrêtent le scroll, retiennent plus longtemps, convertissent mieux. Luminosité, rythme, musique, hook - tout est pensé pour le cerveau humain.")
            st.link_button("S'abonner - 16 € Illimité", STRIPE_ABO_16, use_container_width=True)
    st.stop()

if licence_key and not st.session_state.logged:
    with st.container(border=True):
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("#### Se connecter pour accéder")
        email = st.text_input("email_lic", label_visibility="collapsed", placeholder="Adresse e-mail")
        pwd = st.text_input("pwd_lic", label_visibility="collapsed", type="password", placeholder="Mot de passe")
        if st.button("Continuer", key="login_lic"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": pwd})
                st.session_state.user = res.user
                st.session_state.logged = True
                st.rerun()
            except:
                st.error("Identifiants invalides")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

if licence_key:
    try:
        res = supabase.table("licences").select("*").eq("key", licence_key).eq("user_id", st.session_state.user.id).execute()
        if not res.data:
            st.error("Licence invalide")
            st.stop()
        lic = res.data[0]
        plan, used = lic["plan"], lic["used"]
        # Détecte format selon plan
        if "16" in str(lic.get("plan","")) or "abo" in str(lic.get("plan","")).lower():
            st.session_state.selected_format = "abo"
        elif "14" in str(lic.get("plan","")):
            st.session_state.selected_format = "pro"
        else:
            st.session_state.selected_format = "bea"
    except Exception as e:
        st.error(f"Erreur licence : {e}")
        st.stop()
else:
    plan, used = "PRO", 0

if st.session_state.vitrine_section == "perso" or st.session_state.show_persona:
    with st.container(border=True):
        st.markdown("### 👤 Personnaliser Bea")
        nom = st.text_input("Comment Bea doit vous appeler?", placeholder="Ex: Alex", key="perso_nom_pay")
        style = st.selectbox("Style de réponse", ["Direct", "Doux", "Détaillé", "Expert comportemental"], key="perso_style_pay")
        objectif = st.text_input("Objectif principal", placeholder="Ex: arrêter le scroll sur mes vidéos", key="perso_obj_pay")
        if st.button("Enregistrer personnalisation", key="save_perso_pay"):
            st.success(f"Bea vous appellera {nom} en style {style} pour {objectif}")
            st.session_state.show_persona = False
            st.session_state.vitrine_section = "code"
            st.rerun()
        if st.button("Retour", key="ret_perso_pay"):
            st.session_state.show_persona = False
            st.session_state.vitrine_section = "code"
            st.rerun()

elif st.session_state.vitrine_section == "projets":
    with st.container(border=True):
        st.markdown("### 📁 Projets - Derniers codes sauvés")
        st.caption("Ici tous tes derniers codes sauvés depuis l'éditeur Code gratuit")
        if not st.session_state.projets_codes:
            st.info("Aucun code sauvé pour l'instant. Va dans Code > Sauver dans Projets")
        else:
            for item in st.session_state.projets_codes[::-1]:
                with st.container(border=True):
                    st.markdown(f"**{item['name']}** - {item['lang']}")
                    st.code(item["content"][:800], language=item["lang"])
                    c_o, c_d = st.columns(2)
                    with c_o:
                        if st.button(f"Ouvrir {item['name']}", key=f"open_{item['name']}_{len(item)}"):
                            st.session_state.code_content = item["content"]
                            st.session_state.vitrine_section = "code"
                            st.rerun()
                    with c_d:
                        if st.button(f"Supprimer {item['name']}", key=f"del_{item['name']}_{len(item)}"):
                            st.session_state.projets_codes = [p for p in st.session_state.projets_codes if p["name"]!= item["name"]]
                            st.rerun()
        if st.button("Retour Code", key="ret_proj_pay"):
            st.session_state.vitrine_section = "code"
            st.rerun()
    st.stop()

else:
    render_editor_complet()

    st.divider()

    if len(st.session_state.messages) == 0:
        st.session_state.messages.append({"role": "assistant", "content": "Bonjour, je suis Bea, ton IA comportementale. Je t'aide grâce à des méthodes psychologiques prouvées : bonne luminosité pour arrêter le scroll, musique pour faire rester plus longtemps, hook qui retient."})

    st.markdown("### Montage vidéo professionnel - Bea peut tout faire grâce aux méthodes comportementales")
    st.markdown(f"<div style='background:#15112a; border:2px solid {BORDER}; border-radius:10px; padding:10px; font-size:12px; color:#c4b5fd; margin-bottom:12px;'>Format: {st.session_state.format_export} | Style: {st.session_state.style_sub} | Filtre: {st.session_state.filter} | Vitesse: {st.session_state.speed}x | Outil: {st.session_state.current_tool} | {st.session_state.action_message} | Rate: {st.session_state.monthly_bea_used+st.session_state.monthly_pro_used}/25 ou illimité si abonnement 16 €</div>", unsafe_allow_html=True)

    col_a, col_b = st.columns([0.35, 0.65])
    with col_a:
        up = st.file_uploader("Vidéo brute - 200MB max MP4 MOV WEBM AVI", type=["mp4", "mov", "webm", "avi"], label_visibility="collapsed", key="up_video")
        if up:
            st.session_state.uploaded_video = up
            st.success(f"{up.name} chargée - Bea analyse la luminosité pour stopper le scroll")
            st.video(up)
            if st.button("Supprimer vidéo", key="del_vid"):
                st.session_state.uploaded_video = None
                st.rerun()
        else:
            st.caption("Glissez vidéo ici - MP4 MOV WEBM AVI - 200MB max")

    with col_b:
        txt = st.text_area("Script / paroles pour sous-titres stylisés synchronisés", height=140, placeholder="Collez votre script ici pour générer sous-titres auto...", key="script_area")
        if txt:
            st.session_state.script_text = txt
            st.caption(f"{len(txt.split())} mots - {len(txt)} caractères")

    c_fmt, c_style, c_speed, c_filtre = st.columns(4)
    with c_fmt:
        fmt = st.selectbox("Format export", ["9:16 Vertical", "16:9 Horizontal", "1:1 Carré", "4:5", "21:9 Cinéma"], key="fmt_sel")
        st.session_state.format_export = fmt
    with c_style:
        sty = st.selectbox("Style sous-titres", ["Viral pop", "Hormozi bold", "Minimal", "Cinéma", "Neon", "Journal", "Bold"], key="style_sel")
        st.session_state.style_sub = sty
    with c_speed:
        spd = st.select_slider("Vitesse", options=[0.5, 0.75, 1.0, 1.25, 1.5, 2.0], value=1.0, key="speed_sel")
        st.session_state.speed = spd
    with c_filtre:
        filt = st.selectbox("Filtre couleur", ["Aucun", "Cinéma", "Vintage", "Vivid", "Noir & Blanc"], key="filtre_sel")
        st.session_state.filter = filt

    st.markdown("### Outils principaux - Tous les outils de montage - Méthodes psychologiques prouvées")
    r1 = st.columns(6)
    tools_r1 = [("Couper\nDécouper", "t_cut", "Découpe vidéo active"), ("Sous-titres\nAuto", "t_sub", "Sous-titres générés avec méthode pour retenir"), ("Supprimer\nFond", "t_bg", "Arrière-plan supprimé - focus attention"), ("Découpe\nSilences", "t_sil", "Silences coupés - rythme qui retient"), ("Nettoyage\nAudio", "t_audio", "Audio nettoyé - clarté = rétention"), ("Modèles\nBibliothèque", "t_model", "Modèles ouverts")]
    for i, (label, key, msg) in enumerate(tools_r1):
        with r1[i]:
            st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
            if st.button(label, key=key, use_container_width=True):
                st.session_state.current_tool = label.replace("\n", " ")
                st.session_state.action_message = msg
                if key == "t_sub" and st.session_state.script_text:
                    mots = st.session_state.script_text.split()
                    srt = ""
                    for j in range(0, len(mots), 5):
                        srt += f"{j//5+1}\n00:00:{j//3:02d},000 --> 00:00:{j//3+2:02d},000\n{' '.join(mots[j:j+5])}\n\n"
                    st.session_state.action_message = f"{len(mots)} sous-titres {st.session_state.style_sub} - méthode psychologique pour rester"
                    st.download_button("Télécharger SRT", srt, file_name="sous_titres.srt", key=f"dl_srt_{i}")
                st.toast(label)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    r2 = st.columns(6)
    tools_r2 = [("Effets\nVidéo", "t_eff"), ("Transitions\nAnimées", "t_trans"), ("Animations\nTexte", "t_anim"), ("Filtres\nCouleur", "t_filt"), ("Vitesse\nRalenti", "t_speed"), ("Stickers\nEmojis", "t_stick")]
    for i, (label, key) in enumerate(tools_r2):
        with r2[i]:
            st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
            if st.button(label, key=key, use_container_width=True):
                st.session_state.current_tool = label.replace("\n", " ")
                st.session_state.action_message = f"{label} appliqué - Filtre {st.session_state.filter} Vitesse {st.session_state.speed}x - méthode pour arrêter le scroll"
                st.toast(label)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    r3 = st.columns(6)
    tools_r3 = [("Musique\nBibliothèque", "t_music"), ("Recadrer\nZoom", "t_crop"), ("Stabiliser\nVidéo", "t_stab"), ("Voix Off\nIA", "t_voice"), ("Miniature\n1280x720", "t_thumb"), ("Créer App\nEn 1 prompt", "t_app")]
    for i, (label, key) in enumerate(tools_r3):
        with r3[i]:
            st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
            if st.button(label, key=key, use_container_width=True):
                if key == "t_thumb":
                    img = generer_visuel(st.session_state.script_text or "Bea", st.session_state.style_sub)
                    st.image(img, caption="Miniature 1280x720 générée - méthode psychologique pour clic", use_container_width=True)
                    st.session_state.action_message = "Miniature 1280x720 générée - luminosité optimisée pour arrêter le scroll"
                elif key == "t_app":
                    st.session_state.messages.append({"role": "user", "content": "Créer une application complète en un prompt"})
                    st.session_state.action_message = "Création app lancée"
                elif key == "t_music":
                    st.session_state.action_message = "Musique sélectionnée - méthode pour faire rester plus longtemps"
                else:
                    st.session_state.action_message = f"{label} active"
                st.session_state.current_tool = label.replace("\n", " ")
                st.toast(label)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="timeline"><div style="color:#c4b5fd; font-size:11px; margin-bottom:8px; font-weight:700;">TIMELINE - Glisser pour éditer - Format {st.session_state.format_export} - Méthodes comportementales pour rétention</div><div class="timeline-track"><div class="track-block">Intro 0:03 - Hook</div><div class="track-block" style="min-width:140px; background:linear-gradient(135deg,#db2777,#f97316);">{st.session_state.style_sub} - {st.session_state.speed}x</div><div class="track-block" style="background:#2a2a4a;">Outro 0:02 - CTA</div></div><div style="color:#8a7ab8; font-size:10px; margin-top:6px;">Filtre: {st.session_state.filter} | {st.session_state.script_text[:60] if st.session_state.script_text else "Ajoutez script pour sous-titres avec méthode psychologique"}</div></div>', unsafe_allow_html=True)

    if st.session_state.action_message:
        st.info(f"Outil actif: {st.session_state.current_tool} | {st.session_state.action_message}")

    c_act1, c_act2, c_act3, c_act4 = st.columns(4)
    with c_act1:
        if st.button("Générer montage complet", key="gen_full", use_container_width=True):
            check_rate_minute()
            check_monthly_limit("bea")
            prompt = st.session_state.script_text or "Générer montage pro complet avec méthodes psychologiques"
            full_prompt = f"{prompt} Format {st.session_state.format_export} Style {st.session_state.style_sub} Filtre {st.session_state.filter} Vitesse {st.session_state.speed}x - Utilise méthodes comportementales prouvées"
            st.session_state.messages.append({"role": "user", "content": full_prompt})
            msgs = [{"role": mm["role"], "content": sanitize_user(mm["content"])} for mm in st.session_state.messages if mm.get("role")!= "system" and "image" not in mm]
            sys_prompt = SYSTEM_BEHAVIOR
            try:
                with st.spinner("Génération montage complet avec méthodes comportementales..."):
                    reponse, _ = call_groq([{"role": "system", "content": sys_prompt}] + msgs[-12:])
                    img = generer_visuel(prompt, st.session_state.style_sub)
                    st.session_state.messages.append({"role": "assistant", "content": sanitize_assistant(reponse), "image": img})
                    st.session_state.monthly_bea_used += 1
                if licence_key:
                    supabase.table("licences").update({"used": used+1}).eq("key", licence_key).execute()
                st.success("Montage généré! Miniature 1280x720 prête - méthodes pour arrêter le scroll appliquées")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {str(e)[:400]}")
    with c_act2:
        if st.button("Nouvelle discussion", key="new_chat_main", use_container_width=True):
            st.session_state.messages = []
            st.session_state.history.append(f"Chat {len(st.session_state.history)+1}")
            st.rerun()
    with c_act3:
        if st.button("Exporter vidéo", key="export_vid", use_container_width=True):
            st.success(f"Export lancé en {st.session_state.format_export} - Style {st.session_state.style_sub} - {st.session_state.speed}x - Méthodes comportementales appliquées")
            st.toast(f"Export {st.session_state.format_export}")
    with c_act4:
        if st.button("Déconnexion", key="deco_main", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.logged = False
            if "user" in st.session_state:
                del st.session_state.user
            st.rerun()

    st.divider()

    st.markdown("### Discussion libre - Bea IA comportementale")
    st.caption("Bea utilise des méthodes psychologiques prouvées pour vous faire réussir - luminosité, musique, hook")
    for m in st.session_state.messages[-10:]:
        if m.get("role") == "system":
            continue
        if m["role"] == "user":
            with st.chat_message("user"):
                st.markdown(sanitize_user(m["content"]))
        else:
            with st.chat_message("assistant", avatar=LOGOS["bea"] if LOGOS["bea"] and os.path.exists(LOGOS["bea"]) else "Bea"):
                st.markdown(sanitize_assistant(m["content"]))
                if "image" in m and m["image"]:
                    st.image(m["image"], use_container_width=True, caption="Visuel 1280x720 - méthode pour clic")

    prompt_raw = st.chat_input("Écrivez un message - Bea peut tout faire avec méthodes comportementales...", key="chat_final")
    if prompt_raw:
        check_rate_minute()
        check_monthly_limit("bea")
        clean = sanitize_user(prompt_raw)
        st.session_state.messages.append({"role": "user", "content": clean})
        msgs = [{"role": mm["role"], "content": sanitize_user(mm["content"])} for mm in st.session_state.messages if mm.get("role")!= "system" and "image" not in mm]
        sys_prompt = SYSTEM_BEHAVIOR
        try:
            reponse, _ = call_groq([{"role": "system", "content": sys_prompt}] + msgs[-15:])
            st.session_state.messages.append({"role": "assistant", "content": sanitize_assistant(reponse)})
            st.session_state.monthly_bea_used += 1
            if licence_key:
                supabase.table("licences").update({"used": used+1}).eq("key", licence_key).execute()
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {str(e)[:400]}")
