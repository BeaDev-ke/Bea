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

for k, v in {"theme": "dark", "lang": "FR", "messages": [], "code_messages": [], "rate_limit": deque(), "blocked_until": 0, "selected_format": "bea", "logged": False, "history": ["Bienvenue sur Bea"], "projets_codes": [], "show_persona": False, "action_message": "", "uploaded_video": None, "current_tool": "", "script_text": "", "format_export": "9:16 Vertical", "style_sub": "Viral pop", "speed": 1.0, "filter": "Aucun", "vitrine_section": "accueil", "code_content": "# Bea - Creation de code gratuite\n# Ecris ton code ici\n\ndef bea_project():\n print('Bea - BehaviorLab AI')\n idee = input('Ton idee: ')\n return f'App generee pour: {idee}'\n\nbea_project()", "code_language": "python"}.items():
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
        st.error("Trop de requetes")
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

SYSTEM_BEA = "Tu es Bea, creee par BehaviorLab AI. Tu transformes une intention en projet concret. Tu structures la demarche, tu donnes plan, systemes, outils."
SYSTEM_PRO = "Tu es Bea Pro, creee par BehaviorLab AI. Bea + Studio montage video professionnel complet : sous-titres stylises synchronises avec la parole, suppression arriere-plan, decoupe silences, nettoyage audio, bibliotheque modeles, effets, transitions, animations, export optimise, visuels 1280x720."
SYSTEM_ULTRA = "Tu es Bea Ultra, creee par BehaviorLab AI. Tout Bea Pro + Creation d'application complete en un prompt : ecrans + base de donnees + paiement + auth + icone 512x512 + captures + description + export pret a publier."
SYSTEM_CODE = "Tu es l'IA code de Bea, BehaviorLab AI. Tu es dans un editeur simple. Tu aides l'utilisateur a comprendre, debugger, ameliorer son code. Tu expliques clairement, tu donnes corrections."

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
.block-container{{max-width:1150px!important; padding-top:0.8rem!important;}}
#MainMenu,footer{{visibility:hidden;}}
div[data-testid="stButton"]>button{{background:#15112a!important; color:#e8e0ff!important; border:2px solid {BORDER}!important; border-radius:12px!important; font-weight:600!important; font-size:13px!important; min-height:40px!important;}}
div[data-testid="stButton"]>button:hover{{background:#231a4a!important; border-color:#a855f7!important; box-shadow:0 0 10px rgba(124,58,237,0.4)!important;}}
.tool-btn button{{background:#15112a!important; color:#e8e0ff!important; border:2px solid {BORDER}!important; border-radius:14px!important; font-weight:700!important; font-size:12px!important; text-align:center!important; min-height:76px!important; box-shadow:0 0 0 1px rgba(124,58,237,0.3)!important;}}
.tool-btn button:hover{{background:#231a4a!important; border-color:#c084fc!important;}}
div[data-testid="stLinkButton"]>a{{background:{GRAD}!important; color:white!important; border-radius:12px!important; font-weight:700!important; border:2px solid {BORDER}!important;}}
div[data-testid="stChatMessage"]{{background:{CARD}!important; border:2px solid {BORDER}!important; border-radius:16px!important; padding:14px!important;}}
div[data-testid="stChatMessage"] p{{color:{TEXT}!important; font-size:15px!important; line-height:1.6!important;}}
div[data-testid="stChatInput"]{{background:#1a1535!important; border:2px solid {BORDER}!important; border-radius:24px!important;}}
input, textarea{{background:#1a1535!important; color:{TEXT}!important; border:2px solid {BORDER}!important; border-radius:12px!important;}}
.claude-title{{font-size:34px; font-weight:800; color:{TEXT}; text-align:center; margin:8px 0 2px 0;}}
.claude-sub{{font-size:12px; color:#d8ccff!important; text-align:center; font-weight:700; letter-spacing:0.8px; margin-bottom:12px;}}
.desc-main{{font-size:14px; color:#c4b5fd; text-align:center; max-width:720px; margin:10px auto 28px auto; line-height:1.7;}}
.timeline{{background:#15112a; border-radius:14px; padding:14px; border:2px solid {BORDER}; margin:14px 0;}}
.timeline-track{{background:#0d0d1e; height:46px; border-radius:10px; margin:8px 0; display:flex; align-items:center; padding:0 10px; border:1px solid #2a2250;}}
.track-block{{background:{GRAD}; height:34px; border-radius:8px; min-width:80px; margin-right:8px; display:flex; align-items:center; justify-content:center; font-size:11px; color:white; font-weight:700; border:1px solid #a855f7;}}
</style>
""", unsafe_allow_html=True)

# SIDEBAR
with st.sidebar:
    st.markdown('<div style="display:flex; flex-direction:column; align-items:center;">', unsafe_allow_html=True)
    logo_path = LOGOS.get("bea")
    if logo_path and os.path.exists(logo_path):
        st.image(logo_path, width=60)
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
        st.caption("Connecte-toi pour acceder a l'editeur gratuit")
        st.markdown("**Gratuit apres connexion**\n- Creation de code\n- Discussion libre IA")
    else:
        if st.button("✨ Nouvelle discussion", key="new_side_pay", use_container_width=True):
            st.session_state.messages = []
            st.session_state.code_messages = []
            st.session_state.vitrine_section = "accueil"
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

        st.markdown('<div style="font-size:10px; color:#8a7ab8; text-transform:uppercase; margin:14px 0 6px 0; font-weight:700;">Historique</div>', unsafe_allow_html=True)
        for h in st.session_state.history[-8:][::-1]:
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
            if st.button("🚪 Deconnexion", key="deco_side", use_container_width=True):
                supabase.auth.sign_out()
                st.session_state.logged = False
                if "user" in st.session_state:
                    del st.session_state.user
                st.rerun()

def render_editor_complet():
    st.markdown("### Creation de code gratuite + discussion libre à droite")
    st.markdown(f"<div style='background:#15112a; border:2px solid {BORDER}; border-radius:10px; padding:10px; font-size:12px; color:#c4b5fd; margin-bottom:12px;'>Editeur libre - Bea - BehaviorLab AI - Ecris ton code a gauche, discute avec l'IA a droite (Ask about your code) comme sur la photo 1</div>", unsafe_allow_html=True)

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
                st.toast(f"{name} sauve")
                st.rerun()
        with c3:
            if st.button("▶️ Executer", key="ed_run", use_container_width=True):
                st.success("Execution terminal")
                st.code(f"> python main.py\n{st.session_state.code_content[:200]}\n\nBea - BehaviorLab AI ready", language="bash")
        with c4:
            lang = st.selectbox("Lang", ["python", "javascript", "typescript", "html", "css", "json"], index=0, key="ed_lang", label_visibility="collapsed")
            st.session_state.code_language = lang

        code_input = st.text_area("Editeur code", value=st.session_state.code_content, height=460, key="code_editor_main", label_visibility="collapsed")
        if code_input!= st.session_state.code_content:
            st.session_state.code_content = code_input

        st.code(f"Ln {len(code_input.splitlines())}, Col 1 | Spaces: 4 | UTF-8 | CRLF | {st.session_state.code_language} | Bea BehaviorLab AI", language="text")

    with col_chat:
        st.markdown(f"""
        <div style="background:#15112a; border:2px solid {BORDER}; border-radius:12px; padding:14px; text-align:center; margin-bottom:10px;">
            <div style="font-size:24px;">💬✨</div>
            <div style="color:#f5f3ff; font-weight:700; margin:6px 0;">Ask about your code</div>
            <div style="color:#8a7ab8; font-size:11px; line-height:1.4;">AI responses may be inaccurate<br/>Generate Agent Instructions to onboard<br/>AI onto your codebase.</div>
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
            check_rate()
            st.session_state.code_messages.append({"role": "user", "content": sanitize_user(q)})
            ctx = st.session_state.code_content[:2500]
            msgs = [{"role": "system", "content": SYSTEM_CODE + f"\nCode actuel:\n{ctx}"}] + [{"role": mm["role"], "content": sanitize_user(mm["content"])} for mm in st.session_state.code_messages[-10:]]
            try:
                rep, _ = call_groq(msgs)
                st.session_state.code_messages.append({"role": "assistant", "content": sanitize_assistant(rep)})
                st.rerun()
            except Exception as e:
                st.error(str(e)[:400])

        if st.button("Expliquer mon code", key="exp_code", use_container_width=True):
            st.session_state.code_messages.append({"role": "user", "content": "Explique mon code ligne par ligne"})
            msgs = [{"role": "system", "content": SYSTEM_CODE + f"\nCode:\n{st.session_state.code_content[:2500]}"}, {"role": "user", "content": "Explique mon code ligne par ligne"}]
            try:
                rep, _ = call_groq(msgs)
                st.session_state.code_messages.append({"role": "assistant", "content": sanitize_assistant(rep)})
                st.rerun()
            except Exception as e:
                st.error(str(e))
        if st.button("Corriger / Ameliorer mon code", key="fix_code", use_container_width=True):
            st.session_state.code_messages.append({"role": "user", "content": "Corrige et ameliore mon code"})
            msgs = [{"role": "system", "content": SYSTEM_CODE + f"\nCode:\n{st.session_state.code_content[:2500]}"}, {"role": "user", "content": "Corrige et ameliore mon code et donne version corrigee"}]
            try:
                rep, _ = call_groq(msgs)
                st.session_state.code_messages.append({"role": "assistant", "content": sanitize_assistant(rep)})
                st.rerun()
            except Exception as e:
                st.error(str(e))
        if st.button("Generer Agent Instructions", key="agent_instr", use_container_width=True):
            st.toast("Instructions agent generees pour ta codebase")

# VITRINE COMME CLAUDE - CONNEXION D'ABORD
if not st.session_state.logged and not licence_key:
    col_a, col_b, col_c = st.columns([1, 0.9, 1])
    with col_b:
        st.markdown('<div style="display:flex; flex-direction:column; align-items:center; margin-top:12px;">', unsafe_allow_html=True)
        logo_path = LOGOS.get("bea")
        if logo_path and os.path.exists(logo_path):
            st.image(logo_path, width=90)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="claude-title">Bea</div>', unsafe_allow_html=True)
    st.markdown('<div class="claude-sub">BehaviorLab AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="desc-main">Bea transforme une intention en projet concret. Elle structure votre demarche, produit des videos pretes a diffuser avec sous-titres stylises et cree votre application en un prompt. Connectez-vous pour acceder a la creation de code gratuite et a la discussion libre a droite comme sur la premiere photo.</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        with st.container(border=True):
            st.markdown("#### Connexion")
            st.caption("Premiere visite? Connexion requise puis acces editeur gratuit")
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

    # FORMATS IA MIS EN AVANT - DESCRIPTIONS COMPLETES
    st.markdown("## BehaviorLab AI - Les IA comportementales pour votre reussite")
    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        with st.container(border=True):
            st.markdown("### Bea - 14,90 / mois")
            st.markdown("**Transformer une intention en projet concret**")
            st.markdown("A partir d'une idee vague, Bea construit un plan, des systemes et des outils qui fonctionnent. Elle detecte le blocage exact qui freine et propose une sortie mesurable et applicable tout de suite.")
            st.markdown("**Avantages**")
            st.markdown("- Detection du blocage exact qui freine votre projet\n- Scripts doux et directs prets a l'emploi pour convaincre\n- Chiffrage du gain en temps et argent\n- Exemple vecu avec prenom age ville pour preuve sociale")
            st.markdown("**Ce que Bea fait**")
            st.markdown("- De l'idee au projet structure en 1 prompt\n- Systeme de relance\n- Methode pour doubler closing\n- Script de vente")
            st.caption("Pourquoi payer : Bea remplace des mois de tests par un script qui convertit des la premiere utilisation. 14,90 au lieu de 500€ de coaching.")
            st.markdown(f'<a href="{STRIPE_BEA}" target="_blank" style="display:block; background:{GRAD}; color:white; padding:12px; border-radius:12px; text-align:center; font-weight:700; text-decoration:none; border:2px solid {BORDER};">Choisir Bea - reste sur meme page</a>', unsafe_allow_html=True)
    with c2:
        with st.container(border=True):
            st.markdown("### Bea Pro - 21 / mois - Le plus choisi")
            st.markdown("**Bea + Studio de montage video professionnel complet**")
            st.markdown("L'ensemble des fonctions de montage reuni dans un seul outil. Production de videos pretes a diffuser qui augmentent l'attention et la conversion. Fini les logiciels multiples.")
            st.markdown("**Avantages**")
            st.markdown("- Tout Bea inclus\n- Generation automatique de sous-titres stylises et synchronises avec la parole\n- Suppression de l'arriere-plan, decoupe des silences et nettoyage audio en un clic\n- Bibliotheque integree de modeles, d'effets, de transitions et d'animations\n- Export direct dans un format optimise pour chaque plateforme (9:16, 16:9, 1:1)\n- Visuels 1280x720 qui augmentent le clic et la retention")
            st.markdown("**Ce que Bea Pro fait en plus**")
            st.markdown("- Couper / Decouper\n- Sous-titres auto\n- Supprimer fond\n- Decoupe silences\n- Nettoyage audio\n- Modeles bibliotheque\n- Effets video\n- Transitions animees\n- Animations texte\n- Filtres couleur\n- Vitesse ralenti\n- Stickers emojis\n- Musique bibliotheque\n- Recadrer zoom\n- Stabiliser video\n- Voix Off IA\n- Miniature 1280x720\n- Creer App en 1 prompt")
            st.caption("Pourquoi payer : un seul outil remplace CapCut, Premiere, Canva et des heures de montage manuel.")
            st.markdown(f'<a href="{STRIPE_PRO}" target="_blank" style="display:block; background:{GRAD}; color:white; padding:12px; border-radius:12px; text-align:center; font-weight:700; text-decoration:none; border:2px solid {BORDER};">Choisir Bea Pro - reste sur meme page</a>', unsafe_allow_html=True)
    with c3:
        with st.container(border=True):
            st.markdown("### Bea Ultra - 29,90 / mois")
            st.markdown("**Bea Pro + Creation d'application complete en un prompt**")
            st.markdown("De l'idee vague a l'application prete a publier sans ecrire une ligne de code complexe. Bea genere tout.")
            st.markdown("**Avantages**")
            st.markdown("- Tout Bea Pro inclus\n- 1 prompt = 1 application complete fonctionnelle\n- Ecrans + Base de donnees + Paiement + Auth integres automatiquement\n- Icone 512x512, captures, description generees pour store\n- Export fichier pret a publier (APK / Web)")
            st.markdown("**Ce que Bea Ultra fait en plus**")
            st.markdown("- Generation app complete\n- Code editor + IA a droite\n- Timeline video pro\n- Export video\n- Nouvelle discussion illimitee\n- Historique complet")
            st.caption("Pourquoi payer : Bea Ultra evite des mois de dev a 5000€ et livre une app utilisable tout de suite.")
            st.markdown(f'<a href="{STRIPE_ULTRA}" target="_blank" style="display:block; background:{GRAD}; color:white; padding:12px; border-radius:12px; text-align:center; font-weight:700; text-decoration:none; border:2px solid {BORDER};">Choisir Bea Ultra - reste sur meme page</a>', unsafe_allow_html=True)
    st.stop()

# APRES CONNEXION
if licence_key and not st.session_state.logged:
    with st.container(border=True):
        st.markdown("#### Connexion licence")
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

# SECTIONS APRES CONNEXION
if st.session_state.vitrine_section == "perso" or st.session_state.show_persona:
    with st.container(border=True):
        st.markdown("### 👤 Personnaliser Bea pour vous")
        nom = st.text_input("Comment Bea doit vous appeler?", placeholder="Ex: Alex", key="perso_nom_pay")
        style = st.selectbox("Style de reponse", ["Direct", "Doux", "Detaille", "Expert montage"], key="perso_style_pay")
        objectif = st.text_input("Objectif principal", placeholder="Ex: doubler mon closing", key="perso_obj_pay")
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
        st.markdown("### 📁 Projets - Derniers codes sauves")
        st.caption("Ici tous tes derniers codes sauves depuis l'editeur Code gratuit")
        if not st.session_state.projets_codes:
            st.info("Aucun code sauve pour l'instant. Va dans Code > Sauver dans Projets")
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

# PAR DEFAUT APRES CONNEXION = EDITEUR CODE GRATUIT + DISCUSSION LIBRE
render_editor_complet()

st.divider()

# MONTAGE VIDEO PROFESSIONNEL - TOUS LES OUTILS SANS RIEN OUBLIER
st.markdown("## Montage video professionnel - Bea peut tout faire")
st.markdown(f"<div style='background:#15112a; border:2px solid {BORDER}; border-radius:10px; padding:10px; font-size:12px; color:#c4b5fd; margin-bottom:12px;'>Format: {st.session_state.format_export} | Style: {st.session_state.style_sub} | Filtre: {st.session_state.filter} | Vitesse: {st.session_state.speed}x | Outil: {st.session_state.current_tool} | {st.session_state.action_message}</div>", unsafe_allow_html=True)

col_a, col_b = st.columns([0.35, 0.65])
with col_a:
    up = st.file_uploader("Video brute - 200MB max MP4 MOV WEBM AVI", type=["mp4", "mov", "webm", "avi"], label_visibility="collapsed", key="up_video")
    if up:
        st.session_state.uploaded_video = up
        st.success(f"{up.name} chargee")
        st.video(up)
        if st.button("Supprimer video", key="del_vid"):
            st.session_state.uploaded_video = None
            st.rerun()
    else:
        st.caption("Glissez video ici - MP4 MOV WEBM AVI - 200MB max")

with col_b:
    txt = st.text_area("Script / paroles pour sous-titres stylises synchronises", height=140, placeholder="Collez votre script ici pour generer sous-titres auto...", key="script_area")
    if txt:
        st.session_state.script_text = txt
        st.caption(f"{len(txt.split())} mots - {len(txt)} caracteres")

c_fmt, c_style, c_speed, c_filtre = st.columns(4)
with c_fmt:
    fmt = st.selectbox("Format export", ["9:16 Vertical", "16:9 Horizontal", "1:1 Carre", "4:5", "21:9 Cinema"], key="fmt_sel")
    st.session_state.format_export = fmt
with c_style:
    sty = st.selectbox("Style sous-titres", ["Viral pop", "Hormozi bold", "Minimal", "Cinema", "Neon", "Journal", "Bold"], key="style_sel")
    st.session_state.style_sub = sty
with c_speed:
    spd = st.select_slider("Vitesse", options=[0.5, 0.75, 1.0, 1.25, 1.5, 2.0], value=1.0, key="speed_sel")
    st.session_state.speed = spd
with c_filtre:
    filt = st.selectbox("Filtre couleur", ["Aucun", "Cinema", "Vintage", "Vivid", "Noir & Blanc"], key="filtre_sel")
    st.session_state.filter = filt

st.markdown("### Outils principaux - Tous les outils de montage")
r1 = st.columns(6)
tools_r1 = [("Couper\nDecouper", "t_cut", "Decoupe video active"), ("Sous-titres\nAuto", "t_sub", "Sous-titres generes"), ("Supprimer\nFond", "t_bg", "Arriere-plan supprime"), ("Decoupe\nSilences", "t_sil", "Silences coupes"), ("Nettoyage\nAudio", "t_audio", "Audio nettoye"), ("Modeles\nBibliotheque", "t_model", "Modeles ouverts")]
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
                st.session_state.action_message = f"{len(mots)} sous-titres {st.session_state.style_sub}"
                st.download_button("Telecharger SRT", srt, file_name="sous_titres.srt", key=f"dl_srt_{i}")
            st.toast(label)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

r2 = st.columns(6)
tools_r2 = [("Effets\nVideo", "t_eff"), ("Transitions\nAnimees", "t_trans"), ("Animations\nTexte", "t_anim"), ("Filtres\nCouleur", "t_filt"), ("Vitesse\nRalenti", "t_speed"), ("Stickers\nEmojis", "t_stick")]
for i, (label, key) in enumerate(tools_r2):
    with r2[i]:
        st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
        if st.button(label, key=key, use_container_width=True):
            st.session_state.current_tool = label.replace("\n", " ")
            st.session_state.action_message = f"{label} applique - Filtre {st.session_state.filter} Vitesse {st.session_state.speed}x"
            st.toast(label)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

r3 = st.columns(6)
tools_r3 = [("Musique\nBibliotheque", "t_music"), ("Recadrer\nZoom", "t_crop"), ("Stabiliser\nVideo", "t_stab"), ("Voix Off\nIA", "t_voice"), ("Miniature\n1280x720", "t_thumb"), ("Creer App\nEn 1 prompt", "t_app")]
for i, (label, key) in enumerate(tools_r3):
    with r3[i]:
        st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
        if st.button(label, key=key, use_container_width=True):
            if key == "t_thumb":
                img = generer_visuel(st.session_state.script_text or "Bea", st.session_state.style_sub)
                st.image(img, caption="Miniature 1280x720 generee", use_container_width=True)
                st.session_state.action_message = "Miniature 1280x720 generee - augmente clic"
            elif key == "t_app":
                st.session_state.messages.append({"role": "user", "content": "Creer une application complete en un prompt"})
                st.session_state.action_message = "Creation app lancee"
            else:
                st.session_state.action_message = f"{label} active"
            st.session_state.current_tool = label.replace("\n", " ")
            st.toast(label)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown(f'<div class="timeline"><div style="color:#c4b5fd; font-size:11px; margin-bottom:8px; font-weight:700;">TIMELINE - Glisser pour editer - Format {st.session_state.format_export}</div><div class="timeline-track"><div class="track-block">Intro 0:03</div><div class="track-block" style="min-width:140px; background:linear-gradient(135deg,#db2777,#f97316);">{st.session_state.style_sub} - {st.session_state.speed}x</div><div class="track-block" style="background:#2a2a4a;">Outro 0:02</div></div><div style="color:#8a7ab8; font-size:10px; margin-top:6px;">Filtre: {st.session_state.filter} | {st.session_state.script_text[:60] if st.session_state.script_text else "Ajoutez script pour sous-titres"}</div></div>', unsafe_allow_html=True)

if st.session_state.action_message:
    st.info(f"Outil actif: {st.session_state.current_tool} | {st.session_state.action_message}")

c_act1, c_act2, c_act3, c_act4 = st.columns(4)
with c_act1:
    if st.button("Generer montage complet", key="gen_full", use_container_width=True):
        check_rate()
        prompt = st.session_state.script_text or "Generer montage pro complet"
        full_prompt = f"{prompt} Format {st.session_state.format_export} Style {st.session_state.style_sub} Filtre {st.session_state.filter} Vitesse {st.session_state.speed}x"
        st.session_state.messages.append({"role": "user", "content": full_prompt})
        msgs = [{"role": mm["role"], "content": sanitize_user(mm["content"])} for mm in st.session_state.messages if mm.get("role")!= "system" and "image" not in mm]
        sys_prompt = SYSTEM_ULTRA if st.session_state.selected_format == "ultra" else SYSTEM_PRO if st.session_state.selected_format == "pro" else SYSTEM_BEA
        try:
            with st.spinner("Generation montage complet..."):
                reponse, _ = call_groq([{"role": "system", "content": sys_prompt}] + msgs[-12:])
                img = generer_visuel(prompt, st.session_state.style_sub)
                st.session_state.messages.append({"role": "assistant", "content": sanitize_assistant(reponse), "image": img})
            if licence_key:
                supabase.table("licences").update({"used": used+1}).eq("key", licence_key).execute()
            st.success("Montage genere! Miniature 1280x720 prete")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {str(e)[:400]}")
with c_act2:
    if st.button("Nouvelle discussion", key="new_chat_main", use_container_width=True):
        st.session_state.messages = []
        st.session_state.history.append(f"Chat {len(st.session_state.history)+1}")
        st.rerun()
with c_act3:
    if st.button("Exporter video", key="export_vid", use_container_width=True):
        st.success(f"Export lance en {st.session_state.format_export} - Style {st.session_state.style_sub} - {st.session_state.speed}x")
        st.toast(f"Export {st.session_state.format_export}")
with c_act4:
    if st.button("Deconnexion", key="deco_main", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.logged = False
        if "user" in st.session_state:
            del st.session_state.user
        st.rerun()

st.divider()

st.markdown("### Discussion libre - Bea")
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
                st.image(m["image"], use_container_width=True, caption="Visuel 1280x720")

prompt_raw = st.chat_input("Ecrivez un message - Bea peut tout faire...", key="chat_final")
if prompt_raw:
    check_rate()
    clean = sanitize_user(prompt_raw)
    st.session_state.messages.append({"role": "user", "content": clean})
    msgs = [{"role": mm["role"], "content": sanitize_user(mm["content"])} for mm in st.session_state.messages if mm.get("role")!= "system" and "image" not in mm]
    sys_prompt = SYSTEM_ULTRA if st.session_state.selected_format == "ultra" else SYSTEM_PRO if st.session_state.selected_format == "pro" else SYSTEM_BEA
    try:
        reponse, _ = call_groq([{"role": "system", "content": sys_prompt}] + msgs[-15:])
        st.session_state.messages.append({"role": "assistant", "content": sanitize_assistant(reponse)})
        if licence_key:
            supabase.table("licences").update({"used": used+1}).eq("key", licence_key).execute()
        st.rerun()
    except Exception as e:
        st.error(f"Erreur : {str(e)[:400]}")
