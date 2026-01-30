#!/usr/bin/env bash
set -euo pipefail

# Deploy backend to Render
# This script must be run with RENDER_API_KEY set in environment

echo "=== Deploying Backend to Render ==="

# Validate required environment variables
if [[ -z "${RENDER_API_KEY:-}" ]]; then
  echo "ERROR: RENDER_API_KEY environment variable is not set"
  exit 1
fi

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../backend" && pwd)"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Backend directory: $BACKEND_DIR"

# Change to backend directory
cd "$BACKEND_DIR"

# Run tests before deployment
echo "=== Running tests ==="
if [[ -f "requirements.txt" ]]; then
  pip install -q -r requirements.txt
fi

if [[ -f "requirements-dev.txt" ]]; then
  pip install -q -r requirements-dev.txt
fi

# Run pytest if available
if command -v pytest &> /dev/null; then
  echo "Running pytest..."
  MOCK_SUPABASE=true pytest tests/ -v --tb=short || {
    echo "ERROR: Tests failed. Aborting deployment."
    exit 1
  }
else
  echo "WARNING: pytest not found, skipping tests"
fi

echo "=== Tests passed ==="

# Check if service ID is configured
if [[ -z "${RENDER_SERVICE_ID:-}" ]]; then
  echo "RENDER_SERVICE_ID not set. Checking .env for existing configuration..."

  if [[ -f "$PROJECT_ROOT/.env" ]] && grep -q "RENDER_SERVICE_ID" "$PROJECT_ROOT/.env"; then
    source "$PROJECT_ROOT/.env"
  fi
fi

if [[ -z "${RENDER_SERVICE_ID:-}" ]]; then
  echo ""
  echo "No existing Render service found."
  echo "Please create a Web Service on Render dashboard:"
  echo "  1. Go to https://dashboard.render.com"
  echo "  2. Create a new Web Service"
  echo "  3. Connect your repository"
  echo "  4. Set root directory to 'backend'"
  echo "  5. Set build command: pip install -r requirements.txt"
  echo "  6. Set start command: uvicorn app.main:app --host 0.0.0.0 --port \$PORT"
  echo "  7. Add environment variables from backend/.env"
  echo "  8. Copy the service ID and set RENDER_SERVICE_ID"
  echo ""
  echo "Then re-run this script with:"
  echo "  export RENDER_SERVICE_ID=srv-xxxxx"
  echo ""
  exit 1
fi

# Trigger deployment via Render API
echo "=== Triggering Render deployment ==="
DEPLOY_RESPONSE=$(curl -s -X POST \
  "https://api.render.com/v1/services/${RENDER_SERVICE_ID}/deploys" \
  -H "Authorization: Bearer ${RENDER_API_KEY}" \
  -H "Content-Type: application/json")

DEPLOY_ID=$(echo "$DEPLOY_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [[ -z "$DEPLOY_ID" ]]; then
  echo "ERROR: Failed to trigger deployment"
  echo "$DEPLOY_RESPONSE"
  exit 1
fi

echo "Deployment triggered: $DEPLOY_ID"

# Wait for deployment to complete
echo "=== Waiting for deployment ==="
MAX_ATTEMPTS=60
ATTEMPT=0

while [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; do
  DEPLOY_STATUS=$(curl -s \
    "https://api.render.com/v1/services/${RENDER_SERVICE_ID}/deploys/${DEPLOY_ID}" \
    -H "Authorization: Bearer ${RENDER_API_KEY}")

  STATUS=$(echo "$DEPLOY_STATUS" | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)

  case "$STATUS" in
    "live")
      echo "Deployment successful!"
      break
      ;;
    "build_failed"|"deactivated"|"canceled")
      echo "ERROR: Deployment failed with status: $STATUS"
      exit 1
      ;;
    *)
      echo "Status: $STATUS (attempt $((ATTEMPT + 1))/$MAX_ATTEMPTS)"
      sleep 10
      ;;
  esac

  ATTEMPT=$((ATTEMPT + 1))
done

if [[ $ATTEMPT -ge $MAX_ATTEMPTS ]]; then
  echo "WARNING: Deployment timed out. Check Render dashboard for status."
fi

# Get service URL
SERVICE_INFO=$(curl -s \
  "https://api.render.com/v1/services/${RENDER_SERVICE_ID}" \
  -H "Authorization: Bearer ${RENDER_API_KEY}")

SERVICE_URL=$(echo "$SERVICE_INFO" | grep -o '"url":"[^"]*"' | head -1 | cut -d'"' -f4)

echo ""
echo "=== Deployment Complete ==="
echo "Backend URL: ${SERVICE_URL:-https://your-service.onrender.com}"
echo ""
