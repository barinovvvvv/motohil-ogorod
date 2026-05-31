from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Optional

from google.genai import types

from .config import AppConfig, CONFIG_DIR, OUTPUTS_DIR, build_genai_client


def load_topics() -> list[dict]:
    with open(CONFIG_DIR / "topics.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_system_prompt() -> str:
    return (CONFIG_DIR / "agent_system_prompt.md").read_text(encoding="utf-8")


def build_user_prompt(selected_topic: dict) -> str:
    return json.dumps(
        {
            "instruction": "Generate one fresh story from the selected theme. Return only valid JSON.",
            "selected_theme": selected_topic,
            "scene_count": 5,
            "seconds_per_scene": 8,
            "market": "Poland",
            "season": "Polish summer",
        },
        ensure_ascii=False,
        indent=2,
    )


def generate_story(config: AppConfig, topic_number: Optional[int] = None) -> dict:
    topics = load_topics()
    selected_topic = (
        next(t for t in topics if t["number"] == topic_number)
        if topic_number
        else random.choice(topics)
    )

    client = build_genai_client(config)
    response = client.models.generate_content(
        model=config.story_model,
        contents=build_user_prompt(selected_topic),
        config=types.GenerateContentConfig(
            system_instruction=load_system_prompt(),
            response_mime_type="application/json",
            temperature=1.0,
        ),
    )
    return json.loads(response.text)


def save_story(story: dict) -> Path:
    safe_title = "".join(c.lower() if c.isalnum() else "-" for c in story["title"])
    safe_title = "-".join(p for p in safe_title.split("-") if p)[:80]
    path = OUTPUTS_DIR / "stories" / f"{safe_title}.json"
    path.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
