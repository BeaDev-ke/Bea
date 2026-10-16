import streamlit as st
import os
import re
import time
from groq import Groq
from supabase import create_client
from collections import deque

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
            c = client.chat.completions.create(model=mid, messages=messages, temperature=0.7, max_tokens=2200)
            return c.choices[0].message.content, mid
        except Exception as e:
            last = e
            continue
    raise last

for k, v in {"theme": "dark", "lang": "FR", "messages": [], "code_messages": [], "rate_limit": deque(), "blocked_until": 0, "selected_format": "bea", "logged": False, "history": [], "projets_codes": [], "show_persona": False, "vitrine_section": "accueil", "code_content": "# Bea - app_v2.py - BehaviorLab AI\n# Creation de code gratuite\n\nimport streamlit as st\n\ndef bea_app():\n st.title('Mon app Bea')\n idee = st.text_input('Ton idee')\n if idee:\n st.success(f'Bea genere: {idee} -> app prete')\n\nif __name__ == '__main__':\n bea_app()\n", "code_language": "python", "open_files": ["app_v2.py", "requirements.txt", "README.md"], "active_file": "app_v2.py"}.items():
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

SYSTEM_CODE = "Tu es l'IA code de Bea BehaviorLab AI, integree dans VS Code. Tu aides a comprendre, debugger, ameliorer le code. Reponses courtes et utiles."
SYSTEM_BEA = "Tu es Bea BehaviorLab AI."

licence_key = sanitize_key(st.query_params.get("key", ""))
GRAD = "linear-gradient(135deg, #1d4ed8 0%, #7c3aed 60%, #c026d3 85%, #db2777 100%)"
BORDER = "#7c3aed"
BG = "#0f0a1e"
CARD = "#1a1535"

st.markdown(f"""
<style>
.stApp{{background:{BG}!important;}}
[data-testid="stSidebar"]{{background:#0d0d14!important; border-right:3px solid {BORDER}!important;}}
[data-testid="stSidebar"] *{{color:#e2d6ff!important;}}
header[data-testid="stHeader"]{{background:{BG}!important;}}
.block-container{{max-width:1280px!important; padding-top:0.2rem!important;}}
#MainMenu,footer{{visibility:hidden;}}
div[data-testid="stButton"]>button{{background:#15112a!important; color:#e8e0ff!important; border:2px solid {BORDER}!important; border-radius:10px!important; font-weight:600!important; min-height:38px!important;}}
div[data-testid="stButton"]>button:hover{{background:#231a4a!important;}}
.vscode-shell{{background:#1e1e1e; border:2px solid {BORDER}; border-radius:8px; overflow:hidden; font-family:'Consolas','Courier New',monospace;}}
.vscode-titlebar{{background:#181818; color:#cccccc; height:35px; display:flex; align-items:center; padding:0 12px; font-size:12px; border-bottom:1px solid #2d2d2d;}}
.vscode-activitybar{{background:#181818; width:48px; display:flex; flex-direction:column; align-items:center; padding:8px 0; gap:18px; border-right:1px solid #2d2d2d;}}
.vscode-sidebar{{background:#252526; width:260px; border-right:1px solid #2d2d2d; padding:8px; color:#cccccc; font-size:12px;}}
.vscode-editor-header{{background:#252526; height:35px; display:flex; align-items:center; padding:0 10px; border-bottom:1px solid #2d2d2d; color:#cccccc; font-size:12px;}}
.vscode-editor{{background:#1e1e1e; padding:12px; color:#d4d4d4; min-height:380px;}}
.vscode-chat{{background:#252526; width:380px; border-left:1px solid #2d2d2d; display:flex; flex-direction:column;}}
.vscode-chat-header{{background:#252526; height:35px; display:flex; align-items:center; justify-content:space-between; padding:0 12px; border-bottom:1px solid #2d2d2d; color:#cccccc; font-size:13px;}}
.vscode-statusbar{{background:#007acc; color:white; height:22px; display:flex; align-items:center; padding:0 10px; font-size:11px; gap:16px;}}
.file-tab{{background:#2d2d2d; color:#cccccc; padding:6px 12px; border-right:1px solid #1e1e1e; font-size:12px; display:inline-block; margin-right:2px;}}
.file-tab.active{{background:#1e1e1e; color:white; border-top:2px solid #007acc;}}
</style>
""", unsafe_allow_html=True)

# SIDEBAR - VITRINE VIDE / APRES CONNEXION COMPLET
with st.sidebar:
    st.markdown('<div style="display:flex; flex-direction:column; align-items:center;">', unsafe_allow_html=True)
    logo_path = LOGOS.get("bea")
    if logo_path and os.path.exists(logo_path):
        st.image(logo_path, width=58)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; font-size:17px; font-weight:800; color:#f5f3ff; margin-top:5px;">Bea</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; font-size:10px; color:#d8ccff!important; font-weight:700; letter-spacing:0.8px; margin-bottom:10px;">BehaviorLab AI</div>', unsafe_allow_html=True)

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        if st.button("🌙 Sombre", key="btn_theme", use_container_width=True):
            st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
            st.rerun()
    with col_t2:
        if st.button(f"🌐 {st.session_state.lang}", key="btn_lang", use_container_width=True):
            st.session_state.lang = "EN" if st.session_state.lang == "FR" else "FR"
            st.rerun()

    st.divider()

    # VITRINE = SIDEBAR VIDE - PAS DE NOUVEAU / CODE / PERSONNALISATION
    if not st.session_state.logged and not licence_key:
        st.caption("Acces libre - creation code gratuite")
        st.caption("Connecte-toi pour sauvegarder")
        st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
        st.markdown("**Gratuit**\n- Editeur code\n- Discussion libre IA")
    else:
        # APRES CONNEXION = CODE / PERSONNALISATION / PROJETS + NOUVELLE DISCUSSION + HISTORIQUE
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

        st.markdown('<div style="font-size:10px; color:#8a7ab8; text-transform:uppercase; margin:14px 0 6px 0; font-weight:700;">Historique</div>', unsafe_allow_html=True)
        for h in st.session_state.history[-8:][::-1]:
            if st.button(f"• {h[:20]}", key=f"hist_{h}", use_container_width=True):
                st.toast(h)
                st.rerun()

        for idx, code_item in enumerate(st.session_state.projets_codes[-5:][::-1]):
            if st.button(f"💾 {code_item['name'][:18]}", key=f"code_proj_{idx}", use_container_width=True):
                st.session_state.code_content = code_item["content"]
                st.session_state.vitrine_section = "code"
                st.rerun()

        if "user" in st.session_state:
            st.caption(f"{st.session_state.user.email}")
            if st.button("🚪 Deconnexion", key="deco_side", use_container_width=True):
                supabase.auth.sign_out()
                st.session_state.logged = False
                if "user" in st.session_state:
                    del st.session_state.user
                st.rerun()

def render_vscode_full():
    # BARRE TITRE VS CODE
    st.markdown(f"""
    <div class="vscode-shell">
        <div class="vscode-titlebar">
            <div style="display:flex; gap:8px; align-items:center;">
                <span>File</span><span>Edit</span><span>Selection</span><span>View</span><span>Go</span><span>Run</span><span>Terminal</span><span>Help</span>
            </div>
            <div style="margin-left:auto; display:flex; gap:12px;">
                <span>─</span><span>□</span><span>✕</span>
            </div>
        </div>
        <div style="display:flex;">
            <div class="vscode-activitybar">
                <div title="Explorer" style="font-size:20px;">📁</div>
                <div title="Search" style="font-size:20px;">🔍</div>
                <div title="Source Control" style="font-size:20px;">🌿</div>
                <div title="Run and Debug" style="font-size:20px;">▶️</div>
                <div title="Extensions" style="font-size:20px;">🧩</div>
                <div title="Accounts" style="margin-top:auto; font-size:20px;">👤</div>
                <div title="Settings" style="font-size:20px;">⚙️</div>
            </div>
            <div class="vscode-sidebar">
                <div style="font-weight:700; font-size:11px; text-transform:uppercase; margin-bottom:10px;">Explorer</div>
                <div style="margin-bottom:8px; font-weight:600;">BEA-PROJECT</div>
                <div style="padding-left:8px; line-height:22px;">
                    📁.venv<br/>
                    📁 src<br/>
                    &nbsp;&nbsp;📄 app_v2.py<br/>
                    &nbsp;&nbsp;📄 main.py<br/>
                    📄 requirements.txt<br/>
                    📄 README.md<br/>
                    📄.gitignore
                </div>
                <div style="margin-top:18px; font-weight:600; font-size:11px;">OUTLINE</div>
                <div style="margin-top:12px; font-weight:600; font-size:11px;">TIMELINE</div>
            </div>
            <div style="flex:1; display:flex; flex-direction:column;">
                <div class="vscode-editor-header">
                    {"".join([f"<div class='file-tab {'active' if f==st.session_state.active_file else ''}'>{f} {'✕' if f==st.session_state.active_file else ''}</div>" for f in st.session_state.open_files])}
                    <div style="margin-left:auto; display:flex; gap:8px;">
                        <span>+</span><span>⋁</span><span>⚙️</span><span>⋯</span><span>🗖</span><span>✕</span>
                    </div>
                </div>
            </div>
            <div class="vscode-chat">
                <div class="vscode-chat-header">
                    <span>💬 Chat</span>
                    <span>+ ⋁ ⚙️ ⋯ 🗖 ✕</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # EDITEUR + CHAT EN STREAMLIT EN DESSOUS DU HEADER
    col_editor, col_chat = st.columns([1.25, 0.75], gap="small")

    with col_editor:
        st.markdown("**File - Edit - Selection - View - Go - Run - Terminal - Help** - menus utiles")
        c_file, c_edit, c_run = st.columns(3)
        with c_file:
            if st.button("📄 New File", key="new_file", use_container_width=True):
                st.session_state.open_files.append(f"new_{len(st.session_state.open_files)}.py")
                st.session_state.active_file = st.session_state.open_files[-1]
                st.rerun()
            if st.button("💾 Save", key="save_file", use_container_width=True):
                st.toast(f"{st.session_state.active_file} sauve")
                st.session_state.projets_codes.append({"name": st.session_state.active_file, "content": st.session_state.code_content, "lang": "python"})
        with c_edit:
            if st.button("✂️ Cut/Copy/Paste", key="edit_menu", use_container_width=True):
                st.toast("Edit : Cut Copy Paste Undo Redo Find Replace")
            if st.button("🔍 Find in Files", key="find_menu", use_container_width=True):
                st.toast("Search : Find Replace in Files")
        with c_run:
            if st.button("▶️ Run Python File", key="run_file", use_container_width=True):
                st.success(f"Running {st.session_state.active_file}")
                st.code(f"> python {st.session_state.active_file}\nBea - BehaviorLab AI ready", language="bash")
            if st.button("🐛 Debug", key="debug_file", use_container_width=True):
                st.toast("Run and Debug lance")

        lang = st.selectbox("Language", ["python", "javascript", "typescript", "html", "css", "json"], index=0, key="lang_sel")
        st.session_state.code_language = lang

        code_input = st.text_area("Code Editor", value=st.session_state.code_content, height=380, key="code_editor", label_visibility="collapsed")
        if code_input!= st.session_state.code_content:
            st.session_state.code_content = code_input

        st.markdown(f"<div style='background:#007acc; color:white; padding:4px 10px; font-size:11px; border-radius:0 0 6px 6px; display:flex; gap:14px;'><span>Ln {len(code_input.splitlines())}, Col 76</span><span>Spaces: 4</span><span>UTF-8</span><span>CRLF</span><span>{{}} {lang}</span><span>Python extension</span></div>", unsafe_allow_html=True)

        c_term1, c_term2 = st.columns(2)
        with c_term1:
            if st.button("📟 Terminal - New", key="term_new", use_container_width=True):
                st.code("> Terminal\n> pip install -r requirements.txt", language="bash")
        with c_term2:
            if st.button("🧹 Clear Terminal", key="term_clear", use_container_width=True):
                st.toast("Terminal efface")

    with col_chat:
        st.markdown(f"""
        <div style="background:#252526; border:2px solid {BORDER}; border-radius:8px; padding:16px; text-align:center; margin-bottom:10px;">
            <div style="font-size:28px; margin-bottom:8px;">💬✨</div>
            <div style="color:#cccccc; font-weight:700; margin-bottom:6px;">Ask about your code</div>
            <div style="color:#8a8a8a; font-size:11px; line-height:1.4;">AI responses may be inaccurate<br/>
            <span style="color:#4ec9b0; text-decoration:underline;">Generate Agent Instructions</span> to onboard<br/>AI onto your codebase.</div>
        </div>
        """, unsafe_allow_html=True)

        for m in st.session_state.code_messages[-6:]:
            if m["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(sanitize_user(m["content"]))
            else:
                with st.chat_message("assistant", avatar=LOGOS["bea"] if LOGOS["bea"] and os.path.exists(LOGOS["bea"]) else "Bea"):
                    st.markdown(sanitize_assistant(m["content"]))

        chat_input = st.chat_input("Ask about your code...", key="code_chat_input")
        if chat_input:
            check_rate()
            st.session_state.code_messages.append({"role": "user", "content": sanitize_user(chat_input)})
            context = st.session_state.code_content[:2000]
            msgs = [{"role": "system", "content": SYSTEM_CODE + f"\nCode:\n{context}"}] + [{"role": mm["role"], "content": sanitize_user(mm["content"])} for mm in st.session_state.code_messages[-8:]]
            try:
                rep, _ = call_groq(msgs)
                st.session_state.code_messages.append({"role": "assistant", "content": sanitize_assistant(rep)})
                st.rerun()
            except Exception as e:
                st.error(str(e)[:300])

        if st.button("Explain this file", key="explain_file", use_container_width=True):
            st.session_state.code_messages.append({"role": "user", "content": f"Explique {st.session_state.active_file}"})
            msgs = [{"role": "system", "content": SYSTEM_CODE + f"\nCode:\n{st.session_state.code_content[:2000]}"}, {"role": "user", "content": f"Explique {st.session_state.active_file} ligne par ligne"}]
            try:
                rep, _ = call_groq(msgs)
                st.session_state.code_messages.append({"role": "assistant", "content": rep})
                st.rerun()
            except Exception as e:
                st.error(str(e))

        if st.button("Fix errors", key="fix_errors", use_container_width=True):
            st.session_state.code_messages.append({"role": "user", "content": "Corrige les erreurs"})
            msgs = [{"role": "system", "content": SYSTEM_CODE + f"\nCode:\n{st.session_state.code_content[:2000]}"}, {"role": "user", "content": "Corrige et ameliore ce code"}]
            try:
                rep, _ = call_groq(msgs)
                st.session_state.code_messages.append({"role": "assistant", "content": rep})
                st.rerun()
            except Exception as e:
                st.error(str(e))

        st.markdown(f"<div style='background:#1e1e1e; border:1px solid #2d2d2d; border-radius:6px; padding:6px 10px; font-size:11px; color:#cccccc; margin-top:10px; display:flex; gap:6px; align-items:center;'><span style='background:#3c3c3c; padding:2px 6px; border-radius:4px;'>✕ 🔵 {st.session_state.active_file}</span><span style='margin-left:auto;'>Install Python extension?</span></div>", unsafe_allow_html=True)

# VITRINE - GRATUIT CODE + DISCUSSION
if not st.session_state.logged and not licence_key:
    st.markdown('<div style="text-align:center; font-size:22px; font-weight:800; color:#f5f3ff; margin-top:4px;">Bea</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; font-size:11px; color:#d8ccff!important; font-weight:700; letter-spacing:0.8px; margin-bottom:10px;">BehaviorLab AI - Creation de code gratuite + discussion libre</div>', unsafe_allow_html=True)

    render_vscode_full()

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.container(border=True):
            st.markdown("#### Connexion pour sauvegarder tes projets")
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

    st.markdown("### BehaviorLab AI - Formats payants")
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        with st.container(border=True):
            st.markdown("#### Bea\n14,90 / mois\nDe l'idee au projet structure")
            st.markdown(f'<a href="{STRIPE_BEA}" target="_blank" style="display:block; background:{GRAD}; color:white; padding:10px; border-radius:10px; text-align:center; font-weight:700; text-decoration:none; border:2px solid {BORDER};">Choisir Bea</a>', unsafe_allow_html=True)
    with c2:
        with st.container(border=True):
            st.markdown("#### Bea Pro\n21 / mois\nBea + Studio montage pro")
            st.markdown(f'<a href="{STRIPE_PRO}" target="_blank" style="display:block; background:{GRAD}; color:white; padding:10px; border-radius:10px; text-align:center; font-weight:700; text-decoration:none; border:2px solid {BORDER};">Choisir Bea Pro</a>', unsafe_allow_html=True)
    with c3:
        with st.container(border=True):
            st.markdown("#### Bea Ultra\n29,90 / mois\nBea Pro + App en un prompt")
            st.markdown(f'<a href="{STRIPE_ULTRA}" target="_blank" style="display:block; background:{GRAD}; color:white; padding:10px; border-radius:10px; text-align:center; font-weight:700; text-decoration:none; border:2px solid {BORDER};">Choisir Bea Ultra</a>', unsafe_allow_html=True)
    st.stop()

# APRES CONNEXION
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
            st.info("Aucun code sauve")
        else:
            for item in st.session_state.projets_codes[::-1]:
                with st.container(border=True):
                    st.markdown(f"**{item['name']}**")
                    st.code(item["content"][:500], language=item["lang"])
                    if st.button(f"Ouvrir {item['name']}", key=f"open_{item['name']}"):
                        st.session_state.code_content = item["content"]
                        st.session_state.vitrine_section = "code"
                        st.rerun()
        if st.button("Retour Code", key="ret_proj"):
            st.session_state.vitrine_section = "code"
            st.rerun()

# EDITEUR PRINCIPAL APRES CONNEXION
st.markdown('<div style="text-align:center; font-size:18px; font-weight:800; color:#f5f3ff;">Bea</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center; font-size:10px; color:#d8ccff!important; font-weight:700; letter-spacing:0.8px; margin-bottom:10px;">BehaviorLab AI</div>', unsafe_allow_html=True)

render_vscode_full()

st.divider()
st.markdown("### Discussion libre - Bea")
for m in st.session_state.messages[-6:]:
    if m.get("role") == "system":
        continue
    if m["role"] == "user":
        with st.chat_message("user"):
            st.markdown(sanitize_user(m["content"]))
    else:
        with st.chat_message("assistant", avatar=LOGOS["bea"] if LOGOS["bea"] and os.path.exists(LOGOS["bea"]) else "Bea"):
            st.markdown(sanitize_assistant(m["content"]))

prompt_raw = st.chat_input("Discussion libre avec Bea...", key="chat_final")
if prompt_raw:
    check_rate()
    st.session_state.messages.append({"role": "user", "content": sanitize_user(prompt_raw)})
    msgs = [{"role": "system", "content": SYSTEM_BEA}] + [{"role": mm["role"], "content": sanitize_user(mm["content"])} for mm in st.session_state.messages[-10:] if mm.get("role")!= "system"]
    try:
        rep, _ = call_groq(msgs)
        st.session_state.messages.append({"role": "assistant", "content": sanitize_assistant(rep)})
        if licence_key:
            supabase.table("licences").update({"used": used+1}).eq("key", licence_key).execute()
        st.rerun()
    except Exception as e:
        st.error(str(e)[:300])
