"""Voix de Bea (synthèse vocale).

Ordre des moteurs :
1. MiniMax (si le secret MINIMAX_API_KEY est défini) : voix très naturelle, payant à l'usage.
2. Edge TTS (gratuit, sans clé) : voix neuronales Microsoft, toutes les langues de Bea.
3. gTTS (gratuit, sans clé) : secours si Edge TTS est indisponible.
"""

import asyncio
import hashlib
import io
import json
import re
import threading
import urllib.request

import streamlit as st

from bea_i18n import current_lang, lang_info, tr

MAX_TTS_CHARS = 2500
AUTO_KEY = "bea_voice_auto"

_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\U00002B00-\U00002BFF\uFE0F\u200D]+"
)


def _secret(name, default=""):
    try:
        return str(st.secrets.get(name, default) or default).strip()
    except Exception:
        return default


def clean_for_speech(text):
    s = re.sub(r"```.*?```", " ", text or "", flags=re.DOTALL)
    s = re.sub(r"`([^`]*)`", r"\1", s)
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"^\s{0,3}#{1,6}\s*", "", s, flags=re.MULTILINE)
    s = re.sub(r"^\s*[-*•]\s+", "", s, flags=re.MULTILINE)
    s = re.sub(r"[*_~>|]+", "", s)
    s = _EMOJI_RE.sub("", s)
    s = re.sub(r"\n{2,}", ". ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > MAX_TTS_CHARS:
        cut = s[:MAX_TTS_CHARS]
        s = cut[: max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "), 200) + 1]
    return s


def _minimax(text, lang):
    api_key = _secret("MINIMAX_API_KEY")
    if not api_key:
        return None
    body = {
        "model": _secret("MINIMAX_MODEL", "speech-02-turbo"),
        "text": text,
        "stream": False,
        "output_format": "hex",
        "language_boost": lang["minimax"],
        "voice_setting": {"voice_id": _secret("MINIMAX_VOICE_ID", "Wise_Woman"), "speed": 1, "vol": 1, "pitch": 0},
        "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1},
    }
    req = urllib.request.Request(
        _secret("MINIMAX_API_URL", "https://api.minimax.io/v1/t2a_v2"),
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        audio_hex = (data.get("data") or {}).get("audio")
        return bytes.fromhex(audio_hex) if audio_hex else None
    except Exception:
        return None


def _run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        result = {}

        def runner():
            result["value"] = asyncio.run(coro)

        thread = threading.Thread(target=runner)
        thread.start()
        thread.join()
        return result.get("value")


def _edge(text, lang):
    try:
        import edge_tts
    except ImportError:
        return None

    async def synth():
        communicate = edge_tts.Communicate(text, _secret("EDGE_TTS_VOICE_" + lang["gtts"].upper().replace("-", "_"), lang["edge"]))
        buf = bytearray()
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                buf.extend(chunk["data"])
        return bytes(buf)

    try:
        audio = _run_async(synth())
        return audio or None
    except Exception:
        return None


def _gtts(text, lang):
    try:
        from gtts import gTTS
        buf = io.BytesIO()
        gTTS(text=text, lang=lang["gtts"]).write_to_fp(buf)
        return buf.getvalue() or None
    except Exception:
        return None


class _NoAudio(Exception):
    pass


@st.cache_data(show_spinner=False, max_entries=300, ttl=86400)
def _synthesize_cached(text, lang_code):
    speech = clean_for_speech(text)
    if speech:
        lang = lang_info(lang_code)
        for engine in (_minimax, _edge, _gtts):
            audio = engine(speech, lang)
            if audio:
                return audio
    raise _NoAudio()


def synthesize(text, lang_code):
    """Renvoie l'audio MP3 de `text` dans la langue `lang_code`, ou None (les échecs ne sont pas mis en cache)."""
    try:
        return _synthesize_cached(text, lang_code)
    except _NoAudio:
        return None


def _text_id(text):
    return hashlib.md5((text or "").encode()).hexdigest()[:16]


def queue_autoplay(text):
    """À appeler après une nouvelle réponse : elle sera lue automatiquement si l'option est activée."""
    if st.session_state.get(AUTO_KEY):
        st.session_state["_tts_autoplay_id"] = _text_id(text)


def render_voice_button(key):
    """Petit bouton 🔊 à placer dans la rangée d'actions d'un message de Bea."""
    if st.button("🔊", key=f"tts_btn_{key}", help=tr("Écouter la réponse de Bea")):
        st.session_state[f"_tts_on_{key}"] = True
        st.session_state[f"_tts_play_{key}"] = True


def render_voice_player(text, key):
    """Lecteur audio du message (affiché après un clic sur 🔊 ou en lecture automatique)."""
    text_id = _text_id(text)
    auto = st.session_state.get("_tts_autoplay_id") == text_id
    if not (auto or st.session_state.get(f"_tts_on_{key}")):
        return
    with st.spinner(tr("Bea prépare sa voix...")):
        audio = synthesize(text, current_lang())
    if not audio:
        st.caption(tr("La voix est indisponible pour le moment. Réessaie dans un instant."))
        return
    play_now = auto or st.session_state.pop(f"_tts_play_{key}", False)
    if auto:
        st.session_state.pop("_tts_autoplay_id", None)
        st.session_state[f"_tts_on_{key}"] = True
    st.audio(audio, format="audio/mpeg", autoplay=play_now)


def render_voice_settings():
    """Interrupteur « lecture automatique » (à placer dans la barre latérale)."""
    st.session_state.setdefault(AUTO_KEY, False)

    def on_change():
        st.session_state[AUTO_KEY] = st.session_state["_w_voice_auto"]

    st.toggle(
        "🔊 Voix de Bea automatique",
        value=st.session_state[AUTO_KEY],
        key="_w_voice_auto",
        on_change=on_change,
        help="Bea lit ses nouvelles réponses à voix haute dans la langue choisie.",
    )
