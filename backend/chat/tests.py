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


