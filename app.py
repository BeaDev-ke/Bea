import ast
import base64
import difflib
import html
import io
import json
import os
import re
import time
import urllib.error
import urllib.request
import zipfile
from collections import deque
from datetime import datetime, timezone

import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
from PIL import Image, ImageDraw, ImageFont, ImageOps
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

LOGO = find_file(["logo_bea.png", "logo.png", "logo_bea.svg"])
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

AUTH_COOKIE_NAME = "bea_auth_token"
AUTH_COOKIE_MAX_AGE = 30 * 86400

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
    ],
    "etudiant": [
        "Je dois réviser mais je n'arrive pas à m'y mettre",
        "Je ne comprends pas un cours et je ne sais pas comment le reprendre",
        "J'ai plusieurs devoirs et je ne sais pas par quoi commencer",
    ],
    "salarie": [
        "Je me sens débordé au travail, comment reprendre le contrôle ?",
        "Je veux mieux m'organiser entre mes priorités et mes réunions",
        "Je n'ose pas parler d'un problème avec mon équipe",
    ],
    "recherche_emploi": [
        "Je cherche un emploi mais je repousse mes candidatures",
        "Je veux mieux présenter mon parcours en entretien",
        "Je ne sais pas quelle direction professionnelle choisir",
    ],
    "parent": [
        "Je veux mieux m'organiser entre ma vie familiale et mes projets",
        "Je manque de temps pour avancer sur ce qui compte pour moi",
        "Je culpabilise quand je prends du temps pour moi",
    ],
    "enseignant": [
        "Je veux préparer mes cours avec plus de méthode",
        "Je cherche une façon plus claire d'expliquer une notion",
        "Je veux aider mes élèves à mieux mémoriser",
    ],
    "autre": [
        "Je procrastine sur un projet important",
        "Je me sens bloqué sans comprendre pourquoi",
        "Je veux construire une routine qui tienne dans le temps",
    ],
}

@st.cache_resource
def get_groq():
    return Groq(api_key=GROQ_KEY)

@st.cache_data(ttl=3600)
def get_modeles():
    pref_fast = ["llama-3.1-8b-instant", "openai/gpt-oss-20b", "llama-3.3-70b-versatile", "openai/gpt-oss-120b"]
    pref_power = ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "openai/gpt-oss-20b", "llama-3.1-8b-instant"]
    try:
        ids = [m.id for m in get_groq().models.list().data]
        chat_ids = [
            model_id for model_id in ids
            if "whisper" not in model_id
            and "guard" not in model_id
            and "orpheus" not in model_id
        ]
        fast = [model_id for model_id in pref_fast if model_id in chat_ids]
        power = [model_id for model_id in pref_power if model_id in chat_ids]
        return {
            "rapide": fast or chat_ids[:1],
            "puissant": power or fast or chat_ids[:1],
        }
    except Exception:
        return {"rapide": pref_fast[:1], "puissant": pref_power[:1]}

DEV_MODELES = {
    "Ultra (gratuit) - GPT OSS 120B [RECOMMANDÉ - ne casse rien]": "openai/gpt-oss-120b",
    "Puissant (gratuit) - Llama 3.3 70B": "llama-3.3-70b-versatile",
    "Codeur (gratuit) - GPT OSS 20B": "openai/gpt-oss-20b",
    "Rapide (gratuit) - Llama 3.1 8B": "llama-3.1-8b-instant",
    "Plus rapide — GPT OSS 20B": "openai/gpt-oss-20b",
}

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def password_strength(password):
    if not password:
        return None, "", ""
    score = 0
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if re.search(r"[a-z]", password) and re.search(r"[A-Z]", password):
        score += 1
    if re.search(r"\d", password):
        score += 1
    if re.search(r"[^A-Za-z0-9]", password):
        score += 1
    if len(password) < 8 or score <= 1:
        return "Faible", "#ef4444", "Ajoute au moins 8 caractères, avec des chiffres et des symboles."
    if score <= 3:
        return "Modéré", "#facc15", "Plus long et plus varié sera plus sûr."
    if score == 4:
        return "Fort", "#4ade80", "Bon niveau de sécurité."
    return "Très fort", "#22c55e", "Mot de passe robuste."

for k, v in {
    "page": "chat", "sb": None, "user": None, "plan": "free", "quota": {}, "prefs": {},
    "conv_id": None, "messages": [], "convs": None, "projects": None,
    "code_messages": [], "code_project_id": None, "code_name_in": "", "code_lang_in": "python",
    "rate": deque(), "blocked_until": 0.0, "up_key": 0, "expanded": None, "auth_notice": "", "pending_confirmation_email": "",
    "sub_result": None, "plan_result": None, "app_result": None, "app_versions": [], "app_generation_count": 0, "thumb_png": None, "pending_login": None, "is_admin": False,
    "model_choice": "rapide", "search_q": "", "editing_msg_id": None, "studio_menu": "importer", "memories": None, "profile_type": "createur",
    "dev_mode": None, "dev_result": None, "dev_raw": None, "dev_key_ok": False, "dev_model_choice": "Recommandé pour le code — GPT OSS 120B",
    "dev_full_original": "", "dev_backup_name": "", "transcribed_text": "",
    "onboarding_step": 1, "onboarding_profile": "createur", "onboarding_profile_choice": "createur", "onboarding_goal_choice": "clients", "onboarding_goal": "", "onboarding_goal_text": "", "onboarding_study_country": "France", "onboarding_study_level": "Collège - 6e", "landing_tab": "connexion",
    "canvas_png": None, "canvas_zip": None,
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

[data-testid="stSidebar"] div[data-testid="stButton"]>button{{
  background:transparent!important;
  color:#e2d6ff!important;
  border:1px solid transparent!important;
  border-radius:10px!important;
  box-shadow:none!important;
  text-align:left!important;
  justify-content:flex-start!important;
  padding:8px 12px!important;
  min-height:40px!important;
  transition:background .15s ease, color .15s ease!important;
}}
[data-testid="stSidebar"] div[data-testid="stButton"]>button:hover{{
  background:#3b246b!important;
  color:#ffffff!important;
  border-color:transparent!important;
  box-shadow:none!important;
}}

div[data-testid="stButton"]>button:hover{{background:#231a4a!important; border-color:#a855f7!important; box-shadow:0 0 10px rgba(124,58,237,0.4)!important;}}
div[data-testid="stLinkButton"]>a{{background:{GRAD}!important; color:white!important; border-radius:12px!important; font-weight:700!important; border:2px solid {BORDER}!important; padding:12px!important;}}
div[data-testid="stChatMessage"]{{background:{CARD}!important; border:2px solid {BORDER}!important; border-radius:16px!important; padding:14px!important;}}
div[data-testid="stChatMessage"] p{{color:{TEXT}!important; font-size:15px!important; line-height:1.6!important;}}
div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="select"]>div{{background:#1a1535!important; border:2px solid {BORDER}!important; border-radius:12px!important;}}
div[data-baseweb="base-input"]{{background:transparent!important; border:none!important;}}
div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea, div[data-baseweb="select"] input{{background:transparent!important; color:{TEXT}!important; border:none!important; box-shadow:none!important; outline:none!important;}}

/* ==========================================================================
   BARRE D'ENVOI STYLE CHATGPT (Capsule unifiée avec +, Micro et Flèche)
   ========================================================================== */
div[data-testid="stBottom"] {{
    background: transparent !important;
}}
div[data-testid="stBottom"] > div {{
    background: transparent !important;
}}

/* Capsule principale */
div[data-testid="stChatInput"] {{
    position: relative !important;
    background: #18132e !important;
    border: 1.5px solid #6d28d9 !important;
    border-radius: 28px !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
    padding: 6px 12px !important;
    min-height: 52px !important;
    display: flex !important;
    align-items: flex-end !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}}

div[data-testid="stChatInput"]:focus-within {{
    border-color: #a855f7 !important;
    box-shadow: 0 0 16px rgba(168, 85, 247, 0.35) !important;
}}

/* Zone de texte au centre */
div[data-testid="stChatInput"] textarea {{
    background: transparent !important;
    color: #f5f3ff !important;
    font-size: 15px !important;
    line-height: 1.5 !important;
    padding-left: 46px !important;   /* Espace réservé pour le bouton + */
    padding-right: 86px !important;  /* Espace réservé pour Micro + Flèche */
    padding-top: 8px !important;
    padding-bottom: 8px !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    resize: none !important;
}}

/* Bouton + (Popover pièces jointes / options) */
[data-testid="stPopover"] {{
    position: absolute !important;
    left: 8px !important;
    bottom: 8px !important;
    z-index: 25 !important;
    margin: 0 !important;
    padding: 0 !important;
    width: 36px !important;
    height: 36px !important;
}}

[data-testid="stPopover"] > button {{
    width: 36px !important;
    height: 36px !important;
    min-height: 36px !important;
    border-radius: 50% !important;
    background: #231a47 !important;
    border: 1px solid rgba(168, 85, 247, 0.35) !important;
    color: #e2d6ff !important;
    font-size: 20px !important;
    font-weight: 400 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 !important;
    margin: 0 !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
}}

[data-testid="stPopover"] > button:hover {{
    background: #39246d !important;
    border-color: #a855f7 !important;
    color: #ffffff !important;
    transform: scale(1.05) !important;
}}

/* Bouton Microphone */
[data-testid="stAudioInput"] {{
    position: absolute !important;
    right: 48px !important;
    bottom: 8px !important;
    z-index: 25 !important;
    width: 36px !important;
    height: 36px !important;
    min-width: 36px !important;
    margin: 0 !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    background: transparent !important;
    border: none !important;
}}

[data-testid="stAudioInput"] label {{
    display: none !important;
}}

[data-testid="stAudioInput"] button {{
    width: 36px !important;
    height: 36px !important;
    min-height: 36px !important;
    border-radius: 50% !important;
    background: #231a47 !important;
    border: 1px solid rgba(168, 85, 247, 0.35) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 !important;
    margin: 0 !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
}}

[data-testid="stAudioInput"] button:hover {{
    background: #39246d !important;
    border-color: #a855f7 !important;
    transform: scale(1.05) !important;
}}

[data-testid="stAudioInput"] svg {{
    width: 17px !important;
    height: 17px !important;
    fill: #c4b5fd !important;
}}

/* Bouton Flèche d'envoi */
div[data-testid="stChatInput"] button[data-testid="stChatInputSubmitButton"],
div[data-testid="stChatInput"] button:not([data-testid="stPopover"] button) {{
    position: absolute !important;
    right: 8px !important;
    bottom: 8px !important;
    z-index: 25 !important;
    width: 36px !important;
    height: 36px !important;
    min-height: 36px !important;
    border-radius: 50% !important;
    background: #7c3aed !important;
    border: none !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 !important;
    margin: 0 !important;
    box-shadow: 0 2px 8px rgba(124, 58, 237, 0.4) !important;
    transition: all 0.2s ease !important;
}}

div[data-testid="stChatInput"] button[data-testid="stChatInputSubmitButton"]:hover {{
    background: #9333ea !important;
    box-shadow: 0 0 12px rgba(168, 85, 247, 0.6) !important;
    transform: scale(1.05) !important;
}}

div[data-testid="stChatInput"] button[data-testid="stChatInputSubmitButton"]:disabled {{
    background: #2a2046 !important;
    opacity: 0.45 !important;
    cursor: not-allowed !important;
    transform: none !important;
    box-shadow: none !important;
}}

div[data-testid="stChatInput"] button[data-testid="stChatInputSubmitButton"] svg {{
    fill: #ffffff !important;
    width: 16px !important;
    height: 16px !important;
}}

.claude-title{{font-size:34px; font-weight:800; color:{TEXT}; text-align:center; margin:8px 0 2px 0;}}
.claude-sub{{font-size:12px; color:#d8ccff!important; text-align:center; font-weight:700; letter-spacing:0.8px; margin-bottom:16px;}}
.landing-copy{{max-width:820px; margin:18px auto 34px auto; padding:24px 30px; background:rgba(26,21,53,.72); border:1px solid rgba(124,58,237,.65); border-radius:18px; text-align:center;}}
.landing-copy h2{{color:{TEXT}; font-size:23px; margin:0 0 14px 0; line-height:1.25;}}
.landing-copy p{{color:#d8d1eb; font-size:15px; line-height:1.75; margin:10px 0;}}
.landing-copy strong{{color:#93c5fd;}}
@media (max-width:700px){{.landing-copy{{padding:20px 18px;}} .landing-copy h2{{font-size:20px;}} .landing-copy p{{font-size:14px;}}}}
.limit-badge{{background:#2a1a4a; border:1px solid {BORDER}; border-radius:8px; padding:6px 10px; font-size:11px; color:#c4b5fd; margin-bottom:10px;}}
.soon{{font-size:12px; color:#8a7ab8;}}
.studio-step{{background:{CARD}!important; border:2px solid {BORDER}!important; border-radius:14px!important; padding:18px!important; margin-bottom:14px!important;}}
.studio-step h4{{color:{TEXT}!important; margin:0 0 6px 0!important; font-size:17px!important;}}
.studio-step p{{color:#c4b5fd!important; font-size:13px!important; margin:0 0 12px 0!important; line-height:1.5!important;}}
</style>
""", unsafe_allow_html=True)

# Détection visuelle des gros collages
components.html("""
<script>
(function(){
  try {
    const doc = window.parent.document;
    if (doc.documentElement.dataset.beaPasteWatcher) return;
    doc.documentElement.dataset.beaPasteWatcher = '1';
    function showPasteBadge(target, length) {
      if (!target || !target.closest) return;
      const host = target.closest('[data-testid="stChatInput"]') || target.closest('[data-testid="stTextArea"]') || target.parentElement;
      if (!host) return;
      if (getComputedStyle(host).position === 'static') host.style.position = 'relative';
      let badge = host.querySelector('[data-bea-paste-badge="1"]');
      if (!badge) {
        badge = doc.createElement('span');
        badge.setAttribute('data-bea-paste-badge', '1');
        badge.style.cssText = 'position:absolute;right:8px;top:-22px;z-index:99999;padding:3px 9px;border-radius:999px;background:#6d28d9;color:#fff;font:700 11px/1.4 sans-serif;box-shadow:0 2px 8px #0005;pointer-events:none;';
        host.appendChild(badge);
      }
      badge.textContent = 'PASTE · ' + Number(length).toLocaleString('fr-FR') + ' caractères';
      badge.style.display = 'inline-block';
      if (badge._beaTimer) clearTimeout(badge._beaTimer);
      badge._beaTimer = setTimeout(function(){ if (badge.isConnected) badge.style.display = 'none'; }, 6000);
    }
    doc.addEventListener('paste', function(event){
      const target = event.target;
      if (!target || !('value' in target)) return;
      let pasted = '';
      try { pasted = event.clipboardData ? event.clipboardData.getData('text') : ''; } catch(e) {}
      const lines = pasted.split(/\r?\n/).length;
      if (pasted.length >= 500 || lines >= 8) showPasteBadge(target, pasted.length);
    }, true);
  } catch(e) {}
})();
</script>
""", height=0)

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

SYSTEM_USE_CASES = {
    "clients": (
        "MODE ANALYSE CLIENTS / PROSPECTS.\n"
        "L'utilisateur vient pour mieux comprendre et analyser ses clients, prospects ou partenaires à partir de leurs messages (e-mails, DM, échanges).\n"
        "MÉTHODE : tu mobilises les biais cognitifs liés à la décision d'achat (preuve sociale, aversion à la perte, réciprocité, autorité, engagement et cohérence, ancrage) et la détection des émotions derrière les mots (signal d'achat, de doute, d'objection, d'urgence).\n"
        "FORMAT DE RÉPONSE :\n"
        "1. **Lecture du message** : reformule en une ligne ce que le client dit vraiment (intention consciente + intention sous-jacente).\n"
        "2. **Signaux détectés** : 3 à 5 signaux (ton, intention, biais cognitif probable, émotion dominante, niveau d'engagement).\n"
        "3. **Biais à activer** : 2 ou 3 leviers psycho éthiques pour avancer la relation avec une phrase prête à l'emploi pour chacun.\n"
        "4. **Réponse suggérée** : un modèle de réponse concret, prêt à copier-coller, adapté au ton du client.\n"
        "5. **Angle de relance** : une idée de relance si pas de réponse dans X jours.\n"
        "RÈGLES : pas de manipulation trompeuse, pas de promesses fausses ; tu respectes le client tout en maximisant la clarté de l'offre. Réponds dans la langue de l'utilisateur. N'invente aucune statistique."
    ),
    "contenu": (
        "MODE STRATÈGE CONTENU CRÉATEUR.\n"
        "L'utilisateur vient pour créer et publier du contenu plus vite (TikTok, Reels, Shorts, LinkedIn, YouTube, newsletter).\n"
        "MÉTHODE : tu mobilises les biais cognitifs d'attention et de mémorisation et les déclencheurs émotionnels qui arrêtent le scroll.\n"
        "FORMAT DE RÉPONSE :\n"
        "1. **Accroche (3 premières secondes)** : 2 à 3 propositions d'hook avec le biais cognitif activé pour chacune.\n"
        "2. **Structure du contenu** : plan clair (hook → corps → preuve → CTA).\n"
        "3. **Titres cliquables** : 3 titres optimisés.\n"
        "4. **Idée de miniature / visuel** : 1 proposition concrète de visuel accrocheur.\n"
        "5. **Levier psycho principal** : le biais cognitif ou l'émotion clé expliqué simplement.\n"
        "RÈGLES : pas de promesses trompeuses, pas de statistiques inventées. Réponds dans la langue de l'utilisateur."
    ),
    "site": (
        "MODE BÂTISSEUR DE SITE / PAGE.\n"
        "L'utilisateur vient pour créer un site ou une page de présentation.\n"
        "MÉTHODE : psychologie de la conversion, charge cognitive, hiérarchie visuelle, preuve sociale et CTA clair.\n"
        "FORMAT DE RÉPONSE :\n"
        "1. **Structure de la page** : sections dans l'ordre logique.\n"
        "2. **Texte de chaque section** : proposition prête à l'emploi.\n"
        "3. **Appel à l'action** : CTA précis ancré dans un bénéfice.\n"
        "4. **Conseils visuels** : points clés pour réduire la friction.\n"
        "5. **Si Bea Ultra** : propose en plus un fichier HTML one-page prêt à l'emploi.\n"
        "RÈGLES : pas de statistiques inventées. Réponds dans la langue de l'utilisateur."
    ),
    "code": (
        "MODE COACH CODE.\n"
        "Tu aides à comprendre, déboguer et améliorer du code. Quand tu proposes une correction, donne le code complet corrigé dans un bloc de code, puis explique brièvement les changements. Réponds dans la langue de l'utilisateur."
    ),
    "general": None,
    "scolaire": (
        "MODE ACCOMPAGNEMENT SCOLAIRE.\n"
        "L'utilisateur vient pour être accompagné dans sa scolarité : devoirs, révisions, méthodologie, préparation aux contrôles.\n"
        "MÉTHODE : active recall, espacement, méthode Feynman, blocs de temps-pomodoro.\n"
        "FORMAT DE RÉPONSE :\n"
        "1. **Compréhension** : reformule la consigne en une phrase simple.\n"
        "2. **Résolution / explication** : étape par étape.\n"
        "3. **Vérification** : contrôle rapide pour s'assurer que l'élève a compris.\n"
        "4. **Astuce mémorisation** : mnémotechnique ou analogie.\n"
        "5. **Pour aller plus loin** : question ou exercice facultatif.\n"
        "RÈGLES : ne fais JAMAIS le devoir noté à la place de l'élève : guide et explique."
    ),
}

SYSTEM_CODE = ("Tu es l'IA code de Bea. Tu aides à comprendre, déboguer et améliorer du code. Réponds en français sauf demande contraire. "
               "Quand tu proposes une correction, donne le code complet corrigé dans un bloc de code puis explique brièvement les changements.")

SYSTEM_MONTAGE = ("Tu es monteur vidéo et stratège de contenu. Produis un plan de montage concret : "
                  "hook des 3 premières secondes, découpage en séquences, style des sous-titres, musique, CTA, titres et miniature.")

SYSTEM_APP = ("Tu es un product builder senior. Tu génères une application web complète et réellement utilisable dans UN SEUL fichier HTML autonome (HTML + CSS + JavaScript vanilla). "
              "Contraintes : aucune ressource externe, aucun CDN, aucun appel réseau ; sauvegarde locale possible avec localStorage ; interface soignée et responsive. "
              "Réponds uniquement avec le fichier HTML complet dans un bloc ```html, sans explication avant ou après.")

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
    if p.get("profile_type"):
        extra.append(f"Profil déclaré : {p['profile_type']}.")
    if p.get("study_country"):
        extra.append(f"Pays d'études : {p['study_country']}.")
    if p.get("study_level"):
        extra.append(f"Niveau d'études : {p['study_level']}.")
    if mems:
        extra.append("Mémoire sur l'utilisateur : " + "; ".join([m.get('content','')[:120] for m in mems[:5]]))
    base = SYSTEM_BEHAVIOR_BASE
    plan = st.session_state.plan
    allowed = PLAN_ALLOWED_USE_CASES.get(plan, ("general",))
    use_case = p.get("use_case")
    if use_case not in allowed:
        use_case = "general"
    spec = SYSTEM_USE_CASES.get(use_case) if use_case else None
    if spec:
        base = base + "\n\n" + spec
    return base + ("\n\n" + "\n".join(extra) if extra else "")

def stream_groq(messages, max_tokens=2600, model_override=None, temperature=0.3):
    if model_override:
        requested = list(model_override) if isinstance(model_override, (list, tuple)) else [model_override]
        try:
            available_fallbacks = get_modeles().get("puissant", []) + get_modeles().get("rapide", [])
        except Exception:
            available_fallbacks = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
        models = list(dict.fromkeys(requested + available_fallbacks))
    else:
        models = get_modeles().get(st.session_state.model_choice, get_modeles()["rapide"])
    last, started = None, False
    for mid in models:
        try:
            stream = get_groq().chat.completions.create(
                model=mid,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
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

def persist_auth_session(session):
    access_token = getattr(session, "access_token", None) or (session.get("access_token") if isinstance(session, dict) else "")
    refresh_token = getattr(session, "refresh_token", None) or (session.get("refresh_token") if isinstance(session, dict) else "")
    if not access_token or not refresh_token:
        return
    data = json.dumps({"access": access_token, "refresh": refresh_token})
    payload = base64.urlsafe_b64encode(data.encode()).decode()
    components.html(f"""
    <script>
    (function() {{
        const payload = {json.dumps(payload)};
        window.parent.document.cookie = "{AUTH_COOKIE_NAME}=" + payload + "; Max-Age={AUTH_COOKIE_MAX_AGE}; Path=/; SameSite=Lax";
        try {{ window.parent.localStorage.setItem("{AUTH_COOKIE_NAME}", payload); }} catch(e) {{}}
    }})();
    </script>
    """, height=0)

def clear_auth_session():
    st.session_state["just_logged_out"] = True
    components.html(f"""
    <script>
    (function() {{
        window.parent.document.cookie = "{AUTH_COOKIE_NAME}=; Max-Age=0; Path=/; SameSite=Lax";
        try {{ window.parent.localStorage.removeItem("{AUTH_COOKIE_NAME}"); }} catch(e) {{}}
    }})();
    </script>
    """, height=0)

def restore_auth_session():
    if st.session_state.get("just_logged_out", False):
        return False
    try:
        context = getattr(st, "context", None)
        cookies = getattr(context, "cookies", {}) if context else {}
        raw = cookies.get(AUTH_COOKIE_NAME, "")
        if not raw:
            return False
        data = json.loads(base64.urlsafe_b64decode(raw.encode()).decode())
        access_tok = data.get("access")
        refresh_tok = data.get("refresh")
        if not access_tok or not refresh_tok:
            return False

        client = new_client()
        result = client.auth.set_session(access_tok, refresh_tok)
        session = getattr(result, "session", None)
        user = getattr(session, "user", None) if session else None
        if not user:
            return False
        st.session_state.sb, st.session_state.user = client, user
        load_account()
        return True
    except Exception:
        return False

def purge_entire_session():
    keys_to_preserve = {"landing_tab", "landing_language"}
    for k in list(st.session_state.keys()):
        if k not in keys_to_preserve:
            del st.session_state[k]
    st.session_state.sb = None
    st.session_state.user = None
    st.session_state.page = "chat"
    st.session_state.plan = "free"
    st.session_state.messages = []
    st.session_state.code_messages = []
    st.session_state.quota = {}
    st.session_state.prefs = {}
    st.session_state.memories = []
    st.session_state.is_admin = False
    st.session_state.dev_mode = None
    st.session_state.code_area = DEFAULT_CODE
    st.session_state.just_logged_out = True

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
        rows = sb().table("preferences").select("*").eq("user_id", uid()).execute().data
        st.session_state.prefs = rows[0] if rows else {}
    except Exception:
        try:
            rows = sb().table("preferences").select("display_name,style,goal,profile_type,use_case").eq("user_id", uid()).execute().data
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
    if e is not None:
        detail = str(e).lower()
        if "row-level security" in detail or "permission" in detail:
            st.error("Ton compte est bien connecté, mais l'enregistrement du profil a été refusé. Recharge la page et réessaie.")
            return
        if "column" in detail or "schema cache" in detail:
            st.error("Le service de profil est momentanément indisponible. Ce problème n'est pas lié à ton offre payante. Recharge la page et réessaie.")
            return
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
            c0,c1,c2,c3,c4,c5 = st.columns([1,1,1,1,1,2])
            with c0:
                if st.button("🔊", key=f"speak_{idx}", help="Écouter Bea (Web Speech)"):
                    clean_speech = json.dumps(m["content"].replace("**","").replace("#","").replace("`","")[:3500])
                    components.html(f"""
                    <script>
                    if ('speechSynthesis' in window) {{
                        window.speechSynthesis.cancel();
                        const u = new SpeechSynthesisUtterance({clean_speech});
                        u.lang = 'fr-FR';
                        u.rate = 1.02;
                        u.pitch = 1.05;
                        const v = window.speechSynthesis.getVoices().find(x => x.lang.startsWith('fr'));
                        if (v) u.voice = v;
                        window.speechSynthesis.speak(u);
                    }}
                    </script>
                    """, height=0)
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
        mid = sb().table("messages").insert({"conversation_id": st.session_state.conv_id, "user_id": uid(), "role": "assistant", "content": text}).execute().data[0]["id"]
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
        mid = sb().table("messages").insert({"conversation_id": st.session_state.conv_id, "user_id": uid(), "role": "user", "content": text, "attachment_name": att_name, "attachment_text": att_text}).execute().data[0]["id"]
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
        ("bea", c1, "Bea : 9 € par mois", "L'IA de base, sans personnalisation", STRIPE_BEA_9, "Choisir Bea - 9 €"),
        ("pro", c2, "Bea Pro : 14,90 € par mois", "Bea + prompts spécialisés + outils créateurs", STRIPE_PRO_1490, "Choisir Bea Pro - 14,90 €"),
        ("abo", c3, "Bea Ultra : 16 € par mois", "Tout illimité : app, studio, code, aucun plafond", STRIPE_ABO_16, "S'abonner - 16 €"),
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
                            "**L'IA comportementale de base, sans personnalisation.**\n"
                            "- Chat avec limite de messages (25 / mois)\n"
                            "- Analyse des comportements, plans d'action\n"
                            "- Historique et fichiers joints\n"
                            "- Mémoire et dictée vocale\n"
                            "- ❌ Aucun prompt personnalisé\n"
                            "- ❌ Pas de studio créateur ni de génération d'app web"
                        )
                    elif key == "pro":
                        st.markdown(
                            "**Tout Bea, plus les prompts spécialisés et les outils créateurs.**\n"
                            "- 60 requêtes chat + 30 requêtes code / mois\n"
                            "- Prompts personnalisés : Analyse clients, Stratégie contenu, Accompagnement scolaire\n"
                            "- Sous-titres automatiques (SRT/VTT)\n"
                            "- Miniatures 1280×720 & plans de montage\n"
                            "- Montage style Canva & exports\n"
                            "- ❌ Génération d'app web réservée à Bea Ultra"
                        )
                    else:
                        st.markdown(
                            "**Tout Bea Pro, sans aucune limite.**\n"
                            "- Aucune limite de messages (usage équitable)\n"
                            "- Génération d'app web complète (HTML unique)\n"
                            "- Tous les prompts spécialisés + Coach code\n"
                            "- Studio créateur complet\n"
                            "- Quotas très larges"
                        )
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
            if st.session_state.sb:
                st.session_state.sb.auth.sign_out()
        except Exception:
            pass
        clear_auth_session()
        purge_entire_session()
        st.rerun()

# ==============================================================================
# LABO DEV IA - SYNCHRONISATION GITHUB & MODIFICATION PAR NIVEAU
# ==============================================================================

def sync_code_to_github(new_code: str, commit_message: str) -> tuple[bool, str]:
    gh_token = st.secrets.get("GITHUB_TOKEN")
    gh_repo = st.secrets.get("GITHUB_REPOSITORY")
    gh_branch = st.secrets.get("GITHUB_BRANCH", "main")
    gh_path = st.secrets.get("GITHUB_FILE_PATH", "app.py")

    if not gh_token or not gh_repo:
        return False, "GITHUB_TOKEN ou GITHUB_REPOSITORY non configuré dans les secrets."

    headers = {
        "Authorization": f"Bearer {gh_token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Bea-Dev-Lab"
    }
    url = f"https://api.github.com/repos/{gh_repo}/contents/{gh_path}?ref={gh_branch}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            current_sha = data.get("sha")
    except urllib.error.HTTPError as e:
        return False, f"Lecture GitHub échouée ({e.code}) : {e.reason}"
    except Exception as e:
        return False, f"Connexion GitHub impossible : {str(e)}"

    content_b64 = base64.b64encode(new_code.encode("utf-8")).decode("utf-8")
    payload = {
        "message": f"🤖 [Bea Lab] {commit_message}",
        "content": content_b64,
        "sha": current_sha,
        "branch": gh_branch
    }

    try:
        put_req = urllib.request.Request(
            f"https://api.github.com/repos/{gh_repo}/contents/{gh_path}",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="PUT"
        )
        with urllib.request.urlopen(put_req) as resp:
            if resp.status in (200, 201):
                return True, f"Commit poussé avec succès sur {gh_repo} ({gh_branch})."
            return False, f"Code retour GitHub : {resp.status}"
    except urllib.error.HTTPError as e:
        return False, f"Écriture GitHub refusée ({e.code}) : {e.read().decode()}"
    except Exception as e:
        return False, f"Erreur commit GitHub : {str(e)}"

LAB_LEVELS = {
    "1": {
        "title": "🎨 Niveau 1 : Cosmétique & UI",
        "badge": "Niveau 1 - Zéro risque",
        "scope": "Textes, boutons, couleurs, styles CSS, messages d'accueil",
        "description": "Modifie les libellés, styles CSS, palettes de couleurs ou textes sans toucher à la logique Python.",
        "targets": {
            "Styles CSS globaux (classes, fonds, bordures)": "CSS_STYLES",
            "Cartes d'accroche (STARTER_CARDS)": "STARTER_CARDS",
            "Styles de réponse de Bea (STYLE_HINT)": "STYLE_HINT",
            "Textes de la page d'accueil (page_vitrine)": "page_vitrine",
            "Barre latérale & badges (render_sidebar)": "render_sidebar",
        },
        "presets": [
            "Changer le texte d'accueil de Bea pour le rendre plus direct et orienté action",
            "Remplacer la couleur violette d'accent par un bleu électrique #2563eb",
            "Ajouter 3 nouvelles questions d'accroche pour les indépendants dans STARTER_CARDS",
            "Modifier le libellé du bouton Se connecter en Continuer vers Bea"
        ]
    },
    "2": {
        "title": "🧩 Niveau 2 : Page ou Fonction isolée",
        "badge": "Niveau 2 - Chirurgical",
        "scope": "Une fonction de page ciblée (chat, studio, code, onboarding, compte...)",
        "description": "Isole et modifie uniquement la fonction ciblée.",
        "targets": {
            "💬 Page Chat (page_chat)": "page_chat",
            "🎬 Page Studio Créateur (page_studio)": "page_studio",
            "💻 Page Éditeur de Code (page_code)": "page_code",
            "🌐 Page Atelier Web HTML (page_app)": "page_app",
            "🎓 Page Parcours d'Accueil (page_onboarding)": "page_onboarding",
            "🎨 Page Personnalisation (page_perso)": "page_perso",
            "💎 Page Compte & Offres (page_compte)": "page_compte",
            "🧠 Page Mémoire (page_memoire)": "page_memoire",
            "📁 Page Projets Enregistrés (page_projets)": "page_projets",
            "🚪 Page Portail Développeur (page_dev_portal)": "page_dev_portal",
            "📌 Barre Latérale Complète (render_sidebar)": "render_sidebar",
            "🌐 Page Vitrine & Auth (page_vitrine)": "page_vitrine",
        },
        "presets": [
            "Ajouter un bouton pour copier la réponse en format Markdown dans page_chat",
            "Ajouter un compteur de caractères sous la zone de texte dans page_code",
            "Ajouter un filtre par format de réseau social dans page_studio",
            "Ajouter un bouton de test rapide dans la page de personnalisation"
        ]
    },
    "3": {
        "title": "🧠 Niveau 3 : Moteur Comportemental & Prompts IA",
        "badge": "Niveau 3 - Intelligence IA",
        "scope": "Prompts système, biais cognitifs, règles d'analyse comportementale",
        "description": "Ajuste la psychologie et la méthode d'analyse de Bea.",
        "targets": {
            "Système de prompt dynamique (system_behavior)": "system_behavior",
            "Comportement de base de Bea (SYSTEM_BEHAVIOR_BASE)": "SYSTEM_BEHAVIOR_BASE",
            "Cas d'usage spécialisés (SYSTEM_USE_CASES)": "SYSTEM_USE_CASES",
            "Prompt de l'IA Code (SYSTEM_CODE)": "SYSTEM_CODE",
            "Prompt du Monteur Vidéo (SYSTEM_MONTAGE)": "SYSTEM_MONTAGE",
            "Prompt du Bâtisseur d'App Web (SYSTEM_APP)": "SYSTEM_APP",
        },
        "presets": [
            "Renforcer l'analyse des biais cognitifs dans SYSTEM_USE_CASES clients",
            "Ajouter une étape 'Micro-défi du jour' dans SYSTEM_BEHAVIOR_BASE",
            "Adapter le prompt scolaire pour toujours donner une analogie du quotidien",
            "Rendre le prompt du bâtisseur web encore plus strict sur le responsive mobile"
        ]
    },
    "4": {
        "title": "⚡ Niveau 4 : Nouveau Module ou Fonctionnalité",
        "badge": "Niveau 4 - Évolution fonctionnelle",
        "scope": "Ajout de nouvelle page, nouvelle section studio, nouveau profil utilisateur",
        "description": "Ajoute une nouvelle brique fonctionnelle dans Bea.",
        "targets": {
            "Nouveau profil utilisateur (PROFILE_OPTIONS)": "PROFILE_OPTIONS",
            "Nouvel outil dans le Studio (STUDIO_SECTIONS)": "STUDIO_SECTIONS",
            "Nouveau use-case dans l'onboarding (USE_CASE_OPTIONS)": "USE_CASE_OPTIONS",
            "Nouvelle page complète dans l'application": "NEW_PAGE",
        },
        "presets": [
            "Ajouter une option de profil 'Artisan / Commerçant' dans PROFILE_OPTIONS",
            "Ajouter un outil 'Script Téléprompteur' dans STUDIO_SECTIONS",
            "Ajouter une section 'Journal d'habitudes' dans le menu latéral"
        ]
    },
    "5": {
        "title": "🏛️ Niveau 5 : Architecture Complète (Full-Stack)",
        "badge": "Niveau 5 - Refonte globale",
        "scope": "Fichier app.py complet",
        "description": "Modifications transversales avec validation de syntaxe intégrale.",
        "targets": {
            "Fichier complet app.py (Architecture)": "FULL_FILE",
        },
        "presets": [
            "Optimiser la gestion du cache et des modèles Groq",
            "Renforcer la gestion des erreurs réseau et de reconnexion"
        ]
    }
}

def extract_target_code(full_code: str, target: str) -> str:
    if not full_code:
        return ""
    if target == "FULL_FILE":
        return full_code
    if target == "CSS_STYLES":
        m = re.search(r'st\.markdown\(f?"""\s*<style>[\s\S]*?</style>\s*"""', full_code)
        return m.group(0) if m else ""
    if target in ("SYSTEM_BEHAVIOR_BASE", "SYSTEM_USE_CASES", "STARTER_CARDS", "STYLE_HINT", "PLANS", "STUDIO_SECTIONS", "PROFILE_OPTIONS", "USE_CASE_OPTIONS", "SYSTEM_CODE", "SYSTEM_MONTAGE", "SYSTEM_APP"):
        m = re.search(rf'^{target}\s*=\s*[\s\S]*?(?=\n\n[A-Z_a-z]|\n\ndef |\Z)', full_code, re.MULTILINE)
        return m.group(0) if m else ""
    if target == "NEW_PAGE":
        return "# Exemple pour ajouter une page:\ndef page_journal():\n    st.markdown('### 📔 Mon Journal')\n    st.info('Journal personnel')"
    m = re.search(rf'def {target}\(.*?\)[\s\S]*?(?=\n\ndef |\n\n[A-Z_a-z0-9]+\s*=|\Z)', full_code)
    return m.group(0) if m else ""

def inject_target_code(full_code: str, target: str, new_code: str) -> str:
    if target == "FULL_FILE":
        return new_code
    pattern = None
    if target == "CSS_STYLES":
        pattern = re.compile(r'st\.markdown\(f?"""\s*<style>[\s\S]*?</style>\s*"""\)')
    elif target in ("SYSTEM_BEHAVIOR_BASE", "SYSTEM_USE_CASES", "STARTER_CARDS", "STYLE_HINT", "PLANS", "STUDIO_SECTIONS", "PROFILE_OPTIONS", "USE_CASE_OPTIONS", "SYSTEM_CODE", "SYSTEM_MONTAGE", "SYSTEM_APP"):
        pattern = re.compile(rf'^{target}\s*=\s*[\s\S]*?(?=\n\n[A-Z_a-z]|\n\ndef |\Z)', re.MULTILINE)
    elif target == "NEW_PAGE":
        insert_marker = "\nrender_sidebar()"
        if insert_marker in full_code:
            return full_code.replace(insert_marker, "\n\n" + new_code + "\n\n" + insert_marker, 1)
        return full_code + "\n\n" + new_code
    else:
        pattern = re.compile(rf'def {target}\(.*?\)[\s\S]*?(?=\n\ndef |\n\n[A-Z_a-z0-9]+\s*=|\Z)')

    match = pattern.search(full_code) if pattern else None
    if match:
        start, end = match.span()
        suffix = "\n\n" if not new_code.endswith("\n") else ""
        return full_code[:start] + new_code + suffix + full_code[end:]
    return full_code

def validate_python_code(code_str: str):
    try:
        ast.parse(code_str)
        return True, "Syntaxe Python valide."
    except SyntaxError as e:
        return False, f"Erreur de syntaxe ligne {e.lineno} : {e.msg}"
    except Exception as e:
        return False, f"Erreur de structure : {str(e)}"

def page_dev_lab():
    st.markdown("### 🧪 Labo Dev IA — Modifier l’application")
    q = st.session_state.quota.get('code') or {}
    st.markdown(f'<div class="limit-badge">Modèle: {st.session_state.dev_model_choice} · Quota code: {q.get("used","?")}/{q.get("limit","?")}</div>', unsafe_allow_html=True)

    tab_lab, tab_diff, tab_backups, tab_guide = st.tabs([
        "1. Modifier", "2. Diff & Validation", "3. Sauvegardes", "Guide"
    ])

    try:
        with open(__file__, 'r', encoding='utf-8') as fh:
            full_code = fh.read()
    except Exception:
        full_code = ""

    with tab_lab:
        c_lev, c_mod = st.columns([1.6, 1.4])
        with c_lev:
            level_key = st.selectbox("Niveau", list(LAB_LEVELS.keys()), format_func=lambda k: LAB_LEVELS[k]["title"], key="lab_level_choice")
            lvl_info = LAB_LEVELS[level_key]
            st.caption(f"**Portée :** {lvl_info['scope']}")
        with c_mod:
            st.selectbox("Cerveau IA", list(DEV_MODELES.keys()), key="dev_model_choice")
            st.text_input("Nom sauvegarde", value=f"backup_lvl{level_key}_{datetime.now().strftime('%Y%m%d_%H%M')}", key="dev_backup_name")

        st.divider()
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1:
            target_labels = list(lvl_info["targets"].keys())
            chosen_label = st.selectbox("Élément ciblé", target_labels, key=f"target_sel_{level_key}")
            target_id = lvl_info["targets"][chosen_label]
        with col_t2:
            apply_mode = st.radio("Application", ["Prévisualiser le diff", "1-Clic direct"], key="lab_apply_mode")

        st.markdown("**Suggestions**")
        p_cols = st.columns(len(lvl_info["presets"]))
        for i, preset in enumerate(lvl_info["presets"]):
            with p_cols[i]:
                if st.button(preset[:32] + "...", key=f"btn_preset_{level_key}_{i}", help=preset, use_container_width=True):
                    st.session_state["dev_consigne"] = preset
                    st.rerun()

        consigne = st.text_area("Consigne", height=120, placeholder="Ce que tu souhaites modifier...", key="dev_consigne")
        code_cible = extract_target_code(full_code, target_id)
        with st.expander(f"Code source actuel ({target_id})"):
            st.code(code_cible[:2500] + ("\n... [suite tronquée]" if len(code_cible) > 2500 else ""), language="python")

        btn_label = "APPLIQUER LA MODIFICATION" if apply_mode.startswith("1-Clic") else "GÉNÉRER L’APERÇU"
        launch = st.button(btn_label, key="dev_go_level", use_container_width=True, type="primary")

        if launch and consigne.strip():
            if not rate_ok() or not quota_ok("code"):
                st.stop()

            try:
                sb().table("code_projects").insert({
                    "user_id": uid(), "name": st.session_state.dev_backup_name, "language": "python", "content": full_code
                }).execute()
            except Exception:
                pass

            model_id = DEV_MODELES.get(st.session_state.dev_model_choice, "openai/gpt-oss-120b")
            model_fallbacks = [model_id, "openai/gpt-oss-120b", "openai/gpt-oss-20b"]

            SYSTEM_DEV = f"""Tu es un ingénieur senior chargé de modifier le code réel de Bea.
CIBLE : {target_id}
RÈGLES :
- Fournis le code complet de la cible sans omissions, sans placeholders (pas de 'reste inchangé').
- Rends uniquement du code dans un bloc ```python ... ```."""

            with st.spinner(f"Génération avec {model_id}..."):
                try:
                    raw = "".join(stream_groq([
                        {"role": "system", "content": SYSTEM_DEV},
                        {"role": "user", "content": f"CODE ACTUEL :\n{code_cible}\n\nCONSIGNE :\n{consigne}"}
                    ], 16000, model_override=model_fallbacks, temperature=0.1))

                    mm = re.search(r'```(?:python)?\s*(.*?)```', raw, re.DOTALL | re.IGNORECASE)
                    new_block = mm.group(1).strip() if mm else raw.strip()

                    final_code = inject_target_code(full_code, target_id, new_block)
                    is_valid, validation_msg = validate_python_code(final_code)
                    if not is_valid:
                        st.error(f"Annulé pour sécurité : {validation_msg}")
                    else:
                        diff = difflib.unified_diff(
                            full_code.splitlines(), final_code.splitlines(),
                            fromfile="actuel.py", tofile="modifie.py", lineterm=""
                        )
                        st.session_state["dev_last_diff"] = "\n".join(list(diff))
                        st.session_state["dev_pending_code"] = final_code

                        if apply_mode.startswith("1-Clic"):
                            with open(__file__, 'w', encoding='utf-8') as f:
                                f.write(final_code)
                            quota_consume("code")
                            synced, gh_msg = sync_code_to_github(final_code, f"Modif {target_id}")
                            st.success(f"✅ MODIFICATION APPLIQUÉE ! ({gh_msg})")
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.success("✅ Code validé ! Vérifie dans l'onglet Diff.")
                except Exception as e:
                    st.error(f"Échec : {e}")

    with tab_diff:
        st.markdown("#### 🔍 Comparaison des changements (Diff)")
        pending_code = st.session_state.get("dev_pending_code")
        diff_text = st.session_state.get("dev_last_diff")
        if diff_text:
            st.code(diff_text[:12000], language="diff")
            if pending_code:
                if st.button("✅ CONFIRMER ET ÉCRIRE LE CODE", key="apply_pending_code", type="primary", use_container_width=True):
                    with open(__file__, 'w', encoding='utf-8') as f:
                        f.write(pending_code)
                    quota_consume("code")
                    synced, gh_msg = sync_code_to_github(pending_code, "Validation diff")
                    st.success(f"✅ MODIFICATION APPLIQUÉE ! ({gh_msg})")
                    st.session_state["dev_pending_code"] = None
                    time.sleep(1.5)
                    st.rerun()
        else:
            st.info("Aucune modification en attente.")

    with tab_backups:
        st.markdown("#### 💾 Sauvegardes")
        try:
            projs = sb().table("code_projects").select("id,name,updated_at,content").order("updated_at", desc=True).limit(10).execute().data or []
            if projs:
                for p in projs:
                    col_b1, col_b2, col_b3 = st.columns([2, 1, 1])
                    with col_b1:
                        st.markdown(f"**{p['name']}**")
                        st.caption(p.get("updated_at", "")[:19])
                    with col_b2:
                        st.download_button("Télécharger", p.get("content", ""), file_name=f"{p['name']}.py", key=f"dl_bk_{p['id']}", use_container_width=True)
                    with col_b3:
                        if st.button("Restaurer", key=f"restore_bk_{p['id']}", use_container_width=True):
                            with open(__file__, 'w', encoding='utf-8') as f:
                                f.write(p.get("content", ""))
                            sync_code_to_github(p.get("content", ""), f"Restauration {p['name']}")
                            st.success(f"Sauvegarde {p['name']} restaurée !")
                            time.sleep(1.5)
                            st.rerun()
        except Exception as e:
            st.warning("Impossible de lister les sauvegardes : " + str(e))

    with tab_guide:
        st.markdown("""
        - **Niveau 1** : Textes, CSS, styles, cartes.
        - **Niveau 2** : Une page ou fonction isolée.
        - **Niveau 3** : Comportement et prompts IA.
        - **Niveau 4** : Nouveau module ou menu.
        - **Niveau 5** : Fichier complet.
        """)

    st.divider()
    c_ret1, c_ret2 = st.columns(2)
    with c_ret1:
        if st.button("← Retour portail", key="back_portal_lvl", use_container_width=True):
            st.session_state.page = "dev_portal"
            st.rerun()
    with c_ret2:
        if st.button("🌐 Ouvrir le site fonctionnel", key="to_prod_from_lab_lvl", use_container_width=True):
            st.session_state.dev_mode = "prod"
            st.session_state.page = "chat"
            st.rerun()

def page_vitrine():
    nav_a, nav_b, nav_spacer, nav_c = st.columns([1, 1.35, 4.8, 1])
    with nav_a:
        if st.button("Offres", key="landing_offers", use_container_width=True):
            st.session_state.landing_tab = "offres"
            st.rerun()
    with nav_b:
        if st.button("BehaviorLab AI", key="landing_about", use_container_width=True):
            st.session_state.landing_tab = "about"
            st.rerun()
    with nav_c:
        st.selectbox("Langues", ["Français", "English"], key="landing_language", label_visibility="collapsed")
    if LOGO:
        _, c, _ = st.columns([1, 0.3, 1])
        with c:
            st.image(LOGO, width=96)
    st.markdown('<div class="claude-title">Bea</div><div class="claude-sub">BehaviorLab AI</div>', unsafe_allow_html=True)
    landing_tab = st.session_state.get("landing_tab", "connexion")
    if landing_tab == "about":
        st.markdown("""
        <div class="landing-copy">
            <h2>Une intelligence artificielle pensée pour votre progression</h2>
            <p><strong>BehaviorLab AI</strong> développe des IA dédiées à votre réussite en analysant les mécanismes comportementaux concrets.</p>
        </div>
        """, unsafe_allow_html=True)
    elif landing_tab == "offres":
        st.markdown("""
        <div class="landing-copy">
            <h2>Choisissez le niveau d'accompagnement qui vous convient</h2>
        </div>
        """, unsafe_allow_html=True)
        render_offers()
    else:
        st.markdown("""
        <div class="landing-copy">
            <h2>Clarifiez vos idées. Comprenez vos blocages. Avancez.</h2>
            <p>Bea vous accompagne pour transformer vos intentions en actions concrètes.</p>
        </div>
        """, unsafe_allow_html=True)

    _, col, _ = st.columns([0.5, 1.6, 0.5])
    with col:
        with st.container(border=True):
            if st.session_state.auth_notice:
                st.info(st.session_state.auth_notice)
            t_in, t_up, t_rst = st.tabs(["Se connecter", "Créer un compte", "Mot de passe oublié"])
            with t_in:
                pend = st.session_state.pending_login
                if pend:
                    st.info(f"Un code a été envoyé à {pend['email']}.")
                    with st.form("form_code"):
                        code = st.text_input("Code reçu", key="li_code", max_chars=10)
                        go_code = st.form_submit_button("Valider le code", use_container_width=True)
                    if go_code:
                        try:
                            d = new_client()
                            res = d.auth.verify_otp({"email": pend["email"], "token": code.strip(), "type": "email"})
                            st.session_state.sb, st.session_state.user = d, res.user
                            st.session_state.pop("just_logged_out", None)
                            persist_auth_session(getattr(res, "session", None))
                            st.session_state.pending_login = None
                            st.session_state.auth_notice = ""
                            load_account()
                            st.rerun()
                        except Exception:
                            st.error("Code invalide ou expiré.")
                else:
                    with st.form("form_login"):
                        email = st.text_input("Adresse e-mail", key="li_email")
                        pwd = st.text_input("Mot de passe", type="password", key="li_pwd")
                        go = st.form_submit_button("Continuer", use_container_width=True)
                    if go:
                        login_attempts = st.session_state.setdefault("_login_attempts", [])
                        now_ts = time.time()
                        st.session_state._login_attempts = [t for t in login_attempts if now_ts - t < 60]
                        if len(st.session_state._login_attempts) >= 5:
                            st.error("Trop de tentatives infructueuses. Attends 60 secondes.")
                            st.stop()

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
                            st.session_state.pop("just_logged_out", None)
                            persist_auth_session(getattr(res, "session", None))
                            st.session_state.auth_notice = ""
                            load_account()
                            st.rerun()
                        except Exception as e:
                            st.session_state._login_attempts.append(now_ts)
                            if "confirm" in str(e).lower():
                                st.session_state.pending_confirmation_email = email.strip()
                                st.error("Adresse non confirmée. Re-vérifie tes e-mails.")
                            else:
                                st.error("Identifiants invalides.")
            with t_up:
                email2 = st.text_input("Adresse e-mail", key="su_email")
                pwd2 = st.text_input("Mot de passe", type="password", key="su_pwd")
                strength_label, strength_color, strength_tip = password_strength(pwd2)
                if strength_label:
                    st.markdown(f'<span style="color:{strength_color};font-size:12px;">{strength_label} : {strength_tip}</span>', unsafe_allow_html=True)
                with st.expander("Politique de confidentialité"):
                    st.markdown(privacy_md())
                ok_cgu = st.checkbox("J'accepte la politique de confidentialité", key="su_cgu")
                go2 = st.button("Créer mon compte", key="signup_create_button", use_container_width=True, type="primary")
                if go2:
                    if len(pwd2) < 8 or "@" not in email2:
                        st.error("E-mail invalide ou mot de passe trop court (8 car. min).")
                    elif not ok_cgu:
                        st.error("Coche la case pour continuer.")
                    else:
                        try:
                            c = new_client()
                            res = c.auth.sign_up({"email": email2.strip(), "password": pwd2})
                            if getattr(res, "session", None):
                                st.session_state.sb, st.session_state.user = c, res.user
                                st.session_state.pop("just_logged_out", None)
                                persist_auth_session(getattr(res, "session", None))
                                load_account()
                                st.rerun()
                            else:
                                st.success("Compte créé ! Confirme ton e-mail pour te connecter.")
                        except Exception:
                            st.error("Création impossible.")
            with t_rst:
                email3 = st.text_input("Adresse e-mail", key="rs_email")
                if st.button("Envoyer le lien de réinitialisation", key="btn_rst", use_container_width=True):
                    try:
                        c = new_client()
                        fn = getattr(c.auth, "reset_password_for_email", None) or getattr(c.auth, "reset_password_email")
                        fn(email3.strip())
                    except Exception:
                        pass
                    st.success("Si ce compte existe, un e-mail a été envoyé.")

STUDIO_SECTIONS = [
    ("composer", "🎨 Composer", "Éditeur visuel avec modèles façon Canva", "free"),
    ("assistant_ia", "✨ Assistant IA du studio", "Idées, textes, scripts et conseils de création", "free"),
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
            if st.button("← Retour à Bea", key="back_bea", use_container_width=True):
                st.session_state.page = "chat"
                st.rerun()
            st.divider()
            current = st.session_state.studio_menu
            moved_to_editor = {"texte", "effets", "transitions", "filtres", "ajustement"}
            for key, title, desc, req_plan in STUDIO_SECTIONS:
                if key in moved_to_editor:
                    continue
                is_locked = req_plan != "free" and st.session_state.plan == "free"
                active = "● " if key == current else "   "
                if st.button(f"{active}{title}", key=f"studio_menu_{key}", use_container_width=True, help=desc):
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
        st.selectbox("Modèle", ["rapide","puissant"], key="model_choice")
        if st.button("✨ Nouvelle discussion", key="nav_new", use_container_width=True):
            new_chat()
            st.rerun()
        for label, pg in [("💬 Chat", "chat"), ("💻 Code", "code"), ("🌐 App web (Ultra)", "app"), ("🎬 Studio créateur", "studio"), ("📁 Projets", "projets"), ("🧠 Mémoire", "memoire"), ("🎨 Personnalisation", "perso"), ("💎 Compte & offres", "compte")]:
            if st.button(label, key=f"nav_{pg}", use_container_width=True):
                st.session_state.page = pg
                st.rerun()
        
        current_email = (st.session_state.user.email or "").lower().strip() if st.session_state.user else ""
        is_you = current_email == "saydoukebe31@gmail.com" or (DEV_EMAIL and current_email == DEV_EMAIL.lower().strip())
        
        if is_you:
            st.divider()
            st.markdown('<div style="font-size:10px; color:#a855f7; font-weight:800; margin-bottom:8px;">ZONE DEV PRIVÉE</div>', unsafe_allow_html=True)
            if not st.session_state.is_admin and DEV_ACCESS_KEY:
                with st.expander("🔒 Clé dev", expanded=True):
                    with st.form("dev_key_form"):
                        k = st.text_input("Clé dev", type="password")
                        if st.form_submit_button("Déverrouiller", use_container_width=True, type="primary"):
                            if k.strip() == DEV_ACCESS_KEY.strip():
                                st.session_state.dev_key_ok = True
                                check_admin()
                                st.rerun()
            if st.session_state.is_admin:
                if st.button("🛠️ Portail Dev", key="nav_dev_portal", use_container_width=True):
                    st.session_state.dev_mode = None
                    st.session_state.page = "dev_portal"
                    st.rerun()
                if st.button("🧪 Labo IA", key="nav_dev_lab", use_container_width=True):
                    st.session_state.dev_mode = "lab"
                    st.session_state.page = "dev_lab"
                    st.rerun()

        convs = get_convs()
        if convs:
            st.markdown('<div style="font-size:10px; text-transform:uppercase; margin:14px 0 6px 0; font-weight:700;">Historique</div>', unsafe_allow_html=True)
            for c in convs[:10]:
                prefix = "▶ " if c["id"] == st.session_state.conv_id else "• "
                if st.button(f"{prefix}{c['title'][:22]}", key=f"hist_{c['id']}", use_container_width=True):
                    open_conv(c["id"])
                    st.rerun()

        if st.session_state.is_admin and is_you:
            with st.expander("🛠️ Mode développeur"):
                cols = st.columns(2)
                for i, p in enumerate(PLANS):
                    with cols[i % 2]:
                        if st.button(PLAN_LABEL[p], key=f"dev_{p}", use_container_width=True):
                            dev_set_plan(p)
                            st.rerun()

        st.divider()
        st.caption(st.session_state.user.email or "")
        if st.button("🚪 Déconnexion", key="nav_logout", use_container_width=True):
            try:
                if st.session_state.sb:
                    st.session_state.sb.auth.sign_out()
            except Exception:
                pass
            clear_auth_session()
            purge_entire_session()
            st.rerun()

PROFILE_OPTIONS = [
    ("entreprise", "🏢 Entreprise / organisation"),
    ("independant", "💼 Indépendant / freelance"),
    ("salarie", "🧑‍💼 Salarié"),
    ("etudiant", "🎓 Étudiant / élève"),
    ("createur", "🎬 Créateur de contenu"),
    ("developpeur", "💻 Développeur"),
    ("recherche_emploi", "🔎 En recherche d'emploi"),
    ("parent", "👨‍👩‍👧 Parent"),
    ("enseignant", "📚 Enseignant / formateur"),
    ("autre", "✨ Autre"),
]

USE_CASE_OPTIONS = [
    ("clients", "Mieux comprendre et analyser mes clients / prospects"),
    ("contenu", "Créer et publier du contenu plus vite"),
    ("site", "Créer un site ou une page de présentation"),
    ("code", "Écrire, corriger ou améliorer du code"),
    ("scolaire", "Accompagnement scolaire (devoirs, révisions, méthodo)"),
    ("general", "Me débloquer sur mes projets et mes habitudes"),
]

PLAN_ALLOWED_USE_CASES = {
    "free": ("general",),
    "bea": ("general",),
    "pro": ("clients", "contenu", "scolaire", "general"),
    "abo": ("clients", "contenu", "site", "code", "scolaire", "general"),
}

USE_CASE_LABEL = {
    "clients": "Analyse clients",
    "contenu": "Stratégie contenu",
    "site": "Bâtisseur de site",
    "code": "Coach code",
    "scolaire": "Accompagnement scolaire",
    "general": "Général (projets & habitudes)",
}

PROMPT_OFFER_RECOMMENDATIONS = {
    "clients": {"plan": "pro", "title": "Bea Pro", "reason": "son prompt Analyse clients", "description": "Biais cognitifs d'achat et réponses prêtes à envoyer.", "url": STRIPE_PRO_1490, "label": "Choisir Bea Pro - 14,90 €"},
    "contenu": {"plan": "pro", "title": "Bea Pro", "reason": "son prompt Stratégie contenu", "description": "Hooks percutants et plans de contenu.", "url": STRIPE_PRO_1490, "label": "Choisir Bea Pro - 14,90 €"},
    "scolaire": {"plan": "pro", "title": "Bea Pro", "reason": "son accompagnement scolaire", "description": "Méthodologie et explications progressives.", "url": STRIPE_PRO_1490, "label": "Choisir Bea Pro - 14,90 €"},
    "general": {"plan": "bea", "title": "Bea", "reason": "son IA comportementale générale", "description": "Déblocage et passage à l'action.", "url": STRIPE_BEA_9, "label": "Choisir Bea - 9 €"},
    "site": {"plan": "abo", "title": "Bea Ultra", "reason": "son bâtisseur de site et d'applications", "description": "Pages de vente et apps web complètes.", "url": STRIPE_ABO_16, "label": "Choisir Bea Ultra - 16 €"},
    "code": {"plan": "abo", "title": "Bea Ultra", "reason": "son Coach code illimité", "description": "Coach code et éditeur de projets.", "url": STRIPE_ABO_16, "label": "Choisir Bea Ultra - 16 €"},
}

SCHOOL_COUNTRIES = ["France", "Maroc", "Sénégal", "Côte d'Ivoire", "Belgique", "Suisse", "Canada", "Cameroun", "Tunisie", "Algérie", "Autre"]
STUDY_COUNTRIES = ["France", "Belgique", "Suisse", "Canada", "Maroc", "Sénégal", "Côte d'Ivoire", "Cameroun", "Tunisie", "Algérie"]
STUDY_LEVELS = ["Collège - 6e", "Collège - 5e", "Collège - 4e", "Collège - 3e", "Lycée - Seconde", "Lycée - Première", "Lycée - Terminale"]

def recommend_use_case(goal, custom_goal):
    if goal != "custom":
        return goal
    text = clean_text(custom_goal, 300).lower()
    keywords = {
        "clients": ("client", "prospect", "vente", "commercial", "email", "prospection"),
        "contenu": ("contenu", "tiktok", "reels", "vidéo", "video", "youtube", "scroll"),
        "site": ("site", "landing", "page web", "application", "app", "conversion"),
        "code": ("code", "program", "python", "javascript", "bug"),
        "scolaire": ("devoir", "cours", "révision", "école", "lycée", "collège"),
    }
    for use_case, terms in keywords.items():
        if any(term in text for term in terms):
            return use_case
    return "general"

def save_onboarding(profile_type, use_case, display_name, goal, school_country=None, study_country=None, study_level=None):
    clean_nom = clean_text(display_name, 40) or "Utilisateur"
    clean_obj = clean_text(goal, 300)
    
    st.session_state.profile_type = profile_type
    st.session_state.prefs = {
        "display_name": clean_nom, "style": "Expert comportemental", "goal": clean_obj,
        "profile_type": profile_type, "use_case": use_case,
        "school_country": school_country or "France", "study_country": study_country or "France", "study_level": study_level or "Collège - 6e",
    }
    st.session_state.onboarding_done = True
    
    user_id = uid()
    if not user_id:
        return True
        
    full_payload = {
        "user_id": user_id, "use_case": use_case, "display_name": clean_nom,
        "goal": clean_obj, "style": "Expert comportemental", "profile_type": profile_type, "updated_at": now_iso(),
    }
    if school_country:
        full_payload["school_country"] = school_country
    if study_country:
        full_payload["study_country"] = study_country
    if study_level:
        full_payload["study_level"] = study_level

    try:
        sb().table("preferences").upsert(full_payload, on_conflict="user_id").execute()
        return True
    except Exception as e:
        err_msg = str(e).lower()
        if "column" in err_msg or "schema" in err_msg:
            minimal = {k: v for k, v in full_payload.items() if k not in ("school_country", "study_country", "study_level")}
            try:
                sb().table("preferences").upsert(minimal, on_conflict="user_id").execute()
            except Exception:
                pass
        return True

def page_onboarding():
    step = int(st.session_state.get("onboarding_step", 1))
    if step == 1:
        st.markdown("### Bienvenue chez Bea")
        prof = st.radio("Qu'est-ce qui te décrit le plus ?", [k for k, _ in PROFILE_OPTIONS], format_func=lambda x: dict(PROFILE_OPTIONS)[x], key="onboarding_profile_choice")
        study_country, study_level = None, None
        if prof == "etudiant":
            study_country = st.selectbox("Pays d'études", STUDY_COUNTRIES, key="onboarding_study_country")
            study_level = st.selectbox("Niveau", STUDY_LEVELS, key="onboarding_study_level")
        if st.button("Valider", key="onboarding_profile_next", use_container_width=True, type="primary"):
            st.session_state.onboarding_profile = prof
            st.session_state.onboarding_step = 2
            st.rerun()
        return

    if step == 2:
        st.markdown("### Ton but avec Bea")
        choices = [("clients", "Analyse clients"), ("contenu", "Stratégie contenu"), ("site", "Créer un site/app"), ("code", "Coach code"), ("scolaire", "Accompagnement scolaire"), ("general", "Habitudes"), ("custom", "Autre")]
        goal = st.selectbox("Quel est ton but ?", [k for k, _ in choices], format_func=lambda k: dict(choices)[k], key="onboarding_goal_choice")
        custom_goal = st.text_area("Précision", key="onboarding_goal_text") if goal == "custom" else ""
        c_back, c_next = st.columns(2)
        with c_back:
            if st.button("Retour", key="onboarding_goal_back", use_container_width=True):
                st.session_state.onboarding_step = 1
                st.rerun()
        with c_next:
            if st.button("Valider", key="onboarding_goal_next", use_container_width=True, type="primary"):
                st.session_state.onboarding_goal = goal
                st.session_state.onboarding_recommended_use_case = recommend_use_case(goal, custom_goal)
                st.session_state.onboarding_step = 3
                st.rerun()
        return

    use_case = st.session_state.get("onboarding_recommended_use_case", "general")
    rec = PROMPT_OFFER_RECOMMENDATIONS[use_case]
    if step == 3:
        st.markdown("### Analyse de ton profil")
        st.success(f"Offre conseillée : {rec['title']} ({rec['reason']})")
        with st.container(border=True):
            st.markdown(f"#### {rec['title']}")
            st.markdown(rec["description"])
            st.link_button(rec["label"], rec["url"], use_container_width=True)
        if st.button("Continuer", key="onboarding_offer_next", use_container_width=True, type="primary"):
            st.session_state.onboarding_step = 4
            st.rerun()
        return

    st.markdown("### Comment veux-tu que Bea t'appelle ?")
    nom = st.text_input("Prénom ou pseudo", key="onboarding_name", max_chars=40)
    goal = st.session_state.get("onboarding_goal", "general")
    custom_goal = st.session_state.get("onboarding_goal_text", "")
    use_case = st.session_state.get("onboarding_recommended_use_case", "general")
    saved_goal = custom_goal if goal == "custom" else dict(USE_CASE_OPTIONS).get(goal, goal)
    school_country = st.session_state.get("onboarding_country") if use_case == "scolaire" else None
    study_country = st.session_state.get("onboarding_study_country") if st.session_state.get("onboarding_profile") == "etudiant" else None
    study_level = st.session_state.get("onboarding_study_level") if st.session_state.get("onboarding_profile") == "etudiant" else None

    if st.button("Valider et entrer dans Bea", key="onboarding_finish", use_container_width=True, type="primary"):
        if save_onboarding(st.session_state.get("onboarding_profile", "autre"), use_case, nom, saved_goal, school_country, study_country, study_level):
            st.session_state.page = "chat"
            st.rerun()

def page_chat():
    st.markdown("### 💬 Discussion avec Bea")
    if not st.session_state.messages:
        pt = (st.session_state.prefs or {}).get("profile_type") or "createur"
        if pt not in STARTER_CARDS:
            pt = "createur"
        st.info("Bonjour, je suis Bea. Décris-moi un projet ou un blocage et construisons ton plan d'action :")
        cols = st.columns(3)
        for i, q in enumerate(STARTER_CARDS[pt]):
            with cols[i % 3]:
                if st.button(q, key=f"starter_{pt}_{i}", use_container_width=True):
                    handle_send(q, None)
    else:
        for idx, m in enumerate(st.session_state.messages):
            render_message(m, idx)
        c1, c2, c3, c4 = st.columns(4)
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
            if st.session_state.conv_id and st.button("🗑️ Supprimer", key="del_conv", use_container_width=True):
                delete_conv(st.session_state.conv_id)
                st.rerun()

    if st.session_state.pop("regen_flag", False):
        if generate_reply():
            st.rerun()

    up = None
    with st.popover("＋", help="Joindre un fichier ou exporter"):
        st.markdown("#### Options")
        up = st.file_uploader("Glisser un fichier", type=["txt", "md", "csv", "json", "py", "pdf"], key=f"chat_up_{st.session_state.up_key}")
        st.download_button("Télécharger la discussion", export_markdown(), file_name="discussion_bea.md", key=f"dl_menu_{st.session_state.up_key}", use_container_width=True)
    if up:
        st.caption(f"Fichier prêt : {up.name}")

    default = st.session_state.transcribed_text if st.session_state.get("transcribed_text") else ""
    prompt = st.chat_input("Écris ton message à Bea..." if not default else default)
    audio = st.audio_input("micro", key=f"mic_{st.session_state.up_key}", label_visibility="collapsed")

    # Script JavaScript pour injecter les boutons directement dans la barre comme ChatGPT
    components.html("""
    <script>
    (function(){
        const doc = window.parent.document;
        function placeChatGPTBar() {
            const chat = doc.querySelector('div[data-testid="stChatInput"]');
            if(!chat) return;

            const mic = doc.querySelector('div[data-testid="stAudioInput"]');
            const plus = Array.from(doc.querySelectorAll('[data-testid="stPopover"]')).pop();

            if (plus && !chat.contains(plus)) {
                chat.appendChild(plus);
            }
            if (mic && !chat.contains(mic)) {
                chat.appendChild(mic);
            }
        }

        placeChatGPTBar();
        const interval = setInterval(placeChatGPTBar, 150);
        setTimeout(() => clearInterval(interval), 4000);

        const observer = new MutationObserver(placeChatGPTBar);
        observer.observe(doc.body, { childList: true, subtree: true });
    })();
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
                st.error(f"Échec transcription : {e}")

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
    st.caption(f"Requêtes IA code : {d.get('used', '?')}/{d.get('limit', '?')}")
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
        with b3:
            st.download_button("⬇️ Télécharger", code, file_name=fname, key="ed_dl", use_container_width=True)
    with col_c:
        hist = st.container()
        with hist:
            st.markdown("**Assistant Code**")
            for m in st.session_state.code_messages[-6:]:
                render_message(m, 9999)
        typed = st.chat_input("Une question sur ton code ?", key="code_chat")
        if typed and rate_ok() and quota_ok("code"):
            question = clean_text(typed, 3000)
            user_msg = {"role": "user", "content": question}
            st.session_state.code_messages.append(user_msg)
            msgs = [{"role": "system", "content": SYSTEM_CODE + f"\n\nLangage : {lang}\nCode actuel :\n{clean_text(code, 8000)}"}]
            msgs += [{"role": m["role"], "content": m["content"]} for m in st.session_state.code_messages[-8:]]
            with hist:
                render_message(user_msg, 10000)
                with st.chat_message("assistant", avatar=AVATAR):
                    try:
                        text = st.write_stream(stream_groq(msgs, 3000))
                    except Exception:
                        text = ""
                        st.error("IA code indisponible.")
            if text:
                st.session_state.code_messages.append({"role": "assistant", "content": clean_text(text, 12000)})
                quota_consume("code")
                st.rerun()

def page_projets():
    st.markdown("### 📁 Projets enregistrés")
    projets = get_projects()
    if not projets:
        st.info("Aucun projet enregistré.")
        return
    for p in projets:
        with st.container(border=True):
            st.markdown(f"**{p['name']}** · {p['language']}")
            st.code(p["content"][:400], language=p["language"] if p["language"] in EXT else "text")
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
                    except Exception as e:
                        db_error(e)
                    st.rerun()

def page_memoire():
    st.markdown("### 🧠 Mémoire de Bea")
    mems = st.session_state.memories or []
    new_mem = st.text_input("Ajouter une info", placeholder="Ex : Je prépare un concours de droit", key="new_mem_input")
    if st.button("Mémoriser", use_container_width=True) and clean_text(new_mem, 200):
        try:
            sb().table("memories").insert({"user_id": uid(), "content": clean_text(new_mem, 500)}).execute()
            load_account()
            st.toast("Mémorisé")
            st.rerun()
        except Exception:
            st.error("Erreur d'accès à la mémoire.")
    for m in mems:
        with st.container(border=True):
            st.markdown(m.get("content",""))
            if st.button("Supprimer", key=f"del_mem_{m['id']}", use_container_width=True):
                try:
                    sb().table("memories").delete().eq("id", m["id"]).execute()
                    load_account()
                    st.rerun()
                except Exception:
                    db_error()

def generate_app(prompt, mode):
    if not clean_text(prompt, 12000):
        return False
    if not rate_ok() or not quota_ok("code"):
        return False
    messages = [{"role": "system", "content": SYSTEM_APP}]
    if mode == "refine" and st.session_state.app_result:
        messages.append({"role": "user", "content": "Application actuelle :\n```html\n" + clean_text(st.session_state.app_result, 30000) + "\n```"})
        messages.append({"role": "user", "content": "Retouches : " + clean_text(prompt, 4000)})
    else:
        messages.append({"role": "user", "content": clean_text(prompt, 12000)})
    with st.spinner("Construction en cours..."):
        try:
            raw = "".join(stream_groq(messages, 10000))
            html_code = extract_html(raw)
        except Exception:
            html_code = ""
    if not html_code or "<" not in html_code:
        st.error("Génération incomplète, réessaie.")
        return False
    st.session_state.app_result = html_code
    quota_consume("code")
    return True

def page_app():
    st.markdown("### 🌐 Atelier Web")
    if st.session_state.plan != "abo":
        st.info("Inclus dans Bea Ultra.")
        st.button("Voir les offres", on_click=goto, args=("compte",))
        return
    brief = st.text_area("Décris ton application", placeholder="Ex : Un gestionnaire de tâches minimaliste avec filtres.")
    if st.button("Générer l'application", use_container_width=True, type="primary"):
        if generate_app(brief, "initial"):
            st.rerun()
    if st.session_state.app_result:
        st.download_button("Télécharger HTML", st.session_state.app_result, file_name="app.html", mime="text/html", use_container_width=True)
        components.html(st.session_state.app_result, height=650, scrolling=True)

def canvas_font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def compose_canvas(assets, size, layout, title, subtitle, accent, background):
    w, h = size
    canvas = Image.new("RGB", size, background)
    draw = ImageDraw.Draw(canvas)
    margin = 32
    if assets:
        img_h = int(h * 0.65)
        canvas.paste(ImageOps.fit(assets[0].convert("RGB"), (w - margin * 2, img_h)), (margin, margin))
    draw.rounded_rectangle((margin, int(h * 0.70), w - margin, h - margin), radius=20, fill="#120e24")
    f_title = canvas_font(42, True)
    f_sub = canvas_font(24, False)
    draw.text((margin + 20, int(h * 0.73)), title or "Ton titre", font=f_title, fill="#ffffff")
    draw.text((margin + 20, int(h * 0.82)), subtitle or "Ton sous-titre", font=f_sub, fill="#c4b5fd")
    return canvas

def page_studio():
    menu = st.session_state.studio_menu
    st.markdown(f"### 🎬 Studio créateur — {studio_section_label(menu)}")

    if menu == "composer":
        title = st.text_input("Titre", key="cv_title", value="Nouveau Projet")
        subtitle = st.text_input("Sous-titre", key="cv_sub", value="Une idée à développer")
        photos = st.file_uploader("Photo(s)", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
        assets = [Image.open(io.BytesIO(p.getvalue())).convert("RGB") for p in photos] if photos else []
        canvas = compose_canvas(assets, (1080, 1080), "Hero photo", title, subtitle, "#7c3aed", "#18132e")
        st.image(canvas, use_container_width=True)
        png = image_to_png_bytes(canvas)
        st.download_button("Télécharger PNG", png, file_name="visuel.png", mime="image/png", use_container_width=True)

    elif menu == "sous_titres":
        if st.session_state.plan not in ("pro", "abo"):
            st.warning("Réservé aux offres Pro et Ultra.")
            st.button("Voir les offres", on_click=goto, args=("compte",))
        else:
            up = st.file_uploader("Fichier audio ou vidéo", type=["mp3", "mp4", "m4a", "wav"], key="sub_up")
            if up and st.button("Générer les sous-titres", type="primary", use_container_width=True):
                with st.spinner("Transcription en cours..."):
                    try:
                        res = get_groq().audio.transcriptions.create(file=(up.name, up.getvalue()), model=WHISPER_MODEL, response_format="verbose_json")
                        data = res.model_dump() if hasattr(res, "model_dump") else (res if isinstance(res, dict) else {})
                        cues = segments_to_cues(data.get("segments"))
                        st.session_state.sub_result = {"srt": cues_to_srt(cues), "vtt": cues_to_vtt(cues)}
                        quota_consume("chat")
                        st.rerun()
                    except Exception:
                        st.error("Échec transcription.")
            if st.session_state.get("sub_result"):
                r = st.session_state.sub_result
                st.download_button("Télécharger SRT", r["srt"], file_name="sous_titres.srt")

    elif menu == "miniature":
        th_t = st.text_input("Titre de la miniature", max_chars=80)
        th_s = st.text_input("Sous-titre", max_chars=90)
        bg = st.file_uploader("Fond (optionnel)", type=["png", "jpg", "jpeg"])
        if st.button("Générer la miniature", type="primary", use_container_width=True):
            try:
                st.session_state.thumb_png = image_to_png_bytes(make_thumbnail(th_t, th_s, "Violet & Jaune (Contraste fort)", bg.getvalue() if bg else None))
            except Exception:
                st.error("Échec de la génération.")
        if st.session_state.thumb_png:
            st.image(st.session_state.thumb_png)
            st.download_button("Télécharger PNG", st.session_state.thumb_png, file_name="miniature.png", mime="image/png")

    elif menu == "plan_ia":
        sujet = st.text_area("Sujet de la vidéo")
        if st.button("Créer le plan", type="primary", use_container_width=True) and clean_text(sujet, 6000):
            try:
                res = "".join(stream_groq([{"role": "system", "content": SYSTEM_MONTAGE}, {"role": "user", "content": sujet}]))
                st.session_state.plan_result = res
                quota_consume("chat")
                st.rerun()
            except Exception:
                st.error("Erreur IA.")
        if st.session_state.get("plan_result"):
            st.markdown(st.session_state.plan_result)

    else:
        st.info("Section en cours de configuration.")

def page_perso():
    st.markdown("### 🎨 Personnaliser Bea")
    p = st.session_state.prefs or {}
    styles = list(STYLE_HINT)
    profs = [k for k,_ in PROFILE_OPTIONS]
    allowed = PLAN_ALLOWED_USE_CASES.get(st.session_state.plan, ("general",))
    ucs = [k for k,_ in USE_CASE_OPTIONS if k in allowed] or ["general"]

    with st.form("form_perso"):
        nom = st.text_input("Comment Bea doit-elle t'appeler ?", value=p.get("display_name") or "", max_chars=40)
        style = st.selectbox("Style de réponse", styles, index=styles.index(p["style"]) if p.get("style") in styles else 0)
        objectif = st.text_input("Objectif principal", value=p.get("goal") or "", max_chars=160)
        prof = st.selectbox("Profil", profs, index=profs.index(p["profile_type"]) if p.get("profile_type") in profs else 0, format_func=lambda x: dict(PROFILE_OPTIONS)[x])
        uc = st.selectbox("Ton but", ucs, index=ucs.index(p["use_case"]) if p.get("use_case") in ucs else 0, format_func=lambda x: USE_CASE_LABEL.get(x, x))
        ok = st.form_submit_button("Enregistrer", use_container_width=True)

    if ok:
        row = {
            "user_id": uid(), "display_name": clean_text(nom, 40), "style": style, "goal": clean_text(objectif, 160),
            "profile_type": prof, "use_case": uc, "updated_at": now_iso()
        }
        try:
            sb().table("preferences").upsert(row, on_conflict="user_id").execute()
            st.session_state.prefs = row
            st.session_state.profile_type = prof
            st.success("Préférences enregistrées !")
            st.rerun()
        except Exception as e:
            db_error(e)

def page_compte():
    st.markdown("### 💎 Compte & offres")
    q = st.session_state.quota or {}
    st.markdown(f"**Offre actuelle :** {PLAN_LABEL[st.session_state.plan]}")
    for k, label in (("chat", "Requêtes de chat"), ("code", "Requêtes code")):
        if q.get(k):
            st.progress(min(q[k]["used"] / max(q[k]["limit"], 1), 1.0), text=f"{label} : {q[k]['used']}/{q[k]['limit']}")
    render_offers()
    st.divider()
    if st.checkbox("Confirmer la suppression de l'historique"):
        if st.button("Supprimer l'historique", type="primary"):
            try:
                sb().table("conversations").delete().eq("user_id", uid()).execute()
                sb().table("code_projects").delete().eq("user_id", uid()).execute()
                new_chat()
                st.success("Historique effacé.")
                st.rerun()
            except Exception as e:
                db_error(e)

# ==============================================================================
# ROUTAGE PRINCIPAL DE L'APPLICATION
# ==============================================================================

if not logged_in():
    restore_auth_session()

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

if not st.session_state.get("onboarding_done") and not (st.session_state.prefs or {}).get("use_case") and not st.session_state.is_admin:
    page_onboarding()
    st.stop()

render_sidebar()
{
    "chat": page_chat, "code": page_code, "app": page_app, "studio": page_studio,
    "projets": page_projets, "perso": page_perso, "compte": page_compte, "memoire": page_memoire,
    "dev_portal": page_dev_portal, "dev_lab": page_dev_lab,
}.get(st.session_state.page, page_chat)()
