"""Centralized env-loaded config. Read once, import everywhere."""
from __future__ import annotations

import os
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    """Minimal .env loader (no python-dotenv dep) — looks at repo root."""
    root = Path(__file__).resolve().parent.parent
    env = root / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    # LLM provider — OpenAI or compatible API
    llm_base_url: str | None = os.getenv("LLM_BASE_URL")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

    # ElevenLabs Voice API
    elevenlabs_api_key: str = os.getenv("ELEVENLABS_API_KEY", "")
    elevenlabs_voice_id: str = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel / Default
    elevenlabs_model_id: str = os.getenv("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5")

    # Postgres + pgvector
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://trego:trego@localhost:5432/trego"
    )

    # Windows executor link.
    #
    # The Windows side opens a WebSocket to us at /executor (so the backend
    # never needs to know any client IP). EXECUTOR_TOKEN is the shared
    # secret that gates that connection; both sides need the same value.
    # BACKEND_WS_URL is only used by the Windows-side script — see
    # client/scripts/dev_all.ps1.
    executor_token: str = os.getenv("EXECUTOR_TOKEN", "")

    # Backend / chat UI
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "7860"))

    # Agent loop — capped at 15 in production (was 25). Adversarial
    # prompts can otherwise burn many LLM calls per chat message.
    agent_max_steps: int = int(os.getenv("AGENT_MAX_STEPS", "15"))
    similarity_threshold: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.85"))

    # Per-session hard caps (defense against runaway / adversarial loops).
    max_type_chars_per_session: int = int(os.getenv("TREGO_MAX_TYPE_CHARS", "500"))
    max_destructive_calls_per_session: int = int(
        os.getenv("TREGO_MAX_DESTRUCTIVE", "5")
    )

    # IT Dashboard — FAIL CLOSED on missing password.
    it_username: str = os.getenv("IT_USERNAME", "admin")
    it_password: str = os.getenv("IT_PASSWORD", "")

    # TREGO Admin (approves/rejects pending changes from IT) — FAIL CLOSED.
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")

    # Autonomous / Auto-Approval Mode for Real Keyboard and Mouse
    autonomous_mode: bool = os.getenv("AUTONOMOUS_MODE", "1").lower() in ("1", "true", "yes")
    auto_approve_input: bool = os.getenv("AUTO_APPROVE_INPUT", "1").lower() in ("1", "true", "yes")

    # Production mode — when set, MOCK_* / SKIP_DB env vars are ignored.
    prod_mode: bool = os.getenv("TREGO_PROD", "").lower() in ("1", "true", "yes")


def _bootstrap_dev_token() -> None:
    """If EXECUTOR_TOKEN is empty in dev mode, mint one before we freeze
    the Settings dataclass so /executor isn't open by default."""
    prod = os.getenv("TREGO_PROD", "").lower() in ("1", "true", "yes")
    if prod:
        return
    if not os.getenv("EXECUTOR_TOKEN", "").strip():
        generated = secrets.token_hex(24)
        os.environ["EXECUTOR_TOKEN"] = generated
        print(
            f"[trego:config] WARNING: EXECUTOR_TOKEN was empty. Generated "
            f"ephemeral token (add to .env to persist): {generated}",
            file=sys.stderr,
        )


_bootstrap_dev_token()
settings = Settings()


def _validate_secrets() -> None:
    """Refuse to start with empty or default-weak secrets in prod mode.

    In dev mode (no TREGO_PROD), we generate a one-shot random token so the
    operator notices it doesn't match the executor and fixes the .env.
    """
    if settings.prod_mode:
        problems: list[str] = []
        if not settings.llm_api_key.strip():
            problems.append("LLM_API_KEY must be set in TREGO_PROD=1")
        if not settings.executor_token or len(settings.executor_token) < 16:
            problems.append("EXECUTOR_TOKEN must be set and >= 16 chars in TREGO_PROD=1")
        if not settings.it_password or settings.it_password in ("admin", "password", ""):
            problems.append("IT_PASSWORD must be set to a strong value in TREGO_PROD=1")
        if not settings.admin_password or settings.admin_password in (
            "admin", "super_admin", "password", ""
        ):
            problems.append("ADMIN_PASSWORD must be set to a strong value in TREGO_PROD=1")
        if problems:
            print("[trego:config] REFUSING TO START — fix .env:", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            raise SystemExit(2)


_validate_secrets()
