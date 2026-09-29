"""
Speech-to-Text (STT) Engine for Selvie.
Provides microphone listening via SpeechRecognition / Google STT / local Whisper fallback.
"""
import io
import wave
from typing import Optional, Dict, Any

class STTEngine:
    def __init__(self):
        self._recognizer = None

    def _get_recognizer(self):
        if self._recognizer is None:
            try:
                import speech_recognition as sr
                self._recognizer = sr.Recognizer()
                self._recognizer.energy_threshold = 300
                self._recognizer.dynamic_energy_threshold = True
                self._recognizer.pause_threshold = 0.8
            except Exception as e:
                print(f"[STT] Recognizer init error: {e}")
        return self._recognizer

    def transcribe_audio_bytes(self, audio_bytes: bytes, sample_rate: int = 16000) -> Dict[str, Any]:
        """Transcribe raw or WAV audio bytes to text."""
        import speech_recognition as sr
        r = self._get_recognizer()
        if not r:
            return {"success": False, "error": "STT not available"}

        try:
            audio_file = io.BytesIO(audio_bytes)
            with sr.AudioFile(audio_file) as source:
                audio_data = r.record(source)

            # Try recognition with en-IN and hi-IN
            text = r.recognize_google(audio_data, language="en-IN")
            return {"success": True, "text": text}
        except sr.UnknownValueError:
            return {"success": False, "error": "Could not understand speech"}
        except sr.RequestError as e:
            return {"success": False, "error": f"STT request error: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def listen_from_mic(self, timeout: int = 5, phrase_time_limit: int = 10) -> Dict[str, Any]:
        """Record directly from default microphone."""
        import speech_recognition as sr
        r = self._get_recognizer()
        if not r:
            return {"success": False, "error": "Microphone recognizer not available"}

        try:
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)

            text = r.recognize_google(audio, language="en-IN")
            return {"success": True, "text": text}
        except sr.WaitTimeoutError:
            return {"success": False, "error": "Listening timed out"}
        except sr.UnknownValueError:
            return {"success": False, "error": "Could not understand audio"}
        except Exception as e:
            return {"success": False, "error": str(e)}

stt_engine = STTEngine()
