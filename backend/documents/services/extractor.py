import os
import re
import logging
from typing import List, Dict, Any
import pdfplumber
import pypdf
import docx

logger = logging.getLogger(__name__)

class DocumentExtractor:
    """
    Enterprise-grade document parsing service preserving page-level provenance.
    Supports PDF (pdfplumber + pypdf + Gemini OCR), DOCX, and TXT files.
    """

    DEFAULT_VIRTUAL_PAGE_CHARS = 2000

    @classmethod
    def extract_pages(cls, file_path: str, file_type: str) -> List[Dict[str, Any]]:
        """
        Extracts document content as structured, page-tagged objects.
        Returns:
            List of dicts: [{"page_number": 1, "text": "..."}, ...]
        """
        file_type = file_type.lower().replace('.', '').strip()

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at path: {file_path}")

        if file_type == 'pdf':
            return cls._extract_pdf_pages(file_path)
        elif file_type == 'docx':
            return cls._extract_docx_pages(file_path)
        elif file_type in ['txt', 'text']:
            return cls._extract_txt_pages(file_path)
        else:
            raise ValueError(f"Unsupported file format: '{file_type}'")

    @classmethod
    def extract_text(cls, file_path: str, file_type: str) -> str:
        """
        Backward-compatible method returning full extracted text as a single string.
        """
        pages = cls.extract_pages(file_path, file_type)
        return "\n\n".join(p["text"] for p in pages if p.get("text", "").strip())

    @classmethod
    def _extract_pdf_pages(cls, file_path: str) -> List[Dict[str, Any]]:
        pages: List[Dict[str, Any]] = []

        # 1. Primary extractor: pdfplumber (best for layout and table text)
        try:
            with pdfplumber.open(file_path) as pdf:
                for idx, page in enumerate(pdf.pages, start=1):
                    page_text = page.extract_text() or ""
                    clean_text = page_text.strip()
                    if clean_text:
                        pages.append({"page_number": idx, "text": clean_text})
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed for {file_path}: {e}. Trying pypdf...")
            pages = []

        # 2. Secondary fallback: pypdf (handles encrypted or compressed PDFs)
        if not pages:
            try:
                reader = pypdf.PdfReader(file_path)
                for idx, page in enumerate(reader.pages, start=1):
                    p_text = page.extract_text() or ""
                    clean_text = p_text.strip()
                    if clean_text:
                        pages.append({"page_number": idx, "text": clean_text})
            except Exception as e:
                logger.warning(f"pypdf fallback failed for {file_path}: {e}")

        # 3. Tertiary fallback: Gemini Multimodal OCR (for scanned images / pure picture PDFs)
        total_extracted_chars = sum(len(p["text"]) for p in pages)
        if total_extracted_chars < 50:
            logger.info(f"PDF {file_path} contains minimal selectable text ({total_extracted_chars} chars). Attempting Gemini Multimodal OCR fallback...")
            ocr_pages = cls._gemini_ocr_pdf(file_path)
            if ocr_pages:
                return ocr_pages

        return pages or [{"page_number": 1, "text": ""}]

    @classmethod
    def _gemini_ocr_pdf(cls, file_path: str) -> List[Dict[str, Any]]:
        try:
            from ai.services import GeminiProvider
            provider = GeminiProvider()
            if not provider.client:
                return []

            uploaded_file = provider.client.files.upload(file=file_path)
            prompt = (
                "Extract all text from this document accurately page by page without omission.\n"
                "Format each page strictly starting with a marker like this:\n"
                "--- PAGE [page_number] ---\n"
                "Followed by the page text."
            )
            response = provider.client.models.generate_content(
                model=provider.model,
                contents=[uploaded_file, prompt]
            )
            raw_text = response.text.strip() if response and response.text else ""
            if not raw_text:
                return []

            ocr_pages = []
            parts = re.split(r'---\s*PAGE\s+(\d+)\s*---', raw_text, flags=re.IGNORECASE)
            if len(parts) >= 3:
                for i in range(1, len(parts), 2):
                    page_num = int(parts[i])
                    page_content = parts[i + 1].strip() if (i + 1) < len(parts) else ""
                    if page_content:
                        ocr_pages.append({"page_number": page_num, "text": page_content})
            else:
                ocr_pages.append({"page_number": 1, "text": raw_text})

            return ocr_pages
        except Exception as ocr_err:
            logger.warning(f"Gemini Multimodal OCR fallback failed for {file_path}: {ocr_err}")
            return []

    # Alias for backward compatibility and test suites
    _ocr_gemini_fallback = _gemini_ocr_pdf

    @classmethod
    def _extract_docx_pages(cls, file_path: str) -> List[Dict[str, Any]]:
        try:
            doc = docx.Document(file_path)
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_text:
                        paragraphs.append(row_text)

            full_text = "\n\n".join(paragraphs)
            return cls._paginate_virtual_text(full_text, chars_per_page=cls.DEFAULT_VIRTUAL_PAGE_CHARS)
        except Exception as e:
            logger.error(f"DOCX extraction failed for {file_path}: {e}")
            raise Exception(f"Failed to extract text from DOCX file: {e}")

    @classmethod
    def _extract_txt_pages(cls, file_path: str) -> List[Dict[str, Any]]:
        encodings = ['utf-8', 'latin-1', 'cp1252', 'utf-16']
        content = ""
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read().strip()
                    break
            except UnicodeDecodeError:
                continue

        if not content:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read().strip()

        return cls._paginate_virtual_text(content, chars_per_page=cls.DEFAULT_VIRTUAL_PAGE_CHARS)

    @classmethod
    def _paginate_virtual_text(cls, text: str, chars_per_page: int = 2000) -> List[Dict[str, Any]]:
        """
        Partitions unpaginated text (DOCX/TXT) into clean virtual pages,
        respecting paragraph, sentence, and word boundaries. Guarantees that
        even massive continuous text blocks without newlines are properly paginated.
        """
        clean_text = text.strip()
        if not clean_text:
            return [{"page_number": 1, "text": ""}]

        if len(clean_text) <= chars_per_page:
            return [{"page_number": 1, "text": clean_text}]

        # 1. Normalize carriage returns to standard linefeeds
        normalized_text = clean_text.replace('\r\n', '\n').replace('\r', '\n')
        raw_blocks = normalized_text.split('\n\n')

        # 2. Decompose blocks exceeding chars_per_page into atomic sentence/word chunks
        atomic_segments: List[str] = []
        for block in raw_blocks:
            b = block.strip()
            if not b:
                continue
            if len(b) <= chars_per_page:
                atomic_segments.append(b)
            else:
                sentences = re.split(r'(?<=[.?!;:\n])\s+', b)
                curr = ""
                for s in sentences:
                    if len(curr) + len(s) + 1 <= chars_per_page:
                        curr = f"{curr} {s}".strip() if curr else s
                    else:
                        if curr:
                            atomic_segments.append(curr)
                        while len(s) > chars_per_page:
                            atomic_segments.append(s[:chars_per_page])
                            s = s[chars_per_page:]
                        curr = s
                if curr:
                    atomic_segments.append(curr)

        # 3. Assemble atomic segments into bounded virtual pages
        pages: List[Dict[str, Any]] = []
        current_page_text = ""
        page_num = 1

        for seg in atomic_segments:
            if current_page_text and (len(current_page_text) + len(seg) + 2 > chars_per_page):
                pages.append({"page_number": page_num, "text": current_page_text.strip()})
                page_num += 1
                current_page_text = seg
            else:
                current_page_text = f"{current_page_text}\n\n{seg}".strip() if current_page_text else seg

        if current_page_text:
            pages.append({"page_number": page_num, "text": current_page_text.strip()})

        return pages or [{"page_number": 1, "text": ""}]
