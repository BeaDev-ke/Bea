import streamlit as st
import os
import re
import time
from groq import Groq
from supabase import create_client
from collections import deque
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Bea", page_icon="logo_bea.png", layout="wide", initial_sidebar_state="expanded")

STRIPE_BEA = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"
STRIPE_PRO = "https://buy.stripe.com/test_cNieVea1P0c62B08523wQ00"
STRIPE_ULTRA = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"

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
    st.error(f"Erreur : {e}")
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
            c = client.chat.completions.create(model=mid, messages=messages, temperature=0.7, max_tokens=2500)
            return c.choices[0].message.content, mid
        except Exception as e:
            last = e
            continue
    raise last

for k, v in {"theme": "dark", "lang": "FR", "messages": [], "code_messages": [], "rate_limit": deque(), "blocked_until": 0, "selected_format": "bea", "logged": False, "history": ["Bienvenue sur Bea"], "projets_codes": [], "show_persona": False, "vitrine_section": "accueil", "expanded_format": None, "code_content": "# Bea - Création de code gratuite\n# Écris ton code ici\n\ndef bea_project():\n print('Bea - BehaviorLab AI')\n\nbea_project()", "code_language": "python", "script_text": "", "format_export": "9:16 Vertical", "style_sub": "Viral pop", "speed": 1.0, "filter": "Aucun", "current_tool": "", "action_message": "", "uploaded_video": None}.items():
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

def check_rate():
    now = time.time()
    if now < st.session_state.blocked_until:
        st.error(f"Patiente {int(st.session_state.blocked_until - now)}s")
        st.stop()
    dq = st.session_state.rate_limit
    while dq and now - dq[0] > 60:
        dq.popleft()
    if len(dq) >= 25:
        st.session_state.blocked_until = now + 60
        st.error("Trop de requêtes")
        st.stop()
    dq.append(now)

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
    draw.text((50, 180), texte[:120], font=fs, fill="#d1c5ff")
    return img

SYSTEM_BEA = "Tu es Bea, créée par BehaviorLab AI."
SYSTEM_PRO = "Tu es Bea Pro, créée par BehaviorLab AI. Bea + Studio de montage vidéo professionnel complet."
SYSTEM_ULTRA = "Tu es Bea Ultra, créée par BehaviorLab AI. Tout Bea Pro + Création d'application complète en un prompt."
SYSTEM_CODE = "Tu es l'IA code de Bea, BehaviorLab AI."

licence_key = sanitize_key(st.query_params.get("key", ""))
GRAD = "linear-gradient(135deg, #1d4ed8 0%, #7c3aed 60%, #c026d3 85%, #db2777 100%)"
BORDER = "#7c3aed"
BG = "#0f0a1e"
CARD = "#1a1535"
TEXT = "#f5f3ff"

st.markdown(f"""
<style>
.stApp{{background:{BG}!important;}}
[data-testid="stSidebar"]{{background:#0d0d14!important; border-right:3px solid {BORDER}!important;}}
[data-testid="stSidebar"] *{{color:#e2d6ff!important;}}
header[data-testid="stHeader"]{{background:{BG}!important;}}
.block-container{{max-width:1150px!important; padding-top:0.4rem!important;}}
#MainMenu,footer{{visibility:hidden;}}
div[data-testid="stButton"]>button{{background:#15112a!important; color:#e8e0ff!important; border:2px solid {BORDER}!important; border-radius:12px!important; font-weight:600!important; min-height:42px!important;}}
div[data-testid="stButton"]>button:hover{{background:#231a4a!important; border-color:#a855f7!important;}}
.tool-btn button{{background:#15112a!important; color:#e8e0ff!important; border:2px solid {BORDER}!important; border-radius:14px!important; font-weight:700!important; min-height:76px!important;}}
div[data-testid="stLinkButton"]>a{{background:{GRAD}!important; color:white!important; border-radius:12px!important; font-weight:700!important; border:2px solid {BORDER}!important; padding:12px!important;}}
div[data-testid="stChatMessage"]{{background:{CARD}!important; border:2px solid {BORDER}!important; border-radius:16px!important;}}
input, textarea{{background:#1a1535!important; color:{TEXT}!important; border:2px solid {BORDER}!important;}}
.logo-top{{display:flex; justify-content:center; margin-top:8px;}}
.claude-title{{font-size:34px; font-weight:800; color:{TEXT}; text-align:center; margin:6px 0 2px 0;}}
.claude-sub{{font-size:12px; color:#d8ccff!important; text-align:center; font-weight:700; letter-spacing:0.8px; margin-bottom:14px;}}
.desc-main{{font-size:14px; color:#c4b5fd; text-align:center; max-width:720px; margin:10px auto 28px auto; line-height:1.7;}}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div style="display:flex; flex-direction:column; align-items:center;">', unsafe_allow_html=True)
    logo_path = LOGOS.get("bea")
    if logo_path and os.path.exists(logo_path):
        st.image(logo_path, width=62)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; font-size:18px; font-weight:800; color:#f5f3ff; margin-top:6px;">Bea</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; font-size:11px; color:#d8ccff!important; font-weight:700; letter-spacing:0.8px; margin-bottom:12px;">BehaviorLab AI</div>', unsafe_allow_html=True)
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
        st.caption("Bienvenue sur Bea")
    else:
        if st.button("✨ Nouvelle discussion", key="new_side_pay", use_container_width=True):
            st.session_state.messages = []
            st.session_state.code_messages = []
            st.session_state.history.append(f"Chat {len(st.session_state.history)+1}")
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
        st.markdown('<div style="font-size:10px; color:#8a7ab8; text-transform:uppercase; margin:14px 0 6px 0; font-weight:700;">Historique</div>', unsafe_allow_html=True)
        for h in st.session_state.history[-8:][::-1]:
            if st.button(f"• {h[:20]}", key=f"hist_{h}_{len(h)}", use_container_width=True):
                st.rerun()
        for idx, code_item in enumerate(st.session_state.projets_codes[-6:][::-1]):
            if st.button(f"💾 {code_item['name'][:18]}", key=f"code_proj_{idx}", use_container_width=True):
                st.session_state.code_content = code_item["content"]
                st.session_state.vitrine_section = "code"
                st.rerun()
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
    col_editor, col_chat = st.columns([1.25, 0.75], gap="medium")
    with col_editor:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📄 Nouveau fichier", key="ed_new", use_container_width=True):
                st.session_state.code_content = "# Nouveau fichier Bea\n"
                st.rerun()
        with c2:
            if st.button("💾 Sauver dans Projets", key="ed_save", use_container_width=True):
                name = f"Code_{len(st.session_state.projets_codes)+1}.py"
                st.session_state.projets_codes.append({"name": name, "content": st.session_state.code_content, "lang": st.session_state.code_language})
                st.toast(f"{name} sauvé")
                st.rerun()
        with c3:
            if st.button("▶️ Exécuter", key="ed_run", use_container_width=True):
                st.code(f"> python main.py\nBea - BehaviorLab AI ready", language="bash")
        lang = st.selectbox("Langage", ["python", "javascript", "typescript", "html", "css", "json"], index=0, key="ed_lang")
        st.session_state.code_language = lang
        code_input = st.text_area("Éditeur", value=st.session_state.code_content, height=460, key="code_editor_main", label_visibility="collapsed")
        if code_input!= st.session_state.code_content:
            st.session_state.code_content = code_input
    with col_chat:
        st.markdown(f"""
        <div style="background:#15112a; border:2px solid {BORDER}; border-radius:12px; padding:14px; text-align:center; margin-bottom:10px;">
            <div style="font-size:22px;">💬✨</div>
            <div style="color:#f5f3ff; font-weight:700; margin:6px 0;">Ask about your code</div>
            <div style="color:#8a7ab8; font-size:11px;">Demande à l'IA des infos sur ton code</div>
        </div>
        """, unsafe_allow_html=True)
        for m in st.session_state.code_messages[-6:]:
            if m["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(sanitize_user(m["content"]))
            else:
                with st.chat_message("assistant", avatar=LOGOS["bea"] if LOGOS["bea"] and os.path.exists(LOGOS["bea"]) else "Bea"):
                    st.markdown(sanitize_assistant(m["content"]))
        q = st.chat_input("Ask about your code...", key="code_chat")
        if q:
            check_rate()
            st.session_state.code_messages.append({"role": "user", "content": sanitize_user(q)})
            ctx = st.session_state.code_content[:2500]
            msgs = [{"role": "system", "content": SYSTEM_CODE + f"\nCode:\n{ctx}"}] + [{"role": mm["role"], "content": sanitize_user(mm["content"])} for mm in st.session_state.code_messages[-10:]]
            try:
                rep, _ = call_groq(msgs)
                st.session_state.code_messages.append({"role": "assistant", "content": sanitize_assistant(rep)})
                st.rerun()
            except Exception as e:
                st.error(str(e)[:400])
        if st.button("Expliquer mon code", key="exp_code", use_container_width=True):
            st.session_state.code_messages.append({"role": "user", "content": "Explique mon code"})
            msgs = [{"role": "system", "content": SYSTEM_CODE + f"\nCode:\n{st.session_state.code_content[:2500]}"}, {"role": "user", "content": "Explique mon code"}]
            try:
                rep, _ = call_groq(msgs)
                st.session_state.code_messages.append({"role": "assistant", "content": sanitize_assistant(rep)})
                st.rerun()
            except Exception as e:
                st.error(str(e))
        if st.button("Corriger / Améliorer", key="fix_code", use_container_width=True):
            st.session_state.code_messages.append({"role": "user", "content": "Corrige et améliore mon code"})
            msgs = [{"role": "system", "content": SYSTEM_CODE + f"\nCode:\n{st.session_state.code_content[:2500]}"}, {"role": "user", "content": "Corrige et améliore"}]
            try:
                rep, _ = call_groq(msgs)
                st.session_state.code_messages.append({"role": "assistant", "content": sanitize_assistant(rep)})
                st.rerun()
            except Exception as e:
                st.error(str(e))

if not st.session_state.logged and not licence_key:
    st.markdown('<div class="logo-top">', unsafe_allow_html=True)
    logo_path = LOGOS.get("bea")
    if logo_path and os.path.exists(logo_path):
        st.image(logo_path, width=88)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="claude-title">Bea</div>', unsafe_allow_html=True)
    st.markdown('<div class="claude-sub">BehaviorLab AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="desc-main">Bea transforme une intention en projet concret. Elle structure votre démarche, produit des vidéos prêtes à diffuser avec sous-titres stylisés et crée votre application en un prompt.</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        with st.container(border=True):
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

    st.markdown("<div style='height:36px;'></div>", unsafe_allow_html=True)
    st.markdown("## Découvrir les formats")

    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        with st.container(border=True):
            st.markdown("#### Bea : 14,90 € par mois")
            if st.button("Voir description", key="btn_bea", use_container_width=True):
                st.session_state.expanded_format = "bea" if st.session_state.expanded_format!= "bea" else None
                st.rerun()
            if st.session_state.expanded_format == "bea":
                st.markdown("Bea part d'une idée encore floue et la transforme en projet concret. Elle construit un plan, met en place des systèmes et des outils qui fonctionnent réellement. Son point fort : repérer le blocage précis qui ralentit votre avancement, puis proposer une solution mesurable, applicable immédiatement.")
                st.markdown("**Ce que vous obtenez :**\n- L'identification du blocage exact qui freine votre projet\n- Des scripts prêts à l'emploi, à la fois doux et directs, pour convaincre\n- Une estimation chiffrée du temps et de l'argent gagnés\n- Un exemple concret, avec prénom, âge et ville, qui sert de preuve sociale")
                st.markdown("Avec Bea, vous passez de l'idée au projet structuré en un seul prompt. Elle fournit un système de relance, une méthode pour doubler votre taux de closing, et un script de vente.")
            st.link_button("Choisir Bea", STRIPE_BEA, use_container_width=True)

    with c2:
        with st.container(border=True):
            st.markdown("#### Bea Pro : 21 € par mois")
            st.caption("La formule la plus choisie")
            if st.button("Voir description", key="btn_pro", use_container_width=True):
                st.session_state.expanded_format = "pro" if st.session_state.expanded_format!= "pro" else None
                st.rerun()
            if st.session_state.expanded_format == "pro":
                st.markdown("Bea Pro ajoute un studio de montage vidéo complet. Toutes les fonctions de montage sont réunies dans un seul outil, ce qui vous permet de produire des vidéos prêtes à diffuser, plus susceptibles de retenir l'attention et de convertir. Vous n'avez plus besoin de jongler entre plusieurs logiciels.")
                st.markdown("**Ce que vous obtenez :**\n- Toutes les fonctions de Bea\n- La génération automatique de sous-titres stylisés, synchronisés avec la parole\n- La suppression de l'arrière-plan, la découpe des silences et le nettoyage audio en un clic\n- Une bibliothèque intégrée de modèles, d'effets, de transitions et d'animations\n- L'export direct dans un format adapté à chaque plateforme (9:16, 16:9, 1:1)\n- Des visuels en 1280x720 qui augmentent le taux de clic et la rétention")
                st.markdown("**Fonctions supplémentaires de Bea Pro :** couper et découper, sous-titres automatiques, suppression du fond, découpe des silences, nettoyage audio, bibliothèque de modèles, effets vidéo, transitions animées, animations de texte, filtres couleur, vitesse et ralenti, stickers et emojis, bibliothèque musicale, recadrage et zoom, stabilisation vidéo, voix off par IA, miniatures en 1280x720, création d'application en un prompt.")
            st.link_button("Choisir Bea Pro", STRIPE_PRO, use_container_width=True)

    with c3:
        with st.container(border=True):
            st.markdown("#### Bea Ultra : 29,90 € par mois")
            if st.button("Voir description", key="btn_ultra", use_container_width=True):
                st.session_state.expanded_format = "ultra" if st.session_state.expanded_format!= "ultra" else None
                st.rerun()
            if st.session_state.expanded_format == "ultra":
                st.markdown("Bea Ultra reprend Bea Pro et y ajoute la création d'applications complètes à partir d'un seul prompt. Vous partez d'une idée encore vague et vous obtenez une application prête à publier, sans écrire une seule ligne de code complexe. Bea génère l'ensemble.")
                st.markdown("**Ce que vous obtenez :**\n- Toutes les fonctions de Bea Pro\n- Un prompt équivaut à une application complète et fonctionnelle\n- Les écrans, la base de données, le paiement et l'authentification sont intégrés automatiquement\n- L'icône 512x512, les captures d'écran et la description sont générées pour le store\n- Un fichier exporté prêt à publier (APK ou Web)")
                st.markdown("**Fonctions supplémentaires de Bea Ultra :** génération d'applications complètes, éditeur de code avec IA intégrée à droite, timeline vidéo professionnelle, export vidéo, discussions illimitées et historique complet.")
            st.link_button("Choisir Bea Ultra", STRIPE_ULTRA, use_container_width=True)
    st.stop()

if licence_key and not st.session_state.logged:
    with st.container(border=True):
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
    st.stop()

if licence_key:
    try:
        res = supabase.table("licences").select("*").eq("key", licence_key).eq("user_id", st.session_state.user.id).execute()
        if not res.data:
            st.error("Licence invalide")
            st.stop()
        lic = res.data[0]
        plan, used = lic["plan"], lic["used"]
    except Exception as e:
        st.error(f"Erreur licence : {e}")
        st.stop()
else:
    plan, used = "PRO", 0

if st.session_state.vitrine_section == "perso" or st.session_state.show_persona:
    with st.container(border=True):
        st.markdown("### 👤 Personnaliser Bea")
        nom = st.text_input("Comment Bea doit vous appeler?", key="perso_nom_pay")
        if st.button("Enregistrer", key="save_perso_pay"):
            st.toast(f"Bea vous appellera {nom}")
            st.session_state.show_persona = False
            st.session_state.vitrine_section = "code"
            st.rerun()
elif st.session_state.vitrine_section == "projets":
    with st.container(border=True):
        st.markdown("### 📁 Projets - Derniers codes")
        if not st.session_state.projets_codes:
            st.info("Aucun code sauvé")
        else:
            for item in st.session_state.projets_codes[::-1]:
                with st.container(border=True):
                    st.markdown(f"**{item['name']}**")
                    st.code(item["content"][:600], language=item["lang"])
                    if st.button(f"Ouvrir {item['name']}", key=f"open_{item['name']}"):
                        st.session_state.code_content = item["content"]
                        st.session_state.vitrine_section = "code"
                        st.rerun()
        if st.button("Retour Code", key="ret_proj_pay"):
            st.session_state.vitrine_section = "code"
            st.rerun()
    st.stop()
else:
    render_editor_complet()
    st.divider()
    if len(st.session_state.messages) == 0:
        st.session_state.messages.append({"role": "assistant", "content": "Bonjour, je suis Bea. L'IA peut faire tout ce qui est indiqué : montage, code, app."})

    st.markdown("### Montage vidéo professionnel - Bea peut tout faire")
    col_a, col_b = st.columns([0.35, 0.65])
    with col_a:
        up = st.file_uploader("Vidéo brute", type=["mp4", "mov", "webm", "avi"], label_visibility="collapsed", key="up_video")
        if up:
            st.video(up)
    with col_b:
        txt = st.text_area("Script", height=100, placeholder="Collez votre script...", key="script_area")
        if txt:
            st.session_state.script_text = txt

    r1 = st.columns(6)
    for i, (label, key) in enumerate([("Couper\nDécouper", "t_cut"), ("Sous-titres\nAuto", "t_sub"), ("Supprimer\nFond", "t_bg"), ("Découpe\nSilences", "t_sil"), ("Nettoyage\nAudio", "t_audio"), ("Modèles", "t_model")]):
        with r1[i]:
            st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
            if st.button(label, key=key, use_container_width=True):
                st.session_state.current_tool = label
                if key == "t_thumb":
                    img = generer_visuel(st.session_state.script_text or "Bea", st.session_state.style_sub)
                    st.image(img, use_container_width=True)
                st.toast(label)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    r2 = st.columns(6)
    for i, (label, key) in enumerate([("Effets\nVidéo", "t_eff"), ("Transitions", "t_trans"), ("Animations", "t_anim"), ("Filtres", "t_filt"), ("Vitesse", "t_speed"), ("Stickers", "t_stick")]):
        with r2[i]:
            st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
            if st.button(label, key=key, use_container_width=True):
                st.session_state.current_tool = label
                st.toast(label)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    r3 = st.columns(6)
    for i, (label, key) in enumerate([("Musique", "t_music"), ("Recadrer", "t_crop"), ("Stabiliser", "t_stab"), ("Voix Off", "t_voice"), ("Miniature\n1280x720", "t_thumb"), ("Créer App", "t_app")]):
        with r3[i]:
            st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
            if st.button(label, key=key, use_container_width=True):
                if key == "t_thumb":
                    img = generer_visuel(st.session_state.script_text or "Bea", st.session_state.style_sub)
                    st.image(img, use_container_width=True)
                st.toast(label)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    for m in st.session_state.messages[-8:]:
        if m.get("role") == "system":
            continue
        if m["role"] == "user":
            with st.chat_message("user"):
                st.markdown(sanitize_user(m["content"]))
        else:
            with st.chat_message("assistant", avatar=LOGOS["bea"] if LOGOS["bea"] and os.path.exists(LOGOS["bea"]) else "Bea"):
                st.markdown(sanitize_assistant(m["content"]))
                if "image" in m and m["image"]:
                    st.image(m["image"], use_container_width=True)

    prompt_raw = st.chat_input("Écrivez un message - Bea peut tout faire...", key="chat_final")
    if prompt_raw:
        check_rate()
        st.session_state.messages.append({"role": "user", "content": sanitize_user(prompt_raw)})
        msgs = [{"role": mm["role"], "content": sanitize_user(mm["content"])} for mm in st.session_state.messages if mm.get("role")!= "system" and "image" not in mm]
        sys_prompt = SYSTEM_ULTRA if st.session_state.selected_format == "ultra" else SYSTEM_PRO if st.session_state.selected_format == "pro" else SYSTEM_BEA
        try:
            reponse, _ = call_groq([{"role": "system", "content": sys_prompt}] + msgs[-15:])
            st.session_state.messages.append({"role": "assistant", "content": sanitize_assistant(reponse)})
            if licence_key:
                supabase.table("licences").update({"used": used+1}).eq("key", licence_key).execute()
            st.rerun()
        except Exception as e:
            st.error(str(e)[:400])
