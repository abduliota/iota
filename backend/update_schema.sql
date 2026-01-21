-- Add status column to chunks table
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending';

-- Update embedding dimension from 1536 to 3072 (for text-embedding-3-large)
-- Drop existing index first
DROP INDEX IF EXISTS chunks_embedding_idx;

-- Drop and recreate embedding column with new dimension
ALTER TABLE chunks DROP COLUMN IF EXISTS embedding;
ALTER TABLE chunks ADD COLUMN embedding vector(3072);

-- Recreate vector index
CREATE INDEX chunks_embedding_idx 
ON chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
