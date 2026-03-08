#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────────────────────
# Nexus — Google Cloud Run Deployment Script
# Deploys the FastAPI backend with WebSocket support
# ──────────────────────────────────────────────────────────────

# Configuration (override via environment)
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?GOOGLE_CLOUD_PROJECT env var is required}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-nexus-backend}"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# ── Pre-flight checks ────────────────────────────────────────

if [[ -z "${GEMINI_API_KEY:-}" ]]; then
    echo "ERROR: GEMINI_API_KEY env var is required"
    exit 1
fi

if ! command -v gcloud &>/dev/null; then
    echo "ERROR: gcloud CLI is not installed. Install it from https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo "==> Configuring project: ${PROJECT_ID}"
gcloud config set project "${PROJECT_ID}"

# ── Enable required APIs ─────────────────────────────────────

echo "==> Enabling required GCP APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    firestore.googleapis.com

# ── Build container image ─────────────────────────────────────

echo "==> Building container image: ${IMAGE}"
gcloud builds submit \
    --tag "${IMAGE}" \
    --project "${PROJECT_ID}" \
    ./backend

# ── Deploy to Cloud Run ──────────────────────────────────────

echo "==> Deploying ${SERVICE_NAME} to Cloud Run (${REGION})..."
gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE}" \
    --region "${REGION}" \
    --platform managed \
    --memory 2Gi \
    --cpu 1 \
    --timeout 3600 \
    --min-instances 0 \
    --max-instances 3 \
    --session-affinity \
    --allow-unauthenticated \
    --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY},GOOGLE_CLOUD_PROJECT=${PROJECT_ID},REDIS_URL=${REDIS_URL:-}"

# ── Retrieve service URL ─────────────────────────────────────

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --region "${REGION}" \
    --format "value(status.url)")

echo ""
echo "============================================"
echo "  Nexus backend deployed successfully!"
echo "  URL: ${SERVICE_URL}"
echo "============================================"
echo ""

# ── Health check ──────────────────────────────────────────────

echo "==> Running health check..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/health" --max-time 30 || true)

if [[ "${HTTP_STATUS}" == "200" ]]; then
    echo "Health check PASSED (HTTP ${HTTP_STATUS})"
else
    echo "WARNING: Health check returned HTTP ${HTTP_STATUS}"
    echo "The service may still be starting up. Try: curl ${SERVICE_URL}/health"
fi
