#!/bin/bash
# Supabase database migrations for AMD1-1 Alpha

set -euo pipefail

# This script creates the required Supabase tables for RAD enrichment.
# Usage: ./scripts/migrate-supabase.sh

SUPABASE_URL="${SUPABASE_URL}"
SUPABASE_DB_URL="${SUPABASE_DB_URL}"  # Format: postgresql://user:password@host:5432/postgres

if [[ -z "$SUPABASE_URL" ]]; then
    echo "Error: SUPABASE_URL environment variable not set"
    exit 1
fi

# Use supabase-cli or psql
if command -v supabase &> /dev/null; then
    echo "Using supabase-cli..."
    
    # Create tables via SQL
    supabase db push --db-url "$SUPABASE_DB_URL"
else
    echo "Using psql..."
    
    # Create raw_data table
    psql "$SUPABASE_DB_URL" <<EOF
    CREATE TABLE IF NOT EXISTS raw_data (
        id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        email VARCHAR(255) NOT NULL,
        source VARCHAR(50) NOT NULL,
        payload JSONB NOT NULL,
        fetched_at TIMESTAMP DEFAULT NOW(),
        created_at TIMESTAMP DEFAULT NOW()
    );
    
    CREATE INDEX IF NOT EXISTS idx_raw_data_email ON raw_data(email);
    CREATE INDEX IF NOT EXISTS idx_raw_data_source ON raw_data(source);
EOF

    # Create staging_normalized table
    psql "$SUPABASE_DB_URL" <<EOF
    CREATE TABLE IF NOT EXISTS staging_normalized (
        id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        email VARCHAR(255) NOT NULL UNIQUE,
        normalized_fields JSONB NOT NULL,
        status VARCHAR(50) DEFAULT 'resolving',
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );
    
    CREATE INDEX IF NOT EXISTS idx_staging_email ON staging_normalized(email);
EOF

    # Create finalize_data table
    psql "$SUPABASE_DB_URL" <<EOF
    CREATE TABLE IF NOT EXISTS finalize_data (
        id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        email VARCHAR(255) NOT NULL,
        normalized_data JSONB NOT NULL,
        personalization_intro TEXT,
        personalization_cta TEXT,
        data_sources TEXT[] DEFAULT '{}',
        resolved_at TIMESTAMP DEFAULT NOW(),
        created_at TIMESTAMP DEFAULT NOW()
    );
    
    CREATE INDEX IF NOT EXISTS idx_finalize_email ON finalize_data(email);
    CREATE INDEX IF NOT EXISTS idx_finalize_resolved_at ON finalize_data(resolved_at DESC);
EOF

fi

echo "✅ Supabase migrations completed successfully"
