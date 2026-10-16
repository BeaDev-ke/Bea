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

LOGOS = {"bea": find_file(["logo_bea.png", "logo.png", "logo_bea.jpg"]), "main": find_file(["logo.png", "logo_bea.png"])}

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
            c = client.chat.completions.create(model=mid, messages=messages, temperature=0.7, max_tokens=2000)
            return c.choices[0].message.content, mid
        except Exception as e:
            last = e
            continue
    raise last

for k, v in {"theme": "dark", "lang": "FR", "messages": [], "rate_limit": deque(), "blocked_until": 0, "selected_format": "bea", "logged": False, "history": [], "show_persona": False, "action_message": "", "uploaded_video": None, "current_tool": "", "script_text": "", "format_export": "9:16 Vertical", "style_sub": "Viral pop", "speed": 1.0, "filter": "Aucun"}.items():
    if k not in st.session_state:
        st.session_state[k] = v

def toggle_theme():
    st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"

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
    return re.sub(r"<[^>]*>", "", t.strip()[:3000]) if t else ""

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
        ft = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
        fs = ImageFont.truetype("DejaVuSans.ttf", 16)
    except:
        ft = fs = ImageFont.load_default()
    for y in range(80):
        draw.line([(0, y), (W, y)], fill=(int(90+y*0.7), int(40+y*0.3), int(220-y*0.3)))
    draw.rectangle([30, 110, W-30, H-30], fill=(30, 30, 60), outline=(130, 70, 255), width=2)
    draw.text((50, 130), f"Bea - {style}", font=ft, fill="white")
    draw.text((50, 180), texte[:120], font=fs, fill="#d1c5ff")
    return img

SYSTEM_BEA = "Tu es Bea, creee par BehaviorLab."
SYSTEM_PRO = "Tu es Bea Pro, Bea + studio montage pro complet : sous-titres stylises synchronises, suppression arriere-plan, decoupe silences, nettoyage audio, modeles, effets, transitions, animations, export optimise."
SYSTEM_ULTRA = "Tu es Bea Ultra, tout Bea Pro + creation app complete en un prompt."

licence_key = sanitize_key(st.query_params.get("key", ""))
is_dark = st.session_state.theme == "dark"
GRAD = "linear-gradient(135deg, #1d4ed8 0%, #7c3aed 60%, #c026d3 85%, #db2777 100%)"
BG = "#0f0a1e" if is_dark else "#0f0a1e"
TEXT = "#f5f3ff"
CARD = "#1a1535"
BORDER = "#7c3aed"

st.markdown(f"""
<style>
.stApp{{background:{BG}!important;}}
[data-testid="stSidebar"]{{background:#0d0d14!important; border-right:3px solid {BORDER}!important;}}
[data-testid="stSidebar"] *{{color:#e2d6ff!important;}}
header[data-testid="stHeader"]{{background:{BG}!important;}}
.block-container{{max-width:1050px!important; padding-top:1rem!important;}}
#MainMenu,footer{{visibility:hidden;}}
div[data-testid="stButton"]>button{{background:#15112a!important; color:#e8e0ff!important; border:2px solid {BORDER}!important; border-radius:12px!important; font-weight:600!important; font-size:13px!important; min-height:40px!important;}}
div[data-testid="stButton"]>button:hover{{background:#231a4a!important; border-color:#a855f7!important; box-shadow:0 0 12px rgba(124,58,237,0.4)!important;}}
.tool-btn button{{background:#15112a!important; color:#e8e0ff!important; border:2px solid {BORDER}!important; border-radius:14px!important; font-weight:700!important; font-size:12px!important; text-align:center!important; min-height:76px!important; box-shadow:0 0 0 1px rgba(124,58,237,0.3)!important;}}
.tool-btn button:hover{{background:#231a4a!important; border-color:#c084fc!important; box-shadow:0 0 16px rgba(124,58,237,0.6)!important; transform:translateY(-1px)!important;}}
div[data-testid="stLinkButton"]>a{{background:{GRAD}!important; color:white!important; border-radius:12px!important; font-weight:700!important; border:2px solid {BORDER}!important;}}
div[data-testid="stChatMessage"]{{background:{CARD}!important; border:2px solid {BORDER}!important; border-radius:16px!important; padding:16px!important;}}
div[data-testid="stChatMessage"] p{{color:{TEXT}!important; font-size:15px!important;}}
div[data-testid="stChatInput"]{{background:#1a1535!important; border:2px solid {BORDER}!important; border-radius:24px!important;}}
div[data-testid="stChatInput"] textarea{{color:{TEXT}!important;}}
input[type="text"], input[type="password"], textarea{{background:#1a1535!important; color:{TEXT}!important; border:2px solid {BORDER}!important; border-radius:12px!important;}}
.claude-title{{font-size:42px; font-weight:800; color:{TEXT}; text-align:center; margin:40px 0 10px 0;}}
.claude-sub{{font-size:15px; color:#c4b5fd; text-align:center; max-width:650px; margin:0 auto 32px auto; line-height:1.6;}}
.sidebar-logo{{text-align:center; margin-bottom:18px;}}
.sidebar-section{{font-size:10px; color:#8a7ab8!important; text-transform:uppercase; letter-spacing:0.8px; margin:22px 0 8px 0; font-weight:700;}}
.auth-card{{background:#1a1535!important; border:2px solid {BORDER}!important; border-radius:16px; padding:20px;}}
.timeline{{background:#15112a; border-radius:14px; padding:14px; border:2px solid {BORDER}; margin:14px 0;}}
.timeline-track{{background:#0d0d1e; height:46px; border-radius:10px; margin:8px 0; display:flex; align-items:center; padding:0 10px; border:1px solid #2a2250;}}
.track-block{{background:{GRAD}; height:34px; border-radius:8px; min-width:80px; margin-right:8px; display:flex; align-items:center; justify-content:center; font-size:11px; color:white; font-weight:700; border:1px solid #a855f7;}}
</style>
""", unsafe_allow_html=True)

# SIDEBAR AVEC LOGO AGRANDI
with st.sidebar:
    # LOGO AGRANDI DANS SIDEBAR
    logo_path = LOGOS.get("bea") or LOGOS.get("main")
    if logo_path and os.path.exists(logo_path):
        st.image(logo_path, width=140)
    else:
        st.markdown('<div style="width:120px;height:120px;background:linear-gradient(135deg,#1d4ed8,#7c3aed,#db2777);border-radius:24px;display:flex;align-items:center;justify-content:center;font-size:48px;font-weight:900;color:white;border:3px solid #7c3aed;">B</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; color:#f5f3ff; font-size:20px; font-weight:700;">Bea</div>', unsafe_allow_html=True)
    st.markdown('<div style="height:18px;"></div>', unsafe_allow_html=True)

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        if st.button("🌙 Sombre" if st.session_state.theme == "light" else "☀️ Clair", key="btn_theme", use_container_width=True):
            toggle_theme()
            st.rerun()
    with col_t2:
        if st.button(f"🌐 {st.session_state.lang}", key="btn_lang", use_container_width=True):
            toggle_lang()
            st.rerun()

    st.divider()

    if st.button("✨ Nouveau", key="new_side", use_container_width=True):
        st.session_state.messages = []
        st.session_state.action_message = ""
        st.session_state.history.append(f"Chat {len(st.session_state.history)+1}")
        st.rerun()

    if st.button("📁 Projets", key="proj_side", use_container_width=True):
        st.toast("Projets")
        st.session_state.current_tool = "Projets"

    if st.button("💻 Code", key="code_side", use_container_width=True):
        st.toast("Code")
        st.session_state.current_tool = "Code"

    if st.button("🎨 Personnalisation", key="perso_side", use_container_width=True):
        st.session_state.show_persona = not st.session_state.show_persona
        st.rerun()

    st.markdown('<div class="sidebar-section">Formats et options</div>', unsafe_allow_html=True)

    if st.button("🧠 Importer la memoire", key="import_mem", use_container_width=True):
        st.toast("Memoire importee")
        st.session_state.action_message = "Memoire importee"
        st.rerun()

    if st.button("👤 Personnaliser Bea", key="custom_bea", use_container_width=True):
        st.session_state.show_persona = True
        st.rerun()

    if st.button("Bea - 14,90", key="side_bea", use_container_width=True):
        st.session_state.selected_format = "bea"
        st.toast("Bea")
        st.rerun()

    if st.button("Bea Pro - 21", key="side_pro", use_container_width=True):
        st.session_state.selected_format = "pro"
        st.toast("Bea Pro")
        st.rerun()

    if st.button("Bea Ultra - 29,90", key="side_ultra", use_container_width=True):
        st.session_state.selected_format = "ultra"
        st.toast("Bea Ultra")
        st.rerun()

    st.markdown('<div class="sidebar-section">Recents</div>', unsafe_allow_html=True)
    for h in st.session_state.history[-6:]:
        if st.button(h[:26], key=f"hist_{h}_{len(st.session_state.history)}", use_container_width=True):
            st.toast(h)

    st.markdown("<div style='height:30px;'></div>", unsafe_allow_html=True)
    if st.session_state.logged and "user" in st.session_state:
        st.caption(f"{st.session_state.user.email}")
        if st.button("🚪 Deconnexion", key="deco_side", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.logged = False
            if "user" in st.session_state:
                del st.session_state.user
            st.rerun()
    else:
        st.caption("Non connecte - vitrine libre")

# PLUS DE CASE DU HAUT - SUPPRIMEE COMME DEMANDE

# CONNEXION
if not st.session_state.logged and not licence_key:
    # LOGO AGRANDI AU CENTRE
    logo_path = LOGOS.get("bea") or LOGOS.get("main")
    if logo_path and os.path.exists(logo_path):
        col_l1, col_l2, col_l3 = st.columns([1,0.6,1])
        with col_l2:
            st.image(logo_path, width=180)

    st.markdown('<div class="claude-title">Bea</div>', unsafe_allow_html=True)
    st.markdown('<div class="claude-sub">Bea transforme une intention en projet concret. Elle structure votre demarche, produit des videos pretes a diffuser avec sous-titres stylises et cree votre application en un prompt. Connectez-vous pour acceder a votre format.</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.container(border=True):
            st.markdown("#### Connexion")
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

    st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        with st.container(border=True):
            if LOGOS["bea"] and os.path.exists(LOGOS["bea"]):
                st.image(LOGOS["bea"], width=70)
            st.markdown("### Bea\n14,90 / mois")
            st.caption("De l'idee au projet structure")
            # RESTE SUR MEME PAGE APRES PAIEMENT - target blank
            st.markdown(f'<a href="{STRIPE_BEA}" target="_blank" style="display:block; background:{GRAD}; color:white; padding:12px; border-radius:12px; text-align:center; font-weight:700; text-decoration:none; border:2px solid {BORDER};">Choisir Bea</a>', unsafe_allow_html=True)
    with c2:
        with st.container(border=True):
            st.markdown("### Bea Pro\n21 / mois")
            st.caption("Bea + Studio montage pro complet")
            st.markdown(f'<a href="{STRIPE_PRO}" target="_blank" style="display:block; background:{GRAD}; color:white; padding:12px; border-radius:12px; text-align:center; font-weight:700; text-decoration:none; border:2px solid {BORDER};">Choisir Bea Pro</a>', unsafe_allow_html=True)
    with c3:
        with st.container(border=True):
            st.markdown("### Bea Ultra\n29,90 / mois")
            st.caption("Bea Pro + App complete en un prompt")
            st.markdown(f'<a href="{STRIPE_ULTRA}" target="_blank" style="display:block; background:{GRAD}; color:white; padding:12px; border-radius:12px; text-align:center; font-weight:700; text-decoration:none; border:2px solid {BORDER};">Choisir Bea Ultra</a>', unsafe_allow_html=True)
    st.stop()

if licence_key and not st.session_state.logged:
    st.markdown('<div class="claude-title">Bea</div>', unsafe_allow_html=True)
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
        plan, used, max_req = lic["plan"], lic["used"], lic["max_requests"]
    except Exception as e:
        st.error(f"Erreur licence : {e}")
        st.stop()
else:
    plan, used, max_req = "PRO", 0, 100

if len(st.session_state.messages) == 0:
    fmt = st.session_state.selected_format
    if fmt == "ultra":
        st.session_state.messages.append({"role": "assistant", "content": "Bonjour, je suis Bea Ultra. Montage pro + app en un prompt."})
    elif fmt == "pro":
        st.session_state.messages.append({"role": "assistant", "content": "Bonjour, je suis Bea Pro. Montage pro complet."})
    else:
        st.session_state.messages.append({"role": "assistant", "content": "Bonjour, je suis Bea."})

if st.session_state.show_persona:
    with st.container(border=True):
        st.markdown("#### Personnaliser Bea")
        nom = st.text_input("Comment Bea doit vous appeler?", key="perso_nom")
        if st.button("Enregistrer", key="save_perso"):
            st.toast(f"Bea vous appellera {nom}")
            st.session_state.show_persona = False
            st.rerun()

# VERSION UTILISABLE - PLUS DE BLANC SUR BLANC
st.markdown("### Montage video professionnel")
st.markdown(f"<div style='color:#c4b5fd; font-size:12px; margin-bottom:12px; background:#15112a; border:2px solid {BORDER}; border-radius:10px; padding:10px;'>Format: {st.session_state.format_export} | Style: {st.session_state.style_sub} | Outil: {st.session_state.current_tool} | {st.session_state.action_message}</div>", unsafe_allow_html=True)

col_a, col_b = st.columns([0.35, 0.65])
with col_a:
    up = st.file_uploader("Video brute", type=["mp4", "mov", "webm", "avi"], label_visibility="collapsed", key="up_video")
    if up:
        st.session_state.uploaded_video = up
        st.success(f"{up.name}")
        st.video(up)
        if st.button("Supprimer video", key="del_vid"):
            st.session_state.uploaded_video = None
            st.rerun()
    else:
        st.caption("200MB max - MP4 MOV WEBM AVI")

with col_b:
    txt = st.text_area("Script / paroles pour sous-titres", height=130, placeholder="Collez votre script...", key="script_area")
    if txt:
        st.session_state.script_text = txt

c_fmt, c_style, c_speed = st.columns(3)
with c_fmt:
    fmt = st.selectbox("Format export", ["9:16 Vertical", "16:9 Horizontal", "1:1 Carre", "4:5", "21:9"], key="fmt_sel")
    if fmt!= st.session_state.format_export:
        st.session_state.format_export = fmt
        st.toast(f"Format {fmt}")
with c_style:
    sty = st.selectbox("Style sous-titres", ["Viral pop", "Hormozi bold", "Minimal", "Cinema", "Neon", "Journal"], key="style_sel")
    if sty!= st.session_state.style_sub:
        st.session_state.style_sub = sty
        st.toast(f"Style {sty}")
with c_speed:
    spd = st.select_slider("Vitesse", options=[0.5, 0.75, 1.0, 1.25, 1.5, 2.0], value=1.0, key="speed_sel")
    st.session_state.speed = spd

st.markdown("**Outils principaux**")
r1_c1, r1_c2, r1_c3, r1_c4, r1_c5, r1_c6 = st.columns(6)
with r1_c1:
    st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
    if st.button("Couper\nDecouper", key="t_cut", use_container_width=True):
        st.session_state.current_tool = "Couper"; st.session_state.action_message = "Decoupe active"; st.toast("Couper"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with r1_c2:
    st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
    if st.button("Sous-titres\nAuto", key="t_sub", use_container_width=True):
        st.session_state.current_tool = "Sous-titres auto"
        if st.session_state.script_text:
            mots = st.session_state.script_text.split()
            srt = ""
            for i in range(0, len(mots), 5):
                srt += f"{i//5+1}\n00:00:{i//3:02d},000 --> 00:00:{i//3+2:02d},000\n{' '.join(mots[i:i+5])}\n\n"
            st.toast(f"{len(mots)} sous-titres")
            st.download_button("Telecharger SRT", srt, file_name="sous_titres.srt", key="dl_srt_now")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with r1_c3:
    st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
    if st.button("Supprimer\nFond", key="t_bg", use_container_width=True):
        st.session_state.current_tool = "Supprimer fond"; st.toast("Fond"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with r1_c4:
    st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
    if st.button("Decoupe\nSilences", key="t_sil", use_container_width=True):
        st.session_state.current_tool = "Decoupe silences"; st.toast("Silences"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with r1_c5:
    st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
    if st.button("Nettoyage\nAudio", key="t_audio", use_container_width=True):
        st.session_state.current_tool = "Nettoyage audio"; st.toast("Audio"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with r1_c6:
    st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
    if st.button("Modeles\nBibliotheque", key="t_model", use_container_width=True):
        st.session_state.current_tool = "Modeles"; st.toast("Modeles"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

r2_c1, r2_c2, r2_c3, r2_c4, r2_c5, r2_c6 = st.columns(6)
with r2_c1:
    st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
    if st.button("Effets\nVideo", key="t_eff", use_container_width=True):
        st.session_state.current_tool = "Effets"; st.toast("Effets"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with r2_c2:
    st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
    if st.button("Transitions\nAnimees", key="t_trans", use_container_width=True):
        st.session_state.current_tool = "Transitions"; st.toast("Transitions"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with r2_c3:
    st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
    if st.button("Animations\nTexte", key="t_anim", use_container_width=True):
        st.session_state.current_tool = "Animations texte"; st.toast("Animations"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with r2_c4:
    st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
    if st.button("Filtres\nCouleur", key="t_filt", use_container_width=True):
        st.session_state.current_tool = "Filtres"; st.toast("Filtres"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with r2_c5:
    st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
    if st.button("Vitesse\nRalenti", key="t_speed", use_container_width=True):
        st.session_state.current_tool = f"Vitesse {st.session_state.speed}x"; st.toast(f"Vitesse {st.session_state.speed}x"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with r2_c6:
    st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
    if st.button("Stickers\nEmojis", key="t_stick", use_container_width=True):
        st.session_state.current_tool = "Stickers"; st.toast("Stickers"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

r3_c1, r3_c2, r3_c3, r3_c4, r3_c5, r3_c6 = st.columns(6)
with r3_c1:
    st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
    if st.button("Musique\nBibliotheque", key="t_music", use_container_width=True):
        st.session_state.current_tool = "Musique"; st.toast("Musique"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with r3_c2:
    st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
    if st.button("Recadrer\nZoom", key="t_crop", use_container_width=True):
        st.session_state.current_tool = "Recadrer"; st.toast("Recadrer"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with r3_c3:
    st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
    if st.button("Stabiliser\nVideo", key="t_stab", use_container_width=True):
        st.session_state.current_tool = "Stabiliser"; st.toast("Stabilisee"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with r3_c4:
    st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
    if st.button("Voix Off\nIA", key="t_voice", use_container_width=True):
        st.session_state.current_tool = "Voix Off"; st.toast("Voix Off"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with r3_c5:
    st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
    if st.button("Miniature\n1280x720", key="t_thumb", use_container_width=True):
        img = generer_visuel(st.session_state.script_text or "Bea", st.session_state.style_sub)
        st.image(img, use_container_width=True)
        st.toast("Miniature")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with r3_c6:
    st.markdown('<div class="tool-btn">', unsafe_allow_html=True)
    if st.button("Creer App\nEn 1 prompt", key="t_app", use_container_width=True):
        st.session_state.current_tool = "Creation app"; st.session_state.messages.append({"role": "user", "content": "Creer app en un prompt"}); st.toast("App"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown(f'<div class="timeline"><div style="color:#c4b5fd; font-size:11px; margin-bottom:6px;">TIMELINE - Encadre couleur</div><div class="timeline-track"><div class="track-block">Intro 0:03</div><div class="track-block" style="min-width:130px;">Principal - {st.session_state.style_sub}</div><div class="track-block">Outro 0:02</div></div></div>', unsafe_allow_html=True)

if st.session_state.action_message:
    st.info(f"Outil: {st.session_state.current_tool} | {st.session_state.action_message}")

c_act1, c_act2, c_act3, c_act4 = st.columns(4)
with c_act1:
    if st.button("Generer montage complet", key="gen_full", use_container_width=True):
        check_rate()
        prompt = st.session_state.script_text or "Generer montage pro"
        st.session_state.messages.append({"role": "user", "content": f"{prompt} Format {st.session_state.format_export} Style {st.session_state.style_sub}"})
        msgs = [{"role": mm["role"], "content": sanitize_user(mm["content"])} for mm in st.session_state.messages if mm.get("role")!= "system" and "image" not in mm]
        sys_prompt = SYSTEM_ULTRA if st.session_state.selected_format == "ultra" else SYSTEM_PRO if st.session_state.selected_format == "pro" else SYSTEM_BEA
        try:
            with st.spinner("Generation..."):
                reponse, _ = call_groq([{"role": "system", "content": sys_prompt}] + msgs[-12:])
                img = generer_visuel(prompt, st.session_state.style_sub)
                st.session_state.messages.append({"role": "assistant", "content": sanitize_assistant(reponse), "image": img})
            if licence_key:
                supabase.table("licences").update({"used": used+1}).eq("key", licence_key).execute()
            st.success("Montage genere!")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {str(e)[:300]}")
with c_act2:
    if st.button("Nouvelle discussion", key="new_chat_main", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
with c_act3:
    if st.button("Exporter video", key="export_vid", use_container_width=True):
        st.success(f"Export {st.session_state.format_export} lance")
        st.toast(f"Export {st.session_state.format_export}")
with c_act4:
    if st.button("Deconnexion", key="deco_main", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.logged = False
        if "user" in st.session_state:
            del st.session_state.user
        st.rerun()

st.divider()

for m in st.session_state.messages:
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

prompt_raw = st.chat_input("Ecrivez un message...", key="chat_claude_final")
if prompt_raw:
    check_rate()
    prompt_clean = sanitize_user(prompt_raw)
    st.session_state.messages.append({"role": "user", "content": prompt_clean})
    msgs = [{"role": mm["role"], "content": sanitize_user(mm["content"])} for mm in st.session_state.messages if mm.get("role")!= "system" and "image" not in mm]
    sys_prompt = SYSTEM_ULTRA if st.session_state.selected_format == "ultra" else SYSTEM_PRO if st.session_state.selected_format == "pro" else SYSTEM_BEA
    try:
        reponse, _ = call_groq([{"role": "system", "content": sys_prompt}] + msgs[-15:])
        st.session_state.messages.append({"role": "assistant", "content": sanitize_assistant(reponse)})
        if licence_key:
            supabase.table("licences").update({"used": used+1}).eq("key", licence_key).execute()
        st.rerun()
    except Exception as e:
        st.error(f"Erreur : {str(e)[:300]}")
