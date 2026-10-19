import html
import io
import json
import os
import re
import time
from collections import deque
from datetime import datetime, timezone

import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
from PIL import Image
from supabase import create_client

from bea_utils import (
    PALETTES,
    clean_text,
    cues_to_srt,
    cues_to_vtt,
    extract_html,
    image_to_png_bytes,
    make_thumbnail,
    script_to_cues,
    segments_to_cues,
)

def find_file(cands):
    for f in cands:
        if os.path.exists(f):
            return f
    return None

LOGO = find_file(["logo_bea.png", "logo.png"])
try:
    _icon = Image.open(LOGO) if LOGO else "🧠"
except Exception:
    _icon = "🧠"

st.set_page_config(page_title="Bea", page_icon=_icon, layout="wide", initial_sidebar_state="expanded")
AVATAR = LOGO or "🧠"

STRIPE_BEA_9 = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"
STRIPE_PRO_1490 = "https://buy.stripe.com/test_cNieVea1P0c62B08523wQ00"
STRIPE_ABO_16 = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"

try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    SUPA_URL = st.secrets["SUPABASE_URL"]
    SUPA_KEY = st.secrets.get("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_KEY")
    if not SUPA_KEY:
        raise KeyError("SUPABASE_ANON_KEY")
    DEV_ACCESS_KEY = st.secrets.get("DEV_ACCESS_KEY", "")
    DEV_EMAIL = st.secrets.get("DEV_EMAIL", "saydoukebe31@gmail.com")
except Exception:
    st.error("Configuration manquante : GROQ_API_KEY, SUPABASE_URL et SUPABASE_ANON_KEY doivent être définis dans les secrets.")
    st.stop()

CONTACT_EMAIL = st.secrets.get("CONTACT_EMAIL", "")
REQUIRE_LOGIN_CODE = str(st.secrets.get("REQUIRE_LOGIN_CODE", "false")).strip().lower() in ("1", "true", "yes", "oui")

PLANS = ("free", "bea", "pro", "abo")
PLAN_LABEL = {"free": "Gratuit", "bea": "Bea", "pro": "Bea Pro", "abo": "Bea Ultra"}
WHISPER_MODEL = "whisper-large-v3-turbo"
MAX_AUDIO_BYTES = 25 * 1024 * 1024
EXT = {"python": "py", "javascript": "js", "typescript": "ts", "html": "html", "css": "css", "json": "json", "sql": "sql"}
DEFAULT_CODE = ""

STARTER_CARDS = {
    "entreprise": [
        "Je n'arrive pas à déléguer, je fais tout moi-même et je m'épuise",
        "Mon équipe n'est pas assez régulière, comment créer une routine ?",
        "Je repousse les décisions difficiles, comment trancher plus vite ?",
    ],
    "independant": [
        "Je procrastine sur la prospection clients",
        "Je n'arrive pas à fixer mes prix sans culpabiliser",
        "J'alterne hyper-productif et à plat, comment stabiliser ?",
    ],
    "createur": [
        "Je n'arrive pas à publier tous les jours, je bloque",
        "Mon montage me prend 5h, comment aller plus vite ?",
        "Je ne sais pas quoi dire en face cam, comment me débloquer ?",
    ]
}

@st.cache_resource
def get_groq():
    return Groq(api_key=GROQ_KEY)

@st.cache_data(ttl=3600)
def get_modeles():
    pref_fast = ["llama-3.1-8b-instant", "openai/gpt-oss-20b", "llama-3.3-70b-versatile"]
    pref_power = ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "llama-3.1-70b-versatile"]
    try:
        ids = [m.id for m in get_groq().models.list().data]
        chat_ids = [i for i in ids if "whisper" not in i and "guard" not in i]
        fast = [m for m in pref_fast if m in chat_ids] or chat_ids[:2]
        power = [m for m in pref_power if m in chat_ids] or chat_ids[:2]
        return {"rapide": fast, "puissant": power}
    except Exception:
        return {"rapide": pref_fast[:1], "puissant": pref_power[:1]}

DEV_MODELES = {
    "Ultra (gratuit) - GPT OSS 120B [RECOMMANDÉ - ne casse rien]": "openai/gpt-oss-120b",
    "Puissant (gratuit) - Llama 3.3 70B": "llama-3.3-70b-versatile",
    "Codeur (gratuit) - GPT OSS 20B": "openai/gpt-oss-20b",
    "Rapide (gratuit) - Llama 3.1 8B": "llama-3.1-8b-instant",
}

def now_iso():
    return datetime.now(timezone.utc).isoformat()

for k, v in {
    "page": "chat", "sb": None, "user": None, "plan": "free", "quota": {}, "prefs": {},
    "conv_id": None, "messages": [], "convs": None, "projects": None,
    "code_messages": [], "code_project_id": None, "code_name_in": "", "code_lang_in": "python",
    "rate": deque(), "blocked_until": 0.0, "up_key": 0, "expanded": None, "auth_notice": "",
    "sub_result": None, "plan_result": None, "app_result": None, "thumb_png": None, "pending_login": None, "is_admin": False,
    "model_choice": "rapide", "search_q": "", "editing_msg_id": None, "studio_menu": "importer", "memories": None, "profile_type": "createur",
    "dev_mode": None, "dev_result": None, "dev_raw": None, "dev_key_ok": False, "dev_model_choice": "Ultra (gratuit) - GPT OSS 120B [RECOMMANDÉ - ne casse rien]",
    "dev_full_original": "", "dev_backup_name": "", "transcribed_text": "",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v
if "code_area" not in st.session_state:
    st.session_state["code_area"] = DEFAULT_CODE

GRAD = "linear-gradient(135deg, #1d4ed8 0%, #7c3aed 60%, #c026d3 85%, #db2777 100%)"
BORDER, BG, CARD, TEXT = "#7c3aed", "#0f0a1e", "#1a1535", "#f5f3ff"
st.markdown(f"""
<style>
.stApp{{background:{BG}!important;}}
[data-testid="stSidebar"]{{background:#0d0d14!important; border-right:3px solid {BORDER}!important;}}
[data-testid="stSidebar"] *{{color:#e2d6ff!important;}}
header[data-testid="stHeader"]{{background:transparent!important;}}
.block-container{{max-width:1150px!important; padding-top:2.8rem!important; padding-bottom:7rem!important;}}
#MainMenu,footer{{visibility:hidden;}}
div[data-testid="stButton"]>button{{background:#15112a!important; color:#e8e0ff!important; border:2px solid {BORDER}!important; border-radius:12px!important; font-weight:600!important; font-size:13px!important; min-height:44px!important;}}
div[data-testid="stButton"]>button:hover{{background:#231a4a!important; border-color:#a855f7!important; box-shadow:0 0 10px rgba(124,58,237,0.4)!important;}}
div[data-testid="stLinkButton"]>a{{background:{GRAD}!important; color:white!important; border-radius:12px!important; font-weight:700!important; border:2px solid {BORDER}!important; padding:12px!important;}}
div[data-testid="stChatMessage"]{{background:{CARD}!important; border:2px solid {BORDER}!important; border-radius:16px!important; padding:14px!important;}}
div[data-testid="stChatMessage"] p{{color:{TEXT}!important; font-size:15px!important; line-height:1.6!important;}}
div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="select"]>div{{background:#1a1535!important; border:2px solid {BORDER}!important; border-radius:12px!important;}}
div[data-baseweb="base-input"]{{background:transparent!important; border:none!important;}}
div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea, div[data-baseweb="select"] input{{background:transparent!important; color:{TEXT}!important; border:none!important; box-shadow:none!important; outline:none!important;}}
div[data-testid="stChatInput"]{{background:#1a1535!important; border:2px solid {BORDER}!important; border-radius:24px!important; padding-right:90px!important;}}
div[data-testid="stChatInput"] div, div[data-testid="stChatInput"] textarea{{background:transparent!important; border:none!important; box-shadow:none!important; color:{TEXT}!important;}}
div[data-testid="stBottom"]{{background:transparent!important; position:relative!important;}}
div[data-testid="stBottom"]>div{{background:transparent!important;}}
.claude-title{{font-size:34px; font-weight:800; color:{TEXT}; text-align:center; margin:8px 0 2px 0;}}
.claude-sub{{font-size:12px; color:#d8ccff!important; text-align:center; font-weight:700; letter-spacing:0.8px; margin-bottom:16px;}}
.desc-main{{font-size:14px; color:#c4b5fd; text-align:center; max-width:760px; margin:12px auto 32px auto; line-height:1.7;}}
.limit-badge{{background:#2a1a4a; border:1px solid {BORDER}; border-radius:8px; padding:6px 10px; font-size:11px; color:#c4b5fd; margin-bottom:10px;}}
.soon{{font-size:12px; color:#8a7ab8;}}
#mic-point-vert{{position:absolute!important; right:60px!important; bottom:10px!important; z-index:9999!important; width:42px!important; height:42px!important;}}
#mic-point-vert div[data-testid="stAudioInput"]{{background:transparent!important; border:none!important; width:42px!important; min-width:42px!important;}}
#mic-point-vert div[data-testid="stAudioInput"] button{{background:#1a1535!important; border:2px solid {BORDER}!important; border-radius:50%!important; width:42px!important; height:42px!important; min-height:42px!important; padding:0!important; display:flex!important; align-items:center!important; justify-content:center!important;}}
#mic-point-vert div[data-testid="stAudioInput"] button:hover{{background:#231a4a!important; border-color:#a855f7!important; box-shadow:0 0 12px rgba(124,58,237,0.5)!important;}}
#mic-point-vert div[data-testid="stAudioInput"] > div{{background:transparent!important; border:none!important;}}
#mic-point-vert div[data-testid="stAudioInput"] svg{{width:18px!important; height:18px!important;}}
.studio-step{{background:{CARD}!important; border:2px solid {BORDER}!important; border-radius:14px!important; padding:18px!important; margin-bottom:14px!important;}}
.studio-step h4{{color:{TEXT}!important; margin:0 0 6px 0!important; font-size:17px!important;}}
.studio-step p{{color:#c4b5fd!important; font-size:13px!important; margin:0 0 12px 0!important; line-height:1.5!important;}}
.studio-nav-btn>button{{text-align:left!important; padding:10px 14px!important;}}
.studio-badge{{display:inline-block; background:#2a1a4a; color:#c4b5fd; border:1px solid {BORDER}; border-radius:6px; padding:2px 8px; font-size:10px; font-weight:700; margin-left:6px;}}
.studio-badge-free{{background:#3a2a1a; color:#fbbf24; border-color:#f59e0b;}}
.studio-badge-pro{{background:#1a2a3a; color:#60a5fa; border-color:#3b82f6;}}
</style>
""", unsafe_allow_html=True)

STYLE_HINT = {
    "Direct": "Va droit au but, phrases courtes, sans détour.",
    "Doux": "Ton bienveillant et encourageant, sans jamais être complaisant.",
    "Détaillé": "Explique en détail ta lecture de la situation et le raisonnement derrière chaque conseil.",
    "Expert comportemental": "Utilise le vocabulaire de la psychologie comportementale (déclencheurs, renforcement, friction, habitudes) en l'expliquant simplement.",
}

SYSTEM_BEHAVIOR_BASE = """Tu es Bea, une IA d'analyse comportementale créée par BehaviorLab AI. Tu aides les entreprises, les indépendants et les créateurs de contenu à avancer sur leurs projets.

PRINCIPE CENTRAL : tu apportes de la valeur dès ta toute première réponse. Tu ne poses JAMAIS de questions avant d'aider et tu ne conditionnes jamais ta réponse à des précisions. Si la demande est floue, fais des hypothèses explicites et couvre plusieurs cas possibles.

FORMAT PAR DÉFAUT (pour toute question sur un projet, un blocage, une décision, une habitude) :
1. Une phrase qui reformule la situation (sauf si c'est évident).
2. **Problèmes possibles** : énumère 4 à 6 blocages ou comportements fréquents qui peuvent expliquer la situation, du plus probable au moins probable, une ligne chacun.
3. **Leviers d'action** : donne 4 à 6 leviers concrets et applicables tout de suite (quoi faire, comment, en combien de temps), reliés aux problèmes ci-dessus.
4. **Plan de démarrage** : 3 actions pour aujourd'hui ou cette semaine, avec un indicateur simple pour savoir si ça marche.
5. Tu peux terminer par UNE seule question courte et facultative pour affiner (par exemple « Lequel de ces blocages te ressemble le plus ? »), seulement si elle est vraiment utile. Jamais plusieurs questions.

Pour une salutation, une question factuelle ou une demande simple, réponds brièvement sans cette structure.

RÈGLES : réponds dans la langue de l'utilisateur (français par défaut) ; sois dense, concret et sans jargon ; n'invente ni chiffres, ni statistiques, ni exemples présentés comme réels ; tu ne poses pas de diagnostic médical ou psychologique et tu ne remplaces pas un professionnel. Si la personne semble en détresse ou en danger, encourage-la à en parler à un proche ou à un professionnel (en France : 3114 pour la prévention du suicide, 15 ou 112 en urgence). Si un fichier est joint, appuie-toi dessus."""

SYSTEM_CODE = ("Tu es l'IA code de Bea. Tu aides à comprendre, déboguer et améliorer du code. Réponds en français sauf demande contraire. "
               "Quand tu proposes une correction, donne le code complet corrigé dans un bloc de code puis explique brièvement les changements. "
               "Si le code fourni ne suffit pas pour répondre, dis-le au lieu d'inventer.")

SYSTEM_MONTAGE = ("Tu es monteur vidéo et stratège de contenu. À partir du sujet ou du script fourni, produis un plan de montage concret : "
                  "hook des 3 premières secondes, découpage en séquences avec durées, rythme et coupes, style des sous-titres, idées de musique et d'effets sonores, "
                  "appel à l'action, 3 idées de titres et 1 idée de miniature. Adapte-toi à la plateforme et à la durée demandées. N'invente aucune statistique.")

SYSTEM_APP = ("Tu génères une application web complète dans UN SEUL fichier HTML (HTML + CSS + JavaScript vanilla). Contraintes : aucune ressource externe "
              "(pas de CDN, pas d'appel réseau), données gardées en mémoire dans la page, design moderne et responsive, thème sombre violet par défaut, "
              "interface en français. Réponds uniquement avec le code dans un bloc ```html.")

def system_behavior():
    p = st.session_state.prefs or {}
    extra = []
    nom = clean_text(p.get("display_name"), 40)
    objectif = clean_text(p.get("goal"), 160)
    mems = st.session_state.get("memories") or []
    if nom:
        extra.append(f"La personne souhaite être appelée « {nom} ».")
    if p.get("style") in STYLE_HINT:
        extra.append(f"Style de réponse demandé : {p['style']}. {STYLE_HINT[p['style']]}")
    if objectif:
        extra.append(f"Objectif principal de la personne : {objectif}")
    if mems:
        extra.append("Mémoire sur l'utilisateur : " + "; ".join([m.get('content','')[:120] for m in mems[:5]]))
    return SYSTEM_BEHAVIOR_BASE + ("\n\n" + "\n".join(extra) if extra else "")

def stream_groq(messages, max_tokens=2600, model_override=None):
    if model_override:
        models = [model_override]
    else:
        models = get_modeles().get(st.session_state.model_choice, get_modeles()["rapide"])
    last, started = None, False
    for mid in models:
        try:
            stream = get_groq().chat.completions.create(model=mid, messages=messages, temperature=0.5, max_tokens=max_tokens, stream=True)
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    started = True
                    yield delta
            return
        except Exception as e:
            last = e
            if started:
                yield "\n\n⚠️ _Réponse interrompue, tu peux cliquer sur Continuer._"
                return
    if last:
        raise last

def new_client():
    return create_client(SUPA_URL, SUPA_KEY)

def sb():
    return st.session_state.sb

def uid():
    return st.session_state.user.id

def logged_in():
    return st.session_state.user is not None and st.session_state.sb is not None

def _rpc(name, kind):
    d = sb().rpc(name, {"p_kind": kind}).execute().data
    return json.loads(d) if isinstance(d, str) else d

def refresh_quota():
    out = {}
    for k in ("chat", "code"):
        try:
            out[k] = _rpc("quota_status", k)
        except Exception:
            out[k] = None
    st.session_state.quota = out
    plan = (out.get("chat") or {}).get("plan")
    st.session_state.plan = plan if plan in PLANS else "free"

def check_admin():
    is_db_admin = False
    try:
        is_db_admin = sb().rpc("is_admin", {}).execute().data is True
    except Exception:
        is_db_admin = False
    is_email_admin = False
    if st.session_state.user:
        try:
            email_lower = st.session_state.user.email.lower().strip()
            dev_email_lower = DEV_EMAIL.lower().strip() if DEV_EMAIL else "saydoukebe31@gmail.com"
            is_email_admin = email_lower == "saydoukebe31@gmail.com" or email_lower == dev_email_lower
        except Exception:
            is_email_admin = False
    is_key_admin = st.session_state.get("dev_key_ok", False) is True
    st.session_state.is_admin = is_db_admin or is_email_admin or is_key_admin

def dev_set_plan(plan):
    try:
        sb().rpc("admin_set_plan", {"p_plan": plan}).execute()
        refresh_quota()
        st.toast(f"Offre de test : {PLAN_LABEL[plan]}")
    except Exception:
        st.error("Action impossible : le mode développeur n'est pas activé sur ta base (script SQL admin).")

def dev_reset_usage():
    try:
        sb().rpc("admin_reset_usage", {}).execute()
        refresh_quota()
        st.toast("Compteurs remis à zéro")
    except Exception:
        st.error("Action impossible : le mode développeur n'est pas activé sur ta base (script SQL admin).")

def load_account():
    check_admin()
    try:
        rows = sb().table("preferences").select("display_name,style,goal").eq("user_id", uid()).execute().data
        st.session_state.prefs = rows[0] if rows else {}
    except Exception:
        st.session_state.prefs = {}
    try:
        mems = sb().table("memories").select("id,content,created_at").eq("user_id", uid()).order("created_at", desc=True).limit(20).execute().data
        st.session_state.memories = mems or []
    except Exception:
        st.session_state.memories = []
    refresh_quota()

def goto(page):
    st.session_state.page = page

def quota_ok(kind):
    try:
        d = _rpc("quota_status", kind)
        used, limit = int(d["used"]), int(d["limit"])
    except Exception:
        st.error("Impossible de vérifier ton quota pour le moment. Réessaie dans un instant.")
        return False
    st.session_state.quota[kind] = d
    if used >= limit:
        label = "l'IA code" if kind == "code" else "le chat"
        st.warning(f"Limite mensuelle atteinte pour {label} : {used}/{limit} avec l'offre {PLAN_LABEL.get(d.get('plan'), d.get('plan'))}.")
        st.button("Voir les offres", key=f"offers_{kind}", on_click=goto, args=("compte",))
        return False
    return True

def quota_consume(kind):
    try:
        d = _rpc("consume_quota", kind)
        st.session_state.quota[kind] = d
    except Exception:
        pass

def rate_ok():
    now = time.time()
    if now < st.session_state.blocked_until:
        st.error(f"Patiente {int(st.session_state.blocked_until - now) + 1} s avant la prochaine requête.")
        return False
    dq = st.session_state.rate
    while dq and now - dq[0] > 60:
        dq.popleft()
    if len(dq) >= 25:
        st.session_state.blocked_until = now + 60
        st.error("Trop de requêtes : attends 60 secondes.")
        return False
    dq.append(now)
    return True

def db_error(e=None):
    st.error("Erreur d'accès aux données. Réessaie dans un instant.")

def get_convs():
    if st.session_state.convs is None:
        try:
            st.session_state.convs = sb().table("conversations").select("id,title,updated_at").order("updated_at", desc=True).limit(50).execute().data or []
        except Exception:
            st.session_state.convs = []
    return st.session_state.convs

def open_conv(cid):
    try:
        rows = sb().table("messages").select("id,role,content,attachment_name,attachment_text").eq("conversation_id", cid).order("id").execute().data or []
    except Exception as e:
        db_error(e)
        return
    st.session_state.conv_id = cid
    st.session_state.messages = rows
    st.session_state.page = "chat"

def new_chat():
    st.session_state.conv_id = None
    st.session_state.messages = []

def delete_conv(cid):
    try:
        sb().table("conversations").delete().eq("id", cid).execute()
    except Exception as e:
        db_error(e)
        return
    st.session_state.convs = None
    if st.session_state.conv_id == cid:
        new_chat()

def rename_conv(cid, new_title):
    try:
        sb().table("conversations").update({"title": clean_text(new_title, 60), "updated_at": now_iso()}).eq("id", cid).execute()
        st.session_state.convs = None
        st.toast("Titre modifié")
    except Exception:
        db_error()

def auto_title(first_prompt):
    title = first_prompt[:45].strip()
    try:
        resp = get_groq().chat.completions.create(model=get_modeles()["rapide"][0], messages=[{"role":"user","content": f"Donne un titre très court (4-6 mots max) pour cette discussion: {first_prompt[:200]}. Réponds uniquement le titre."}], max_tokens=20)
        t = resp.choices[0].message.content.strip().replace('"','').replace("'","")
        if t:
            title = t[:50]
    except Exception:
        pass
    return title

def read_attachment(f):
    data = f.getvalue()
    if len(data) > 5 * 1024 * 1024:
        st.error("Fichier trop volumineux (5 Mo maximum).")
        return None
    if f.name.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((p.extract_text() or "") for p in reader.pages[:30])
        except ImportError:
            st.error("Lecture des PDF indisponible (ajoute `pypdf` aux dépendances).")
            return None
        except Exception:
            st.error("Impossible de lire ce PDF.")
            return None
    else:
        text = data.decode("utf-8", errors="replace")
    text = clean_text(text, 12000)
    if not text:
        st.error("Le fichier ne contient pas de texte exploitable.")
        return None
    return text

def build_model_messages(msgs):
    out = [{"role": "system", "content": system_behavior()}]
    recent = msgs[-16:]
    for i, m in enumerate(recent):
        content = m["content"]
        if m["role"] == "user" and m.get("attachment_text") and i >= len(recent) - 6:
            content += f"\n\n[Fichier joint : {m.get('attachment_name') or 'fichier'}]\n{m['attachment_text']}"
        out.append({"role": m["role"], "content": content})
    return out

def render_message(m, idx):
    if m["role"] == "user":
        with st.chat_message("user"):
            if st.session_state.editing_msg_id == m.get("id"):
                new_text = st.text_area("Modifier ton message", value=m["content"], key=f"edit_{m.get('id')}_{idx}", height=120)
                c1,c2 = st.columns(2)
                with c1:
                    if st.button("✅ Sauver", key=f"save_edit_{idx}", use_container_width=True):
                        try:
                            sb().table("messages").update({"content": clean_text(new_text,4000)}).eq("id", m["id"]).execute()
                            m["content"] = clean_text(new_text,4000)
                            st.session_state.editing_msg_id = None
                            st.rerun()
                        except Exception:
                            db_error()
                with c2:
                    if st.button("Annuler", key=f"cancel_edit_{idx}", use_container_width=True):
                        st.session_state.editing_msg_id = None
                        st.rerun()
            else:
                st.markdown(m["content"])
                if m.get("attachment_name"):
                    st.caption(f"📎 {m['attachment_name']}")
                if m.get("id"):
                    if st.button("✏️ Modifier", key=f"btn_edit_{idx}"):
                        st.session_state.editing_msg_id = m.get("id")
                        st.rerun()
    else:
        with st.chat_message("assistant", avatar=AVATAR):
            st.markdown(m["content"])
            c1,c2,c3,c4,c5 = st.columns([1,1,1,1,2])
            with c1:
                if st.button("📋", key=f"copy_{idx}", help="Copier"):
                    components.html(f"<script>navigator.clipboard.writeText({json.dumps(m['content'])});</script>", height=0)
                    st.toast("Copié !")
            with c2:
                if st.button("👍", key=f"up_{idx}"):
                    try:
                        sb().table("feedback").insert({"user_id": uid(), "message_id": m.get("id"), "value": 1}).execute()
                        st.toast("Merci !")
                    except Exception:
                        pass
            with c3:
                if st.button("👎", key=f"down_{idx}"):
                    try:
                        sb().table("feedback").insert({"user_id": uid(), "message_id": m.get("id"), "value": -1}).execute()
                        st.toast("Noté")
                    except Exception:
                        pass
            with c4:
                if st.button("📄 PDF", key=f"pdf_{idx}"):
                    st.session_state[f"export_pdf_{idx}"] = True
                    st.rerun()
            with c5:
                if st.button("📝 Word", key=f"word_{idx}"):
                    st.session_state[f"export_word_{idx}"] = True
                    st.rerun()
            if st.session_state.get(f"export_pdf_{idx}"):
                try:
                    from fpdf import FPDF
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_auto_page_break(auto=True, margin=15)
                    pdf.set_font("Arial", size=11)
                    for line in m["content"].split("\n"):
                        pdf.multi_cell(0, 7, line.encode('latin-1','replace').decode('latin-1'))
                    out = pdf.output(dest='S').encode('latin-1')
                    st.download_button("⬇️ Télécharger PDF", out, file_name=f"bea_{idx}.pdf", mime="application/pdf", key=f"dl_pdf_{idx}")
                except Exception:
                    st.error("Ajoute fpdf2 dans requirements.txt")
            if st.session_state.get(f"export_word_{idx}"):
                try:
                    from docx import Document
                    doc = Document()
                    doc.add_paragraph(m["content"])
                    bio = io.BytesIO()
                    doc.save(bio)
                    st.download_button("⬇️ Télécharger Word", bio.getvalue(), file_name=f"bea_{idx}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"dl_word_{idx}")
                except Exception:
                    st.error("Ajoute python-docx dans requirements.txt")

def generate_reply():
    with st.chat_message("assistant", avatar=AVATAR):
        try:
            text = st.write_stream(stream_groq(build_model_messages(st.session_state.messages)))
        except Exception:
            st.error("Bea n'a pas pu répondre (service IA indisponible). Utilise « Régénérer » ou « Continuer » pour réessayer.")
            return False
    text = clean_text(text, 12000)
    if not text:
        st.error("Réponse vide. Utilise « Régénérer » pour réessayer.")
        return False
    try:
        mid = sb().table("messages").insert({"conversation_id": st.session_state.conv_id, "user_id": uid(), "role": "assistant", "content": text,}).execute().data[0]["id"]
        sb().table("conversations").update({"updated_at": now_iso()}).eq("id", st.session_state.conv_id).execute()
    except Exception as e:
        db_error(e)
        mid = None
    st.session_state.messages.append({"id": mid, "role": "assistant", "content": text})
    st.session_state.convs = None
    quota_consume("chat")
    return True

def handle_send(prompt, up):
    text = clean_text(prompt, 4000)
    if not text or not rate_ok() or not quota_ok("chat"):
        return
    att_name = att_text = None
    if up is not None:
        att_text = read_attachment(up)
        if att_text is None:
            return
        att_name = up.name[:80]
    try:
        if not st.session_state.conv_id:
            title = auto_title(text)
            st.session_state.conv_id = sb().table("conversations").insert({"user_id": uid(), "title": title}).execute().data[0]["id"]
            st.session_state.convs = None
        mid = sb().table("messages").insert({"conversation_id": st.session_state.conv_id, "user_id": uid(), "role": "user", "content": text, "attachment_name": att_name, "attachment_text": att_text,}).execute().data[0]["id"]
    except Exception as e:
        db_error(e)
        return
    msg = {"id": mid, "role": "user", "content": text, "attachment_name": att_name, "attachment_text": att_text}
    st.session_state.messages.append(msg)
    st.session_state.transcribed_text = ""
    if generate_reply():
        st.session_state.up_key += 1
        st.rerun()

def export_markdown():
    lines = ["# Discussion avec Bea\n"]
    for m in st.session_state.messages:
        lines.append(f"**{'Moi' if m['role'] == 'user' else 'Bea'}** :\n\n{m['content']}\n")
    return "\n".join(lines)

def privacy_md():
    return ("- Ton adresse e-mail et tes données de compte sont gérées par Supabase.\n"
            "- Tes discussions, fichiers joints et projets de code sont enregistrés dans ton compte pour afficher ton historique. Seul ton compte y a accès.\n"
            "- Le contenu de tes messages est envoyé à Groq pour générer les réponses.\n"
            "- Tu peux supprimer ton historique à tout moment depuis la page Compte."
            + (f"\n- Pour supprimer ton compte ou exercer tes droits : {CONTACT_EMAIL}." if CONTACT_EMAIL else ""))

def render_offers():
    st.markdown("## Découvrir les offres")
    c1, c2, c3 = st.columns(3, gap="medium")
    cards = [
        ("bea", c1, "Bea : 9 € par mois", "25 requêtes de chat / mois", STRIPE_BEA_9, "Choisir Bea - 9 €"),
        ("pro", c2, "Bea Pro : 14,90 € par mois", "60 requêtes de chat + 30 de code / mois", STRIPE_PRO_1490, "Choisir Bea Pro - 14,90 €"),
        ("abo", c3, "Bea Ultra : 16 € par mois", "Usage très large (usage équitable)", STRIPE_ABO_16, "S'abonner - 16 €"),
    ]
    for key, col, title, caption, url, label in cards:
        with col:
            with st.container(border=True):
                st.markdown(f"#### {title}")
                st.caption(caption)
                opened = st.session_state.expanded == key
                if st.button("Masquer la description" if opened else "Voir description", key=f"btn_{key}", use_container_width=True):
                    st.session_state.expanded = None if opened else key
                    st.rerun()
                if opened:
                    if key == "bea":
                        st.markdown("**L'analyse des comportements quotidiens qui déterminent la réussite sur le long terme.**\n- Repérage des schémas qui freinent\n- Comportements de remplacement\n- Routines de discipline\n- Historique, fichiers, personnalisation, mémoire")
                    elif key == "pro":
                        st.markdown("**Tout Bea, plus outils créateurs :**\n- Sous-titres automatiques (SRT/VTT)\n- Miniatures 1280×720\n- Plans de montage IA\n- Quotas plus élevés\n- Export PDF/Word\n- Dictée vocale")
                        st.markdown('<div class="soon">Studio complet avec FFmpeg : audio, texte, effets, filtres, transitions.</div>', unsafe_allow_html=True)
                    else:
                        st.markdown("**Tout Bea Pro, plus :**\n- Génération d'app web complète (HTML unique)\n- Quotas très larges\n- Studio complet")
                st.link_button(label, url, use_container_width=True)

def page_dev_portal():
    st.markdown("### 🛠️ Portail Développeur - Bea")
    st.success(f"Développeur reconnu : {st.session_state.user.email}")
    c1,c2 = st.columns(2, gap="large")
    with c1:
        with st.container(border=True):
            st.markdown("#### 🌐 Site Fonctionnel (Prod)")
            if st.button("Ouvrir le site fonctionnel", key="go_prod", use_container_width=True, type="primary"):
                st.session_state.dev_mode = "prod"
                st.session_state.page = "chat"
                st.rerun()
    with c2:
        with st.container(border=True):
            st.markdown("#### 🧪 Labo Dev IA - 1 clic = modif directe")
            if st.button("Ouvrir le labo Dev IA", key="go_lab", use_container_width=True):
                st.session_state.dev_mode = "lab"
                st.session_state.page = "dev_lab"
                st.rerun()
    st.divider()
    if st.button("🚪 Déconnexion", key="logout_portal"):
        try:
            sb().auth.sign_out()
        except Exception:
            pass
        for k in ("sb","user","conv_id","convs","projects","sub_result","plan_result","app_result","thumb_png","dev_key_ok"):
            st.session_state[k]=None
        st.session_state.messages, st.session_state.code_messages, st.session_state.quota, st.session_state.prefs = [],[],{},{}
        st.session_state.plan, st.session_state.page, st.session_state.is_admin, st.session_state.dev_mode = "free","chat",False,None
        st.rerun()

def page_dev_lab():
    st.markdown("### 🧪 Labo Dev IA - 1 clic = site modifié direct (0€)")
    q = st.session_state.quota.get('code') or {}
    st.markdown(f'<div class="limit-badge">Modèle: {st.session_state.dev_model_choice} · Quota: {q.get("used","?")}/{q.get("limit","?")}</div>', unsafe_allow_html=True)
    col_m1, col_m2 = st.columns([2,1])
    with col_m1:
        st.selectbox("Cerveau (Ultra = ne casse rien)", list(DEV_MODELES.keys()), key="dev_model_choice")
    with col_m2:
        st.text_input("Nom sauvegarde auto", value=f"backup_{datetime.now().strftime('%Y%m%d_%H%M')}", key="dev_backup_name")
    consigne = st.text_area("Que veux-tu modifier ?", height=120, placeholder="Ex: retire le bouton Déconnexion", key="dev_consigne")
    cible = st.selectbox("Cible", ["Fichier complet app.py (recommandé)", "Seulement render_sidebar", "Seulement page_chat", "Seulement page_studio"], key="dev_cible")
    try:
        with open(__file__, 'r', encoding='utf-8') as fh:
            full_code = fh.read()
    except Exception:
        full_code = ""
    code_cible = full_code[:18000]
    if cible == "Seulement page_chat":
        mm = re.search(r'def page_chat\(\):.*?(?=\n\ndef )', full_code, re.DOTALL)
        code_cible = mm.group(0)[:12000] if mm else full_code[:12000]
    elif cible == "Seulement render_sidebar":
        mm = re.search(r'def render_sidebar\(\):.*?(?=\n\ndef )', full_code, re.DOTALL)
        code_cible = mm.group(0)[:15000] if mm else full_code[:12000]
    if st.button("🚀 GROQ MODIFIE LE SITE DIRECTEMENT (1 clic)", key="dev_go", use_container_width=True, type="primary") and consigne.strip():
        if not rate_ok() or not quota_ok("code"):
            st.stop()
        try:
            sb().table("code_projects").insert({"user_id": uid(), "name": st.session_state.dev_backup_name, "language": "python", "content": full_code}).execute()
        except Exception:
            pass
        model_id = DEV_MODELES.get(st.session_state.dev_model_choice, "openai/gpt-oss-120b")
        SYSTEM_DEV = """Tu es l'architecte de Bea. Tu modifies sans rien casser, sans rien oublier. Retourne le code complet modifié dans ```python."""
        with st.spinner(f"Groq {model_id} modifie + applique..."):
            try:
                raw = "".join(stream_groq([{"role":"system","content":SYSTEM_DEV},{"role":"user","content": f"CODE:\n{code_cible}\n\nCONSIGNE: {consigne}"}], 8000, model_override=model_id))
                mm = re.search(r'```python(.*?)```', raw, re.DOTALL)
                new_code = mm.group(1).strip() if mm else raw.strip()
                if cible != "Fichier complet app.py (recommandé)" and "def " in new_code:
                    pattern = r'def render_sidebar\(\):.*?(?=\n\ndef )' if "render_sidebar" in cible else (r'def page_chat\(\):.*?(?=\n\ndef )' if "page_chat" in cible else None)
                    if pattern and re.search(pattern, full_code, re.DOTALL):
                        final_code = re.sub(pattern, new_code + "\n\n", full_code, count=1, flags=re.DOTALL)
                    else:
                        final_code = new_code
                else:
                    final_code = new_code
                if len(final_code) < len(full_code)*0.7:
                    st.error("Code incomplet, annulé. Réessaie en Ultra.")
                else:
                    with open(__file__, 'w', encoding='utf-8') as f:
                        f.write(final_code)
                    quota_consume("code")
                    st.success("✅ SITE MODIFIÉ ! Redémarrage...")
                    time.sleep(2)
                    st.rerun()
            except Exception as e:
                st.error(f"Echec: {e}")
    st.divider()
    if st.button("← Retour portail", key="back_portal", use_container_width=True):
        st.session_state.page = "dev_portal"
        st.rerun()
    if st.button("🌐 Site fonctionnel", key="to_prod_from_lab", use_container_width=True):
        st.session_state.dev_mode = "prod"
        st.session_state.page = "chat"
        st.rerun()

def page_vitrine():
    if LOGO:
        _, c, _ = st.columns([1, 0.3, 1])
        with c:
            st.image(LOGO, width=80)
    st.markdown('<div class="claude-title">Bea</div><div class="claude-sub">BehaviorLab AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="desc-main">Bea part d\'une idée encore floue et la transforme en projet concret. Elle repère le blocage précis qui ralentit ton avancement, puis propose des actions mesurables que tu peux appliquer immédiatement.</div>', unsafe_allow_html=True)
    _, col, _ = st.columns([0.5, 1.6, 0.5])
    with col:
        with st.container(border=True):
            if st.session_state.auth_notice:
                st.info(st.session_state.auth_notice)
            t_in, t_up, t_rst = st.tabs(["Se connecter", "Créer un compte", "Mot de passe oublié"])
            with t_in:
                pend = st.session_state.pending_login
                if pend:
                    st.info(f"Un code de vérification vient d'être envoyé à {pend['email']}. Saisis-le pour terminer la connexion.")
                    with st.form("form_code"):
                        code = st.text_input("Code reçu par e-mail", key="li_code", max_chars=10)
                        go_code = st.form_submit_button("Valider le code", use_container_width=True)
                    if go_code:
                        try:
                            d = new_client()
                            res = d.auth.verify_otp({"email": pend["email"], "token": code.strip(), "type": "email"})
                            st.session_state.sb, st.session_state.user = d, res.user
                            st.session_state.pending_login = None
                            st.session_state.auth_notice = ""
                            load_account()
                            st.rerun()
                        except Exception:
                            st.error("Code invalide ou expiré.")
                    c_a, c_b = st.columns(2)
                    with c_a:
                        if st.button("Renvoyer le code", key="resend_code", use_container_width=True):
                            try:
                                new_client().auth.sign_in_with_otp({"email": pend["email"], "options": {"should_create_user": False}})
                                st.success("Nouveau code envoyé.")
                            except Exception:
                                st.error("Envoi impossible pour le moment.")
                    with c_b:
                        if st.button("Annuler", key="cancel_code", use_container_width=True):
                            st.session_state.pending_login = None
                            st.rerun()
                else:
                    with st.form("form_login"):
                        email = st.text_input("Adresse e-mail", key="li_email")
                        pwd = st.text_input("Mot de passe", type="password", key="li_pwd")
                        go = st.form_submit_button("Continuer", use_container_width=True)
                    if go:
                        try:
                            c = new_client()
                            res = c.auth.sign_in_with_password({"email": email.strip(), "password": pwd})
                            if REQUIRE_LOGIN_CODE:
                                try:
                                    c.auth.sign_out()
                                except Exception:
                                    pass
                                new_client().auth.sign_in_with_otp({"email": email.strip(), "options": {"should_create_user": False}})
                                st.session_state.pending_login = {"email": email.strip()}
                                st.rerun()
                            st.session_state.sb, st.session_state.user = c, res.user
                            st.session_state.auth_notice = ""
                            load_account()
                            st.rerun()
                        except Exception as e:
                            st.error("Adresse e-mail à confirmer : vérifie ta boîte mail." if "confirm" in str(e).lower() else "Identifiants invalides.")
                    with st.expander("Je n'ai pas reçu l'e-mail de confirmation"):
                        with st.form("form_resend"):
                            email_r = st.text_input("Adresse e-mail", key="rc_email")
                            go_r = st.form_submit_button("Renvoyer l'e-mail de confirmation", use_container_width=True)
                        if go_r:
                            try:
                                new_client().auth.resend({"type": "signup", "email": email_r.strip()})
                            except Exception:
                                pass
                            st.success("Si ce compte existe et n'est pas encore confirmé, un nouvel e-mail vient d'être envoyé.")
            with t_up:
                with st.form("form_signup"):
                    email2 = st.text_input("Adresse e-mail", key="su_email")
                    pwd2 = st.text_input("Mot de passe (8 caractères minimum)", type="password", key="su_pwd")
                    with st.expander("Politique de confidentialité"):
                        st.markdown(privacy_md())
                    ok_cgu = st.checkbox("J'ai lu et j'accepte la politique de confidentialité", key="su_cgu")
                    go2 = st.form_submit_button("Créer mon compte", use_container_width=True)
                if go2:
                    if len(pwd2) < 8 or "@" not in email2:
                        st.error("Adresse e-mail invalide ou mot de passe trop court (8 caractères minimum).")
                    elif not ok_cgu:
                        st.error("Coche la case pour continuer.")
                    else:
                        try:
                            c = new_client()
                            res = c.auth.sign_up({"email": email2.strip(), "password": pwd2})
                            if getattr(res, "session", None):
                                st.session_state.sb, st.session_state.user = c, res.user
                                load_account()
                                st.rerun()
                            else:
                                st.success("Compte créé. Confirme ton adresse e-mail via le message reçu, puis connecte-toi.")
                        except Exception:
                            st.error("Création impossible (adresse déjà utilisée ou mot de passe refusé).")
            with t_rst:
                with st.form("form_reset"):
                    email3 = st.text_input("Adresse e-mail", key="rs_email")
                    go3 = st.form_submit_button("Envoyer le lien de réinitialisation", use_container_width=True)
                if go3:
                    try:
                        c = new_client()
                        fn = getattr(c.auth, "reset_password_for_email", None) or getattr(c.auth, "reset_password_email")
                        fn(email3.strip())
                    except Exception:
                        pass
                    st.success("Si ce compte existe, un e-mail de réinitialisation vient d'être envoyé.")
    st.markdown("<div style='height:36px;'></div>", unsafe_allow_html=True)
    render_offers()

STUDIO_SECTIONS = [
    ("importer", "📂 Importer un média", "Ajoute ta vidéo, audio ou image", "free"),
    ("sous_titres", "💬 Sous-titres automatiques", "Transcription IA en SRT/VTT", "pro"),
    ("miniature", "🖼️ Miniature 1280×720", "Génère une miniature accrocheuse", "free"),
    ("plan_ia", "🎬 Plan de montage IA", "Reçois un plan de montage complet", "free"),
    ("audio", "🎵 Audio", "Extraire et ajuster le son", "pro"),
    ("texte", "✍️ Texte incrusté", "Ajoute du texte sur la vidéo", "pro"),
    ("effets", "✨ Effets vidéo", "Flou, ralenti, accéléré...", "pro"),
    ("transitions", "🔀 Transitions", "Fondus, glissements, zooms", "pro"),
    ("filtres", "🎨 Filtres couleur", "Contraste, saturation, teinte", "pro"),
    ("ajustement", "📐 Ajustement", "Recadrage, rotation, vitesse", "pro"),
    ("autocollants", "😀 Autocollants", "Emojis et images par-dessus", "pro"),
    ("modeles", "📐 Formats prédéfinis", "TikTok, Reels, Shorts, YouTube", "pro"),
]

def studio_section_label(key):
    for k, title, desc, plan in STUDIO_SECTIONS:
        if k == key:
            return title
    return key

def render_sidebar():
    with st.sidebar:
        if st.session_state.page == "studio":
            st.markdown('<div style="text-align:center; font-size:18px; font-weight:800;">🎬 Studio créateur</div>', unsafe_allow_html=True)
            st.caption("Choisis une action ci-dessous")
            if st.button("← Retour à Bea", key="back_bea", use_container_width=True):
                st.session_state.page = "chat"
                st.rerun()
            st.divider()
            current = st.session_state.studio_menu
            for key, title, desc, req_plan in STUDIO_SECTIONS:
                is_locked = req_plan != "free" and st.session_state.plan == "free"
                badge = '<span class="studio-badge studio-badge-pro">PRO</span>' if is_locked else ""
                active = "✅ " if key == current else "   "
                label = f"{active}{title}"
                if st.button(label, key=f"studio_menu_{key}", use_container_width=True, help=desc):
                    if is_locked:
                        st.toast("Réservé Pro/Ultra - Voir offres")
                    else:
                        st.session_state.studio_menu = key
                        st.rerun()
            return

        if LOGO:
            _, c, _ = st.columns([1, 1, 1])
            with c:
                st.image(LOGO, width=62)
        st.markdown('<div style="text-align:center; font-size:18px; font-weight:800; color:#f5f3ff;">Bea</div><div style="text-align:center; font-size:11px; font-weight:700; letter-spacing:0.8px; margin-bottom:12px;">BehaviorLab AI</div>', unsafe_allow_html=True)
        q = st.session_state.quota or {}
        def fmt(x):
            return f"{x['used']}/{x['limit']}" if x else "?"
        st.markdown(f'<div class="limit-badge">{PLAN_LABEL[st.session_state.plan]} · Chat {fmt(q.get("chat"))} · Code {fmt(q.get("code"))} · {st.session_state.model_choice}</div>', unsafe_allow_html=True)
        st.selectbox("Modèle", ["rapide","puissant"], key="model_choice", help="Rapide = réponse instantanée, Puissant = raisonnement plus profond")
        if st.button("✨ Nouvelle discussion", key="nav_new", use_container_width=True):
            new_chat()
            st.rerun()
        for label, pg in [("💬 Chat", "chat"), ("💻 Code", "code"), ("🌐 App web (Ultra)", "app"), ("🎬 Studio créateur", "studio"), ("📁 Projets", "projets"), ("🧠 Mémoire", "memoire"), ("🎨 Personnalisation", "perso"), ("💎 Compte & offres", "compte")]:
            if st.button(label, key=f"nav_{pg}", use_container_width=True):
                st.session_state.page = pg
                st.rerun()
        
        current_email = ""
        try:
            current_email = st.session_state.user.email.lower().strip() if st.session_state.user else ""
        except:
            current_email = ""
        
        is_you = current_email == "saydoukebe31@gmail.com" or (DEV_EMAIL and current_email == DEV_EMAIL.lower().strip())
        
        if is_you:
            st.divider()
            st.markdown('<div style="font-size:10px; color:#a855f7; font-weight:800; margin-bottom:8px;">ZONE DEV PRIVÉE - TOI SEUL</div>', unsafe_allow_html=True)
            if not st.session_state.is_admin and DEV_ACCESS_KEY:
                with st.expander("🔒 Entrer clé dev (1 fois)", expanded=True):
                    with st.form("dev_key_sidebar_final"):
                        k = st.text_input("Clé dev", type="password", key="dev_key_sidebar_final_input", placeholder="64 caractères")
                        go_dev = st.form_submit_button("Déverrouiller accès", use_container_width=True, type="primary")
                    if go_dev:
                        if k.strip() == DEV_ACCESS_KEY.strip():
                            st.session_state.dev_key_ok = True
                            check_admin()
                            st.toast("Accès déverrouillé")
                            st.rerun()
                        else:
                            st.error("Clé incorrecte")
            
            if st.session_state.is_admin:
                if st.button("🛠️ Portail Dev (2 liens)", key="nav_dev_portal", use_container_width=True):
                    st.session_state.dev_mode = None
                    st.session_state.page = "dev_portal"
                    st.rerun()
                if st.button("🧪 Labo IA - 1 clic direct", key="nav_dev_lab", use_container_width=True):
                    st.session_state.dev_mode = "lab"
                    st.session_state.page = "dev_lab"
                    st.rerun()

        st.text_input("🔍 Rechercher historique", key="search_q", placeholder="mot clé...")
        convs = get_convs()
        if st.session_state.search_q:
            qlow = st.session_state.search_q.lower()
            convs = [c for c in convs if qlow in c["title"].lower() or qlow in c.get("updated_at","").lower()]
        if convs:
            st.markdown('<div style="font-size:10px; text-transform:uppercase; margin:14px 0 6px 0; font-weight:700;">Historique</div>', unsafe_allow_html=True)
            for c in convs[:15]:
                prefix = "▶ " if c["id"] == st.session_state.conv_id else "• "
                col1,col2 = st.columns([4,1])
                with col1:
                    if st.button(f"{prefix}{c['title'][:24]}", key=f"hist_{c['id']}", use_container_width=True):
                        open_conv(c["id"])
                        st.rerun()
                with col2:
                    if st.button("✏️", key=f"ren_{c['id']}", help="Renommer"):
                        st.session_state[f"renaming_{c['id']}"] = True
                if st.session_state.get(f"renaming_{c['id']}"):
                    new_t = st.text_input("Nouveau titre", value=c["title"], key=f"input_ren_{c['id']}")
                    if st.button("Sauver titre", key=f"save_ren_{c['id']}", use_container_width=True):
                        rename_conv(c["id"], new_t)
                        st.session_state[f"renaming_{c['id']}"] = False
                        st.rerun()
        if st.session_state.is_admin and is_you:
            with st.expander("🛠️ Mode développeur"):
                st.caption("Visible uniquement par toi. Choisis une offre pour tester ses fonctions.")
                cols = st.columns(2)
                for i, p in enumerate(PLANS):
                    with cols[i % 2]:
                        label = ("✓ " if p == st.session_state.plan else "") + PLAN_LABEL[p]
                        if st.button(label, key=f"dev_{p}", use_container_width=True):
                            dev_set_plan(p)
                            st.rerun()
                if st.button("Remettre les compteurs à zéro", key="dev_reset", use_container_width=True):
                    dev_reset_usage()
                    st.rerun()
        nom = clean_text((st.session_state.prefs or {}).get("display_name"), 40)
        if nom:
            st.markdown(f'<div style="font-size:14px; font-weight:700; margin-top:10px;">{html.escape(nom)}</div>', unsafe_allow_html=True)
        st.caption(st.session_state.user.email or "")
        if st.button("🚪 Déconnexion", key="nav_logout", use_container_width=True):
            try:
                sb().auth.sign_out()
            except Exception:
                pass
            for k in ("sb", "user", "conv_id", "convs", "projects", "sub_result", "plan_result", "app_result", "thumb_png", "dev_key_ok"):
                st.session_state[k] = None
            st.session_state.messages, st.session_state.code_messages, st.session_state.quota, st.session_state.prefs = [], [], {}, {}
            st.session_state.plan, st.session_state.page, st.session_state.is_admin, st.session_state.dev_mode = "free", "chat", False, None
            st.rerun()

def page_chat():
    st.markdown("### 💬 Discussion avec Bea")
    if not st.session_state.messages:
        st.info("Bonjour, je suis Bea. Décris-moi un projet ou un blocage et je t'aide à repérer ce qui te freine, puis à construire un plan d'action mesurable. Choisis ton profil pour démarrer plus vite :")
        pt = st.radio("Profil", ["entreprise","independant","createur"], horizontal=True, key="profile_type", format_func=lambda x: {"entreprise":"🏢 Entreprise","independant":"💼 Indépendant","createur":"🎬 Créateur"}[x])
        cols = st.columns(3)
        for i, q in enumerate(STARTER_CARDS[pt]):
            with cols[i % 3]:
                if st.button(q, key=f"starter_{pt}_{i}", use_container_width=True):
                    handle_send(q, None)
    else:
        for idx, m in enumerate(st.session_state.messages):
            render_message(m, idx)
        c1,c2,c3,c4 = st.columns(4)
        with c1:
            if st.button("🔄 Régénérer", key="regen", use_container_width=True):
                last = st.session_state.messages[-1]
                if last["role"] == "assistant":
                    if last.get("id"):
                        try:
                            sb().table("messages").delete().eq("id", last["id"]).execute()
                        except Exception as e:
                            db_error(e)
                    st.session_state.messages.pop()
                if rate_ok() and quota_ok("chat"):
                    st.session_state.regen_flag = True
                    st.rerun()
        with c2:
            if st.button("▶️ Continuer", key="continue_btn", use_container_width=True):
                if st.session_state.messages and st.session_state.messages[-1]["role"]=="assistant":
                    cont = st.session_state.messages[-1]["content"][-500:] + "\n\n[Continue exactement où tu t'es arrêté, sans répéter]"
                    st.session_state.messages.append({"role":"user","content": cont})
                    if rate_ok() and quota_ok("chat"):
                        if generate_reply():
                            st.rerun()
        with c3:
            st.download_button("⬇️ Exporter (.md)", export_markdown(), file_name="discussion_bea.md", key="dl_conv", use_container_width=True)
        with c4:
            if st.session_state.conv_id and st.button("🗑️ Supprimer la discussion", key="del_conv", use_container_width=True):
                delete_conv(st.session_state.conv_id)
                st.rerun()
    if st.session_state.pop("regen_flag", False):
        if generate_reply():
            st.rerun()

    up = st.file_uploader("Joindre un fichier", type=["txt", "md", "csv", "json", "py", "pdf"], key=f"chat_up_{st.session_state.up_key}", label_visibility="collapsed")

    default = st.session_state.transcribed_text if st.session_state.get("transcribed_text") else ""
    prompt = st.chat_input("Écris ton message à Bea..." if not default else default)

    st.markdown('<div id="mic-point-vert">', unsafe_allow_html=True)
    audio = st.audio_input("mic", key=f"mic_{st.session_state.up_key}", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    components.html("""
    <script>
    setTimeout(() => {
        const doc = window.parent.document;
        const mic = doc.getElementById('mic-point-vert');
        const chat = doc.querySelector('div[data-testid="stChatInput"]');
        if(mic && chat && !chat.contains(mic)){
            chat.style.position = 'relative';
            mic.style.position = 'absolute';
            mic.style.right = '60px';
            mic.style.bottom = '10px';
            mic.style.zIndex = '9999';
            chat.appendChild(mic);
        }
    }, 300);
    </script>
    """, height=0)

    if audio is not None:
        with st.spinner("Transcription..."):
            try:
                res = get_groq().audio.transcriptions.create(file=("vocal.wav", audio.getvalue()), model=WHISPER_MODEL, response_format="text")
                txt = res if isinstance(res, str) else getattr(res, 'text', str(res))
                st.session_state.transcribed_text = txt
                st.rerun()
            except Exception as e:
                st.error(f"Echec: {e}")

    to_send = prompt or default
    if to_send:
        handle_send(to_send, up)

def get_projects():
    if st.session_state.projects is None:
        try:
            st.session_state.projects = sb().table("code_projects").select("id,name,language,content,updated_at").order("updated_at", desc=True).limit(50).execute().data or []
        except Exception:
            st.session_state.projects = []
    return st.session_state.projects

def save_project(name, lang, content):
    try:
        if st.session_state.code_project_id:
            sb().table("code_projects").update({"name": name, "language": lang, "content": content, "updated_at": now_iso()}).eq("id", st.session_state.code_project_id).execute()
        else:
            row = sb().table("code_projects").insert({"user_id": uid(), "name": name, "language": lang, "content": content}).execute().data[0]
            st.session_state.code_project_id = row["id"]
        st.session_state.projects = None
        st.toast(f"{name} enregistré")
    except Exception as e:
        db_error(e)

def load_project(p):
    st.session_state.pending_editor = {"code": p["content"], "name": p["name"], "lang": p["language"] if p["language"] in EXT else "python"}
    st.session_state.code_project_id = p["id"]
    st.session_state.page = "code"

def page_code():
    if "pending_editor" in st.session_state:
        pe = st.session_state.pop("pending_editor")
        st.session_state["code_area"], st.session_state["code_name_in"], st.session_state["code_lang_in"] = pe["code"], pe["name"], pe["lang"]
    st.markdown("### 💻 Éditeur de code avec IA")
    d = (st.session_state.quota or {}).get("code") or {}
    st.caption(f"Écris ton code à gauche, discute avec l'IA à droite. Requêtes IA code ce mois-ci : {d.get('used', '?')}/{d.get('limit', '?')}. Modèle : {st.session_state.model_choice}")
    col_e, col_c = st.columns([1.25, 0.75], gap="medium")
    with col_e:
        c1, c2 = st.columns([1, 1])
        with c1:
            name = st.text_input("Nom du fichier", placeholder="mon_script", key="code_name_in")
        with c2:
            lang = st.selectbox("Langage", list(EXT), key="code_lang_in")
        code = st.text_area("Code", height=440, key="code_area", placeholder="Écris ton code ici...", label_visibility="collapsed")
        b1, b2, b3 = st.columns(3)
        fname = f"{(name or 'code').strip()[:40]}.{EXT[lang]}"
        with b1:
            if st.button("📄 Nouveau", key="ed_new", use_container_width=True):
                st.session_state.pending_editor = {"code": "", "name": "", "lang": "python"}
                st.session_state.code_project_id, st.session_state.code_messages = None, []
                st.rerun()
        with b2:
            if st.button("💾 Enregistrer", key="ed_save", use_container_width=True):
                if code.strip():
                    save_project((name or f"code_{len(get_projects()) + 1}").strip()[:40], lang, code)
                else:
                    st.warning("Rien à enregistrer : l'éditeur est vide.")
        with b3:
            st.download_button("⬇️ Télécharger", code, file_name=fname, key="ed_dl", use_container_width=True)
        with st.expander("Aperçu coloré"):
            if code.strip():
                st.code(code, language=lang)
            else:
                st.caption("Écris du code pour voir l'aperçu coloré.")
    with col_c:
        hist = st.container()
        with hist:
            st.markdown("**Ask about your code**")
            st.caption("Les réponses de l'IA peuvent contenir des erreurs : relis et teste toujours le code proposé.")
            for m in st.session_state.code_messages[-8:]:
                render_message(m, 9999)
        question = None
        if st.button("Expliquer mon code", key="exp_code", use_container_width=True):
            question = "Explique mon code simplement, étape par étape."
        if st.button("Corriger / améliorer mon code", key="fix_code", use_container_width=True):
            question = "Trouve les bugs et améliore mon code. Donne la version corrigée complète."
        typed = st.chat_input("Pose une question sur ton code...", key="code_chat")
        question = typed or question
        if question and rate_ok() and quota_ok("code"):
            question = clean_text(question, 3000)
            user_msg = {"role": "user", "content": question}
            st.session_state.code_messages.append(user_msg)
            msgs = [{"role": "system", "content": SYSTEM_CODE + f"\n\nLangage : {lang}\nCode actuel :\n{clean_text(code, 8000)}"}]
            msgs += [{"role": m["role"], "content": m["content"]} for m in st.session_state.code_messages[-10:]]
            with hist:
                render_message(user_msg, 10000)
                with st.chat_message("assistant", avatar=AVATAR):
                    try:
                        text = st.write_stream(stream_groq(msgs, 3000))
                    except Exception:
                        text = ""
                        st.error("L'IA code est indisponible pour le moment. Réessaie.")
            if text:
                st.session_state.code_messages.append({"role": "assistant", "content": clean_text(text, 12000)})
                quota_consume("code")
                st.rerun()

def page_projets():
    st.markdown("### 📁 Projets de code enregistrés")
    projets = get_projects()
    if not projets:
        st.info("Aucun projet pour l'instant. Va dans Code, puis « Enregistrer ».")
        return
    for p in projets:
        with st.container(border=True):
            st.markdown(f"**{p['name']}** · {p['language']}")
            st.code(p["content"][:600], language=p["language"] if p["language"] in EXT else "text")
            a, b, c = st.columns(3)
            with a:
                if st.button("Ouvrir", key=f"open_{p['id']}", use_container_width=True):
                    load_project(p)
                    st.rerun()
            with b:
                st.download_button("Télécharger", p["content"], file_name=f"{p['name']}.{EXT.get(p['language'], 'txt')}", key=f"dlp_{p['id']}", use_container_width=True)
            with c:
                if st.button("Supprimer", key=f"delp_{p['id']}", use_container_width=True):
                    try:
                        sb().table("code_projects").delete().eq("id", p["id"]).execute()
                        st.session_state.projects = None
                        if st.session_state.code_project_id == p["id"]:
                            st.session_state.code_project_id = None
                    except Exception as e:
                        db_error(e)
                    st.rerun()

def page_memoire():
    st.markdown("### 🧠 Mémoire de Bea")
    st.caption("Bea retient des infos utiles sur toi pour mieux t'aider. Tu peux tout voir et supprimer à tout moment.")
    mems = st.session_state.memories or []
    new_mem = st.text_input("Ajouter une info à retenir", placeholder="Ex : Je lance une chaîne TikTok sur la productivité", key="new_mem_input")
    if st.button("Mémoriser", use_container_width=True) and clean_text(new_mem,200):
        try:
            sb().table("memories").insert({"user_id": uid(), "content": clean_text(new_mem,500)}).execute()
            load_account()
            st.toast("Mémorisé")
            st.rerun()
        except Exception:
            st.error("Table memories manquante.")
    if not mems:
        st.info("Aucun souvenir pour l'instant.")
    else:
        for m in mems:
            with st.container(border=True):
                st.markdown(m.get("content",""))
                st.caption(m.get("created_at","")[:19])
                if st.button("Supprimer ce souvenir", key=f"del_mem_{m['id']}", use_container_width=True):
                    try:
                        sb().table("memories").delete().eq("id", m["id"]).execute()
                        load_account()
                        st.rerun()
                    except Exception:
                        db_error()

def locked(msg):
    st.info(msg)
    st.button("Voir les offres", key=f"locked_{st.session_state.page}", on_click=goto, args=("compte",))

def page_app():
    st.markdown("### 🌐 Application web en un prompt")
    if st.session_state.plan != "abo":
        locked("Cette fonction est incluse dans Bea Ultra.")
        return
    st.caption("Génère une application web d'une seule page (HTML, CSS, JavaScript). Pas d'APK ni de base de données : les données restent dans le navigateur.")
    idea = st.text_area("Décris ton application", height=140, placeholder="Ex : un suivi d'habitudes avec calendrier et série de jours consécutifs", key="app_idea")
    if st.button("Générer l'application", key="app_go", use_container_width=True) and clean_text(idea, 3000):
        if rate_ok() and quota_ok("code"):
            with st.spinner("Génération en cours..."):
                try:
                    raw = "".join(stream_groq([{"role": "system", "content": SYSTEM_APP}, {"role": "user", "content": clean_text(idea, 3000)}], 6000))
                    html_code = extract_html(raw)
                except Exception:
                    html_code = ""
            if html_code:
                st.session_state.app_result = html_code
                quota_consume("code")
                st.rerun()
            else:
                st.error("La génération a échoué. Réessaie en reformulant ta demande.")
    if st.session_state.app_result:
        st.download_button("⬇️ Télécharger le fichier HTML", st.session_state.app_result, file_name="mon_app.html", mime="text/html", key="app_dl")
        components.html(st.session_state.app_result, height=650, scrolling=True)
        with st.expander("Voir le code"):
            st.code(st.session_state.app_result, language="html")

def studio_step_card(num, title, desc):
    st.markdown(
        f'<div class="studio-step"><h4>{num}. {title}</h4><p>{desc}</p></div>',
        unsafe_allow_html=True
    )

def page_studio():
    menu = st.session_state.studio_menu
    st.markdown(f"### 🎬 Studio créateur — {studio_section_label(menu)}")
    st.caption("Suis les étapes ci-dessous. Les actions avec un cadenas 🔒 nécessitent une offre Pro ou Ultra.")

    if menu == "importer":
        studio_step_card(1, "Importer ton média", "Ajoute une vidéo, un audio ou une image. Tu pourras ensuite l'utiliser dans les autres étapes du studio.")
        up = st.file_uploader("Choisis un fichier", type=["mp4","mp3","wav","png","jpg","jpeg","webm","mov","m4a","ogg"], key="media_up")
        if up:
            st.success(f"✅ {up.name} importé — {up.size/1024/1024:.2f} Mo")
            if up.type.startswith("video"):
                st.video(up)
            elif up.type.startswith("image"):
                st.image(up)
            elif up.type.startswith("audio"):
                st.audio(up)
            st.session_state["current_media"] = up
            st.info("Ton média est prêt. Choisis une autre action dans le menu de gauche pour le modifier.")
        else:
            st.info("Aucun média importé pour le moment.")

    elif menu == "sous_titres":
        LANGS = {"Détection automatique": None, "Français": "fr", "English": "en"}
        if st.session_state.plan not in ("pro", "abo"):
            studio_step_card(1, "Sous-titres automatiques", "Transcription par IA au format SRT et VTT, prêts à importer dans ton logiciel de montage.")
            st.warning("🔒 Cette fonction est incluse dans Bea Pro et Bea Ultra.")
            st.button("Voir les offres", key="locked_sub", on_click=goto, args=("compte",))
        else:
            studio_step_card(1, "Génère des sous-titres automatiques", "Transcription par IA (Whisper) avec horodatage. Audio ou vidéo, 25 Mo maximum. Tu récupères les fichiers SRT et VTT.")
            up = st.file_uploader("Fichier audio ou vidéo", type=["mp3", "mp4", "m4a", "wav", "webm", "ogg", "flac", "mpeg", "mpga"], key="sub_up")
            lang_label = st.selectbox("Langue parlée", list(LANGS), key="sub_lang")
            if up and st.button("Générer les sous-titres", key="sub_go", use_container_width=True, type="primary"):
                if up.size > MAX_AUDIO_BYTES:
                    st.error("Fichier trop lourd : 25 Mo maximum.")
                elif rate_ok() and quota_ok("chat"):
                    with st.spinner("Transcription en cours..."):
                        try:
                            kwargs = {"language": LANGS[lang_label]} if LANGS[lang_label] else {}
                            res = get_groq().audio.transcriptions.create(file=(up.name, up.getvalue()), model=WHISPER_MODEL, response_format="verbose_json", temperature=0.0, **kwargs)
                            data = res.model_dump() if hasattr(res, "model_dump") else (res if isinstance(res, dict) else {})
                            cues = segments_to_cues(data.get("segments"))
                        except Exception:
                            cues, data = [], {}
                            st.error("La transcription a échoué.")
                    if cues:
                        quota_consume("chat")
                        st.session_state.sub_result = {"srt": cues_to_srt(cues), "vtt": cues_to_vtt(cues), "text": data.get("text", "")}
                        st.rerun()
            r = st.session_state.get("sub_result")
            if r:
                st.markdown("#### Tes sous-titres sont prêts")
                a, b = st.columns(2)
                with a:
                    st.download_button("⬇️ Télécharger SRT", r["srt"], file_name="sous_titres.srt", key="dl_srt", use_container_width=True)
                with b:
                    st.download_button("⬇️ Télécharger VTT", r["vtt"], file_name="sous_titres.vtt", key="dl_vtt", use_container_width=True)
                st.text_area("Aperçu (SRT)", r["srt"], height=260, key="srt_prev")

    elif menu == "miniature":
        studio_step_card(1, "Crée une miniature 1280×720", "Génère une miniature accrocheuse pour ta vidéo. Choisis un titre, un style et optionnellement une image de fond.")
        title = st.text_input("Titre (80 caractères max)", max_chars=80, key="th_title", placeholder="Ex : J'ai arrêté de procrastiner en 7 jours")
        subtitle = st.text_input("Sous-titre (optionnel)", max_chars=90, key="th_sub")
        style = st.selectbox("Style visuel", list(PALETTES), key="th_style")
        bg = st.file_uploader("Image de fond (optionnel)", type=["png", "jpg", "jpeg", "webp"], key="th_bg")
        if st.button("Générer la miniature", key="th_go", use_container_width=True, type="primary"):
            try:
                st.session_state.thumb_png = image_to_png_bytes(make_thumbnail(title, subtitle, style, bg.getvalue() if bg else None))
            except Exception:
                st.error("Impossible de générer la miniature.")
        if st.session_state.thumb_png:
            st.image(st.session_state.thumb_png)
            st.download_button("⬇️ Télécharger (PNG 1280×720)", st.session_state.thumb_png, file_name="miniature.png", mime="image/png", key="th_dl", use_container_width=True)

    elif menu == "plan_ia":
        studio_step_card(1, "Reçois un plan de montage complet", "Décris le sujet de ta vidéo et choisis la plateforme. L'IA te donne un plan détaillé : hook, séquences, sous-titres, musique, appel à l'action, titres et idée de miniature.")
        sujet = st.text_area("Sujet ou script de la vidéo", height=140, key="pm_sujet", placeholder="Ex : 3 astuces pour rester concentré toute la journée")
        c1, c2 = st.columns(2)
        with c1:
            plateforme = st.selectbox("Plateforme", ["TikTok", "Instagram Reels", "YouTube Shorts", "YouTube (long)", "LinkedIn"], key="pm_plat")
        with c2:
            duree = st.selectbox("Durée visée", ["15 s", "30 s", "60 s", "3 min", "8-10 min"], key="pm_dur")
        if st.button("Générer le plan de montage", key="pm_go", use_container_width=True, type="primary") and clean_text(sujet, 6000):
            if rate_ok() and quota_ok("chat"):
                prompt = f"Plateforme : {plateforme}\nDurée : {duree}\nSujet / script :\n{clean_text(sujet, 6000)}"
                try:
                    text = st.write_stream(stream_groq([{"role": "system", "content": SYSTEM_MONTAGE}, {"role": "user", "content": prompt}]))
                except Exception:
                    text = ""
                    st.error("L'IA est indisponible.")
                if text.strip():
                    st.session_state.plan_result = text
                    quota_consume("chat")
                    st.rerun()
        if st.session_state.get("plan_result"):
            st.markdown("#### Ton plan de montage")
            st.markdown(st.session_state.plan_result)
            st.download_button("⬇️ Télécharger (.md)", st.session_state.plan_result, file_name="plan_montage.md", key="pm_dl", use_container_width=True)

    elif menu == "audio":
        studio_step_card(1, "Audio", "Extrais l'audio d'une vidéo, ajuste le volume, réduis le bruit ou coupe les silences. Nécessite FFmpeg.")
        if "current_media" not in st.session_state:
            st.info("Importe d'abord une vidéo dans « Importer un média ».")
        else:
            st.code("ffmpeg -i input.mp4 -vn -q:a 0 output.mp3", language="bash")
            if st.button("Extraire l'audio", key="audio_ex", use_container_width=True):
                st.success("Commande prête. Sur Streamlit Cloud, elle sera exécutée via subprocess.")

    elif menu == "texte":
        studio_step_card(1, "Texte incrusté", "Ajoute du texte par-dessus ta vidéo. Choisis la taille, la couleur et la position.")
        st.text_input("Texte à incruster", key="text_overlay", placeholder="Ex : Nouvelle vidéo !")
        st.slider("Taille du texte", 10, 100, 40, key="text_size")
        st.color_picker("Couleur du texte", "#FFFFFF", key="text_color")

    elif menu == "effets":
        studio_step_card(1, "Effets vidéo", "Applique des effets : flou, netteté, vignette, ralenti, accéléré.")
        st.slider("Intensité du flou", 0, 10, 0, key="eff_blur")
        st.caption("D'autres effets seront disponibles dans une prochaine version.")

    elif menu == "transitions":
        studio_step_card(1, "Transitions", "Choisis une transition entre tes clips : fondu, glissement, zoom, wipe.")
        st.selectbox("Type de transition", ["Fondu", "Slide", "Zoom", "Wipe"], key="trans_type")

    elif menu == "filtres":
        studio_step_card(1, "Filtres couleur", "Ajuste le rendu couleur de ta vidéo : contraste, saturation, teinte.")
        st.slider("Contraste", 0.5, 2.0, 1.0, key="filt_contrast")

    elif menu == "ajustement":
        studio_step_card(1, "Ajustement", "Recadre, pivote ou change la vitesse de ta vidéo.")
        st.slider("Vitesse de lecture", 0.25, 2.0, 1.0, key="adj_speed")

    elif menu == "autocollants":
        studio_step_card(1, "Autocollants", "Ajoute des emojis ou des images par-dessus ta vidéo.")
        st.file_uploader("Image autocollant (PNG recommandé)", type=["png","jpg","webp"], key="sticker_up")

    elif menu == "modeles":
        studio_step_card(1, "Formats prédéfinis", "Choisis un format selon la plateforme de destination.")
        st.selectbox("Modèle", ["TikTok 9:16", "Reels 9:16", "Shorts 9:16", "YouTube 16:9"], key="model_tpl")
        st.caption("Le format sera appliqué à ton export vidéo.")

def page_perso():
    st.markdown("### 🎨 Personnaliser Bea")
    if st.session_state.pop("perso_saved", False):
        st.success("Personnalisation enregistrée : Bea l'utilisera dans toutes tes discussions.")
    p = st.session_state.prefs or {}
    styles = list(STYLE_HINT)
    with st.form("form_perso"):
        nom = st.text_input("Comment Bea doit-elle t'appeler ?", value=p.get("display_name") or "", max_chars=40)
        style = st.selectbox("Style de réponse", styles, index=styles.index(p["style"]) if p.get("style") in styles else 0)
        objectif = st.text_input("Objectif principal", value=p.get("goal") or "", max_chars=160, placeholder="Ex : arrêter de procrastiner sur mes vidéos")
        ok = st.form_submit_button("Enregistrer", use_container_width=True)
    if ok:
        row = {"user_id": uid(), "display_name": clean_text(nom, 40), "style": style, "goal": clean_text(objectif, 160), "updated_at": now_iso()}
        try:
            sb().table("preferences").upsert(row).execute()
            st.session_state.prefs = {k: row[k] for k in ("display_name", "style", "goal")}
            st.session_state.perso_saved = True
        except Exception as e:
            db_error(e)
            return
        st.rerun()

def page_compte():
    st.markdown("### 💎 Compte & offres")
    q = st.session_state.quota or {}
    st.markdown(f"**Offre actuelle :** {PLAN_LABEL[st.session_state.plan]}")
    if st.button("🔄 Actualiser mon offre", key="refresh_plan"):
        refresh_quota()
        st.rerun()
    for k, label in (("chat", "Requêtes de chat"), ("code", "Requêtes IA code")):
        if q.get(k):
            st.progress(min(q[k]["used"] / max(q[k]["limit"], 1), 1.0), text=f"{label} ce mois-ci : {q[k]['used']}/{q[k]['limit']}")
    st.caption("Après un paiement, ton offre est activée sur ton compte (si ce n'est pas le cas, contacte le support).")
    render_offers()
    st.divider()
    st.markdown("#### 🔒 Confidentialité")
    st.markdown(privacy_md())
    st.caption("Texte indicatif : à faire valider et compléter (mentions légales, CGU, politique de confidentialité complète) avant l'ouverture au public.")
    confirm = st.checkbox("Je confirme vouloir supprimer toutes mes discussions et tous mes projets de code", key="del_all_ok")
    if st.button("Supprimer mon historique", key="del_all", disabled=not confirm):
        try:
            sb().table("conversations").delete().eq("user_id", uid()).execute()
            sb().table("code_projects").delete().eq("user_id", uid()).execute()
            st.session_state.convs = st.session_state.projects = None
            new_chat()
            st.session_state.page = "compte"
            st.success("Historique supprimé.")
        except Exception as e:
            db_error(e)

if not logged_in():
    page_vitrine()
    st.stop()

if st.session_state.is_admin and st.session_state.dev_mode is None:
    st.session_state.page = "dev_portal"

if st.session_state.page == "dev_portal":
    page_dev_portal()
    st.stop()
if st.session_state.page == "dev_lab":
    page_dev_lab()
    st.stop()

render_sidebar()
{
    "chat": page_chat, "code": page_code, "app": page_app, "studio": page_studio,
    "projets": page_projets, "perso": page_perso, "compte": page_compte, "memoire": page_memoire,
    "dev_portal": page_dev_portal, "dev_lab": page_dev_lab,
}.get(st.session_state.page, page_chat)()
