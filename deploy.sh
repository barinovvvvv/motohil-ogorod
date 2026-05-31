#!/bin/bash
# Deploy Motohill Ogrod to Google Cloud Run Jobs.
# Run once to set up, then each push just rebuilds the image.
#
# Prerequisites:
#   gcloud auth login
#   gcloud config set project YOUR_PROJECT_ID
#   Edit the variables below before running.

set -euo pipefail

PROJECT_ID="$(gcloud config get-value project)"
REGION="us-central1"
REPO="motohill"
IMAGE="motohill-ogrod"
JOB_NAME="motohill-ogrod"
SA_NAME="motohill-runner"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Hours between runs (Cloud Scheduler cron).
# "0 */4 * * *" = every 4 hours. Adjust as needed.
CRON_SCHEDULE="0 */4 * * *"

echo "=== Project: $PROJECT_ID ==="

# 1. Enable required APIs
echo "[1/6] Enabling APIs..."
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudscheduler.googleapis.com \
    aiplatform.googleapis.com \
    storage.googleapis.com \
    --project "$PROJECT_ID"

# 2. Create Artifact Registry repo (skip if exists)
echo "[2/6] Creating Artifact Registry repo..."
gcloud artifacts repositories create "$REPO" \
    --repository-format=docker \
    --location="$REGION" \
    --project "$PROJECT_ID" 2>/dev/null || echo "  Repo already exists, skipping."

# 3. Build and push Docker image
echo "[3/6] Building and pushing image..."
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE}:latest"
gcloud builds submit . \
    --tag "$IMAGE_URI" \
    --project "$PROJECT_ID"

# 4. Create service account (skip if exists)
echo "[4/6] Creating service account..."
gcloud iam service-accounts create "$SA_NAME" \
    --display-name "Motohill Runner" \
    --project "$PROJECT_ID" 2>/dev/null || echo "  SA already exists, skipping."

# Grant roles to SA
for ROLE in roles/aiplatform.user roles/storage.objectAdmin; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member "serviceAccount:${SA_EMAIL}" \
        --role "$ROLE" \
        --condition=None \
        --quiet
done

# 5. Create or update Cloud Run Job
echo "[5/6] Deploying Cloud Run Job..."
gcloud run jobs deploy "$JOB_NAME" \
    --image "$IMAGE_URI" \
    --region "$REGION" \
    --service-account "$SA_EMAIL" \
    --memory 1Gi \
    --cpu 1 \
    --task-timeout 3600 \
    --max-retries 1 \
    --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID},GCP_LOCATION=${REGION}" \
    --project "$PROJECT_ID"

echo ""
echo "=== Job deployed. ==="
echo "Set remaining env vars (GCS_OUTPUT_BUCKET, TELEGRAM_*) via:"
echo "  gcloud run jobs update $JOB_NAME --region $REGION --update-env-vars KEY=VALUE"
echo ""

# 6. Create Cloud Scheduler trigger
echo "[6/6] Creating Cloud Scheduler trigger..."
# Get Cloud Run Job invoker SA for scheduler
gcloud scheduler jobs create http "trigger-${JOB_NAME}" \
    --location "$REGION" \
    --schedule "$CRON_SCHEDULE" \
    --uri "https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
    --http-method POST \
    --oauth-service-account-email "$SA_EMAIL" \
    --project "$PROJECT_ID" 2>/dev/null || \
gcloud scheduler jobs update http "trigger-${JOB_NAME}" \
    --location "$REGION" \
    --schedule "$CRON_SCHEDULE" \
    --project "$PROJECT_ID"

echo ""
echo "=== Done! ==="
echo "Manual run: gcloud run jobs execute $JOB_NAME --region $REGION"
echo "View logs:  gcloud logging read 'resource.type=cloud_run_job' --limit=50 --format='value(textPayload)'"
