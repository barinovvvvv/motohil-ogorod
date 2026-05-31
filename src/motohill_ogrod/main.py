from __future__ import annotations

import argparse
import logging
import sys
import time

from .config import ensure_output_dirs, load_config, OUTPUTS_DIR
from .render import generate_thumbnail, stitch_clips
from .story_agent import generate_story, save_story
from .telegram import send_video
from .veo_generator import generate_all_clips


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Motohill Ogrod video pipeline.")
    parser.add_argument("--story-only", action="store_true", help="Generate story JSON only.")
    parser.add_argument("--topic", type=int, choices=range(1, 11), help="Force a specific topic number.")
    return parser.parse_args()


def main() -> None:
    _setup_logging()
    log = logging.getLogger("motohill")
    started = time.monotonic()

    args = parse_args()
    config = load_config()
    ensure_output_dirs()

    log.info("[1/5] Generating story with Gemini")
    story = generate_story(config, topic_number=args.topic)
    story_path = save_story(story)
    log.info("Story saved: %s", story_path)

    if args.story_only:
        return

    log.info("[2/5] Generating %d clips with Veo (parallel)", 5)
    clip_paths = generate_all_clips(config, story)

    log.info("[3/5] Stitching clips with ffmpeg")
    final_video = stitch_clips(clip_paths, story["title"])
    log.info("Final video: %s", final_video)

    log.info("[4/5] Generating thumbnail")
    thumbnail = OUTPUTS_DIR / "final" / (final_video.stem + "-thumb.jpg")
    try:
        generate_thumbnail(final_video, thumbnail)
    except Exception as exc:
        log.warning("Thumbnail generation failed (non-fatal): %s", exc)
        thumbnail = None

    log.info("[5/5] Sending to Telegram")
    caption = f"{story['title']}\n\n{story.get('description', '')}"
    send_video(config, final_video, thumbnail, caption)

    elapsed = time.monotonic() - started
    log.info("Done in %.1fs", elapsed)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.getLogger("motohill").exception("Pipeline failed: %s", exc)
        sys.exit(1)
