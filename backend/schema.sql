-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table: stores PDF metadata
CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    source_url TEXT,
    pdf_url TEXT,
    filename TEXT NOT NULL,
    page_title TEXT,
    total_chunks INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chunks table: stores text chunks with embeddings
CREATE TABLE IF NOT EXISTS chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    token_count INTEGER,
    section_heading TEXT,
    language TEXT,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, chunk_index)
);

-- Vector index for fast similarity search
CREATE INDEX IF NOT EXISTS chunks_embedding_idx 
ON chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Index on document_id for faster lookups
CREATE INDEX IF NOT EXISTS chunks_document_id_idx ON chunks(document_id);
