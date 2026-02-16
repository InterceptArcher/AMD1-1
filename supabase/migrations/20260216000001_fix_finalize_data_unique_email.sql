-- Migration: Add UNIQUE constraint on finalize_data.email
-- Required for upsert(on_conflict="email") to work correctly.
-- Without this, every upsert fails and enrichment data never persists.

-- Step 1: Remove duplicates (keep newest by resolved_at)
DELETE FROM finalize_data a
USING finalize_data b
WHERE a.email = b.email
  AND a.resolved_at < b.resolved_at;

-- Step 2: Add UNIQUE constraint
ALTER TABLE finalize_data
ADD CONSTRAINT finalize_data_email_unique UNIQUE (email);
