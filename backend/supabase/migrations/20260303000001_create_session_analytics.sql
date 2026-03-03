-- Create anonymized session analytics table (NO PII)
CREATE TABLE IF NOT EXISTS session_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    industry TEXT,
    company_size TEXT,
    stage TEXT,
    persona TEXT,
    challenge TEXT,
    enrichment_sources TEXT[],
    llm_source TEXT,
    llm_latency_ms INTEGER,
    enrichment_latency_ms INTEGER,
    total_latency_ms INTEGER,
    pdf_generated BOOLEAN DEFAULT FALSE,
    email_delivered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE session_analytics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role insert only"
    ON session_analytics FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Service role read only"
    ON session_analytics FOR SELECT
    USING (true);

CREATE INDEX idx_session_analytics_created_at ON session_analytics(created_at);
CREATE INDEX idx_session_analytics_industry ON session_analytics(industry);
