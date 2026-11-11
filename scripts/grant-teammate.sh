#!/usr/bin/env bash
# Run by the project owner. Grants a teammate's Google account the IAM roles needed to run
# the agent locally and to redeploy the Cloud Run service.
# Usage: scripts/grant-teammate.sh teammate@example.com
set -euo pipefail

PROJECT="${PROJECT:-copilot-gdg-11111801}"

if [[ $# -ne 1 || "$1" != *@* ]]; then
  echo "usage: $0 <google-account-email>" >&2
  exit 1
fi
EMAIL="$1"

RUN_ROLES=(
  roles/aiplatform.user                    # Gemini on Vertex AI
  roles/modelarmor.user                    # Model Armor template copilot-guard
  roles/datastore.user                     # Firestore receipts
  roles/serviceusage.serviceUsageConsumer  # use the project as quota project
)
DEPLOY_ROLES=(
  roles/run.developer                      # gcloud run deploy
  roles/cloudbuild.builds.editor           # build from source
  roles/artifactregistry.writer            # push the image
  roles/iam.serviceAccountUser             # deploy as the Cloud Run service account
)

for role in "${RUN_ROLES[@]}" "${DEPLOY_ROLES[@]}"; do
  echo "granting $role to $EMAIL on $PROJECT"
  gcloud projects add-iam-policy-binding "$PROJECT" \
    --member="user:$EMAIL" --role="$role" --condition=None >/dev/null
done
echo "done: $EMAIL has run and deploy roles on $PROJECT"
