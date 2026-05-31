# API Access Checklist

Fill these values in `.env`. Do not paste secret keys into chat unless you are comfortable with that. The cleanest path is to create `.env` locally in this folder.

## Google Cloud / Vertex AI Mode

Recommended when using Google Cloud free credits.

Required:

- Google Cloud project ID
- Billing enabled on that project
- Vertex AI API enabled
- A region where Veo is available, for example `us-central1`
- Local authentication through either:
  - `gcloud auth application-default login`, or
  - a service account JSON file with the needed Vertex AI permissions

`.env` values:

```env
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=your-google-cloud-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
```

## Gemini API Key Mode

Alternative path if you want to use a Gemini API key directly.

Required:

- Gemini API key
- Paid tier access for Veo models, if required by Google for your account

`.env` values:

```env
GOOGLE_GENAI_USE_VERTEXAI=false
GEMINI_API_KEY=your-gemini-api-key
```

## Models

Default values:

```env
STORY_MODEL=gemini-2.5-flash
VEO_MODEL=veo-3.1-fast-generate-preview
VIDEO_ASPECT_RATIO=9:16
VIDEO_RESOLUTION=720p
VIDEO_DURATION_SECONDS=8
PERSON_GENERATION=allow_adult
```

If you specifically get access to a Lite model name, replace `VEO_MODEL` with the exact model ID Google shows in your console/docs.

## Local Tools

Required:

- Python 3.9+
- ffmpeg

On macOS:

```bash
brew install ffmpeg
```

## Telegram Later

Not needed yet. When we enable Telegram, provide:

- Telegram bot token from BotFather
- Telegram channel ID or chat ID
- The bot must be added as an admin to the channel if posting to a channel

`.env` values:

```env
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your-token
TELEGRAM_CHAT_ID=your-chat-id
```

