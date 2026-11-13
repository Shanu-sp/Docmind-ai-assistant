import os
from django.test import TestCase
from ai.services import LLMProvider, GeminiProvider, LLMService

class LLMProviderInterfaceTests(TestCase):
    """
    Test suite for LLMProvider, GeminiProvider, and LLMService.
    """

    def setUp(self):
        self.sample_text = (
            "Artificial Intelligence (AI) is transforming modern software engineering. "
            "Large Language Models (LLMs) allow applications to parse unstructured text, "
            "answer user queries, and extract actionable insights efficiently."
        )

    def test_provider_summarize_and_insights(self):
        provider = GeminiProvider(api_key="")
        service = LLMService(provider=provider)

        result = service.summarize_document(self.sample_text)

        self.assertIn("executive_summary", result)
        self.assertIn("suggested_questions", result)
        self.assertIsInstance(result["executive_summary"], list)
        self.assertIsInstance(result["suggested_questions"], list)
        self.assertGreater(len(result["executive_summary"]), 0)
        self.assertGreater(len(result["suggested_questions"]), 0)

    def test_provider_answer_question(self):
        provider = GeminiProvider(api_key="")
        service = LLMService(provider=provider)

        prompt = "What is this document about?"
        response = service.answer_question(prompt=prompt, context=self.sample_text)

        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)

    def test_empty_input_handling(self):
        service = LLMService()
        
        summary_res = service.summarize_document("")
        self.assertIn("executive_summary", summary_res)
        
        answer_res = service.answer_question("")
        self.assertEqual(answer_res, "Please provide a valid question.")

    def test_embedding_service_empty_input(self):
        from ai.services import EmbeddingService
        service = EmbeddingService()
        self.assertEqual(service.generate_batch_embeddings([]), [])

    def test_embedding_service_dimension(self):
        from ai.services import EmbeddingService
        service = EmbeddingService()
        # Verify single and batch embedding dimension (768d)
        vec = service.generate_embedding("Test embedding text")
        self.assertEqual(len(vec), 768)
        self.assertIsInstance(vec[0], float)

        batch_vecs = service.generate_batch_embeddings(["Chunk A", "Chunk B"])
        self.assertEqual(len(batch_vecs), 2)
        self.assertEqual(len(batch_vecs[0]), 768)
        self.assertEqual(len(batch_vecs[1]), 768)


class HybridRetrieverTests(TestCase):
    """
    Test suite for HybridRetriever: multi-tenant isolation, cosine search,
    document scoping, and query condensation.
    """

    def setUp(self):
        from django.contrib.auth.models import User
        from documents.models import Document, DocumentChunk

        self.user_a = User.objects.create_user(username="usera@example.com", password="password123")
        self.user_b = User.objects.create_user(username="userb@example.com", password="password123")

        self.doc_a1 = Document.objects.create(user=self.user_a, title="User A Doc 1")
        self.doc_a2 = Document.objects.create(user=self.user_a, title="User A Doc 2")
        self.doc_b1 = Document.objects.create(user=self.user_b, title="User B Confidential Doc")

        # Create distinct test embeddings (768 dimensions)
        # Vector A: heavy in first dimension
        self.vec_a = [1.0] + [0.0] * 767
        # Vector B: heavy in second dimension
        self.vec_b = [0.0, 1.0] + [0.0] * 766
        # Vector C: balanced
        self.vec_c = [0.5, 0.5] + [0.0] * 766

        # Populate chunks for User A
        self.chunk_a1 = DocumentChunk.objects.create(
            document=self.doc_a1,
            user=self.user_a,
            chunk_index=0,
            page_number=1,
            content="User A primary content discussing enterprise architecture.",
            embedding=self.vec_a
        )
        self.chunk_a2 = DocumentChunk.objects.create(
            document=self.doc_a2,
            user=self.user_a,
            chunk_index=0,
            page_number=3,
            content="User A secondary document with backend database details.",
            embedding=self.vec_c
        )

        # Populate chunk for User B (confidential)
        self.chunk_b1 = DocumentChunk.objects.create(
            document=self.doc_b1,
            user=self.user_b,
            chunk_index=0,
            page_number=1,
            content="Confidential User B financial report and executive salaries.",
            embedding=self.vec_a  # Same embedding direction to test strict isolation
        )

    def test_multi_tenant_isolation(self):
        """
        CRITICAL SECURITY TEST: Ensure User A can NEVER retrieve User B's chunks,
        even if User B's chunk has a 1.0 cosine similarity to the query.
        """
        from ai.services import HybridRetriever
        from unittest.mock import MagicMock

        # Mock embedder to return vec_a (matches both chunk_a1 and chunk_b1)
        mock_embedder = MagicMock()
        mock_embedder.generate_embedding.return_value = self.vec_a

        retriever = HybridRetriever(embedder=mock_embedder)

        # 1. Search as User A
        results_a = retriever.retrieve(query="enterprise architecture", user_id=self.user_a.id, top_k=10)
        user_a_chunk_ids = [r["chunk_id"] for r in results_a]

        self.assertIn(self.chunk_a1.id, user_a_chunk_ids)
        self.assertNotIn(self.chunk_b1.id, user_a_chunk_ids, "SECURITY VIOLATION: User B chunk leaked to User A!")

        # 2. Search as User B
        results_b = retriever.retrieve(query="enterprise architecture", user_id=self.user_b.id, top_k=10)
        user_b_chunk_ids = [r["chunk_id"] for r in results_b]

        self.assertIn(self.chunk_b1.id, user_b_chunk_ids)
        self.assertNotIn(self.chunk_a1.id, user_b_chunk_ids, "SECURITY VIOLATION: User A chunk leaked to User B!")

    def test_document_scoping(self):
        """
        Verify that passing document_id restricts results strictly to that document.
        """
        from ai.services import HybridRetriever
        from unittest.mock import MagicMock

        mock_embedder = MagicMock()
        mock_embedder.generate_embedding.return_value = self.vec_c

        retriever = HybridRetriever(embedder=mock_embedder)

        # Scope strictly to doc_a2
        results = retriever.retrieve(
            query="database details",
            user_id=self.user_a.id,
            document_id=self.doc_a2.id,
            top_k=5
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["chunk_id"], self.chunk_a2.id)
        self.assertEqual(results[0]["document_id"], self.doc_a2.id)

    def test_user_id_mandatory_and_empty_query(self):
        """
        Verify that missing user_id raises ValueError and empty query returns empty list.
        """
        from ai.services import HybridRetriever

        retriever = HybridRetriever()

        # Missing user_id
        with self.assertRaises(ValueError):
            retriever.retrieve(query="hello", user_id=None)

        with self.assertRaises(ValueError):
            retriever.retrieve(query="hello", user_id=0)

        # Empty or whitespace query
        self.assertEqual(retriever.retrieve(query="", user_id=self.user_a.id), [])
        self.assertEqual(retriever.retrieve(query="   ", user_id=self.user_a.id), [])

    def test_top_k_and_similarity_scoring(self):
        """
        Verify top_k limiting and similarity score computation.
        """
        from ai.services import HybridRetriever
        from unittest.mock import MagicMock

        mock_embedder = MagicMock()
        mock_embedder.generate_embedding.return_value = self.vec_a

        retriever = HybridRetriever(embedder=mock_embedder)

        # Request top_k = 1
        results = retriever.retrieve(query="test", user_id=self.user_a.id, top_k=1)
        self.assertEqual(len(results), 1)
        self.assertAlmostEqual(results[0]["similarity_score"], 1.0, places=2)

    def test_condense_query_conversational(self):
        """
        Verify multi-turn conversational query condensation.
        """
        from ai.services import HybridRetriever
        from unittest.mock import MagicMock

        retriever = HybridRetriever()

        # Case 1: Standalone query with no history
        self.assertEqual(retriever.condense_query("Who is the CEO?"), "Who is the CEO?")

        # Case 2: Multi-turn history with rule-based fallback
        history = [
            {"sender": "user", "content": "Tell me about the engineering team manager."},
            {"sender": "assistant", "content": "Alex Smith is the Engineering Manager."}
        ]
        condensed = retriever.condense_query("What is his email?", history=history)
        self.assertIn("What is his email?", condensed)
        self.assertIn("Alex Smith", condensed)

        # Case 3: Neural reformulation using mock LLM
        mock_llm = MagicMock()
        mock_llm.answer_question.return_value = "What is Alex Smith's email address?"
        neural_condensed = retriever.condense_query("What is his email?", history=history, llm_service=mock_llm)
        self.assertEqual(neural_condensed, "What is Alex Smith's email address?")



