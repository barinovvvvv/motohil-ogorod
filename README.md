# Motohill Ogrod Automation

Vertical Polish rural comedy ads for Motohill-style garden equipment.

The pipeline creates one 40-second video from five 8-second Veo scenes:

1. Select one summer theme.
2. Generate a Polish 5-scene story JSON with Gemini.
3. Generate five Veo 3.1 Lite/Fast clips.
4. Stitch clips into one vertical video.
5. Optionally send the result to Telegram later.

## Current Status

Telegram publishing is intentionally disabled for now. The project is prepared for local generation and manual review first.

## What You Need To Provide

Create a local `.env` file from `.env.example` and fill in the values you want to use.

Required for Google generation:

- `GOOGLE_GENAI_USE_VERTEXAI`: use `true` for Google Cloud / Vertex AI credits, or `false` for Gemini API key mode.
- `GOOGLE_CLOUD_PROJECT`: Google Cloud project ID, required for Vertex AI mode.
- `GOOGLE_CLOUD_LOCATION`: Vertex AI region, for example `us-central1`.
- `GOOGLE_APPLICATION_CREDENTIALS`: path to a Google service account JSON file, required for Vertex AI mode when not using local gcloud auth.
- `GEMINI_API_KEY`: only needed if using Gemini Developer API key mode.

Required local tools:

- Python 3.9+
- `ffmpeg` installed and available in PATH

Later, for Telegram:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Important Google Note

Veo 3.1 is available through Gemini API and Vertex AI, but video generation is generally tied to paid access/billing. Google Cloud credits can usually be used only when billing is enabled on a Google Cloud project. The project is configured to support Vertex AI mode because that is the cleanest path for cloud credits.

## Setup

```bash
cd /Users/dmytrobarinov/Documents/Codex/2026-05-27/youtube-facebook-tiktok-vio-3-1/motohill.ogrod
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
cp .env.example .env
```

Install ffmpeg if needed:

```bash
brew install ffmpeg
```

## Run

Generate the story only:

```bash
python -m motohill_ogrod.main --story-only
```

Generate story, clips, and final stitched video:

```bash
python -m motohill_ogrod.main
```

Outputs are written to:

- `outputs/stories`
- `outputs/clips`
- `outputs/final`
