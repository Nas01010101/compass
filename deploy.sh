#!/usr/bin/env bash
# Sets up Google Cloud for Accessibility Copilot and deploys the ADK agent to Cloud Run.
# Usage: PROJECT=my-gcp-project ./deploy.sh            (needs: gcloud auth login, uv)
#        PROJECT=my-gcp-project ./deploy.sh local      (APIs + template only, then run locally)
set -euo pipefail
: "${PROJECT:?set PROJECT to your GCP project id}"
REGION="${REGION:-us-central1}"
TEMPLATE="${TEMPLATE:-copilot-guard}"
cd "$(dirname "$0")"

gcloud config set project "$PROJECT"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  aiplatform.googleapis.com webrisk.googleapis.com modelarmor.googleapis.com firestore.googleapis.com

# Model Armor template: prompt-injection/jailbreak + malicious URL filters on page text.
# gcloud must call the regional endpoint or template writes fail with PERMISSION_DENIED.
gcloud config set api_endpoint_overrides/modelarmor "https://modelarmor.$REGION.rep.googleapis.com/"
gcloud model-armor templates describe "$TEMPLATE" --location="$REGION" >/dev/null 2>&1 ||
  gcloud model-armor templates create "$TEMPLATE" --location="$REGION" \
    --pi-and-jailbreak-filter-settings-enforcement=enabled \
    --pi-and-jailbreak-filter-settings-confidence-level=medium-and-above \
    --malicious-uri-filter-settings-enforcement=enabled

# Firestore (native mode) holds receipts.
gcloud firestore databases describe >/dev/null 2>&1 ||
  gcloud firestore databases create --location="$REGION" --type=firestore-native

SA="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')-compute@developer.gserviceaccount.com"
for role in roles/aiplatform.user roles/modelarmor.user roles/datastore.user; do
  gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$SA" --role="$role" --condition=None >/dev/null
done

cat > agent/copilot/.env <<EOF
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=$PROJECT
GOOGLE_CLOUD_LOCATION=global
MODEL_ARMOR_TEMPLATE=$TEMPLATE
MODEL_ARMOR_LOCATION=$REGION
COPILOT_MODEL=${COPILOT_MODEL:-gemini-3.8-flash}
EOF
echo "wrote agent/copilot/.env"

if [[ "${1:-}" == "local" ]]; then
  echo "Run: cd agent && uv run adk web   (then open http://localhost:8000)"
  exit 0
fi

# Cloud Run hosts the agent API and the ADK web UI. The browser tools drive a local Chrome
# through npx, which the default ADK container does not ship; the demo runs `adk web` locally.
cd agent
uv run adk deploy cloud_run --project "$PROJECT" --region "$REGION" --service_name copilot \
  --app_name copilot --with_ui copilot
