from ai.services import LLMService
from chat.models import ChatMessage

class ChatOrchestratorService:
    """
    Service responsible for building conversation context and invoking the LLM Service.
    """

    def __init__(self, llm_service=None):
        self.llm_service = llm_service or LLMService()

    MAX_HISTORY_MESSAGES = 20

    def handle_user_message(self, session, user_query: str):
        document_text = ""
        if session.document and session.document.extracted_text:
            document_text = session.document.extracted_text

        # Fetch and prune message history to last 20 messages
        past_messages = session.messages.order_by('timestamp')
        total_count = past_messages.count()
        if total_count > self.MAX_HISTORY_MESSAGES:
            past_messages = past_messages[total_count - self.MAX_HISTORY_MESSAGES:]

        history = [
            {"sender": msg.sender, "content": msg.content}
            for msg in past_messages
        ]

        user_message = ChatMessage.objects.create(
            session=session,
            sender='user',
            content=user_query
        )

        ai_response_text = self.llm_service.answer_question(
            prompt=user_query,
            context=document_text,
            history=history
        )

        assistant_message = ChatMessage.objects.create(
            session=session,
            sender='assistant',
            content=ai_response_text
        )

        return user_message, assistant_message

    def stream_user_message(self, session, user_query: str):
        """
        Yields streamed text tokens for SSE endpoint and saves completed message at end.
        """
        document_text = ""
        if session.document and session.document.extracted_text:
            document_text = session.document.extracted_text

        past_messages = session.messages.order_by('timestamp')
        total_count = past_messages.count()
        if total_count > self.MAX_HISTORY_MESSAGES:
            past_messages = past_messages[total_count - self.MAX_HISTORY_MESSAGES:]

        history = [
            {"sender": msg.sender, "content": msg.content}
            for msg in past_messages
        ]

        user_message = ChatMessage.objects.create(
            session=session,
            sender='user',
            content=user_query
        )

        full_response_chunks = []
        for chunk in self.llm_service.stream_question(prompt=user_query, context=document_text, history=history):
            full_response_chunks.append(chunk)
            yield chunk

        full_text = "".join(full_response_chunks)
        ChatMessage.objects.create(
            session=session,
            sender='assistant',
            content=full_text
        )


