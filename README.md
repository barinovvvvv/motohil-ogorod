# Motohill Ogrod — AI Video Pipeline

Automated pipeline that generates Polish rural comedy video ads for [Motohill Ogrod](https://motohill.pl) garden equipment brand. Runs fully autonomously on Google Cloud every 4 hours.

```
Gemini 2.5 Flash        →   5 scene story JSON
Veo 3.1 Lite (×5)      →   5 parallel video clips (GCS)
ffmpeg                  →   stitched 40-second vertical video
Telegram Bot API        →   posted to group topic
```

## Characters

| Character | Description |
|---|---|
| **Babcia Zosia** | Sharp, practical Polish grandmother. Finds the real solution. |
| **Dziadek Staszek** | Stubborn grandfather. Tries the old way first. Always fails. |

Together they discover Motohill products through comedic misadventure in a Polish summer countryside setting.

## Tech Stack

| Layer | Technology |
|---|---|
| Story generation | Google Gemini 2.5 Flash (Vertex AI) |
| Video generation | Google Veo 3.1 Lite (Vertex AI) |
| Video storage | Google Cloud Storage |
| Video stitching | ffmpeg |
| Publishing | Telegram Bot API |
| Runtime | Google Cloud Run Jobs |
| Scheduler | Google Cloud Scheduler (every 4h) |
| Container registry | Google Artifact Registry |

## Project Structure

```
config/
  agent_system_prompt.md   # Gemini prompt: story + Veo scene format
  topics.json              # Comedy themes library

src/motohill_ogrod/
  config.py                # AppConfig, ADC credential builder
  story_agent.py           # Gemini story generation
  veo_generator.py         # Parallel Veo clip generation + GCS download
  render.py                # ffmpeg stitch + thumbnail
  telegram.py              # Telegram sendDocument with thread support
  main.py                  # Pipeline orchestrator

Dockerfile                 # Python 3.11 + ffmpeg
deploy.sh                  # One-shot GCP infrastructure setup
```

## Local Setup

**Prerequisites:** Python 3.11+, ffmpeg, gcloud CLI authenticated

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
cp .env .env.local  # fill in your values
```

```bash
python -m motohill_ogrod   # full pipeline run
```

## Environment Variables

Copy `.env` and fill in your values. On Cloud Run, set via `gcloud run jobs update --update-env-vars`.

| Variable | Description |
|---|---|
| `GCP_PROJECT_ID` | Google Cloud project ID string |
| `GCP_LOCATION` | Vertex AI region (default: `us-central1`) |
| `GCS_OUTPUT_BUCKET` | GCS bucket name for Veo output clips |
| `STORY_MODEL` | Gemini model (default: `gemini-2.5-flash`) |
| `VEO_MODEL` | Veo model (default: `veo-3.1-lite-generate-001`) |
| `TELEGRAM_ENABLED` | `true` / `false` |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Group chat ID (negative number) |
| `TELEGRAM_THREAD_ID` | Topic/thread ID inside the group |

## Deploy to Google Cloud

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
chmod +x deploy.sh && ./deploy.sh
```

`deploy.sh` creates the Artifact Registry repo, Cloud Run Job, service account with required IAM roles, and Cloud Scheduler trigger. After first deploy, each code change is a one-liner:

```bash
gcloud builds submit . --tag REGION-docker.pkg.dev/PROJECT/motohill/motohill-ogrod:latest
```

## Manual Trigger

```bash
gcloud run jobs execute motohill-ogrod --region us-central1
```

## View Logs

```bash
gcloud logging read 'resource.type=cloud_run_job' --limit=50 --format='value(textPayload)'
```
