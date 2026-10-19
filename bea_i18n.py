"""Traduction complète de l'interface Bea + langue des réponses.

Principe : les fonctions d'affichage de Streamlit (st.markdown, st.button, st.tabs...)
sont enveloppées pour traduire leurs textes à la volée. Les textes inconnus sont
regroupés pendant l'exécution, traduits en un seul appel Groq à la fin du script,
mis en cache (mémoire + disque) puis la page est relancée une fois.
"""

import hashlib
import json
import os
import re
import threading

import streamlit as st
from groq import Groq
from streamlit.delta_generator import DeltaGenerator

# Langues parlées par les modèles Groq utilisés par Bea.
# Les 8 premières sont officiellement supportées par Llama 3.1 / 3.3 ;
# les suivantes sont bien maîtrisées par GPT-OSS 120B / Llama 3.3 70B.
LANGUAGES = {
    "fr": {"label": "Français", "name": "French", "edge": "fr-FR-DeniseNeural", "gtts": "fr", "minimax": "French", "rtl": False},
    "en": {"label": "English", "name": "English", "edge": "en-US-AvaMultilingualNeural", "gtts": "en", "minimax": "English", "rtl": False},
    "es": {"label": "Español", "name": "Spanish", "edge": "es-ES-ElviraNeural", "gtts": "es", "minimax": "Spanish", "rtl": False},
    "de": {"label": "Deutsch", "name": "German", "edge": "de-DE-KatjaNeural", "gtts": "de", "minimax": "German", "rtl": False},
    "it": {"label": "Italiano", "name": "Italian", "edge": "it-IT-ElsaNeural", "gtts": "it", "minimax": "Italian", "rtl": False},
    "pt": {"label": "Português", "name": "Portuguese", "edge": "pt-BR-FranciscaNeural", "gtts": "pt", "minimax": "Portuguese", "rtl": False},
    "hi": {"label": "हिन्दी", "name": "Hindi", "edge": "hi-IN-SwaraNeural", "gtts": "hi", "minimax": "Hindi", "rtl": False},
    "th": {"label": "ไทย", "name": "Thai", "edge": "th-TH-PremwadeeNeural", "gtts": "th", "minimax": "Thai", "rtl": False},
    "ar": {"label": "العربية", "name": "Arabic", "edge": "ar-SA-ZariyahNeural", "gtts": "ar", "minimax": "Arabic", "rtl": True},
    "zh": {"label": "中文", "name": "Simplified Chinese", "edge": "zh-CN-XiaoxiaoNeural", "gtts": "zh-CN", "minimax": "Chinese", "rtl": False},
    "ja": {"label": "日本語", "name": "Japanese", "edge": "ja-JP-NanamiNeural", "gtts": "ja", "minimax": "Japanese", "rtl": False},
    "ko": {"label": "한국어", "name": "Korean", "edge": "ko-KR-SunHiNeural", "gtts": "ko", "minimax": "Korean", "rtl": False},
    "ru": {"label": "Русский", "name": "Russian", "edge": "ru-RU-SvetlanaNeural", "gtts": "ru", "minimax": "Russian", "rtl": False},
    "nl": {"label": "Nederlands", "name": "Dutch", "edge": "nl-NL-ColetteNeural", "gtts": "nl", "minimax": "Dutch", "rtl": False},
    "tr": {"label": "Türkçe", "name": "Turkish", "edge": "tr-TR-EmelNeural", "gtts": "tr", "minimax": "Turkish", "rtl": False},
    "pl": {"label": "Polski", "name": "Polish", "edge": "pl-PL-ZofiaNeural", "gtts": "pl", "minimax": "Polish", "rtl": False},
}
DEFAULT_LANG = "fr"
STATE_KEY = "bea_lang"

TRANSLATION_MODELS = ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "llama-3.1-8b-instant"]
CHUNK_SIZE = 40

# (nom de l'argument texte, est un widget à clé)
_SPEC = {
    "markdown": ("body", False), "caption": ("body", False), "title": ("body", False),
    "header": ("body", False), "subheader": ("body", False), "text": ("body", False),
    "info": ("body", False), "warning": ("body", False), "error": ("body", False),
    "success": ("body", False), "toast": ("body", False), "write": (None, False),
    "expander": ("label", False), "popover": ("label", False), "tabs": ("tabs", False),
    "link_button": ("label", False), "spinner": ("text", False),
    "button": ("label", True), "download_button": ("label", True), "form_submit_button": ("label", True),
    "text_input": ("label", True), "text_area": ("label", True), "number_input": ("label", True),
    "checkbox": ("label", True), "toggle": ("label", True), "selectbox": ("label", True),
    "radio": ("label", True), "multiselect": ("label", True), "file_uploader": ("label", True),
    "audio_input": ("label", True), "chat_input": ("placeholder", True), "slider": ("label", True),
}
_OPTION_WIDGETS = {"selectbox", "radio", "multiselect"}

_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".bea_i18n_cache.json")
_LOCK = threading.Lock()


def _store():
    # Stocké sur le module streamlit (pas st.cache_resource, qui afficherait un spinner traduit -> récursion).
    store = getattr(st, "_bea_i18n_store", None)
    if store is None:
        try:
            with open(_CACHE_FILE, encoding="utf-8") as f:
                store = json.load(f)
        except Exception:
            store = {}
        if not isinstance(store, dict):
            store = {}
        st._bea_i18n_store = store
    return store


def _save_store():
    try:
        with _LOCK:
            snapshot = json.dumps(_store(), ensure_ascii=False)
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(snapshot)
    except Exception:
        pass


def _client():
    client = getattr(st, "_bea_i18n_groq", None)
    if client is None:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        st._bea_i18n_groq = client
    return client


def _orig():
    return getattr(st, "_bea_i18n_orig", {})


def current_lang():
    lang = st.session_state.get(STATE_KEY, DEFAULT_LANG)
    return lang if lang in LANGUAGES else DEFAULT_LANG


def lang_info(lang=None):
    return LANGUAGES[lang or current_lang()]


def _should_translate(text):
    if not isinstance(text, str):
        return False
    s = text.strip()
    if not s or len(s) > 4000:
        return False
    low = s.lower()
    if "<style" in low or "<script" in low:
        return False
    visible = re.sub(r"<[^>]+>", " ", s)
    return len(re.findall(r"[A-Za-zÀ-ÿ]", visible)) >= 2


def tr(text):
    """Traduit un texte d'interface dans la langue choisie (sinon le renvoie tel quel)."""
    lang = current_lang()
    if lang == DEFAULT_LANG or st.session_state.get("_i18n_raw") or not _should_translate(text):
        return text
    hit = _store().get(lang, {}).get(text)
    if hit is not None:
        return hit
    st.session_state.setdefault("_i18n_pending", set()).add(text)
    return text


t = tr


def _translate_batch(items, lang_name):
    system = (
        f"You are a professional UI translator for the web app 'Bea' by BehaviorLab AI. "
        f"Translate every French string of the given JSON array into {lang_name}. "
        "Return a JSON object {\"translations\": [...]} with exactly the same number of items, in the same order. "
        "Preserve Markdown, HTML tags and attributes, emojis, line breaks, placeholders, numbers, prices, URLs and e-mail addresses. "
        "Never translate brand or product names: Bea, Bea Pro, Bea Ultra, BehaviorLab AI, Groq, Supabase, Stripe, TikTok, Reels, Shorts, YouTube, LinkedIn, PDF, Word, SRT, VTT, HTML, FFmpeg. "
        "Keep the friendly informal tone (French 'tu'). If a string is already in the target language or is not natural language, return it unchanged."
    )
    payload = json.dumps({"strings": items}, ensure_ascii=False)
    for model in TRANSLATION_MODELS:
        try:
            resp = _client().chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": payload}],
                temperature=0,
                max_tokens=6000,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            out = data.get("translations")
            if isinstance(out, list) and len(out) == len(items) and all(isinstance(x, str) for x in out):
                return out
        except Exception:
            continue
    return None


def flush_translations():
    """Traduit en une fois les textes rencontrés pendant l'exécution, puis relance la page."""
    pending = st.session_state.pop("_i18n_pending", None)
    lang = current_lang()
    if lang == DEFAULT_LANG or not pending:
        return
    cache = _store().setdefault(lang, {})
    todo = sorted(x for x in pending if x not in cache)
    if not todo:
        return
    signature = hashlib.md5((lang + "\x00".join(todo)).encode()).hexdigest()
    attempts = st.session_state.setdefault("_i18n_attempts", {})
    if attempts.get(signature, 0) >= 2:
        return
    attempts[signature] = attempts.get(signature, 0) + 1
    translated = 0
    for i in range(0, len(todo), CHUNK_SIZE):
        chunk = todo[i:i + CHUNK_SIZE]
        out = _translate_batch(chunk, LANGUAGES[lang]["name"])
        if out:
            with _LOCK:
                cache.update(zip(chunk, out))
            translated += len(chunk)
    if translated:
        _save_store()
        st.rerun()


def _auto_key(name, label):
    counts = st.session_state.setdefault("_i18n_counts", {})
    base = f"{name}:{label}"
    n = counts.get(base, 0)
    counts[base] = n + 1
    return f"i18n_{name}_{hashlib.md5(base.encode()).hexdigest()[:10]}_{n}"


def _transform(name, args, kwargs):
    if current_lang() == DEFAULT_LANG or st.session_state.get("_i18n_raw"):
        return args, kwargs
    argname, is_widget = _SPEC[name]
    args = list(args)
    original = None

    def conv(value):
        if name == "tabs" and isinstance(value, (list, tuple)):
            return [tr(v) for v in value]
        return tr(value) if isinstance(value, str) else value

    if name == "write":
        args = [tr(a) if isinstance(a, str) else a for a in args]
    elif args:
        original = args[0]
        args[0] = conv(original)
    elif argname in kwargs:
        original = kwargs[argname]
        kwargs[argname] = conv(original)

    for extra in ("help", "placeholder"):
        if extra != argname and isinstance(kwargs.get(extra), str):
            kwargs[extra] = tr(kwargs[extra])

    if name in _OPTION_WIDGETS:
        fmt = kwargs.get("format_func", str)
        kwargs["format_func"] = lambda o, _f=fmt: (lambda v: tr(v) if isinstance(v, str) else v)(_f(o))

    if is_widget and kwargs.get("key") is None and len(args) <= 1 and isinstance(original, str):
        kwargs["key"] = _auto_key(name, original)
    return tuple(args), kwargs


def _wrap_function(name, fn):
    def wrapper(*args, **kwargs):
        args, kwargs = _transform(name, args, kwargs)
        return fn(*args, **kwargs)
    wrapper.__wrapped__ = fn
    return wrapper


def _wrap_method(name, fn):
    def wrapper(self, *args, **kwargs):
        args, kwargs = _transform(name, args, kwargs)
        return fn(self, *args, **kwargs)
    wrapper.__wrapped__ = fn
    return wrapper


def _patch_streamlit():
    if getattr(st, "_bea_i18n_patched", False):
        return
    originals = {}
    for name in _SPEC:
        fn = getattr(st, name, None)
        if callable(fn):
            originals[name] = fn
            setattr(st, name, _wrap_function(name, fn))
        method = DeltaGenerator.__dict__.get(name) or getattr(DeltaGenerator, name, None)
        if callable(method):
            setattr(DeltaGenerator, name, _wrap_method(name, method))
    original_stop = st.stop
    originals["stop"] = original_stop

    def stop_with_flush():
        flush_translations()
        original_stop()

    st.stop = stop_with_flush
    st._bea_i18n_orig = originals
    st._bea_i18n_patched = True


def setup_i18n():
    """À appeler une fois en haut de app.py, juste après st.set_page_config."""
    _patch_streamlit()
    st.session_state.setdefault(STATE_KEY, DEFAULT_LANG)
    st.session_state["_i18n_counts"] = {}
    if lang_info()["rtl"]:
        _orig()["markdown"](
            "<style>div[data-testid='stMarkdownContainer'], div[data-testid='stChatMessage'] p,"
            " div[data-testid='stChatInput'] textarea{direction:rtl!important;text-align:right!important;}</style>",
            unsafe_allow_html=True,
        )


def md_raw(text, **kwargs):
    """Affiche du Markdown sans le traduire (messages de l'utilisateur et de Bea)."""
    return _orig().get("markdown", st.markdown)(text, **kwargs)


class keep_original:
    """Bloc `with keep_original():` dont le contenu n'est pas traduit."""

    def __enter__(self):
        self._prev = st.session_state.get("_i18n_raw", False)
        st.session_state["_i18n_raw"] = True

    def __exit__(self, *exc):
        st.session_state["_i18n_raw"] = self._prev
        return False


def render_language_selector(location="sidebar", label_visibility="visible"):
    codes = list(LANGUAGES)
    widget_key = f"_lang_widget_{location}"

    def on_change():
        st.session_state[STATE_KEY] = st.session_state[widget_key]
        st.session_state.pop("_i18n_attempts", None)

    _orig().get("selectbox", st.selectbox)(
        "🌐 " + tr("Langue"),
        codes,
        index=codes.index(current_lang()),
        format_func=lambda c: LANGUAGES[c]["label"],
        key=widget_key,
        on_change=on_change,
        label_visibility=label_visibility,
    )


def render_landing_nav():
    """Barre du haut de la page d'accueil : Offres + BehaviorLab AI à gauche, Langues à droite."""
    col_offers, col_about, _, col_lang = st.columns([1, 1.3, 2.6, 1.3])
    with col_offers:
        if st.button("Offres", key="landing_offers", use_container_width=True):
            st.session_state.landing_tab = "offres"
            st.rerun()
    with col_about:
        if st.button("BehaviorLab AI", key="landing_about", use_container_width=True):
            st.session_state.landing_tab = "about"
            st.rerun()
    with col_lang:
        render_language_selector("landing", label_visibility="collapsed")


def language_instruction():
    """Consigne à ajouter au prompt système pour que Bea réponde dans la langue choisie."""
    lang = current_lang()
    if lang == DEFAULT_LANG:
        return ""
    info = LANGUAGES[lang]
    return (
        f"\n\nLANGUE OBLIGATOIRE : l'utilisateur a choisi l'interface en {info['name']} ({info['label']}). "
        f"Rédige TOUTE ta réponse en {info['name']}, y compris les titres de sections "
        "(traduis « Problèmes possibles », « Leviers d'action », « Plan de démarrage », etc.), "
        "même si l'utilisateur t'écrit dans une autre langue et même si ces instructions sont en français."
    )
