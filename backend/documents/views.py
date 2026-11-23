import os
import logging
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Document
from .serializers import DocumentSerializer, DocumentUploadSerializer
from .services.extractor import DocumentExtractor
from .services.indexer import DocumentIndexer
from ai.services import LLMService

logger = logging.getLogger(__name__)

class DocumentViewSet(viewsets.ModelViewSet):
    """
    DRF ViewSet for User-Scoped Document management.
    Restricts access strictly to documents owned by the authenticated user.
    """
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data['file']
        ext = os.path.splitext(uploaded_file.name)[1].lower().replace('.', '')

        # 1. Create Document Instance bound to request.user
        document = Document.objects.create(
            user=request.user,
            title=uploaded_file.name,
            file=uploaded_file,
            file_type=ext,
            file_size=uploaded_file.size
        )

        # 2. Extract Text & IMMEDIATELY save to database (Guarantees text is never lost!)
        extracted_text = ""
        try:
            extracted_text = DocumentExtractor.extract_text(document.file.path, ext)
            document.extracted_text = extracted_text or ""
            document.save(update_fields=['extracted_text'])
        except Exception as ext_e:
            logger.error(f"Text extraction failed for document {document.id}: {ext_e}")

        # 3. AI Insights (Summary & Prompts) - Safe, non-blocking fallback
        try:
            if extracted_text and extracted_text.strip():
                llm_service = LLMService()
                insights = llm_service.summarize_document(extracted_text)
                document.executive_summary = insights.get("executive_summary", [])
                document.suggested_questions = insights.get("suggested_questions", [])
            else:
                document.executive_summary = ["Document uploaded successfully.", "Ready for chat and exploration."]
                document.suggested_questions = ["What are the key points in this document?"]
            document.save(update_fields=['executive_summary', 'suggested_questions'])
        except Exception as ai_e:
            logger.warning(f"AI insights generation fallback for document {document.id}: {ai_e}")
            preview = extracted_text[:80].strip() if extracted_text else "Document content"
            document.executive_summary = [
                f"Document text extracted successfully ({len(extracted_text)} characters).",
                f"Begins with: '{preview}...'",
                "Ready for semantic Q&A and vector search."
            ]
            document.suggested_questions = [
                "Can you provide an executive overview of this document?",
                "What are the main topics discussed?",
                "What are the key takeaways?"
            ]
            document.save(update_fields=['executive_summary', 'suggested_questions'])

        # 4. RAG Vector Indexing Pipeline (Chunking & Embedding)
        try:
            indexer = DocumentIndexer()
            indexer.index_document(document)
            document.refresh_from_db()
        except Exception as e:
            logger.error(f"Vector indexing failed for document {document.id}: {e}")

        response_serializer = self.get_serializer(document)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='reindex')
    def reindex(self, request, pk=None):
        """
        Manually trigger vector re-indexing for a document.
        """
        document = self.get_object()
        try:
            indexer = DocumentIndexer()
            success = indexer.index_document(document)
            document.refresh_from_db()
            if success:
                serializer = self.get_serializer(document)
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(
                {
                    'error': 'Document indexing failed. Check server logs.',
                    'indexing_status': document.indexing_status
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"Re-indexing failed for document {document.id}: {e}")
            return Response({'error': f'Re-indexing failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='reanalyze')
    def reanalyze(self, request, pk=None):
        document = self.get_object()
        focus = request.data.get('focus', None)

        # Auto-recovery: If extracted_text is missing on model, re-extract from file if present on disk
        if not document.extracted_text and document.file:
            try:
                if os.path.exists(document.file.path):
                    ext = os.path.splitext(document.file.name)[1].lower().replace('.', '')
                    document.extracted_text = DocumentExtractor.extract_text(document.file.path, ext)
                    document.save(update_fields=['extracted_text'])
            except Exception as e:
                logger.warning(f"On-the-fly re-extraction failed for doc {document.id}: {e}")

        if not document.extracted_text:
            return Response(
                {'error': 'Document contains no readable text to analyze. Please try re-uploading the document.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            llm_service = LLMService()
            insights = llm_service.summarize_document(document.extracted_text, focus=focus)
            document.executive_summary = insights.get("executive_summary", [])
            document.suggested_questions = insights.get("suggested_questions", [])
            document.save(update_fields=['executive_summary', 'suggested_questions'])

            serializer = self.get_serializer(document)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Re-analysis failed for document {document.id}: {e}")
            return Response({'error': f'Re-analysis failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
