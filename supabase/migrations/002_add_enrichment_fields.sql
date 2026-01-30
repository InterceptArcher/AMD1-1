-- Migration: Add RAD enrichment fields
-- Description: Extend personalization_jobs with RAD enrichment data fields and add enrichment cache
-- Author: InterceptArcher
-- Date: 2026-01-27

-- Add enrichment fields to personalization_jobs
ALTER TABLE personalization_jobs
ADD COLUMN IF NOT EXISTS name VARCHAR(255),
ADD COLUMN IF NOT EXISTS employee_count VARCHAR(50),
ADD COLUMN IF NOT EXISTS headquarters VARCHAR(255),
ADD COLUMN IF NOT EXISTS founded_year INTEGER,
ADD COLUMN IF NOT EXISTS technology JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS news_summary TEXT,
ADD COLUMN IF NOT EXISTS intent_signal VARCHAR(20),
ADD COLUMN IF NOT EXISTS confidence_score FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS enrichment_sources JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS enrichment_timestamp TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS enrichment_error TEXT,
ADD COLUMN IF NOT EXISTS enrichment_duration_ms INTEGER;

-- Add template and performance fields to personalization_outputs
ALTER TABLE personalization_outputs
ADD COLUMN IF NOT EXISTS template_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS template_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS llm_model VARCHAR(100),
ADD COLUMN IF NOT EXISTS llm_tokens_used INTEGER,
ADD COLUMN IF NOT EXISTS llm_latency_ms INTEGER,
ADD COLUMN IF NOT EXISTS total_latency_ms INTEGER;

-- Add indexes for new enrichment fields
CREATE INDEX IF NOT EXISTS idx_personalization_jobs_company_name
    ON personalization_jobs(company_name) WHERE company_name IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_personalization_jobs_industry
    ON personalization_jobs(industry) WHERE industry IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_personalization_jobs_company_size
    ON personalization_jobs(company_size) WHERE company_size IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_personalization_jobs_confidence_score
    ON personalization_jobs(confidence_score DESC) WHERE confidence_score IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_personalization_jobs_intent_signal
    ON personalization_jobs(intent_signal) WHERE intent_signal IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_personalization_jobs_enrichment_timestamp
    ON personalization_jobs(enrichment_timestamp DESC) WHERE enrichment_timestamp IS NOT NULL;

-- Create enrichment cache table for performance optimization
CREATE TABLE IF NOT EXISTS enrichment_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain VARCHAR(255) UNIQUE NOT NULL,
    enriched_data JSONB NOT NULL,
    confidence_score FLOAT NOT NULL DEFAULT 0.0,
    cached_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    cache_hits INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for enrichment cache
CREATE INDEX IF NOT EXISTS idx_enrichment_cache_domain
    ON enrichment_cache(domain);

CREATE INDEX IF NOT EXISTS idx_enrichment_cache_expires_at
    ON enrichment_cache(expires_at);

CREATE INDEX IF NOT EXISTS idx_enrichment_cache_confidence_score
    ON enrichment_cache(confidence_score DESC);

-- Add comments for documentation
COMMENT ON COLUMN personalization_jobs.name IS 'Optional name provided by user in form';
COMMENT ON COLUMN personalization_jobs.employee_count IS 'Company employee count from RAD enrichment';
COMMENT ON COLUMN personalization_jobs.headquarters IS 'Company headquarters location from RAD enrichment';
COMMENT ON COLUMN personalization_jobs.founded_year IS 'Company founded year from RAD enrichment';
COMMENT ON COLUMN personalization_jobs.technology IS 'Array of technologies used by company from RAD enrichment';
COMMENT ON COLUMN personalization_jobs.news_summary IS 'Recent company news summary from RAD enrichment';
COMMENT ON COLUMN personalization_jobs.intent_signal IS 'Buying intent stage: early, mid, or late';
COMMENT ON COLUMN personalization_jobs.confidence_score IS 'RAD enrichment confidence score (0.0-1.0)';
COMMENT ON COLUMN personalization_jobs.enrichment_sources IS 'Array of data sources used (e.g., ["apollo", "peopledatalabs"])';
COMMENT ON COLUMN personalization_jobs.enrichment_timestamp IS 'Timestamp when RAD enrichment was performed';
COMMENT ON COLUMN personalization_jobs.enrichment_error IS 'Error message if enrichment failed';
COMMENT ON COLUMN personalization_jobs.enrichment_duration_ms IS 'Time taken for enrichment in milliseconds';

COMMENT ON COLUMN personalization_outputs.template_id IS 'ID of the template used for personalization';
COMMENT ON COLUMN personalization_outputs.template_name IS 'Human-readable name of the template used';
COMMENT ON COLUMN personalization_outputs.llm_model IS 'LLM model used (e.g., claude-3-5-sonnet-20241022)';
COMMENT ON COLUMN personalization_outputs.llm_tokens_used IS 'Total tokens used by LLM';
COMMENT ON COLUMN personalization_outputs.llm_latency_ms IS 'Time taken for LLM generation in milliseconds';
COMMENT ON COLUMN personalization_outputs.total_latency_ms IS 'Total time from request to response in milliseconds';

COMMENT ON TABLE enrichment_cache IS 'Caches RAD enrichment data to improve performance and reduce API costs';
COMMENT ON COLUMN enrichment_cache.enriched_data IS 'Full enrichment data as JSON';
COMMENT ON COLUMN enrichment_cache.cache_hits IS 'Number of times this cached entry has been used';
COMMENT ON COLUMN enrichment_cache.last_accessed_at IS 'Last time this cache entry was accessed';

-- Enable RLS on enrichment_cache
ALTER TABLE enrichment_cache ENABLE ROW LEVEL SECURITY;

-- Create policy for enrichment cache (alpha - permissive, should be restricted in production)
CREATE POLICY "Allow anonymous access to enrichment_cache"
    ON enrichment_cache FOR ALL
    USING (true);

-- Create function to clean expired cache entries (can be called by cron job)
CREATE OR REPLACE FUNCTION clean_expired_enrichment_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM enrichment_cache
    WHERE expires_at < NOW();

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION clean_expired_enrichment_cache IS 'Removes expired enrichment cache entries. Call via cron job.';
