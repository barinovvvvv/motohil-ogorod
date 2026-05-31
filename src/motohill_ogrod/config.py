from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google import genai

ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT_DIR / "config"
OUTPUTS_DIR = ROOT_DIR / "outputs"


@dataclass(frozen=True)
class AppConfig:
    gcp_project_id: str
    gcp_location: str
    gcs_output_bucket: str
    story_model: str
    veo_model: str
    video_aspect_ratio: str
    video_duration_seconds: int
    person_generation: str
    telegram_enabled: bool
    telegram_bot_token: str
    telegram_chat_id: str
    telegram_thread_id: str
    # Optional: SA JSON for local use without gcloud. Empty = use ADC.
    sa_info: Optional[dict] = field(default=None)


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def load_config() -> AppConfig:
    load_dotenv(ROOT_DIR / "API_KEYS.txt", override=False)
    load_dotenv(ROOT_DIR / ".env", override=False)

    sa_info: Optional[dict] = None
    sa_raw = os.environ.get("GCP_SERVICE_ACCOUNT_JSON", "").strip()
    if sa_raw:
        try:
            sa_info = json.loads(sa_raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"GCP_SERVICE_ACCOUNT_JSON is not valid JSON. Got: {sa_raw[:80]}"
            ) from exc

    return AppConfig(
        gcp_project_id=_require("GCP_PROJECT_ID"),
        gcp_location=os.environ.get("GCP_LOCATION", "us-central1"),
        gcs_output_bucket=_require("GCS_OUTPUT_BUCKET"),
        story_model=os.environ.get("STORY_MODEL", "gemini-2.5-flash"),
        veo_model=os.environ.get("VEO_MODEL", "veo-3.1-fast-generate-preview"),
        video_aspect_ratio=os.environ.get("VIDEO_ASPECT_RATIO", "9:16"),
        video_duration_seconds=int(os.environ.get("VIDEO_DURATION_SECONDS", "8")),
        person_generation=os.environ.get("PERSON_GENERATION", "allow_adult"),
        telegram_enabled=os.environ.get("TELEGRAM_ENABLED", "false").lower() == "true",
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
        telegram_thread_id=os.environ.get("TELEGRAM_THREAD_ID", ""),
        sa_info=sa_info,
    )


def _sa_creds(config: AppConfig):
    if not config.sa_info:
        return None
    from google.oauth2 import service_account
    return service_account.Credentials.from_service_account_info(
        config.sa_info,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )


def build_genai_client(config: AppConfig) -> genai.Client:
    # When sa_info is None, SDK uses Application Default Credentials automatically.
    return genai.Client(
        vertexai=True,
        project=config.gcp_project_id,
        location=config.gcp_location,
        credentials=_sa_creds(config),
    )


def build_storage_client(config: AppConfig):
    from google.cloud import storage
    return storage.Client(
        project=config.gcp_project_id,
        credentials=_sa_creds(config),
    )


def ensure_output_dirs() -> None:
    (OUTPUTS_DIR / "stories").mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "clips").mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "final").mkdir(parents=True, exist_ok=True)
