#!/usr/bin/env bash
# Run by a teammate after the project owner ran scripts/grant-teammate.sh for their account.
# Checks local tools, signs in to Google Cloud, writes agent/copilot/.env if absent, installs
# the Python dependencies and runs the tests. Reads cloud state only; creates no cloud resources.
# Usage: scripts/teammate-setup.sh
set -euo pipefail

PROJECT="${PROJECT:-copilot-gdg-11111801}"
REGION="${REGION:-us-central1}"
TEMPLATE="${TEMPLATE:-copilot-guard}"
cd "$(dirname "$0")/.."

missing=0
need() { # name, command to test, install hint
  if eval "$2" >/dev/null 2>&1; then
    echo "ok       $1"
  else
    echo "missing  $1: $3"
    missing=1
  fi
}
need gcloud "command -v gcloud" "brew install --cask google-cloud-sdk, or https://cloud.google.com/sdk/docs/install"
need uv "command -v uv" "brew install uv, or https://docs.astral.sh/uv/getting-started/installation/"
need node "command -v node" "brew install node (Node 20+), or https://nodejs.org"
need chrome "[ -d '/Applications/Google Chrome.app' ] || command -v google-chrome || command -v chromium" \
  "install Chrome 144+ from https://www.google.com/chrome/"
if [[ $missing -eq 1 ]]; then
  echo "install the missing tools and run this script again" >&2
  exit 1
fi

if [[ -z "$(gcloud auth list --filter=status:ACTIVE --format='value(account)')" ]]; then
  gcloud auth login
fi
if ! gcloud auth application-default print-access-token >/dev/null 2>&1; then
  gcloud auth application-default login
fi
gcloud config set project "$PROJECT"
gcloud auth application-default set-quota-project "$PROJECT"
# gcloud must call the regional endpoint for Model Armor.
gcloud config set api_endpoint_overrides/modelarmor "https://modelarmor.$REGION.rep.googleapis.com/"

if [[ -e agent/copilot/.env ]]; then
  echo "agent/copilot/.env exists, left unchanged"
else
  cat > agent/copilot/.env <<ENV
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=$PROJECT
GOOGLE_CLOUD_LOCATION=global
MODEL_ARMOR_TEMPLATE=$TEMPLATE
MODEL_ARMOR_LOCATION=$REGION
COPILOT_MODEL=${COPILOT_MODEL:-gemini-3.8-flash}
ENV
  echo "wrote agent/copilot/.env"
fi

cd agent
uv sync
uv run pytest -q

cat <<MSG

Setup finished. Run the agent:
  cd agent && uv run adk web        (http://localhost:8000, pick "copilot")
In Chrome, open chrome://inspect/#remote-debugging and turn remote debugging on,
or set COPILOT_OWN_CHROME=1 in agent/copilot/.env to start a separate Chrome.
MSG
