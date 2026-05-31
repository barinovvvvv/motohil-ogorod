from __future__ import annotations

import logging
import socket
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter

from .config import AppConfig

log = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org"
CAPTION_LIMIT = 1024
CONNECT_TIMEOUT = 30
READ_TIMEOUT = 600
MAX_ATTEMPTS = 3
BACKOFF_SEC = 15


class _KeepAliveAdapter(HTTPAdapter):
    def send(self, request, **kwargs):
        kwargs.setdefault("timeout", (CONNECT_TIMEOUT, READ_TIMEOUT))
        return super().send(request, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs["socket_options"] = [(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]
        super().init_poolmanager(*args, **kwargs)


def _session() -> requests.Session:
    s = requests.Session()
    adapter = _KeepAliveAdapter()
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def _post_with_retry(url: str, data: dict, files: dict) -> dict:
    last_err: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = _session().post(url, data=data, files=files)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
            payload = resp.json()
            if not payload.get("ok"):
                raise RuntimeError(f"Telegram not ok: {payload}")
            return payload["result"]
        except Exception as exc:
            last_err = exc
            log.warning("Telegram attempt %d/%d failed: %s", attempt, MAX_ATTEMPTS, exc)
            if attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF_SEC * attempt)
    raise RuntimeError(f"Telegram upload failed after {MAX_ATTEMPTS} attempts: {last_err}") from last_err


def send_video(
    config: AppConfig,
    video_path: Path,
    thumbnail_path: Path | None,
    caption: str,
) -> None:
    if not config.telegram_enabled:
        return
    if not config.telegram_bot_token or not config.telegram_chat_id:
        raise ValueError("Telegram enabled but TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing.")

    url = f"{API_BASE}/bot{config.telegram_bot_token}/sendDocument"
    data: dict = {
        "chat_id": config.telegram_chat_id,
        "caption": caption[:CAPTION_LIMIT],
    }
    if config.telegram_thread_id:
        data["message_thread_id"] = config.telegram_thread_id

    log.info("Uploading %s to Telegram chat %s", video_path.name, config.telegram_chat_id)

    with video_path.open("rb") as vf:
        files: dict = {"document": (video_path.name, vf, "video/mp4")}
        if thumbnail_path and thumbnail_path.exists():
            with thumbnail_path.open("rb") as tf:
                files["thumbnail"] = (thumbnail_path.name, tf, "image/jpeg")
                result = _post_with_retry(url, data, files)
        else:
            result = _post_with_retry(url, data, files)

    log.info("Telegram ok, message_id=%s", result.get("message_id"))
