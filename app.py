import io
import json
import os
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

# --- Liens Stripe (inchangés : à remplacer par tes liens définitifs) ---------
STRIPE_BEA_9 = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"
STRIPE_PRO_1490 = "https://buy.stripe.com/test_cNieVea1P0c62B08523wQ00"
STRIPE_ABO_16 = "https://buy.stripe.com/test_8x27sMei58IC6Rg3OM3wQ01"  # TODO : même lien que STRIPE_BEA_9 pour l'instant

# --- Configuration -----------------------------------------------------------
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    SUPA_URL = st.secrets["SUPABASE_URL"]
    SUPA_KEY = st.secrets.get("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_KEY")
    if not SUPA_KEY:
        raise KeyError("SUPABASE_ANON_KEY")
except Exception:
    st.error("Configuration manquante : GROQ_API_KEY, SUPABASE_URL et SUPABASE_ANON_KEY doivent être définis dans les secrets.")
    st.stop()

CONTACT_EMAIL = st.secrets.get("CONTACT_EMAIL", "")

PLANS = ("free", "bea", "pro", "abo")
PLAN_LABEL = {"free": "Gratuit", "bea": "Bea", "pro": "Bea Pro", "abo": "Bea Ultra"}
WHISPER_MODEL = "whisper-large-v3-turbo"
MAX_AUDIO_BYTES = 25 * 1024 * 1024
EXT = {"python": "py", "javascript": "js", "typescript": "ts", "html": "html", "css": "css", "json": "json", "sql": "sql"}
DEFAULT_CODE = "# Écris ton code ici\n\ndef bonjour(nom):\n    return f'Bonjour {nom} !'\n\nprint(bonjour('Bea'))\n"


@st.cache_resource
def get_groq():
    return Groq(api_key=GROQ_KEY)


@st.cache_data(ttl=3600)
def get_modeles():
    pref = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "llama-3.3-70b-versatile", "llama-3.1-70b-versatile"]
    try:
        ids = [m.id for m in get_groq().models.list().data]
        chat_ids = [i for i in ids if "whisper" not in i and "guard" not in i]
        return [m for m in pref if m in ids] or chat_ids or pref[:1]
    except Exception:
        return pref[:1]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# --- État de session ---------------------------------------------------------
for k, v in {
    "page": "chat", "sb": None, "user": None, "plan": "free", "quota": {}, "prefs": {},
    "conv_id": None, "messages": [], "convs": None, "projects": None,
    "code_messages": [], "code_project_id": None, "code_name_in": "", "code_lang_in": "python",
    "rate": deque(), "blocked_until": 0.0, "up_key": 0, "expanded": None, "auth_notice": "",
    "sub_result": None, "plan_result": None, "app_result": None, "thumb_png": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v
if "code_area" not in st.session_state:
    st.session_state["code_area"] = DEFAULT_CODE

# --- Styles ------------------------------------------------------------------
GRAD = "linear-gradient(135deg, #1d4ed8 0%, #7c3aed 60%, #c026d3 85%, #db2777 100%)"
BORDER, BG, CARD, TEXT = "#7c3aed", "#0f0a1e", "#1a1535", "#f5f3ff"
st.markdown(f"""
<style>
.stApp{{background:{BG}!important;}}
[data-testid="stSidebar"]{{background:#0d0d14!important; border-right:3px solid {BORDER}!important;}}
[data-testid="stSidebar"] *{{color:#e2d6ff!important;}}
header[data-testid="stHeader"]{{background:transparent!important;}}
.block-container{{max-width:1150px!important; padding-top:2.8rem!important; padding-bottom:4rem!important;}}
#MainMenu,footer{{visibility:hidden;}}
div[data-testid="stButton"]>button{{background:#15112a!important; color:#e8e0ff!important; border:2px solid {BORDER}!important; border-radius:12px!important; font-weight:600!important; font-size:13px!important; min-height:44px!important;}}
div[data-testid="stButton"]>button:hover{{background:#231a4a!important; border-color:#a855f7!important; box-shadow:0 0 10px rgba(124,58,237,0.4)!important;}}
div[data-testid="stLinkButton"]>a{{background:{GRAD}!important; color:white!important; border-radius:12px!important; font-weight:700!important; border:2px solid {BORDER}!important; padding:12px!important;}}
div[data-testid="stChatMessage"]{{background:{CARD}!important; border:2px solid {BORDER}!important; border-radius:16px!important; padding:14px!important;}}
div[data-testid="stChatMessage"] p{{color:{TEXT}!important; font-size:15px!important; line-height:1.6!important;}}
div[data-testid="stChatInput"]{{background:#1a1535!important; border:2px solid {BORDER}!important; border-radius:24px!important;}}
input, textarea{{background:#1a1535!important; color:{TEXT}!important; border:2px solid {BORDER}!important; border-radius:12px!important;}}
.claude-title{{font-size:34px; font-weight:800; color:{TEXT}; text-align:center; margin:8px 0 2px 0;}}
.claude-sub{{font-size:12px; color:#d8ccff!important; text-align:center; font-weight:700; letter-spacing:0.8px; margin-bottom:16px;}}
.desc-main{{font-size:14px; color:#c4b5fd; text-align:center; max-width:760px; margin:12px auto 32px auto; line-height:1.7;}}
.limit-badge{{background:#2a1a4a; border:1px solid {BORDER}; border-radius:8px; padding:6px 10px; font-size:11px; color:#c4b5fd; margin-bottom:10px;}}
.soon{{font-size:12px; color:#8a7ab8;}}
</style>
""", unsafe_allow_html=True)

# --- Prompts -----------------------------------------------------------------
STYLE_HINT = {
    "Direct": "Va droit au but, phrases courtes, sans détour.",
    "Doux": "Ton bienveillant et encourageant, sans jamais être complaisant.",
    "Détaillé": "Explique en détail ta lecture de la situation et le raisonnement derrière chaque conseil.",
    "Expert comportemental": "Utilise le vocabulaire de la psychologie comportementale (déclencheurs, renforcement, friction, habitudes) en l'expliquant simplement.",
}

SYSTEM_BEHAVIOR_BASE = """Tu es Bea, une IA d'analyse comportementale créée par BehaviorLab AI. Tu aides les entreprises, les indépendants et les créateurs de contenu à avancer sur leurs projets.

Ta méthode :
1. Reformule la situation en une phrase.
2. Repère les schémas de comportement qui freinent la progression (habitudes, réflexes, évitements). Si tu manques d'éléments, pose une ou deux questions précises avant de conclure.
3. Propose des comportements de remplacement concrets, alignés sur l'objectif de la personne.
4. Termine par un plan d'action court et mesurable (quoi, quand, et comment savoir si ça marche).

Règles : réponds dans la langue de l'utilisateur (français par défaut) ; sois concret et structuré ; n'invente ni chiffres, ni statistiques, ni exemples présentés comme réels ; tu ne poses pas de diagnostic médical ou psychologique et tu ne remplaces pas un professionnel. Si la personne semble en détresse ou en danger, encourage-la à en parler à un proche ou à un professionnel (en France : 3114 pour la prévention du suicide, 15 ou 112 en urgence). Si un fichier est joint, appuie-toi dessus."""

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
    if nom:
        extra.append(f"La personne souhaite être appelée « {nom} ».")
    if p.get("style") in STYLE_HINT:
        extra.append(f"Style de réponse demandé : {p['style']}. {STYLE_HINT[p['style']]}")
    if objectif:
        extra.append(f"Objectif principal de la personne : {objectif}")
    return SYSTEM_BEHAVIOR_BASE + ("\n\n" + "\n".join(extra) if extra else "")


# --- IA : streaming avec repli entre modèles ---------------------------------
def stream_groq(messages, max_tokens=2600):
    last, started = None, False
    for mid in get_modeles():
        try:
            stream = get_groq().chat.completions.create(
                model=mid, messages=messages, temperature=0.7, max_tokens=max_tokens, stream=True)
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
                yield "\n\n⚠️ _Réponse interrompue, tu peux réessayer._"
                return
    if last:
        raise last


# --- Supabase ----------------------------------------------------------------
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


def load_account():
    try:
        rows = sb().table("preferences").select("display_name,style,goal").eq("user_id", uid()).execute().data
        st.session_state.prefs = rows[0] if rows else {}
    except Exception:
        st.session_state.prefs = {}
    refresh_quota()


def goto(page):
    st.session_state.page = page


def quota_ok(kind):
    """Vérifie le quota côté serveur (impossible à contourner en rafraîchissant la page)."""
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
    if len(dq) >= 20:
        st.session_state.blocked_until = now + 60
        st.error("Trop de requêtes : attends 60 secondes.")
        return False
    dq.append(now)
    return True


def db_error(e=None):
    st.error("Erreur d'accès aux données. Réessaie dans un instant.")


# --- Conversations -----------------------------------------------------------
def get_convs():
    if st.session_state.convs is None:
        try:
            st.session_state.convs = sb().table("conversations").select("id,title").order("updated_at", desc=True).limit(20).execute().data or []
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
    st.session_state.page = "chat"


def delete_conv(cid):
    try:
        sb().table("conversations").delete().eq("id", cid).execute()
    except Exception as e:
        db_error(e)
        return
    st.session_state.convs = None
    if st.session_state.conv_id == cid:
        new_chat()


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
    recent = msgs[-14:]
    for i, m in enumerate(recent):
        content = m["content"]
        if m["role"] == "user" and m.get("attachment_text") and i >= len(recent) - 6:
            content += f"\n\n[Fichier joint : {m.get('attachment_name') or 'fichier'}]\n{m['attachment_text']}"
        out.append({"role": m["role"], "content": content})
    return out


def render_message(m):
    if m["role"] == "user":
        with st.chat_message("user"):
            st.markdown(m["content"])
            if m.get("attachment_name"):
                st.caption(f"📎 {m['attachment_name']}")
    else:
        with st.chat_message("assistant", avatar=AVATAR):
            st.markdown(m["content"])


def generate_reply():
    """Génère (en streaming) et enregistre la réponse de Bea. Retourne True si OK."""
    with st.chat_message("assistant", avatar=AVATAR):
        try:
            text = st.write_stream(stream_groq(build_model_messages(st.session_state.messages)))
        except Exception:
            st.error("Bea n'a pas pu répondre (service IA indisponible). Utilise « Régénérer » pour réessayer.")
            return False
    text = clean_text(text, 12000)
    if not text:
        st.error("Réponse vide. Utilise « Régénérer » pour réessayer.")
        return False
    try:
        mid = sb().table("messages").insert({
            "conversation_id": st.session_state.conv_id, "user_id": uid(), "role": "assistant", "content": text,
        }).execute().data[0]["id"]
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
            st.session_state.conv_id = sb().table("conversations").insert({"user_id": uid(), "title": text[:50]}).execute().data[0]["id"]
            st.session_state.convs = None
        mid = sb().table("messages").insert({
            "conversation_id": st.session_state.conv_id, "user_id": uid(), "role": "user", "content": text,
            "attachment_name": att_name, "attachment_text": att_text,
        }).execute().data[0]["id"]
    except Exception as e:
        db_error(e)
        return
    msg = {"id": mid, "role": "user", "content": text, "attachment_name": att_name, "attachment_text": att_text}
    st.session_state.messages.append(msg)
    render_message(msg)
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


# --- Offres ------------------------------------------------------------------
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
                        st.markdown(
                            "**L'analyse des comportements quotidiens qui déterminent la réussite sur le long terme.**\n"
                            "- Repérage des schémas de comportement qui freinent ta progression\n"
                            "- Comportements de remplacement alignés sur tes objectifs\n"
                            "- Routines de discipline et de prise de décision\n"
                            "- Historique enregistré, envoi de fichiers texte et PDF, personnalisation du style")
                    elif key == "pro":
                        st.markdown(
                            "**Tout Bea, plus des outils pour créateurs :**\n"
                            "- Sous-titres automatiques à partir d'un audio ou d'une vidéo (SRT et VTT)\n"
                            "- Miniatures 1280×720 prêtes à publier\n"
                            "- Plans de montage générés par l'IA (hook, séquences, rythme, titres)\n"
                            "- Quotas plus élevés pour le chat et l'IA code")
                        st.markdown('<div class="soon">Bientôt : suppression du fond, découpe des silences, nettoyage audio, voix off IA, export vidéo.</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(
                            "**Tout Bea Pro, plus :**\n"
                            "- Génération d'une application web complète (un seul fichier HTML) à partir d'un prompt\n"
                            "- Quotas très larges pour le chat et l'IA code (usage équitable)")
                st.link_button(label, url, use_container_width=True)


# --- Pages publiques ---------------------------------------------------------
def page_vitrine():
    if LOGO:
        _, c, _ = st.columns([1, 0.3, 1])
        with c:
            st.image(LOGO, width=80)
    st.markdown('<div class="claude-title">Bea</div><div class="claude-sub">BehaviorLab AI</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="desc-main">Bea part d\'une idée encore floue et la transforme en projet concret. Elle repère le blocage précis qui ralentit '
        'ton avancement, puis propose des actions mesurables que tu peux appliquer immédiatement.</div>', unsafe_allow_html=True)
    _, col, _ = st.columns([0.5, 1.6, 0.5])
    with col:
        with st.container(border=True):
            if st.session_state.auth_notice:
                st.info(st.session_state.auth_notice)
            t_in, t_up, t_rst = st.tabs(["Se connecter", "Créer un compte", "Mot de passe oublié"])
            with t_in:
                with st.form("form_login"):
                    email = st.text_input("Adresse e-mail", key="li_email")
                    pwd = st.text_input("Mot de passe", type="password", key="li_pwd")
                    go = st.form_submit_button("Continuer", use_container_width=True)
                if go:
                    try:
                        c = new_client()
                        res = c.auth.sign_in_with_password({"email": email.strip(), "password": pwd})
                        st.session_state.sb, st.session_state.user = c, res.user
                        st.session_state.auth_notice = ""
                        load_account()
                        st.rerun()
                    except Exception as e:
                        st.error("Adresse e-mail à confirmer : vérifie ta boîte mail." if "confirm" in str(e).lower() else "Identifiants invalides.")
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


# --- Sidebar -----------------------------------------------------------------
def render_sidebar():
    with st.sidebar:
        if LOGO:
            _, c, _ = st.columns([1, 1, 1])
            with c:
                st.image(LOGO, width=62)
        st.markdown('<div style="text-align:center; font-size:18px; font-weight:800; color:#f5f3ff;">Bea</div>'
                    '<div style="text-align:center; font-size:11px; font-weight:700; letter-spacing:0.8px; margin-bottom:12px;">BehaviorLab AI</div>',
                    unsafe_allow_html=True)
        q = st.session_state.quota or {}
        def fmt(x):
            return f"{x['used']}/{x['limit']}" if x else "?"
        st.markdown(f'<div class="limit-badge">{PLAN_LABEL[st.session_state.plan]} · Chat {fmt(q.get("chat"))} · Code {fmt(q.get("code"))}</div>',
                    unsafe_allow_html=True)
        if st.button("✨ Nouvelle discussion", key="nav_new", use_container_width=True):
            new_chat()
            st.rerun()
        for label, pg in [("💬 Chat", "chat"), ("💻 Code", "code"), ("🌐 App web (Ultra)", "app"), ("🎬 Studio créateur", "studio"),
                          ("📁 Projets", "projets"), ("🎨 Personnalisation", "perso"), ("💎 Compte & offres", "compte")]:
            if st.button(label, key=f"nav_{pg}", use_container_width=True):
                st.session_state.page = pg
                st.rerun()
        convs = get_convs()
        if convs:
            st.markdown('<div style="font-size:10px; text-transform:uppercase; margin:14px 0 6px 0; font-weight:700;">Historique</div>', unsafe_allow_html=True)
            for c in convs[:10]:
                prefix = "▶ " if c["id"] == st.session_state.conv_id else "• "
                if st.button(f"{prefix}{c['title'][:22]}", key=f"hist_{c['id']}", use_container_width=True):
                    open_conv(c["id"])
                    st.rerun()
        st.caption(st.session_state.user.email or "")
        if st.button("🚪 Déconnexion", key="nav_logout", use_container_width=True):
            try:
                sb().auth.sign_out()
            except Exception:
                pass
            for k in ("sb", "user", "conv_id", "convs", "projects", "sub_result", "plan_result", "app_result", "thumb_png"):
                st.session_state[k] = None
            st.session_state.messages, st.session_state.code_messages, st.session_state.quota, st.session_state.prefs = [], [], {}, {}
            st.session_state.plan, st.session_state.page = "free", "chat"
            st.rerun()


# --- Page Chat ---------------------------------------------------------------
def page_chat():
    st.markdown("### 💬 Discussion avec Bea")
    if not st.session_state.messages:
        st.info("Bonjour, je suis Bea. Décris-moi un projet ou un blocage (procrastination, manque de régularité, décisions difficiles…) "
                "et je t'aide à repérer ce qui te freine, puis à construire un plan d'action mesurable.")
    for m in st.session_state.messages:
        render_message(m)
    if st.session_state.messages:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🔄 Régénérer / réessayer", key="regen", use_container_width=True):
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
            st.download_button("⬇️ Exporter (.md)", export_markdown(), file_name="discussion_bea.md", key="dl_conv", use_container_width=True)
        with c3:
            if st.session_state.conv_id and st.button("🗑️ Supprimer la discussion", key="del_conv", use_container_width=True):
                delete_conv(st.session_state.conv_id)
                st.rerun()
    if st.session_state.pop("regen_flag", False):
        if generate_reply():
            st.rerun()
    with st.expander("📎 Joindre un fichier (txt, md, csv, json, py, pdf)"):
        up = st.file_uploader("Fichier", type=["txt", "md", "csv", "json", "py", "pdf"], key=f"chat_up_{st.session_state.up_key}", label_visibility="collapsed")
    prompt = st.chat_input("Écris ton message à Bea...")
    if prompt:
        handle_send(prompt, up)


# --- Projets de code ---------------------------------------------------------
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
    st.caption(f"Écris ton code à gauche, discute avec l'IA à droite. Requêtes IA code ce mois-ci : {d.get('used', '?')}/{d.get('limit', '?')}.")
    col_e, col_c = st.columns([1.25, 0.75], gap="medium")
    with col_e:
        c1, c2 = st.columns([1, 1])
        with c1:
            name = st.text_input("Nom du fichier", placeholder="mon_script", key="code_name_in")
        with c2:
            lang = st.selectbox("Langage", list(EXT), key="code_lang_in")
        code = st.text_area("Code", height=440, key="code_area", label_visibility="collapsed")
        b1, b2, b3 = st.columns(3)
        fname = f"{(name or 'code').strip()[:40]}.{EXT[lang]}"
        with b1:
            if st.button("📄 Nouveau", key="ed_new", use_container_width=True):
                st.session_state.pending_editor = {"code": "# Nouveau fichier\n", "name": "", "lang": "python"}
                st.session_state.code_project_id, st.session_state.code_messages = None, []
                st.rerun()
        with b2:
            if st.button("💾 Enregistrer", key="ed_save", use_container_width=True):
                save_project((name or f"code_{len(get_projects()) + 1}").strip()[:40], lang, code)
        with b3:
            st.download_button("⬇️ Télécharger", code, file_name=fname, key="ed_dl", use_container_width=True)
        with st.expander("Aperçu coloré"):
            st.code(code, language=lang)
    with col_c:
        hist = st.container()
        with hist:
            st.markdown("**Ask about your code**")
            st.caption("Les réponses de l'IA peuvent contenir des erreurs : relis et teste toujours le code proposé.")
            for m in st.session_state.code_messages[-8:]:
                render_message(m)
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
                render_message(user_msg)
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


# --- Générateur d'app web (Ultra) -------------------------------------------
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


# --- Studio créateur ---------------------------------------------------------
LANGS = {"Détection automatique": None, "Français": "fr", "English": "en", "Español": "es", "Deutsch": "de", "Italiano": "it", "Português": "pt", "العربية": "ar"}


def page_studio():
    st.markdown("### 🎬 Studio créateur")
    st.caption("Outils disponibles aujourd'hui : sous-titres, miniatures et plans de montage. Bientôt : suppression du fond, découpe des silences, nettoyage audio, voix off IA, export vidéo.")
    t1, t2, t3, t4 = st.tabs(["Sous-titres automatiques", "Sous-titres depuis un script", "Miniature 1280×720", "Plan de montage IA"])

    with t1:
        if st.session_state.plan not in ("pro", "abo"):
            locked("La transcription automatique est incluse dans Bea Pro et Bea Ultra.")
        else:
            st.caption("Transcription par IA (Whisper) avec horodatage. Audio ou vidéo, 25 Mo maximum.")
            up = st.file_uploader("Fichier audio ou vidéo", type=["mp3", "mp4", "m4a", "wav", "webm", "ogg", "flac", "mpeg", "mpga"], key="sub_up")
            lang_label = st.selectbox("Langue parlée", list(LANGS), key="sub_lang")
            if up and st.button("Générer les sous-titres", key="sub_go", use_container_width=True):
                if up.size > MAX_AUDIO_BYTES:
                    st.error("Fichier trop lourd : 25 Mo maximum. Extrais l'audio en MP3 pour réduire la taille.")
                elif rate_ok() and quota_ok("chat"):
                    with st.spinner("Transcription en cours..."):
                        try:
                            kwargs = {"language": LANGS[lang_label]} if LANGS[lang_label] else {}
                            res = get_groq().audio.transcriptions.create(
                                file=(up.name, up.getvalue()), model=WHISPER_MODEL, response_format="verbose_json", temperature=0.0, **kwargs)
                            data = res.model_dump() if hasattr(res, "model_dump") else (res if isinstance(res, dict) else {})
                            cues = segments_to_cues(data.get("segments"))
                        except Exception:
                            cues, data = [], {}
                            st.error("La transcription a échoué. Vérifie le format du fichier et réessaie.")
                    if cues:
                        quota_consume("chat")
                        st.session_state.sub_result = {"srt": cues_to_srt(cues), "vtt": cues_to_vtt(cues), "text": data.get("text", "")}
                        st.rerun()
                    elif data:
                        st.warning("Aucune parole détectée dans ce fichier.")
            r = st.session_state.sub_result
            if r:
                a, b = st.columns(2)
                with a:
                    st.download_button("⬇️ Télécharger SRT", r["srt"], file_name="sous_titres.srt", key="dl_srt", use_container_width=True)
                with b:
                    st.download_button("⬇️ Télécharger VTT", r["vtt"], file_name="sous_titres.vtt", key="dl_vtt", use_container_width=True)
                st.text_area("Aperçu (SRT)", r["srt"], height=260, key="srt_prev")

    with t2:
        st.caption("Le timing est **estimé** à partir du nombre de mots : il n'est pas synchronisé à la voix. Pour une synchronisation exacte, utilise l'onglet précédent.")
        script = st.text_area("Script", height=160, key="script_area", placeholder="Colle ton script ici...")
        wps = st.slider("Mots par seconde", 1.5, 4.0, 2.6, 0.1, key="wps")
        if clean_text(script, 20000):
            cues = script_to_cues(clean_text(script, 20000), wps)
            a, b = st.columns(2)
            with a:
                st.download_button("⬇️ Télécharger SRT", cues_to_srt(cues), file_name="script.srt", key="dl_srt2", use_container_width=True)
            with b:
                st.download_button("⬇️ Télécharger VTT", cues_to_vtt(cues), file_name="script.vtt", key="dl_vtt2", use_container_width=True)
            st.caption(f"{len(script.split())} mots · {len(cues)} sous-titres · durée estimée {cues[-1][1]:.0f} s" if cues else "")

    with t3:
        title = st.text_input("Titre (80 caractères max)", max_chars=80, key="th_title", placeholder="Ex : J'ai arrêté de procrastiner en 7 jours")
        subtitle = st.text_input("Sous-titre (optionnel)", max_chars=90, key="th_sub")
        style = st.selectbox("Style", list(PALETTES), key="th_style")
        bg = st.file_uploader("Image de fond (optionnel)", type=["png", "jpg", "jpeg", "webp"], key="th_bg")
        if st.button("Générer la miniature", key="th_go", use_container_width=True):
            try:
                st.session_state.thumb_png = image_to_png_bytes(make_thumbnail(title, subtitle, style, bg.getvalue() if bg else None))
            except Exception:
                st.error("Impossible de générer la miniature avec cette image.")
        if st.session_state.thumb_png:
            st.image(st.session_state.thumb_png)
            st.download_button("⬇️ Télécharger (PNG 1280×720)", st.session_state.thumb_png, file_name="miniature.png", mime="image/png", key="th_dl")

    with t4:
        sujet = st.text_area("Sujet ou script de la vidéo", height=140, key="pm_sujet")
        c1, c2 = st.columns(2)
        with c1:
            plateforme = st.selectbox("Plateforme", ["TikTok", "Instagram Reels", "YouTube Shorts", "YouTube (long)", "LinkedIn"], key="pm_plat")
        with c2:
            duree = st.selectbox("Durée visée", ["15 s", "30 s", "60 s", "3 min", "8-10 min"], key="pm_dur")
        if st.button("Générer le plan de montage", key="pm_go", use_container_width=True) and clean_text(sujet, 6000):
            if rate_ok() and quota_ok("chat"):
                prompt = f"Plateforme : {plateforme}\nDurée : {duree}\nSujet / script :\n{clean_text(sujet, 6000)}"
                try:
                    text = st.write_stream(stream_groq([{"role": "system", "content": SYSTEM_MONTAGE}, {"role": "user", "content": prompt}]))
                except Exception:
                    text = ""
                    st.error("L'IA est indisponible pour le moment. Réessaie.")
                if text.strip():
                    st.session_state.plan_result = text
                    quota_consume("chat")
                    st.rerun()
        elif st.session_state.plan_result:
            st.markdown(st.session_state.plan_result)
            st.download_button("⬇️ Télécharger (.md)", st.session_state.plan_result, file_name="plan_montage.md", key="pm_dl")


# --- Personnalisation, compte, confidentialité -------------------------------
def page_perso():
    st.markdown("### 🎨 Personnaliser Bea")
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
            st.success("Personnalisation enregistrée : Bea l'utilisera dans toutes tes discussions.")
        except Exception as e:
            db_error(e)


def page_compte():
    st.markdown("### 💎 Compte & offres")
    q = st.session_state.quota or {}
    st.markdown(f"**Offre actuelle :** {PLAN_LABEL[st.session_state.plan]}")
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


# --- Routeur -----------------------------------------------------------------
if not logged_in():
    page_vitrine()
    st.stop()

render_sidebar()
{
    "chat": page_chat, "code": page_code, "app": page_app, "studio": page_studio,
    "projets": page_projets, "perso": page_perso, "compte": page_compte,
}.get(st.session_state.page, page_chat)()
