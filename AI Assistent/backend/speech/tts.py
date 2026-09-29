"""
Text-to-Speech Engine for Selvie with natural Indian Female Voice.
Uses Edge TTS ('en-IN-NeerjaExpressiveNeural' / 'en-IN-NeerjaNeural' / 'hi-IN-SwaraNeural')
with pyttsx3 offline fallback.
"""
import io
import os
import asyncio
import base64
import hashlib
from pathlib import Path
from typing import Optional, Tuple
import edge_tts
from config.settings import settings

CACHE_DIR = settings.BASE_DIR / "backend" / "speech" / "cache"

class TTSEngine:
    def __init__(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.default_voice = settings.TTS_VOICE
        self.fallback_voice = settings.TTS_VOICE_FALLBACK
        self.hindi_voice = settings.TTS_HINDI_VOICE
        self._pyttsx3_engine = None

    def _get_pyttsx3(self):
        if self._pyttsx3_engine is None:
            try:
                import pyttsx3
                self._pyttsx3_engine = pyttsx3.init()
                # Find female or Indian voice if available in SAPI5
                voices = self._pyttsx3_engine.getProperty('voices')
                for v in voices:
                    if 'zira' in v.name.lower() or 'female' in v.name.lower() or 'india' in v.name.lower():
                        self._pyttsx3_engine.setProperty('voice', v.id)
                        break
                self._pyttsx3_engine.setProperty('rate', 170)
            except Exception as e:
                print(f"[TTS] pyttsx3 init error: {e}")
        return self._pyttsx3_engine

    def _detect_language(self, text: str) -> str:
        """Detect if text contains significant Hindi/Devanagari characters."""
        devanagari_count = sum(1 for char in text if '\u0900' <= char <= '\u097F')
        return self.hindi_voice if devanagari_count > 3 else self.default_voice

    async def synthesize_to_bytes(self, text: str, voice: Optional[str] = None) -> Tuple[bytes, str]:
        """
        Synthesize speech text to MP3 bytes and return (audio_bytes, format).
        Uses disk cache for fast repeat phrases.
        """
        clean_text = text.strip()
        if not clean_text:
            return b"", "audio/mp3"

        chosen_voice = voice or self._detect_language(clean_text)
        cache_key = hashlib.md5(f"{chosen_voice}:{clean_text}".encode()).hexdigest()
        cache_file = CACHE_DIR / f"{cache_key}.mp3"

        if cache_file.exists():
            return cache_file.read_bytes(), "audio/mp3"

        try:
            communicate = edge_tts.Communicate(
                clean_text,
                chosen_voice,
                rate=settings.TTS_RATE,
                pitch=settings.TTS_PITCH
            )
            buffer = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buffer.write(chunk["data"])

            audio_data = buffer.getvalue()
            if audio_data:
                # Save to cache
                try:
                    cache_file.write_bytes(audio_data)
                except Exception:
                    pass
                return audio_data, "audio/mp3"
        except Exception as e:
            print(f"[TTS] Edge TTS error: {e}. Trying fallback voice...")
            # Try secondary voice
            try:
                communicate = edge_tts.Communicate(clean_text, self.fallback_voice)
                buffer = io.BytesIO()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        buffer.write(chunk["data"])
                audio_data = buffer.getvalue()
                if audio_data:
                    return audio_data, "audio/mp3"
            except Exception as e2:
                print(f"[TTS] Fallback voice failed: {e2}. Falling back to pyttsx3 offline audio.")

        # Offline fallback using pyttsx3
        return self._synthesize_pyttsx3(clean_text)

    def _synthesize_pyttsx3(self, text: str) -> Tuple[bytes, str]:
        engine = self._get_pyttsx3()
        if not engine:
            return b"", "audio/wav"

        temp_wav = CACHE_DIR / "temp_offline.wav"
        try:
            engine.save_to_file(text, str(temp_wav))
            engine.runAndWait()
            if temp_wav.exists():
                data = temp_wav.read_bytes()
                try:
                    temp_wav.unlink()
                except Exception:
                    pass
                return data, "audio/wav"
        except Exception as e:
            print(f"[TTS] pyttsx3 synthesis error: {e}")
        return b"", "audio/wav"

    async def synthesize_to_base64(self, text: str) -> str:
        """Synthesize and return as a Base64 data URL for web audio playback."""
        data, mime = await self.synthesize_to_bytes(text)
        if not data:
            return ""
        b64 = base64.b64encode(data).decode('utf-8')
        return f"data:{mime};base64,{b64}"

tts_engine = TTSEngine()
