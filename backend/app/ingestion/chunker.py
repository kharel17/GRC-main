"""
Document Chunker — Structural section detection + recursive token-based splitting.
"""
from dataclasses import dataclass
import re
import uuid
from typing import List, Optional
from app.ingestion.extractor import PageContent

@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    org_id: str
    page_number: int
    section_heading: str
    chunk_index: int
    text: str
    token_count: int
    source_type: str = "evidence"

# Control & section heading detection patterns
HEADING_REGEX = re.compile(
    r"^(?:"
    r"(?:Annex\s+A\.\d+|\d+\.\d+|\bA\.\d{1,2}\.\d{1,2}\b)\s*[-:]?\s*.*|"  # ISO annex / clause patterns
    r"(?:Section|Chapter|Clause)\s+\d+.*|"                                # Generic section headers
    r"#{1,4}\s+.*|"                                                       # Markdown headings
    r"[A-Z0-9\.\s]{4,60}:$"                                               # Capitalized section labels
    r")",
    re.IGNORECASE | re.MULTILINE
)

def estimate_tokens(text: str) -> int:
    """Count tokens using tiktoken (GPT-2 tokenizer) with word-count fallback."""
    try:
        import tiktoken
        encoder = tiktoken.get_encoding("gpt2")
        return len(encoder.encode(text))
    except Exception:
        # Fallback approximation: 1 token ~ 0.75 words (1.33 tokens per word)
        return int(len(text.split()) * 1.33)

def chunk_document(
    pages: List[PageContent],
    document_id: str,
    org_id: str,
    target_token_size: int = 400,
    overlap_ratio: float = 0.15,
    source_type: str = "evidence",
) -> List[Chunk]:
    """
    Chunk a list of pages into structured, token-bounded chunks.
    1. Structural detection: split page text into sections based on detected headings/controls.
    2. Token boundary split: recursively split sections larger than target_token_size into sub-chunks.
    """
    chunks: List[Chunk] = []
    chunk_counter = 0
    overlap_tokens = int(target_token_size * overlap_ratio)

    for page in pages:
        page_text = page.raw_text.strip()
        if not page_text:
            continue

        # Find section breaks on this page
        sections = _split_by_headings(page_text)

        for heading, section_text in sections:
            section_tokens = estimate_tokens(section_text)

            if section_tokens <= target_token_size + 50:
                # Small enough section — keep intact as one chunk
                chunk_counter += 1
                chunks.append(Chunk(
                    chunk_id=str(uuid.uuid4()),
                    document_id=document_id,
                    org_id=org_id,
                    page_number=page.page_number,
                    section_heading=heading,
                    chunk_index=chunk_counter,
                    text=section_text,
                    token_count=section_tokens,
                    source_type=source_type,
                ))
            else:
                # Oversized section — split recursively into sub-chunks with overlap
                sub_texts = _split_text_with_overlap(
                    text=section_text,
                    target_tokens=target_token_size,
                    overlap_tokens=overlap_tokens,
                )
                for sub_text in sub_texts:
                    chunk_counter += 1
                    chunks.append(Chunk(
                        chunk_id=str(uuid.uuid4()),
                        document_id=document_id,
                        org_id=org_id,
                        page_number=page.page_number,
                        section_heading=heading,
                        chunk_index=chunk_counter,
                        text=sub_text,
                        token_count=estimate_tokens(sub_text),
                        source_type=source_type,
                    ))

    return chunks

def _split_by_headings(page_text: str) -> List[tuple[str, str]]:
    """Split page text into (heading, text) pairs based on regex matches."""
    lines = page_text.splitlines()
    sections: List[tuple[str, str]] = []
    current_heading = "General"
    current_lines: List[str] = []

    for line in lines:
        match = HEADING_REGEX.match(line.strip())
        if match:
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
                current_lines = []
            current_heading = line.strip().lstrip("#").strip()
            current_lines.append(line)
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))

    return [s for s in sections if s[1].strip()]

def _split_text_with_overlap(text: str, target_tokens: int, overlap_tokens: int) -> List[str]:
    """Recursively split oversized text blocks by paragraph/sentence with overlapping context."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) <= 1:
        normalized = re.sub(r"\s+", " ", text).strip()
        paragraphs = [
            p.strip()
            for p in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", normalized)
            if p.strip()
        ]
    if not paragraphs:
        paragraphs = [text.strip()]

    chunks: List[str] = []
    current_paras: List[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = estimate_tokens(para)
        if para_tokens > target_tokens:
            if current_paras:
                chunks.append("\n\n".join(current_paras))
                current_paras = []
                current_tokens = 0
            chunks.extend(_split_long_text_by_words(para, target_tokens, overlap_tokens))
            continue

        if current_tokens + para_tokens > target_tokens and current_paras:
            # Emit chunk
            chunk_str = "\n\n".join(current_paras)
            chunks.append(chunk_str)

            # Build overlap context for next chunk
            overlap_paras: List[str] = []
            accumulated_overlap = 0
            for p in reversed(current_paras):
                p_toks = estimate_tokens(p)
                if accumulated_overlap + p_toks <= overlap_tokens:
                    overlap_paras.insert(0, p)
                    accumulated_overlap += p_toks
                else:
                    break

            current_paras = overlap_paras + [para]
            current_tokens = accumulated_overlap + para_tokens
        else:
            current_paras.append(para)
            current_tokens += para_tokens

    if current_paras:
        chunks.append("\n\n".join(current_paras))

    return chunks


def _split_long_text_by_words(text: str, target_tokens: int, overlap_tokens: int) -> List[str]:
    """Split a single oversized sentence/line when PDF extraction has no paragraph boundaries."""
    words = text.split()
    if not words:
        return []

    chunks: List[str] = []
    current_words: List[str] = []

    for word in words:
        candidate = " ".join(current_words + [word])
        if current_words and estimate_tokens(candidate) > target_tokens:
            chunks.append(" ".join(current_words))
            overlap_words: List[str] = []
            for existing in reversed(current_words):
                candidate_overlap = [existing] + overlap_words
                if estimate_tokens(" ".join(candidate_overlap)) <= overlap_tokens:
                    overlap_words = candidate_overlap
                else:
                    break
            current_words = overlap_words + [word]
        else:
            current_words.append(word)

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks
