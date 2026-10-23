# -*- coding: utf-8 -*-
"""
Bea Utils - Module utilitaire & Bouclier de Sécurité Anti-Piratage
BehaviorLab AI
"""

import html
import io
import re

PALETTES = {
    "neon": {"bg": "#0f0a1e", "text": "#ffffff", "accent": "#a855f7"},
    "cyber": {"bg": "#080d1a", "text": "#ffffff", "accent": "#38bdf8"},
    "sunset": {"bg": "#1c0d1b", "text": "#ffffff", "accent": "#fb7185"},
    "emerald": {"bg": "#061612", "text": "#ffffff", "accent": "#34d399"},
}

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"oublie\s+(toutes\s+)?(les\s+)?instructions\s+pr[ée]c[ée]dentes",
    r"reveal\s+(your|the)\s+(system\s+)?prompt",
    r"donne[- ]moi\s+(ton|le)\s+prompt\s+syst[eè]me",
    r"system\s*:\s*you\s+are",
    r"<\|im_start\|>",
    r"<\|endoftext\|>",
    r"\bDAN\s+mode\b",
    r"act\s+as\s+an\s+unfiltered\s+ai",
    r"give\s+me\s+(the\s+)?api\s*key",
]

def clean_text(val, max_len=1000):
    """
    Nettoie et désinfecte le texte contre le piratage XSS et prompt injection.
    """
    if val is None:
        return ""
    text = str(val).strip()
    
    # 1. Neutralisation XSS
    text = re.sub(r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>", "[SCRIPT_BLOQUÉ]", text, flags=re.IGNORECASE)
    text = re.sub(r"<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>", "[IFRAME_BLOQUÉE]", text, flags=re.IGNORECASE)
    text = re.sub(r"\bon\w+\s*=\s*(['\"]).*?\1", "", text, flags=re.IGNORECASE)
    text = re.sub(r"javascript\s*:", "blocked-protocol:", text, flags=re.IGNORECASE)
    
    # 2. Neutralisation Prompt Injection
    for pat in PROMPT_INJECTION_PATTERNS:
        text = re.sub(pat, "[INJECTION_NEUTRALISÉE]", text, flags=re.IGNORECASE)
        
    return text[:max_len]

def extract_html(text):
    if not text:
        return ""
    match = re.search(r"```html\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"(<!doctype html.*<\/html>)", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()

def image_to_png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def make_thumbnail(title, subtitle="", style="neon"):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (1280, 720), color="#0f0a1e")
    draw = ImageDraw.Draw(img)
    draw.text((60, 200), clean_text(title, 80), fill="#ffffff")
    if subtitle:
        draw.text((60, 320), clean_text(subtitle, 120), fill="#c4b5fd")
    return img

def script_to_cues(script):
    return [{"start": 0.0, "end": 3.0, "text": clean_text(script, 100)}]

def segments_to_cues(segments):
    cues = []
    for s in segments:
        cues.append({
            "start": s.get("start", 0.0),
            "end": s.get("end", 3.0),
            "text": clean_text(s.get("text", ""), 200)
        })
    return cues

def cues_to_srt(cues):
    lines = []
    for i, c in enumerate(cues, 1):
        lines.append(f"{i}\n00:00:00,000 --> 00:00:03,000\n{c['text']}\n")
    return "\n".join(lines)

def cues_to_vtt(cues):
    return "WEBVTT\n\n" + cues_to_srt(cues)
