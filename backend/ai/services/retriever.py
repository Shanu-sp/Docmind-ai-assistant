import math
import logging
from typing import List, Dict, Any, Optional
from django.db import connection
from documents.models import DocumentChunk
from ai.services.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Enterprise-grade vector retrieval service with strict multi-tenant isolation.
    
    Capabilities:
      1. Dense vector cosine similarity search on PostgreSQL pgvector with HNSW index.
      2. Automated database adaptation (PostgreSQL <=> operator, SQLite in-memory fallback for tests).
      3. Strict tenant isolation: Every query enforces WHERE user_id = %s.
      4. Optional document-scoped filtering: AND document_id = %s.
      5. Conversational query condensation for multi-turn chats.
    """

    def __init__(self, embedder: Optional[EmbeddingService] = None):
        self.embedder = embedder or EmbeddingService()

    def retrieve(
        self,
        query: str,
        user_id: int,
        document_id: Optional[int] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the top-k most semantically relevant chunks for a user's query.
        
        Args:
            query: The search query string.
            user_id: Mandatory user ID for multi-tenant isolation.
            document_id: Optional document ID to filter chunks to a specific document.
            top_k: Number of chunks to retrieve (default 5).
            similarity_threshold: Minimum cosine similarity score (0.0 to 1.0).
            
        Returns:
            List of dicts:
                [
                    {
                        "chunk_id": int,
                        "document_id": int,
                        "page_number": int | None,
                        "chunk_index": int,
                        "content": str,
                        "similarity_score": float,
                    },
                    ...
                ]
        """
        # 1. Guard Clauses & Input Sanitization
        if not user_id:
            raise ValueError("user_id is strictly required for multi-tenant retrieval.")

        if not query or not query.strip():
            return []

        clean_query = query.strip()
        top_k = max(1, int(top_k))

        # 2. Vector Embedding Generation
        query_vector = self.embedder.generate_embedding(clean_query)

        # 3. Database Execution Path
        is_postgres = connection.vendor == 'postgresql'

        if is_postgres:
            return self._retrieve_postgres(
                query_vector=query_vector,
                user_id=user_id,
                document_id=document_id,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )
        else:
            return self._retrieve_sqlite_fallback(
                query_vector=query_vector,
                user_id=user_id,
                document_id=document_id,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )

    def _retrieve_postgres(
        self,
        query_vector: List[float],
        user_id: int,
        document_id: Optional[int],
        top_k: int,
        similarity_threshold: float,
    ) -> List[Dict[str, Any]]:
        """
        Executes high-performance cosine similarity search directly inside PostgreSQL
        leveraging pgvector's HNSW index (<=> operator).
        """
        vector_str = f"[{','.join(str(f) for f in query_vector)}]"

        params: List[Any] = [vector_str, user_id]
        doc_clause = ""
        if document_id is not None:
            doc_clause = "AND document_id = %s"
            params.append(document_id)

        params.extend([vector_str, top_k])

        sql = f"""
            SELECT 
                id,
                document_id,
                page_number,
                chunk_index,
                content,
                1 - (embedding <=> %s::vector) AS similarity_score
            FROM documents_documentchunk
            WHERE user_id = %s
              {doc_clause}
            ORDER BY embedding <=> %s::vector ASC
            LIMIT %s;
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        results: List[Dict[str, Any]] = []
        for row in rows:
            sim = round(float(row[5]), 4)
            if sim >= similarity_threshold:
                results.append({
                    "chunk_id": row[0],
                    "document_id": row[1],
                    "page_number": row[2],
                    "chunk_index": row[3],
                    "content": row[4],
                    "similarity_score": sim,
                })

        return results

    def _retrieve_sqlite_fallback(
        self,
        query_vector: List[float],
        user_id: int,
        document_id: Optional[int],
        top_k: int,
        similarity_threshold: float,
    ) -> List[Dict[str, Any]]:
        """
        Fallback implementation for SQLite (used during local in-memory automated tests).
        Computes cosine similarity in Python over filtered chunks.
        """
        qs = DocumentChunk.objects.filter(user_id=user_id)
        if document_id is not None:
            qs = qs.filter(document_id=document_id)

        norm_q = math.sqrt(sum(x * x for x in query_vector))
        if norm_q == 0.0:
            return []

        scored = []
        for chunk in qs:
            vec = chunk.embedding
            if isinstance(vec, str):
                import json
                try:
                    vec = json.loads(vec)
                except Exception:
                    continue

            if not vec or not isinstance(vec, (list, tuple)):
                continue

            norm_c = math.sqrt(sum(y * y for y in vec))
            if norm_c == 0.0:
                continue

            dot = sum(x * y for x, y in zip(query_vector, vec))
            sim = dot / (norm_q * norm_c)

            if sim >= similarity_threshold:
                scored.append((sim, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)

        results: List[Dict[str, Any]] = []
        for sim, chunk in scored[:top_k]:
            results.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "similarity_score": round(float(sim), 4),
            })

        return results

    def condense_query(
        self,
        query: str,
        history: Optional[List[Any]] = None,
        llm_service: Optional[Any] = None,
    ) -> str:
        """
        Reformulates conversational follow-up questions into standalone search queries
        by contextualizing with recent conversation history.
        
        Args:
            query: The user's query.
            history: List of previous ChatMessage instances or dicts [{'sender': ..., 'content': ...}].
            llm_service: Optional LLMService instance for neural reformulation.
            
        Returns:
            str: Standalone query ready for vector search.
        """
        if not query or not query.strip():
            return ""

        clean_query = query.strip()

        if not history:
            return clean_query

        # Extract last 3 conversation turns
        turns = []
        for item in history[-3:]:
            if isinstance(item, dict):
                sender = item.get("sender", "user")
                content = item.get("content", "")
            else:
                sender = getattr(item, "sender", "user")
                content = getattr(item, "content", "")
            if content and content.strip():
                turns.append(f"{sender}: {content.strip()[:150]}")

        if not turns:
            return clean_query

        # 1. Neural Reformulation if LLM is provided
        if llm_service:
            try:
                formatted_history = "\n".join(turns)
                prompt = (
                    "Given the following chat history and a follow-up user question, "
                    "rephrase the question into a single, specific, standalone search query. "
                    "Do NOT answer the question. Do NOT include preambles or explanations. "
                    "If the question is already complete and standalone, return it exactly as is.\n\n"
                    f"Conversation:\n{formatted_history}\n\n"
                    f"Follow-up: {clean_query}\n\n"
                    "Standalone Search Query:"
                )
                if hasattr(llm_service, "answer_question"):
                    response = llm_service.answer_question(prompt=prompt)
                elif hasattr(llm_service, "provider") and hasattr(llm_service.provider, "generate_response"):
                    response = llm_service.provider.generate_response(prompt=prompt)
                elif hasattr(llm_service, "provider") and hasattr(llm_service.provider, "generate_content"):
                    response = llm_service.provider.generate_content(prompt)
                else:
                    response = None

                if response and response.strip() and not response.strip().startswith("⚠️"):
                    return response.strip().strip('"')
            except Exception as e:
                logger.debug(f"LLM query condensation failed; falling back to contextual concatenation: {e}")

        # 2. Deterministic Contextual Concatenation Fallback
        # Append recent conversational context so vector embeddings capture relevant keywords
        last_turn = turns[-1]
        return f"{clean_query} (Context: {last_turn})"
