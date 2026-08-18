import os
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Document
from .serializers import DocumentSerializer, DocumentUploadSerializer
from .services.extractor import DocumentExtractor
from ai.services import LLMService

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

        # 2. Service Layer Hooks: Extract Text & Generate AI Insights
        try:
            extracted_text = DocumentExtractor.extract_text(document.file.path, ext)
            document.extracted_text = extracted_text

            llm_service = LLMService()
            insights = llm_service.summarize_document(extracted_text)
            document.executive_summary = insights.get("executive_summary", [])
            document.suggested_questions = insights.get("suggested_questions", [])

            document.save()
        except Exception as e:
            print(f"Extraction or AI processing failed for document {document.id}: {e}")

        response_serializer = self.get_serializer(document)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='reanalyze')
    def reanalyze(self, request, pk=None):
        document = self.get_object()
        focus = request.data.get('focus', None)

        if not document.extracted_text:
            return Response({'error': 'Document contains no extracted text to analyze.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            llm_service = LLMService()
            insights = llm_service.summarize_document(document.extracted_text, focus=focus)
            document.executive_summary = insights.get("executive_summary", [])
            document.suggested_questions = insights.get("suggested_questions", [])
            document.save()

            serializer = self.get_serializer(document)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': f'Re-analysis failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
