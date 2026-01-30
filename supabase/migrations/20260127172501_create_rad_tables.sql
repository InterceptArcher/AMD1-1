-- RAD Enrichment Pipeline Tables
-- raw_data: Stores raw API responses from external sources (Apollo, PDL, Hunter, GNews)
-- staging_normalized: Tracks enrichment progress during resolution
-- finalize_data: Final normalized profiles ready for frontend consumption

-- ============================================================================
-- raw_data table
-- ============================================================================
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

-- ============================================================================
-- staging_normalized table
-- ============================================================================
CREATE TABLE IF NOT EXISTS staging_normalized (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    email VARCHAR(255) NOT NULL UNIQUE,
    normalized_fields JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'resolving',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_staging_email ON staging_normalized(email);

-- ============================================================================
-- finalize_data table
-- ============================================================================
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

-- Enable Row Level Security (optional, can be configured later)
-- ALTER TABLE raw_data ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE staging_normalized ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE finalize_data ENABLE ROW LEVEL SECURITY;
