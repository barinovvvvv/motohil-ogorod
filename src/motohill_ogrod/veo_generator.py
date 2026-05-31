from __future__ import annotations

import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from google.genai import types

from .config import AppConfig, OUTPUTS_DIR, build_genai_client, build_storage_client

log = logging.getLogger(__name__)

POLL_INTERVAL_SEC = 20
POLL_TIMEOUT_SEC = 15 * 60
MAX_ATTEMPTS = 3
BACKOFF_BASE_SEC = 30


class VeoError(RuntimeError):
    pass


def _parse_gs_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("gs://"):
        raise ValueError(f"Not a GCS URI: {uri}")
    rest = uri[len("gs://"):]
    bucket, _, blob = rest.partition("/")
    if not bucket or not blob:
        raise ValueError(f"Malformed GCS URI: {uri}")
    return bucket, blob


def _download_from_gcs(config: AppConfig, gcs_uri: str, dest: Path) -> Path:
    storage_client = build_storage_client(config)
    bucket_name, blob_name = _parse_gs_uri(gcs_uri)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    log.info("Downloading %s -> %s", gcs_uri, dest)
    blob.download_to_filename(str(dest))
    return dest


def _generate_once(config: AppConfig, prompt: str, output_gcs_uri: str) -> str:
    client = build_genai_client(config)
    log.info("Veo submit: %s", output_gcs_uri)
    operation = client.models.generate_videos(
        model=config.veo_model,
        prompt=prompt,
        config=types.GenerateVideosConfig(
            aspect_ratio=config.video_aspect_ratio,
            duration_seconds=config.video_duration_seconds,
            number_of_videos=1,
            output_gcs_uri=output_gcs_uri,
            person_generation=config.person_generation,
        ),
    )

    deadline = time.monotonic() + POLL_TIMEOUT_SEC
    while not operation.done:
        if time.monotonic() > deadline:
            raise VeoError(f"Veo timed out after {POLL_TIMEOUT_SEC}s")
        time.sleep(POLL_INTERVAL_SEC)
        operation = client.operations.get(operation)

    if operation.error:
        raise VeoError(f"Veo operation error: {operation.error}")

    videos = getattr(operation.response, "generated_videos", None)
    if not videos:
        raise VeoError("Veo returned no videos")

    uri = videos[0].video.uri
    if not uri:
        raise VeoError("Veo returned video without URI")

    log.info("Veo done: %s", uri)
    return uri


def generate_scene_clip(
    config: AppConfig, scene_index: int, prompt: str, run_id: str
) -> Path:
    output_gcs_uri = f"gs://{config.gcs_output_bucket}/runs/{run_id}/scene-{scene_index:02d}/"
    dest = OUTPUTS_DIR / "clips" / run_id / f"scene-{scene_index:02d}.mp4"

    last_err: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            gcs_uri = _generate_once(config, prompt, output_gcs_uri)
            return _download_from_gcs(config, gcs_uri, dest)
        except Exception as exc:
            last_err = exc
            log.warning("Scene %d attempt %d/%d failed: %s", scene_index, attempt, MAX_ATTEMPTS, exc)
            if attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF_BASE_SEC * (2 ** (attempt - 1)))

    raise VeoError(f"Scene {scene_index} failed after {MAX_ATTEMPTS} attempts: {last_err}") from last_err


def generate_all_clips(config: AppConfig, story: dict) -> list[Path]:
    run_id = uuid.uuid4().hex[:12]
    scenes = story["scenes"]

    log.info("Generating %d scenes in parallel (run %s)", len(scenes), run_id)
    results: dict[int, Path] = {}

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(generate_scene_clip, config, i, scenes[f"scene {i}"], run_id): i
            for i in range(1, 6)
        }
        for future in as_completed(futures):
            i = futures[future]
            results[i] = future.result()
            log.info("Scene %d done", i)

    return [results[i] for i in range(1, 6)]
