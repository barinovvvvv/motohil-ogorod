from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from .config import OUTPUTS_DIR

log = logging.getLogger(__name__)


def _run_ffmpeg(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.strip()}")


def stitch_clips(clip_paths: list[Path], title: str) -> Path:
    slug = "".join(c.lower() if c.isalnum() else "-" for c in title)
    slug = "-".join(p for p in slug.split("-") if p)[:80]
    concat_file = OUTPUTS_DIR / "clips" / f"{slug}-concat.txt"
    final_path = OUTPUTS_DIR / "final" / f"{slug}.mp4"

    concat_file.write_text(
        "".join(f"file '{p.resolve()}'\n" for p in clip_paths),
        encoding="utf-8",
    )

    cmd_copy = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", str(final_path),
    ]
    log.info("Stitching %d clips -> %s", len(clip_paths), final_path)
    try:
        _run_ffmpeg(cmd_copy)
    except RuntimeError:
        log.warning("Copy concat failed, retrying with re-encode")
        _run_ffmpeg([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k", str(final_path),
        ])

    concat_file.unlink(missing_ok=True)
    return final_path


def generate_thumbnail(video_path: Path, out_path: Path, seek: str = "2") -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _run_ffmpeg([
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", seek, "-i", str(video_path),
        "-vframes", "1", "-vf", "scale=320:568",
        str(out_path),
    ])
    return out_path
