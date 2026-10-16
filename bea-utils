"""Fonctions utilitaires de Bea (sans dépendance à Streamlit, donc testables)."""
import io
import re
import textwrap

from PIL import Image, ImageDraw, ImageFont, ImageOps

# ----------------------------------------------------------------------------
# Texte
# ----------------------------------------------------------------------------


def clean_text(t, limit=4000):
    """Nettoie un texte sans casser le code : on retire seulement les caractères
    de contrôle et on limite la taille. Le HTML n'est PAS supprimé : Streamlit
    n'interprète pas le HTML dans st.markdown (unsafe_allow_html=False)."""
    if not t:
        return ""
    t = str(t).replace("\x00", "")
    t = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f]", "", t)
    return t.strip()[:limit]


def extract_html(text):
    """Récupère un document HTML dans la réponse d'un modèle."""
    if not text:
        return ""
    m = re.search(r"```(?:html)?\s*\n(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    low = text.lower()
    i = low.find("<!doctype")
    if i == -1:
        i = low.find("<html")
    return text[i:].strip() if i != -1 else ""


# ----------------------------------------------------------------------------
# Sous-titres (SRT / VTT)
# ----------------------------------------------------------------------------


def timecode(sec, sep=","):
    ms = int(round(max(sec, 0) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def _wrap(text, width=42):
    return "\n".join(textwrap.wrap(text, width=width)) or text


def split_cues(start, end, text, max_chars=80):
    """Découpe un segment en plusieurs sous-titres lisibles (2 lignes max environ)
    en répartissant la durée au prorata du nombre de caractères."""
    words = (text or "").split()
    if not words:
        return []
    chunks, cur = [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_chars:
            chunks.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        chunks.append(cur)
    total = sum(len(c) for c in chunks) or 1
    dur = max(end - start, 0.3)
    out, t = [], start
    for c in chunks:
        d = dur * len(c) / total
        out.append((t, t + d, _wrap(c)))
        t += d
    return out


def segments_to_cues(segments):
    """Transforme les segments renvoyés par Whisper (dict ou objets) en sous-titres."""
    cues = []
    for s in segments or []:
        get = (lambda k, s=s: s.get(k)) if isinstance(s, dict) else (lambda k, s=s: getattr(s, k, None))
        txt = (get("text") or "").strip()
        a, b = get("start"), get("end")
        if txt and a is not None and b is not None:
            cues.extend(split_cues(float(a), float(b), txt))
    return cues


def script_to_cues(script, words_per_second=2.6, words_per_cue=6):
    """Sous-titres à partir d'un script, avec un timing ESTIMÉ (non synchronisé à la voix)."""
    words = (script or "").split()
    cues, t = [], 0.0
    wps = max(words_per_second, 0.5)
    for i in range(0, len(words), words_per_cue):
        chunk = words[i:i + words_per_cue]
        d = len(chunk) / wps
        cues.append((t, t + d, _wrap(" ".join(chunk))))
        t += d
    return cues


def cues_to_srt(cues):
    return "".join(
        f"{i}\n{timecode(a)} --> {timecode(b)}\n{txt}\n\n" for i, (a, b, txt) in enumerate(cues, 1)
    )


def cues_to_vtt(cues):
    body = "".join(
        f"{timecode(a, '.')} --> {timecode(b, '.')}\n{txt}\n\n" for a, b, txt in cues
    )
    return "WEBVTT\n\n" + body


# ----------------------------------------------------------------------------
# Miniatures 1280x720
# ----------------------------------------------------------------------------

PALETTES = {
    # (couleur haut, couleur bas, texte, accent)
    "Viral pop": ((124, 58, 237), (219, 39, 119), (255, 255, 255), (250, 204, 21)),
    "Néon": ((8, 10, 40), (0, 150, 255), (255, 255, 255), (0, 255, 200)),
    "Cinéma": ((15, 15, 20), (70, 50, 30), (245, 235, 210), (230, 170, 60)),
    "Minimal": ((245, 245, 250), (215, 215, 230), (20, 20, 35), (124, 58, 237)),
    "Bold": ((220, 38, 38), (250, 120, 30), (255, 255, 255), (20, 20, 20)),
}

_FONT_CANDIDATES = [
    "DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def load_font(size):
    for p in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _wrap_pixels(draw, text, font, max_w):
    lines, cur = [], ""
    for w in text.split():
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=font) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_thumbnail(title, subtitle="", style="Viral pop", bg_bytes=None):
    W, H = 1280, 720
    c1, c2, fg, accent = PALETTES.get(style, PALETTES["Viral pop"])
    if bg_bytes:
        bg = ImageOps.fit(Image.open(io.BytesIO(bg_bytes)).convert("RGB"), (W, H))
        img = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.45)
        fg = (255, 255, 255) if style == "Minimal" else fg
    else:
        img = Image.new("RGB", (W, H), c1)
        d0 = ImageDraw.Draw(img)
        for y in range(H):
            t = y / (H - 1)
            d0.line([(0, y), (W, y)], fill=tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3)))
    draw = ImageDraw.Draw(img)

    title = (title or "").strip()[:80] or "Ton titre ici"
    box_w, box_h = W - 160, 400 if subtitle.strip() else 480
    size = 150
    while True:
        font = load_font(size)
        lines = _wrap_pixels(draw, title, font, box_w)
        line_h = int(size * 1.15)
        too_wide = any(draw.textlength(l, font=font) > box_w for l in lines)
        if (len(lines) * line_h <= box_h and not too_wide) or size <= 40:
            break
        size -= 6

    block_h = len(lines) * line_h
    y = (H - block_h) // 2 - (40 if subtitle.strip() else 0)
    stroke = max(2, size // 18)
    outline = (0, 0, 0) if sum(fg) > 380 else (255, 255, 255)
    for l in lines:
        w = draw.textlength(l, font=font)
        draw.text(((W - w) / 2, y), l, font=font, fill=fg, stroke_width=stroke, stroke_fill=outline)
        y += line_h

    if subtitle.strip():
        sfont = load_font(max(34, size // 3))
        sub = subtitle.strip()[:90]
        w = draw.textlength(sub, font=sfont)
        sy = y + 20
        draw.rounded_rectangle([(W - w) / 2 - 24, sy - 10, (W + w) / 2 + 24, sy + sfont.size + 18]
                               if hasattr(sfont, "size") else [(W - w) / 2 - 24, sy - 10, (W + w) / 2 + 24, sy + 60],
                               radius=18, fill=accent)
        draw.text(((W - w) / 2, sy), sub, font=sfont, fill=(20, 20, 20) if sum(accent) > 380 else (255, 255, 255))

    draw.rectangle([0, H - 14, W, H], fill=accent)
    return img


def image_to_png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()
