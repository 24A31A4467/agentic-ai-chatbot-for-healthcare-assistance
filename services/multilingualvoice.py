"""
services/multilingual_voice.py
────────────────────────────────────────────────────────────
Multilingual Voice Layer for Autonomous Agent Care
Supports 13 Indian languages via Whisper STT + Google Translate + gTTS

Drop this file into your existing  services/  folder.

Install once:
    pip install openai-whisper deep-translator gTTS python-multipart
────────────────────────────────────────────────────────────
"""

import os
import tempfile
from pathlib import Path

# ── Lazy-load Whisper so Flask starts fast ────────────────────
_whisper_model = None

def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        size = os.getenv("WHISPER_MODEL", "medium")   # override in .env if needed
        print(f"--- 🎙 Loading Whisper '{size}' model… ---")
        _whisper_model = whisper.load_model(size)
        print("--- ✅ Whisper ready ---")
    return _whisper_model


# ── Supported Indian languages ────────────────────────────────
# Maps Whisper/BCP-47 code → gTTS / Google Translate code
SUPPORTED_LANGUAGES: dict[str, str] = {
    "hi": "hi",   # Hindi
    "bn": "bn",   # Bengali
    "ta": "ta",   # Tamil
    "te": "te",   # Telugu
    "kn": "kn",   # Kannada
    "mr": "mr",   # Marathi
    "gu": "gu",   # Gujarati
    "pa": "pa",   # Punjabi
    "ml": "ml",   # Malayalam
    "or": "or",   # Odia
    "ur": "ur",   # Urdu
    "as": "as",   # Assamese
    "en": "en",   # English (passthrough)
}

LANGUAGE_NAMES = {
    "hi": "Hindi", "bn": "Bengali", "ta": "Tamil",  "te": "Telugu",
    "kn": "Kannada", "mr": "Marathi", "gu": "Gujarati", "pa": "Punjabi",
    "ml": "Malayalam", "or": "Odia",  "ur": "Urdu",   "as": "Assamese",
    "en": "English",
}


# ── STT ───────────────────────────────────────────────────────
def speech_to_text(audio_path: str) -> dict:
    """
    Transcribe an audio file.
    Returns {"text": str, "detected_lang": str (BCP-47 code)}
    """
    model = _get_whisper()
    result = model.transcribe(audio_path, task="transcribe")
    lang = result.get("language", "en")
    if lang not in SUPPORTED_LANGUAGES:
        lang = "en"
    return {
        "text":          result["text"].strip(),
        "detected_lang": lang,
        "lang_name":     LANGUAGE_NAMES.get(lang, lang),
    }


# ── Translation ───────────────────────────────────────────────
def translate_to_english(text: str, source_lang: str) -> str:
    """Translate regional-language text to English. No-op for English."""
    if source_lang == "en" or not text.strip():
        return text
    from deep_translator import GoogleTranslator
    return GoogleTranslator(source=source_lang, target="en").translate(text)


def translate_from_english(text: str, target_lang: str) -> str:
    """Translate English AI response back to the user's language."""
    if target_lang == "en" or not text.strip():
        return text
    from deep_translator import GoogleTranslator
    # Strip internal action tags before translating  (e.g. [SEVERITY:Mild])
    import re
    clean = re.sub(r'\[[\w_]+:[^\]]*\]', '', text).strip()
    return GoogleTranslator(source="en", target=target_lang).translate(clean)


# ── TTS ───────────────────────────────────────────────────────
def text_to_speech(text: str, lang: str, output_path: str) -> str:
    """Generate an MP3 from translated text. Returns the file path."""
    from gtts import gTTS
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.save(output_path)
    return output_path


# ── Full pipeline (used by the /voice-chat endpoint) ──────────
def run_voice_pipeline(audio_bytes: bytes, audio_suffix: str = ".wav") -> dict:
    """
    End-to-end pipeline:
        audio bytes  →  STT  →  translate to English
        →  returns dict ready for your chatbot

    Call this BEFORE passing to Gemini, then call
    finalize_voice_response() AFTER Gemini replies.

    Returns:
        {
            "user_text":      str,   # original transcribed text
            "english_query":  str,   # English translation for Gemini
            "detected_lang":  str,   # BCP-47 code, e.g. "hi"
            "lang_name":      str,   # e.g. "Hindi"
            "tmp_audio_path": str,   # temp file path (delete when done)
        }
    """
    # Save audio to a temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=audio_suffix) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    stt_result     = speech_to_text(tmp_path)
    user_text      = stt_result["text"]
    detected_lang  = stt_result["detected_lang"]
    english_query  = translate_to_english(user_text, detected_lang)

    return {
        "user_text":      user_text,
        "english_query":  english_query,
        "detected_lang":  detected_lang,
        "lang_name":      stt_result["lang_name"],
        "tmp_audio_path": tmp_path,
    }


def finalize_voice_response(english_response: str, detected_lang: str) -> dict:
    """
    After Gemini replies in English:
        translate back  →  generate MP3

    Returns:
        {
            "translated_text": str,
            "audio_path":      str,   # path to .mp3 (caller must delete)
        }
    """
    translated = translate_from_english(english_response, detected_lang)
    tmp_mp3 = tempfile.mktemp(suffix="_response.mp3")
    text_to_speech(translated, detected_lang, tmp_mp3)
    return {
        "translated_text": translated,
        "audio_path":      tmp_mp3,
    }