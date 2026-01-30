#!/usr/bin/env bash
# Deploy entire stack: Supabase + Render + Vercel
# Non-interactive, CI-safe deployment script
# Reads credentials from environment variables only

set -euo pipefail

SCRIPT_DIR="$(dirname "$0")"

echo "============================================"
echo "=== Full Stack Deployment ==="
echo "============================================"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

# Track deployment results
SUPABASE_STATUS="skipped"
RENDER_STATUS="skipped"
VERCEL_STATUS="skipped"
RENDER_URL=""
VERCEL_URL=""

# Step 1: Supabase Database
echo "--- Step 1: Supabase Database ---"
if [[ -n "${SUPABASE_ACCESS_TOKEN:-}" ]] && [[ -n "${SUPABASE_PROJECT_REF:-}" ]]; then
    if "$SCRIPT_DIR/deploy-backend-supabase.sh"; then
        SUPABASE_STATUS="success"
    else
        SUPABASE_STATUS="failed"
        echo "WARNING: Supabase setup failed, continuing..."
    fi
else
    echo "Skipping: SUPABASE_ACCESS_TOKEN or SUPABASE_PROJECT_REF not set"
fi
echo ""

# Step 2: Render Backend
echo "--- Step 2: Render Backend ---"
if [[ -n "${RENDER_API_KEY:-}" ]]; then
    if "$SCRIPT_DIR/deploy-backend-render.sh"; then
        RENDER_STATUS="success"
    else
        RENDER_STATUS="failed"
        echo "WARNING: Render deployment failed, continuing..."
    fi
else
    echo "Skipping: RENDER_API_KEY not set"
fi
echo ""

# Step 3: Vercel Frontend
echo "--- Step 3: Vercel Frontend ---"
if [[ -n "${VERCEL_TOKEN:-}" ]]; then
    if "$SCRIPT_DIR/deploy-frontend-vercel.sh"; then
        VERCEL_STATUS="success"
    else
        VERCEL_STATUS="failed"
        echo "WARNING: Vercel deployment failed"
    fi
else
    echo "Skipping: VERCEL_TOKEN not set"
fi
echo ""

# Summary
echo "============================================"
echo "=== Deployment Summary ==="
echo "============================================"
echo "Supabase: $SUPABASE_STATUS"
echo "Render:   $RENDER_STATUS"
echo "Vercel:   $VERCEL_STATUS"
echo ""

# Check for failures
if [[ "$SUPABASE_STATUS" == "failed" ]] || [[ "$RENDER_STATUS" == "failed" ]] || [[ "$VERCEL_STATUS" == "failed" ]]; then
    echo "WARNING: One or more deployments failed"
    exit 1
fi

echo "All deployments completed successfully!"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
