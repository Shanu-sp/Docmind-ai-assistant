from unittest.mock import patch
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from chat.models import ChatSession, ChatMessage
from documents.models import Document

class ChatOrchestrationEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser@example.com", email="testuser@example.com", password="password123")
        self.client.force_authenticate(user=self.user)
        self.doc = Document.objects.create(
            user=self.user,
            title="AI Intro.txt",
            file_type="txt",
            extracted_text="DocMind is an AI-powered Document Assistant built with DRF and React."
        )
        self.session = ChatSession.objects.create(user=self.user, document=self.doc, title="Discussion on AI Intro")

    def test_list_chat_sessions(self):
        response = self.client.get("/api/chat/sessions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 1)

    def test_create_chat_session_auto_title(self):
        payload = {"document": self.doc.id}
        response = self.client.post("/api/chat/sessions/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["title"], f"Chat: {self.doc.title}")

    def test_list_messages_in_session(self):
        # Create messages first
        ChatMessage.objects.create(session=self.session, sender="user", content="Hello")
        ChatMessage.objects.create(session=self.session, sender="assistant", content="Hi there!")

        url = f"/api/chat/sessions/{self.session.id}/messages/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["content"], "Hello")
        self.assertEqual(data[1]["content"], "Hi there!")

    @patch("chat.services.chat_service.LLMService.answer_question")
    def test_send_chat_message_triggers_ai_response(self, mock_answer):
        mock_answer.return_value = "DocMind is an advanced AI document workspace."
        url = f"/api/chat/sessions/{self.session.id}/send-message/"
        payload = {"content": "What is DocMind?"}

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("user_message", data)
        self.assertIn("assistant_message", data)
        self.assertEqual(data["user_message"]["content"], "What is DocMind?")
        self.assertEqual(data["assistant_message"]["content"], "DocMind is an advanced AI document workspace.")

        # Verify DB messages
        messages = ChatMessage.objects.filter(session=self.session)
        self.assertEqual(messages.count(), 2)

    @patch("chat.services.chat_service.HybridRetriever.retrieve")
    @patch("chat.services.chat_service.LLMService.answer_question")
    def test_send_chat_message_populates_citations(self, mock_answer, mock_retrieve):
        mock_answer.return_value = "DocMind uses pgvector for search [Source 1 (Page 2)]."
        mock_retrieve.return_value = [
            {
                "chunk_id": 42,
                "document_id": self.doc.id,
                "page_number": 2,
                "chunk_index": 1,
                "content": "DocMind vector search utilizes Supabase pgvector.",
                "similarity_score": 0.895
            }
        ]

        url = f"/api/chat/sessions/{self.session.id}/send-message/"
        payload = {"content": "How does DocMind search work?"}

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        assistant_data = data["assistant_message"]
        self.assertIn("citations", assistant_data)
        self.assertEqual(len(assistant_data["citations"]), 1)

        citation = assistant_data["citations"][0]
        self.assertEqual(citation["source_id"], 1)
        self.assertEqual(citation["page_number"], 2)
        self.assertEqual(citation["chunk_id"], 42)
        self.assertIn("DocMind vector search", citation["snippet"])

        # Verify DB model
        assistant_msg_db = ChatMessage.objects.get(id=assistant_data["id"])
        self.assertEqual(len(assistant_msg_db.citations), 1)
        self.assertEqual(assistant_msg_db.citations[0]["chunk_id"], 42)

    @patch("documents.services.indexer.DocumentIndexer.index_document")
    @patch("chat.services.chat_service.LLMService.answer_question")
    def test_jit_indexing_fallback_triggered(self, mock_answer, mock_index):
        from chat.services.chat_service import ChatOrchestratorService

        mock_answer.return_value = "Answer with JIT fallback."
        self.doc.indexing_status = "pending"
        self.doc.save()

        orchestrator = ChatOrchestratorService()
        orchestrator.handle_user_message(self.session, "Test JIT")

        # Verify indexer was called
        mock_index.assert_called_once()

    @patch("chat.services.chat_service.HybridRetriever.retrieve")
    @patch("chat.services.chat_service.LLMService.stream_question")
    def test_stream_user_message_persists_citations(self, mock_stream, mock_retrieve):
        from chat.services.chat_service import ChatOrchestratorService

        mock_stream.return_value = iter(["Streaming ", "chunk ", "response."])
        mock_retrieve.return_value = [
            {
                "chunk_id": 99,
                "document_id": self.doc.id,
                "page_number": 1,
                "chunk_index": 0,
                "content": "Streaming citation content.",
                "similarity_score": 0.92
            }
        ]

        orchestrator = ChatOrchestratorService()
        stream_generator = orchestrator.stream_user_message(self.session, "Test streaming")

        # Consume the generator
        tokens = list(stream_generator)
        self.assertEqual("".join(tokens), "Streaming chunk response.")

        # Verify saved assistant message in DB has citations
        assistant_msg = ChatMessage.objects.filter(session=self.session, sender="assistant").last()
        self.assertIsNotNone(assistant_msg)
        self.assertEqual(assistant_msg.content, "Streaming chunk response.")
        self.assertEqual(len(assistant_msg.citations), 1)
        self.assertEqual(assistant_msg.citations[0]["chunk_id"], 99)



