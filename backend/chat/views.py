from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import ChatSession, ChatMessage
from .serializers import ChatSessionSerializer, ChatMessageSerializer, ChatMessageCreateSerializer
from .services.chat_service import ChatOrchestratorService

from django.http import StreamingHttpResponse

class ChatSessionViewSet(viewsets.ModelViewSet):
    """
    Thin DRF ViewSet for Chat Sessions & Messages.
    Delegates LLM message orchestration to the Service layer.
    """
    queryset = ChatSession.objects.all()
    serializer_class = ChatSessionSerializer

    def create(self, request, *args, **kwargs):
        document_id = request.data.get('document')
        title = request.data.get('title')

        if not title and document_id:
            try:
                from documents.models import Document
                doc = Document.objects.get(id=document_id)
                title = f"Chat: {doc.title}"
            except Exception:
                title = "New Chat Session"

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = serializer.save(title=title or "New Chat Session")

        return Response(self.get_serializer(session).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='messages')
    def list_messages(self, request, pk=None):
        session = self.get_object()
        messages = session.messages.order_by('timestamp')
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='send-message')
    def send_message(self, request, pk=None):
        session = self.get_object()
        serializer = ChatMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_content = serializer.validated_data['content']

        orchestrator = ChatOrchestratorService()
        user_msg, assistant_msg = orchestrator.handle_user_message(session, user_content)

        return Response({
            'user_message': ChatMessageSerializer(user_msg).data,
            'assistant_message': ChatMessageSerializer(assistant_msg).data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='stream-message')
    def stream_message(self, request, pk=None):
        session = self.get_object()
        serializer = ChatMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_content = serializer.validated_data['content']
        orchestrator = ChatOrchestratorService()

        response = StreamingHttpResponse(
            orchestrator.stream_user_message(session, user_content),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        return response
