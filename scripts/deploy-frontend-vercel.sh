#!/usr/bin/env bash
set -euo pipefail

# Deploy frontend to Vercel
# This script must be run with VERCEL_TOKEN set in environment

echo "=== Deploying Frontend to Vercel ==="

# Validate required environment variables
if [[ -z "${VERCEL_TOKEN:-}" ]]; then
  echo "ERROR: VERCEL_TOKEN environment variable is not set"
  exit 1
fi

FRONTEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../frontend" && pwd)"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Frontend directory: $FRONTEND_DIR"

# Change to frontend directory
cd "$FRONTEND_DIR"

# Install dependencies
echo "=== Installing dependencies ==="
npm ci --silent

# Run tests before deployment
echo "=== Running tests ==="
npm test -- --passWithNoTests || {
  echo "ERROR: Tests failed. Aborting deployment."
  exit 1
}

echo "=== Tests passed ==="

# Build the project
echo "=== Building project ==="
npm run build || {
  echo "ERROR: Build failed. Aborting deployment."
  exit 1
}

echo "=== Build successful ==="

# Check for existing Vercel project configuration
if [[ -z "${VERCEL_PROJECT_ID:-}" ]] || [[ -z "${VERCEL_ORG_ID:-}" ]]; then
  echo "Checking for existing Vercel configuration..."

  if [[ -f "$PROJECT_ROOT/.env" ]]; then
    source "$PROJECT_ROOT/.env" 2>/dev/null || true
  fi
fi

# Set up Vercel CLI arguments
VERCEL_ARGS="--token ${VERCEL_TOKEN} --yes"

if [[ -n "${VERCEL_TEAM_ID:-}" ]]; then
  VERCEL_ARGS="$VERCEL_ARGS --scope ${VERCEL_TEAM_ID}"
fi

# Link project if not already linked
if [[ ! -f ".vercel/project.json" ]]; then
  echo "=== Linking Vercel project ==="
  npx vercel link $VERCEL_ARGS || {
    echo "Creating new Vercel project..."
    npx vercel $VERCEL_ARGS
  }
fi

# Deploy to production
echo "=== Deploying to Vercel ==="
DEPLOY_URL=$(npx vercel --prod $VERCEL_ARGS 2>&1 | tail -1)

if [[ -z "$DEPLOY_URL" ]] || [[ "$DEPLOY_URL" == *"Error"* ]]; then
  echo "ERROR: Deployment failed"
  echo "$DEPLOY_URL"
  exit 1
fi

# Save project IDs to .env if they exist
if [[ -f ".vercel/project.json" ]]; then
  PROJECT_ID=$(grep -o '"projectId":"[^"]*"' .vercel/project.json | cut -d'"' -f4)
  ORG_ID=$(grep -o '"orgId":"[^"]*"' .vercel/project.json | cut -d'"' -f4)

  if [[ -n "$PROJECT_ID" ]] && [[ -n "$ORG_ID" ]]; then
    echo "Saving Vercel configuration to .env..."

    # Update or create .env entries
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
      grep -v "VERCEL_PROJECT_ID\|VERCEL_ORG_ID" "$PROJECT_ROOT/.env" > "$PROJECT_ROOT/.env.tmp" || true
      mv "$PROJECT_ROOT/.env.tmp" "$PROJECT_ROOT/.env"
    fi

    echo "VERCEL_PROJECT_ID=$PROJECT_ID" >> "$PROJECT_ROOT/.env"
    echo "VERCEL_ORG_ID=$ORG_ID" >> "$PROJECT_ROOT/.env"
  fi
fi

echo ""
echo "=== Deployment Complete ==="
echo "Frontend URL: $DEPLOY_URL"
echo ""
