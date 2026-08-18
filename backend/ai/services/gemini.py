import os
import json
import logging
from typing import List, Dict, Any
from google import genai
from google.genai import types
from .base import LLMProvider

logger = logging.getLogger(__name__)

# Primary and fallback models for maximum availability
FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-2.5-pro",
    "gemini-1.5-pro",
]

class GeminiProvider(LLMProvider):
    """
    Concrete implementation of LLMProvider with Multi-Key Pooling,
    Round-Robin Load Balancing, and Automatic Failover.
    """

    _key_index = 0
    MAX_CONTEXT_CHARS = 1_000_000

    def __init__(self, api_key: str = None, model: str = None):
        self.model = model or os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"
        self.api_keys = self._load_api_keys(api_key)
        self.api_key = self.api_keys[0] if self.api_keys else None
        self.client = self._get_client(self.api_key) if self.api_key else None

    @classmethod
    def _load_api_keys(cls, override_key: str = None) -> List[str]:
        if override_key and override_key.strip():
            return [override_key.strip()]

        keys_str = os.environ.get("GEMINI_API_KEYS", "") or os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
        keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        return keys

    @classmethod
    def _get_client(cls, key: str):
        try:
            return genai.Client(api_key=key)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Client with key {key[:8]}...: {e}")
            return None

    def _get_clients_to_try(self):
        """
        Returns list of (client, key_label) ordered by round-robin rotation.
        """
        keys = self._load_api_keys()
        if not keys:
            return []

        # Rotate starting index
        start_idx = GeminiProvider._key_index % len(keys)
        GeminiProvider._key_index = (GeminiProvider._key_index + 1) % len(keys)
        ordered_keys = keys[start_idx:] + keys[:start_idx]

        clients = []
        for k in ordered_keys:
            client = self._get_client(k)
            if client:
                clients.append((client, f"***{k[-4:]}"))
        return clients

    def _get_models_to_try(self):
        models = [self.model] if self.model else []
        for m in FALLBACK_MODELS:
            if m not in models:
                models.append(m)
        return models

    def generate_response(self, prompt: str, context: str = "", history: List[Dict[str, str]] = None) -> str:
        """
        Generates a contextual response with automatic multi-key rotation and multi-model fallback.
        """
        clients_pool = self._get_clients_to_try()
        if not clients_pool:
            return self._mock_response(prompt, context)

        formatted_prompt = ""
        if context:
            formatted_prompt += f"Document Context:\n\"\"\"\n{context[:self.MAX_CONTEXT_CHARS]}\n\"\"\"\n\n"

        if history:
            formatted_prompt += "Previous Conversation History:\n"
            for msg in history:
                sender = msg.get("sender", "user").capitalize()
                content = msg.get("content", "")
                formatted_prompt += f"{sender}: {content}\n"
            formatted_prompt += "\n"

        formatted_prompt += f"User Question: {prompt}\n\nPlease provide a clear, well-structured markdown answer based on the document context and conversation history."

        last_error = None
        for client, key_tag in clients_pool:
            for model_name in self._get_models_to_try():
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=formatted_prompt
                    )
                    if response and response.text:
                        return response.text.strip()
                except Exception as e:
                    err_msg = str(e)
                    logger.warning(f"Gemini [Key {key_tag} / Model {model_name}] failed: {err_msg}. Failing over...")
                    last_error = e
                    continue

        logger.error(f"All Gemini keys & models exhausted. Final error: {last_error}")
        return "⚠️ The AI service is currently experiencing high global traffic. Please wait a few moments and try your question again."

    def stream_response(self, prompt: str, context: str = "", history: List[Dict[str, str]] = None):
        """
        Generator function yielding streaming response chunks with multi-key failover and fallback.
        """
        clients_pool = self._get_clients_to_try()
        if not clients_pool:
            yield self._mock_response(prompt, context)
            return

        formatted_prompt = ""
        if context:
            formatted_prompt += f"Document Context:\n\"\"\"\n{context[:self.MAX_CONTEXT_CHARS]}\n\"\"\"\n\n"

        if history:
            formatted_prompt += "Previous Conversation History:\n"
            for msg in history:
                sender = msg.get("sender", "user").capitalize()
                content = msg.get("content", "")
                formatted_prompt += f"{sender}: {content}\n"
            formatted_prompt += "\n"

        formatted_prompt += f"User Question: {prompt}\n\nPlease provide a clear, well-structured markdown answer."

        streamed_any = False
        last_error = None
        for client, key_tag in clients_pool:
            for model_name in self._get_models_to_try():
                try:
                    response_stream = client.models.generate_content_stream(
                        model=model_name,
                        contents=formatted_prompt
                    )
                    for chunk in response_stream:
                        if chunk.text:
                            streamed_any = True
                            yield chunk.text
                    if streamed_any:
                        return
                except Exception as e:
                    err_msg = str(e)
                    logger.warning(f"Gemini streaming [Key {key_tag} / Model {model_name}] failed: {err_msg}")
                    last_error = e
                    if not streamed_any:
                        continue
                    else:
                        break
            if streamed_any:
                return

        if not streamed_any:
            yield "⚠️ The AI service is currently experiencing high global traffic. Please wait a few moments and try again."

    def generate_summary_and_insights(self, document_text: str, focus: str = None) -> Dict[str, Any]:
        """
        Generates structured executive summary and suggested follow-up questions with multi-key failover.
        """
        clients_pool = self._get_clients_to_try()
        if not clients_pool or not document_text.strip():
            return self._mock_summary(document_text)

        focus_instruction = f" Focus specifically on: {focus}." if focus else ""

        prompt = f"""You are DocMind AI. Analyze the following document text{focus_instruction} and provide:
1. Executive Summary: Exactly 3 concise, highly informative bullet points summarizing key takeaways.
2. Suggested Follow-up Questions: Exactly 3 relevant, analytical questions a user should ask about this document.

Return strictly valid JSON with this key structure:
{{
  "executive_summary": ["bullet 1", "bullet 2", "bullet 3"],
  "suggested_questions": ["question 1", "question 2", "question 3"]
}}

Document Text:
\"\"\"
{document_text[:self.MAX_CONTEXT_CHARS]}
\"\"\"
"""
        for client, key_tag in clients_pool:
            for model_name in self._get_models_to_try():
                try:
                    config = types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=config
                    )

                    res_text = response.text.strip()
                    data = json.loads(res_text)

                    summary = data.get("executive_summary", [])
                    questions = data.get("suggested_questions", [])

                    return {
                        "executive_summary": summary if isinstance(summary, list) else [str(summary)],
                        "suggested_questions": questions if isinstance(questions, list) else [str(questions)]
                    }
                except Exception as e:
                    logger.warning(f"Summary [Key {key_tag} / Model {model_name}] failed: {e}. Trying fallback...")
                    continue

        return self._mock_summary(document_text)

    def _mock_response(self, prompt: str, context: str = "") -> str:
        if context:
            snippet = context[:100].replace("\n", " ")
            return f"[Demo Mode] Based on document context ('{snippet}...'): Answering question '{prompt}'."
        return f"[Demo Mode] Standard response for query: '{prompt}'."

    def _mock_summary(self, text: str) -> Dict[str, Any]:
        preview = text[:60].strip() if text else "Document content"
        return {
            "executive_summary": [
                f"Document highlights key information starting with '{preview}'.",
                "Contains structured text formatted for analysis.",
                "Ready for chat Q&A and detailed exploration."
            ],
            "suggested_questions": [
                "What is the main objective of this document?",
                "Can you list the key points discussed?",
                "What are the important action items?"
            ]
        }



