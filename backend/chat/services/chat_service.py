import logging
from typing import List, Dict, Any, Tuple
from ai.services import LLMService
from ai.services.retriever import HybridRetriever
from chat.models import ChatMessage
from documents.services.indexer import DocumentIndexer

logger = logging.getLogger(__name__)


class ChatOrchestratorService:
    """
    Enterprise RAG Chat Orchestration Service.
    Coordinates:
      1. JIT (Just-In-Time) indexing fallback for unindexed documents
      2. Multi-turn conversational query condensation
      3. Top-k semantic vector retrieval via HybridRetriever with tenant isolation
      4. Structured citation metadata extraction and grounded prompt assembly
      5. Execution of LLM inference and persistence of citations in ChatMessage
    """

    MAX_HISTORY_MESSAGES = 20

    def __init__(self, llm_service=None, retriever=None):
        self.llm_service = llm_service or LLMService()
        self.retriever = retriever or HybridRetriever()

    def _jit_index_document(self, document) -> None:
        """
        Ensures a document has generated vector chunks before retrieval.
        Triggers indexer on-demand if chunks are missing or status is not 'ready'.
        """
        if not document:
            return

        if document.indexing_status != 'ready' or document.chunks.count() == 0:
            logger.info(f"JIT indexing triggered for document {document.id} ('{document.title}').")
            try:
                indexer = DocumentIndexer()
                indexer.index_document(document)
                document.refresh_from_db()
            except Exception as e:
                logger.error(f"JIT auto-indexing failed for document {document.id}: {e}", exc_info=True)

    def _build_rag_context_and_citations(
        self,
        session,
        user_query: str,
        history: List[Dict[str, str]]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Retrieves relevant semantic chunks and formats both structured context and citation metadata.
        """
        user_id = session.user_id if session.user_id else (
            session.document.user_id if (session.document and session.document.user_id) else None
        )

        # Trigger JIT indexing if document is attached
        if session.document:
            self._jit_index_document(session.document)

        chunks: List[Dict[str, Any]] = []

        if user_id:
            try:
                # 1. Condense conversational follow-up questions
                search_query = self.retriever.condense_query(
                    query=user_query,
                    history=history,
                    llm_service=self.llm_service
                )

                # 2. Retrieve top semantic chunks
                if session.document:
                    chunks = self.retriever.retrieve(
                        query=search_query,
                        user_id=user_id,
                        document_id=session.document.id,
                        top_k=5,
                        similarity_threshold=0.0
                    )
                else:
                    # General chat: search user's document knowledge base with threshold
                    chunks = self.retriever.retrieve(
                        query=search_query,
                        user_id=user_id,
                        document_id=None,
                        top_k=3,
                        similarity_threshold=0.55
                    )
            except Exception as e:
                logger.warning(f"Vector retrieval failed for session {session.id}: {e}. Falling back to document text.")

        # 3. Format structured context and citations
        context_parts = []
        citations_data = []

        if chunks:
            for idx, chunk in enumerate(chunks, start=1):
                page_num = chunk.get("page_number")
                page_label = f"Page {page_num}" if page_num else "Document"
                content_text = chunk.get("content", "").strip()

                context_parts.append(f"--- [Source {idx} ({page_label})] ---\n{content_text}")

                preview = content_text[:180] + ("..." if len(content_text) > 180 else "")
                citations_data.append({
                    "source_id": idx,
                    "page_number": page_num,
                    "chunk_id": chunk.get("chunk_id"),
                    "document_id": chunk.get("document_id"),
                    "similarity_score": chunk.get("similarity_score"),
                    "snippet": preview
                })
            structured_context = "\n\n".join(context_parts)
        elif session.document and session.document.extracted_text:
            # Fallback for documents without vectors
            structured_context = session.document.extracted_text[:3000]
        else:
            structured_context = ""

        return structured_context, citations_data

    def handle_user_message(self, session, user_query: str) -> Tuple[ChatMessage, ChatMessage]:
        """
        Handles synchronous message orchestration with RAG context injection and citation persistence.
        """
        # Fetch and prune message history
        past_messages = session.messages.order_by('timestamp')
        total_count = past_messages.count()
        if total_count > self.MAX_HISTORY_MESSAGES:
            past_messages = past_messages[total_count - self.MAX_HISTORY_MESSAGES:]

        history = [
            {"sender": msg.sender, "content": msg.content}
            for msg in past_messages
        ]

        # 1. Build RAG Context & Citations
        context, citations_data = self._build_rag_context_and_citations(session, user_query, history)

        # 2. Persist User Message
        user_message = ChatMessage.objects.create(
            session=session,
            sender='user',
            content=user_query
        )

        # 3. Assemble Grounded Prompt
        if context:
            grounded_instruction = (
                "Answer the user's question accurately using ONLY the provided Source excerpts above. "
                "Cite your sources directly in the text whenever stating facts, using exact notation like [Source 1 (Page X)] or [Source 2]. "
                "If the sources do not contain enough information to answer, state that the document does not contain this information, then provide helpful general context."
            )
            prompt_for_llm = f"{user_query}\n\n[Instruction: {grounded_instruction}]"
        else:
            prompt_for_llm = user_query

        # 4. Generate AI Response
        try:
            ai_response_text = self.llm_service.answer_question(
                prompt=prompt_for_llm,
                context=context,
                history=history
            )
        except Exception as e:
            logger.error(f"Error calling LLMService.answer_question: {e}", exc_info=True)
            ai_response_text = (
                "⚠️ An unexpected error occurred while communicating with the AI service. "
                "Please verify your Gemini API key in AI Config or try again."
            )

        # 5. Persist Assistant Message with Citations
        assistant_message = ChatMessage.objects.create(
            session=session,
            sender='assistant',
            content=ai_response_text,
            citations=citations_data
        )

        return user_message, assistant_message

    def stream_user_message(self, session, user_query: str):
        """
        Streams response tokens for real-time SSE streaming while capturing citations.
        """
        past_messages = session.messages.order_by('timestamp')
        total_count = past_messages.count()
        if total_count > self.MAX_HISTORY_MESSAGES:
            past_messages = past_messages[total_count - self.MAX_HISTORY_MESSAGES:]

        history = [
            {"sender": msg.sender, "content": msg.content}
            for msg in past_messages
        ]

        context, citations_data = self._build_rag_context_and_citations(session, user_query, history)

        user_message = ChatMessage.objects.create(
            session=session,
            sender='user',
            content=user_query
        )

        if context:
            grounded_instruction = (
                "Answer the user's question accurately using ONLY the provided Source excerpts above. "
                "Cite your sources directly in the text whenever stating facts, using exact notation like [Source 1 (Page X)] or [Source 2]. "
                "If the sources do not contain enough information to answer, state that the document does not contain this information, then provide helpful general context."
            )
            prompt_for_llm = f"{user_query}\n\n[Instruction: {grounded_instruction}]"
        else:
            prompt_for_llm = user_query

        full_response_chunks = []
        try:
            for chunk in self.llm_service.stream_question(prompt=prompt_for_llm, context=context, history=history):
                full_response_chunks.append(chunk)
                yield chunk
        except Exception as e:
            logger.error(f"Error streaming response from LLMService: {e}", exc_info=True)
            error_chunk = "⚠️ An unexpected error occurred while communicating with the AI service."
            full_response_chunks.append(error_chunk)
            yield error_chunk

        full_text = "".join(full_response_chunks)
        ChatMessage.objects.create(
            session=session,
            sender='assistant',
            content=full_text,
            citations=citations_data
        )
