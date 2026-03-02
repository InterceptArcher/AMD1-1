#!/usr/bin/env bash
set -euo pipefail

# Deploy frontend to Vercel (beta or prod)
# Usage: ./scripts/deploy-frontend-vercel.sh         # deploys beta (default)
#        ./scripts/deploy-frontend-vercel.sh prod     # deploys production

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load deploy credentials
if [[ -f "$PROJECT_ROOT/.env.deploy" ]]; then
  set -a
  source "$PROJECT_ROOT/.env.deploy"
  set +a
fi

# Determine environment
ENV="${1:-beta}"

if [[ "$ENV" != "beta" && "$ENV" != "prod" ]]; then
  echo "ERROR: Invalid environment '$ENV'. Use 'beta' or 'prod'."
  exit 1
fi

# Validate token
if [[ -z "${VERCEL_TOKEN:-}" ]]; then
  echo "ERROR: VERCEL_TOKEN not set (check .env.deploy or environment)"
  exit 1
fi

export VERCEL_ORG_ID="${VERCEL_ORG_ID:?Missing VERCEL_ORG_ID}"

if [[ "$ENV" == "prod" ]]; then
  export VERCEL_PROJECT_ID="${VERCEL_PROJECT_ID_ALPHA:?Missing VERCEL_PROJECT_ID_ALPHA}"
  LIVE_URL="https://amd1-1-alpha.vercel.app"
  echo "=== Deploying frontend to Vercel (production) ==="
else
  export VERCEL_PROJECT_ID="${VERCEL_PROJECT_ID_BETA:?Missing VERCEL_PROJECT_ID_BETA}"
  LIVE_URL="https://amd1-1-beta.vercel.app"
  echo "=== Deploying frontend to Vercel (beta) ==="
fi

cd "$PROJECT_ROOT"
DEPLOY_URL=$(npx vercel deploy --prod --token "$VERCEL_TOKEN" --yes 2>&1 | grep -E '^https://' | tail -1)

echo ""
echo "=== Deployed ==="
echo "Environment: $ENV"
echo "URL: $DEPLOY_URL"
echo "Live: $LIVE_URL"
