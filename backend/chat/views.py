from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import ChatSession, ChatMessage
from .serializers import ChatSessionSerializer, ChatMessageSerializer, ChatMessageCreateSerializer
from .services.chat_service import ChatOrchestratorService

from django.http import StreamingHttpResponse

class ChatSessionViewSet(viewsets.ModelViewSet):
    """
    DRF ViewSet for User-Scoped Chat Sessions & Messages.
    Delegates LLM message orchestration to the Service layer.
    """
    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        document_id = request.data.get('document')
        title = request.data.get('title')

        doc = None
        if document_id:
            try:
                from documents.models import Document
                doc = Document.objects.get(id=document_id, user=request.user)
                if not title:
                    title = f"Chat: {doc.title}"
            except Exception:
                doc = None

        if not title:
            title = "General AI Chat"

        session = ChatSession.objects.create(
            user=request.user,
            document=doc,
            title=title
        )

        return Response(self.get_serializer(session).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='messages')
    def list_messages(self, request, pk=None):
        session = self.get_object()
        messages = session.messages.order_by('timestamp')
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='send-message')
    def send_message(self, request, pk=None):
        try:
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
        except Exception as e:
            return Response(
                {'error': str(e) or 'Failed to send message.'},
                status=status.HTTP_400_BAD_REQUEST
            )

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
