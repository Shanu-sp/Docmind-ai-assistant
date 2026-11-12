import os
import logging
from typing import Optional
from django.db import transaction
from documents.models import Document, DocumentChunk
from documents.services.extractor import DocumentExtractor
from documents.services.chunker import RecursiveSemanticChunker
from ai.services.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """
    Enterprise-grade indexing pipeline for RAG (Retrieval-Augmented Generation).
    Coordinates:
      1. Page-aware text extraction (DocumentExtractor)
      2. Recursive semantic chunking (RecursiveSemanticChunker)
      3. Batch vector embedding generation (EmbeddingService / gemini-embedding-001)
      4. Atomic bulk persistence of DocumentChunk records
      5. State lifecycle management for Document.indexing_status ('indexing' -> 'ready' / 'failed')
    """

    def __init__(
        self,
        chunker: Optional[RecursiveSemanticChunker] = None,
        embedding_service: Optional[EmbeddingService] = None
    ):
        self.chunker = chunker or RecursiveSemanticChunker()
        self.embedding_service = embedding_service or EmbeddingService()

    def index_document(self, document: Document) -> bool:
        """
        Extracts, chunks, embeds, and stores vector embeddings for a given Document.
        Guarantees idempotency by replacing prior chunks on re-index.
        
        Args:
            document: Document instance to index.
            
        Returns:
            bool: True if indexing succeeded ('ready'), False if failed ('failed').
        """
        # Guard: Multi-tenant tenant boundary check
        if not document.user:
            logger.error(f"Cannot index document {document.id} ('{document.title}'): missing associated user.")
            document.indexing_status = 'failed'
            document.save(update_fields=['indexing_status'])
            return False

        # Transition status to indexing
        document.indexing_status = 'indexing'
        document.save(update_fields=['indexing_status'])

        try:
            # 1. Text Extraction
            file_path = None
            if document.file:
                try:
                    if os.path.exists(document.file.path):
                        file_path = document.file.path
                except Exception as path_err:
                    logger.debug(f"Could not access document.file.path for doc {document.id}: {path_err}")

            if file_path:
                pages = DocumentExtractor.extract_pages(file_path, document.file_type or 'txt')
                # If extracted_text on model is empty, populate it from pages
                if not document.extracted_text and pages:
                    document.extracted_text = "\n\n".join(p["text"] for p in pages if p.get("text", "").strip())
                    document.save(update_fields=['extracted_text'])
            elif document.extracted_text and document.extracted_text.strip():
                # Fallback to existing extracted_text if physical file is missing from disk
                logger.warning(
                    f"Physical file for document {document.id} ('{document.title}') not found on disk. "
                    "Falling back to stored extracted_text."
                )
                pages = DocumentExtractor._paginate_virtual_text(document.extracted_text)
            else:
                error_msg = (
                    f"Document {document.id} ('{document.title}') has neither an accessible file on disk "
                    "nor extracted_text. Indexing impossible."
                )
                logger.error(error_msg)
                document.indexing_status = 'failed'
                document.save(update_fields=['indexing_status'])
                return False

            # 2. Semantic Chunking
            chunks_data = self.chunker.chunk_pages(pages)

            # Handle empty document edge case
            if not chunks_data:
                logger.info(f"Document {document.id} ('{document.title}') yielded 0 chunks. Marked as ready.")
                with transaction.atomic():
                    document.chunks.all().delete()
                    document.indexing_status = 'ready'
                    document.save(update_fields=['indexing_status'])
                return True

            # 3. Batch Vector Embeddings
            chunk_texts = [c["content"] for c in chunks_data]
            embeddings = self.embedding_service.generate_batch_embeddings(chunk_texts)

            if len(embeddings) != len(chunks_data):
                raise ValueError(
                    f"Embedding count ({len(embeddings)}) does not match chunk count ({len(chunks_data)})."
                )

            # 4. Atomic Bulk Persistence
            with transaction.atomic():
                # Purge prior chunks to ensure idempotent re-runs
                document.chunks.all().delete()

                chunk_instances = [
                    DocumentChunk(
                        document=document,
                        user=document.user,
                        chunk_index=chunk_item["chunk_index"],
                        page_number=chunk_item.get("page_number"),
                        content=chunk_item["content"],
                        metadata=chunk_item.get("metadata", {}),
                        embedding=emb,
                    )
                    for chunk_item, emb in zip(chunks_data, embeddings)
                ]

                DocumentChunk.objects.bulk_create(chunk_instances, batch_size=100)
                document.indexing_status = 'ready'
                document.save(update_fields=['indexing_status'])

            logger.info(
                f"Successfully indexed document {document.id} ('{document.title}') "
                f"with {len(chunk_instances)} chunks and 768d vectors."
            )
            return True

        except Exception as exc:
            logger.exception(f"Unhandled failure while indexing document {document.id} ('{document.title}'): {exc}")
            document.indexing_status = 'failed'
            document.save(update_fields=['indexing_status'])
            return False

    def index_document_by_id(self, document_id: int) -> bool:
        """
        Convenience wrapper to index a document given its primary key ID.
        """
        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            logger.error(f"Document with id {document_id} does not exist.")
            return False

        return self.index_document(document)
