-- Add ai_priority field to personalization_jobs table
ALTER TABLE personalization_jobs
ADD COLUMN ai_priority TEXT;

-- Add comment for documentation
COMMENT ON COLUMN personalization_jobs.ai_priority IS 'User-selected AI priority from dropdown (Infrastructure Modernization, AI/ML Workloads, Cloud Migration, etc.)';
