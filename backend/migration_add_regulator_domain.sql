-- Add regulator and domain to documents for retrieval scoping (Step 4)
-- Run this after schema.sql / update_schema.sql if you use retrieval filters.

ALTER TABLE documents ADD COLUMN IF NOT EXISTS regulator VARCHAR(50);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS domain VARCHAR(50);

-- Optionally set default for existing SAMA docs (e.g. from filename)
-- UPDATE documents SET regulator = 'SAMA' WHERE filename LIKE 'SAMA%' AND regulator IS NULL;
