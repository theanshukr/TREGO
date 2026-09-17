"""ElevenLabs Voice Integration Layer for TREGO."""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Any

from shared.config import settings


class ElevenLabsVoice:
    """ElevenLabs Voice integration for natural, contextual speech synthesis."""

    def __init__(self):
        self.api_key = settings.elevenlabs_api_key
        self.voice_id = settings.elevenlabs_voice_id or "21m00Tcm4TlvDq8ikWAM"  # Default / Rachel
        self.model_id = settings.elevenlabs_model_id or "eleven_turbo_v2_5"

    def synthesize_speech(self, text: str) -> dict[str, Any]:
        """Convert text to speech audio using ElevenLabs REST API.
        
        Returns a dict containing:
        - ok: bool
        - audio_base64: str (base64-encoded mp3) if available
        - text: str
        - format: "audio/mpeg"
        - error: str | None
        """
        clean_text = text.strip()
        if not clean_text:
            return {"ok": False, "error": "Empty text for speech synthesis"}

        if not self.api_key:
            return {
                "ok": False,
                "error": "ELEVENLABS_API_KEY is not configured",
                "text": clean_text,
                "fallback": "browser_speech",
            }

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key,
        }
        payload = {
            "text": clean_text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True,
            },
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                audio_bytes = resp.read()
                audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
                return {
                    "ok": True,
                    "audio_base64": audio_b64,
                    "format": "audio/mpeg",
                    "text": clean_text,
                }
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            print(f"[elevenlabs] HTTP {e.code} error: {err_body}")
            return {
                "ok": False,
                "error": f"ElevenLabs API returned {e.code}: {err_body}",
                "text": clean_text,
                "fallback": "browser_speech",
            }
        except Exception as e:
            print(f"[elevenlabs] Speech synthesis error: {e}")
            return {
                "ok": False,
                "error": str(e),
                "text": clean_text,
                "fallback": "browser_speech",
            }

    @staticmethod
    def craft_speech_message(phase: str, details: dict[str, Any]) -> str:
        """Generate contextual, concise speech messages for various workflow phases."""
        if phase == "goal_understood":
            goal = details.get("goal", "")
            return f"Understood. Starting inspection for {goal}."

        if phase == "clarification":
            question = details.get("question", "")
            return f"{question}"

        if phase == "permission":
            what = details.get("what", "")
            why = details.get("why", "")
            return f"I need your permission to {what}. {why}. Should I proceed?"

        if phase == "troubleshooting":
            cause = details.get("cause", "")
            return f"I encountered an issue: {cause}. Trying a recovery fix now."

        if phase == "verified":
            summary = details.get("summary", "")
            stack = details.get("stack", "environment")
            return f"Setup completed and verified. {summary or f'Your {stack} is ready to use.'}"

        if phase == "error":
            msg = details.get("msg", "An unexpected error occurred.")
            return f"I could not complete the setup: {msg}"

        return details.get("text", "")
