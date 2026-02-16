-- Migration: Make pdf_deliveries.job_id nullable and drop FK constraint
-- The enrichment flow doesn't always create personalization_jobs records,
-- so the FK reference causes insert failures.

-- Drop the FK constraint
ALTER TABLE pdf_deliveries
DROP CONSTRAINT IF EXISTS pdf_deliveries_job_id_fkey;

-- Make job_id nullable (it already should be, but ensure it)
ALTER TABLE pdf_deliveries
ALTER COLUMN job_id DROP NOT NULL;
