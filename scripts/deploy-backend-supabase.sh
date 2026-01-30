#!/usr/bin/env bash
set -euo pipefail

# Deploy/configure Supabase
# This script must be run with SUPABASE_ACCESS_TOKEN set in environment

echo "=== Configuring Supabase ==="

# Validate required environment variables
if [[ -z "${SUPABASE_ACCESS_TOKEN:-}" ]]; then
  echo "ERROR: SUPABASE_ACCESS_TOKEN environment variable is not set"
  exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Check for existing project reference
if [[ -z "${SUPABASE_PROJECT_REF:-}" ]]; then
  echo "Checking for existing Supabase configuration..."

  if [[ -f "$PROJECT_ROOT/.env" ]]; then
    source "$PROJECT_ROOT/.env" 2>/dev/null || true
  fi
fi

# Install Supabase CLI if not present
if ! command -v supabase &> /dev/null; then
  echo "Installing Supabase CLI..."
  npm install -g supabase
fi

# Login to Supabase
echo "=== Authenticating with Supabase ==="
export SUPABASE_ACCESS_TOKEN

# List projects to verify authentication
echo "Fetching Supabase projects..."
PROJECTS=$(curl -s \
  "https://api.supabase.com/v1/projects" \
  -H "Authorization: Bearer ${SUPABASE_ACCESS_TOKEN}")

if echo "$PROJECTS" | grep -q "error"; then
  echo "ERROR: Failed to authenticate with Supabase"
  echo "$PROJECTS"
  exit 1
fi

echo "Authentication successful."

if [[ -z "${SUPABASE_PROJECT_REF:-}" ]]; then
  echo ""
  echo "Available projects:"
  echo "$PROJECTS" | grep -o '"id":"[^"]*"\|"name":"[^"]*"' | paste - - | sed 's/"id":"//;s/".*"name":"/  /;s/"$//'
  echo ""
  echo "Set SUPABASE_PROJECT_REF to your project reference and re-run."
  echo "  export SUPABASE_PROJECT_REF=your-project-ref"
  echo ""
  exit 0
fi

# Get project details
echo "=== Fetching project details ==="
PROJECT_INFO=$(curl -s \
  "https://api.supabase.com/v1/projects/${SUPABASE_PROJECT_REF}" \
  -H "Authorization: Bearer ${SUPABASE_ACCESS_TOKEN}")

PROJECT_NAME=$(echo "$PROJECT_INFO" | grep -o '"name":"[^"]*"' | head -1 | cut -d'"' -f4)
PROJECT_REGION=$(echo "$PROJECT_INFO" | grep -o '"region":"[^"]*"' | head -1 | cut -d'"' -f4)

if [[ -z "$PROJECT_NAME" ]]; then
  echo "ERROR: Could not find project with ref: $SUPABASE_PROJECT_REF"
  exit 1
fi

echo "Project: $PROJECT_NAME"
echo "Region: $PROJECT_REGION"

# Get API keys
echo "=== Fetching API keys ==="
API_KEYS=$(curl -s \
  "https://api.supabase.com/v1/projects/${SUPABASE_PROJECT_REF}/api-keys" \
  -H "Authorization: Bearer ${SUPABASE_ACCESS_TOKEN}")

ANON_KEY=$(echo "$API_KEYS" | grep -o '"anon[^}]*' | grep -o '"api_key":"[^"]*"' | cut -d'"' -f4)
SERVICE_KEY=$(echo "$API_KEYS" | grep -o '"service_role[^}]*' | grep -o '"api_key":"[^"]*"' | cut -d'"' -f4)

SUPABASE_URL="https://${SUPABASE_PROJECT_REF}.supabase.co"

# Save configuration
echo "=== Saving configuration ==="

# Update backend .env
BACKEND_ENV="$PROJECT_ROOT/backend/.env"
if [[ -f "$BACKEND_ENV" ]]; then
  # Remove existing Supabase entries
  grep -v "^SUPABASE_URL=\|^SUPABASE_KEY=\|^MOCK_SUPABASE=" "$BACKEND_ENV" > "$BACKEND_ENV.tmp" || true
  mv "$BACKEND_ENV.tmp" "$BACKEND_ENV"
fi

cat >> "$BACKEND_ENV" << ENVEOF
MOCK_SUPABASE=false
SUPABASE_URL=$SUPABASE_URL
SUPABASE_KEY=$SERVICE_KEY
ENVEOF

# Update frontend .env.local
FRONTEND_ENV="$PROJECT_ROOT/frontend/.env.local"
if [[ -f "$FRONTEND_ENV" ]]; then
  grep -v "^NEXT_PUBLIC_SUPABASE" "$FRONTEND_ENV" > "$FRONTEND_ENV.tmp" || true
  mv "$FRONTEND_ENV.tmp" "$FRONTEND_ENV"
fi

cat >> "$FRONTEND_ENV" << ENVEOF
NEXT_PUBLIC_SUPABASE_URL=$SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY=$ANON_KEY
ENVEOF

# Save project ref to root .env
if [[ -f "$PROJECT_ROOT/.env" ]]; then
  grep -v "SUPABASE_PROJECT_REF" "$PROJECT_ROOT/.env" > "$PROJECT_ROOT/.env.tmp" || true
  mv "$PROJECT_ROOT/.env.tmp" "$PROJECT_ROOT/.env"
fi
echo "SUPABASE_PROJECT_REF=$SUPABASE_PROJECT_REF" >> "$PROJECT_ROOT/.env"

echo ""
echo "=== Supabase Configuration Complete ==="
echo "Project URL: $SUPABASE_URL"
echo "Configuration saved to:"
echo "  - backend/.env"
echo "  - frontend/.env.local"
echo ""
