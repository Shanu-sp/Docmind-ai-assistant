import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class RecursiveSemanticChunker:
    """
    Enterprise-grade semantic chunker that splits document pages into cohesive
    text fragments, preserving sentence boundaries, natural paragraph breaks,
    and page-level provenance.
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "]

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
        min_chunk_size: int = 50,
        separators: List[str] = None
    ):
        if chunk_overlap >= chunk_size:
            raise ValueError(f"chunk_overlap ({chunk_overlap}) must be smaller than chunk_size ({chunk_size})")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.separators = separators or self.DEFAULT_SEPARATORS

    def chunk_pages(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Splits structured document pages into semantic chunks tagged with exact page numbers.

        Args:
            pages: List of dicts, e.g. [{"page_number": 1, "text": "..."}, ...]

        Returns:
            List of dicts:
                [
                    {
                        "chunk_index": 0,
                        "page_number": 1,
                        "content": "...",
                        "metadata": {"char_count": 850, "word_count": 130, "page_number": 1}
                    },
                    ...
                ]
        """
        if not pages:
            return []

        chunks: List[Dict[str, Any]] = []
        global_chunk_idx = 0

        for page in pages:
            page_num = page.get("page_number", 1)
            raw_text = page.get("text", "")
            if not raw_text or not raw_text.strip():
                continue

            page_fragments = self._split_text(raw_text.strip())

            for frag in page_fragments:
                clean_frag = frag.strip()
                if len(clean_frag) < self.min_chunk_size and len(page_fragments) > 1:
                    # Skip trivial fragments like stray page footers if other content exists
                    continue

                chunks.append({
                    "chunk_index": global_chunk_idx,
                    "page_number": page_num,
                    "content": clean_frag,
                    "metadata": {
                        "char_count": len(clean_frag),
                        "word_count": len(clean_frag.split()),
                        "page_number": page_num
                    }
                })
                global_chunk_idx += 1

        return chunks

    def chunk_text(self, text: str, default_page: int = 1) -> List[Dict[str, Any]]:
        """
        Convenience method to chunk raw unpaginated text.
        """
        return self.chunk_pages([{"page_number": default_page, "text": text}])

    def _split_text(self, text: str) -> List[str]:
        """
        Recursively splits text into overlapping chunks, searching backwards
        for the cleanest linguistic boundary (paragraph -> sentence -> phrase -> word).
        """
        clean_text = text.strip()
        if len(clean_text) <= self.chunk_size:
            return [clean_text] if clean_text else []

        results: List[str] = []
        start = 0
        total_len = len(clean_text)

        while start < total_len:
            end = min(start + self.chunk_size, total_len)

            if end < total_len:
                # Find cleanest split boundary in second half of the chunk window
                best_split = -1
                search_start = start + (self.chunk_size // 3)

                for sep in self.separators:
                    idx = clean_text.rfind(sep, search_start, end)
                    if idx != -1:
                        best_split = idx + len(sep)
                        break

                if best_split != -1:
                    end = best_split

            segment = clean_text[start:end].strip()
            if segment:
                results.append(segment)

            if end >= total_len:
                break

            # Advance by chunk step minus overlap
            start = max(end - self.chunk_overlap, start + 1)

        return results
