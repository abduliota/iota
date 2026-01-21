import os
import json
import glob
import hashlib
import unicodedata
import re
import tiktoken

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
TEXT_DIR = os.path.join(BASE_DIR, "downloads", "extracted_text")
OUTPUT_FILE = os.path.join(BASE_DIR, "downloads", "chunks.jsonl")

TARGET_TOKENS = 500
MAX_TOKENS = 700
MIN_TOKENS = 150
OVERLAP_SENTENCES = 2

tokenizer = tiktoken.get_encoding("cl100k_base")


def normalize_text(text):
    """Normalize Unicode (NFKC), preserve Arabic diacritics."""
    return unicodedata.normalize("NFKC", text)


def count_tokens(text):
    """Count tokens using cl100k_base tokenizer."""
    return len(tokenizer.encode(text))


def detect_language(text):
    """Simple language detection: Arabic if Arabic chars > 30%."""
    if not text:
        return "en"
    arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    total_chars = len([c for c in text if c.isalpha()])
    if total_chars == 0:
        return "en"
    arabic_ratio = arabic_chars / total_chars
    return "ar" if arabic_ratio > 0.3 else "en"


def detect_headings(text):
    """Detect headings: short standalone lines, numbered, all-caps."""
    lines = text.split("\n")
    heading_indices = []
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if len(line_stripped) < 60:
            if i > 0 and not lines[i - 1].strip():
                if i < len(lines) - 1 and not lines[i + 1].strip():
                    heading_indices.append(i)
        if re.match(r"^[\d\.\s]+[A-Z]", line_stripped):
            heading_indices.append(i)
        if line_stripped.isupper() and len(line_stripped) < 100:
            heading_indices.append(i)
    return heading_indices


def split_paragraphs(text):
    """Split by double newline (paragraph boundaries)."""
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def split_sentences(text, language):
    """Split sentences (fallback for oversized paragraphs)."""
    if language == "ar":
        sentences = re.split(r"[.!؟]\s+", text)
    else:
        sentences = re.split(r"[.!?]\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def chunk_text(text, filename):
    """Main chunking logic: section → paragraphs → chunks."""
    text = normalize_text(text)
    language = detect_language(text)
    
    heading_indices = detect_headings(text)
    lines = text.split("\n")
    
    sections = []
    if heading_indices:
        for i in range(len(heading_indices)):
            start = heading_indices[i]
            end = heading_indices[i + 1] if i + 1 < len(heading_indices) else len(lines)
            section_text = "\n".join(lines[start:end])
            section_heading = lines[start].strip()
            sections.append((section_heading, section_text))
    else:
        sections.append(("", text))
    
    chunks = []
    chunk_index = 0
    
    for section_heading, section_text in sections:
        paragraphs = split_paragraphs(section_text)
        chunk_buffer = []
        chunk_tokens = 0
        overlap_sentences = []
        
        for para in paragraphs:
            para_tokens = count_tokens(para)
            
            if para_tokens > MAX_TOKENS:
                sentences = split_sentences(para, language)
                for sent in sentences:
                    sent_tokens = count_tokens(sent)
                    if chunk_tokens + sent_tokens > MAX_TOKENS and chunk_buffer:
                        chunk_text = " ".join(chunk_buffer)
                        if count_tokens(chunk_text) >= MIN_TOKENS:
                            chunks.append(create_chunk(
                                chunk_text, filename, chunk_index,
                                section_heading, language, chunk_buffer
                            ))
                            chunk_index += 1
                            overlap_sentences = chunk_buffer[-OVERLAP_SENTENCES:]
                            chunk_buffer = overlap_sentences.copy()
                            chunk_tokens = sum(count_tokens(s) for s in chunk_buffer)
                        else:
                            chunk_buffer = []
                            chunk_tokens = 0
                    chunk_buffer.append(sent)
                    chunk_tokens += sent_tokens
            else:
                if chunk_tokens + para_tokens > MAX_TOKENS and chunk_buffer:
                    chunk_text = " ".join(chunk_buffer)
                    if count_tokens(chunk_text) >= MIN_TOKENS:
                        chunks.append(create_chunk(
                            chunk_text, filename, chunk_index,
                            section_heading, language, chunk_buffer
                        ))
                        chunk_index += 1
                        overlap_sentences = chunk_buffer[-OVERLAP_SENTENCES:]
                        chunk_buffer = overlap_sentences.copy()
                        chunk_tokens = sum(count_tokens(s) for s in chunk_buffer)
                
                chunk_buffer.append(para)
                chunk_tokens += para_tokens
        
        if chunk_buffer:
            chunk_text = " ".join(chunk_buffer)
            if count_tokens(chunk_text) >= MIN_TOKENS:
                chunks.append(create_chunk(
                    chunk_text, filename, chunk_index,
                    section_heading, language, chunk_buffer
                ))
                chunk_index += 1
    
    return chunks


def create_chunk(text, filename, chunk_index, section_heading, language, sentences):
    """Create chunk dict with metadata."""
    token_count = count_tokens(text)
    
    metadata_prefix = f"[Document: {filename}]\n"
    if section_heading:
        metadata_prefix += f"[Section: {section_heading}]\n"
    metadata_prefix += f"[Chunk Index: {chunk_index}]\n\n"
    
    full_text = metadata_prefix + text
    
    return {
        "filename": filename,
        "chunk_index": chunk_index,
        "text": full_text,
        "token_count": token_count,
        "section_heading": section_heading,
        "language": language,
    }


def main():
    """Process all .txt files and save chunks to JSONL."""
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    txt_files = glob.glob(os.path.join(TEXT_DIR, "*.txt"))
    print(f"Found {len(txt_files)} text files to chunk\n")
    
    all_chunks = []
    for i, txt_path in enumerate(txt_files, 1):
        filename = os.path.basename(txt_path)
        print(f"[{i}/{len(txt_files)}] Chunking: {filename}")
        
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                text = f.read()
            
            chunks = chunk_text(text, filename)
            all_chunks.extend(chunks)
            print(f"  ✓ Created {len(chunks)} chunks")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print(f"\nWriting {len(all_chunks)} chunks to {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    
    print(f"✓ Complete! Chunks saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
