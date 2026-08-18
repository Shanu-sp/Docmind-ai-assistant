import os
import json
import logging
from typing import List, Dict, Any
from google import genai
from google.genai import types
from .base import LLMProvider

logger = logging.getLogger(__name__)

class GeminiProvider(LLMProvider):
    """
    Concrete implementation of LLMProvider using Google Gemini API (google-genai SDK).
    """

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.model = model or os.environ.get("GEMINI_MODEL") or "gemini-flash-latest"
        self.client = None

        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini Client: {e}")

    MAX_CONTEXT_CHARS = 1_000_000  # Expand to 1M chars to fully utilize Gemini Flash's 1M+ token window

    FALLBACK_MODELS = [
        "gemini-2.5-flash",
        "gemini-1.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
    ]

    def _get_models_to_try(self):
        models = [self.model] if self.model else []
        for m in self.FALLBACK_MODELS:
            if m not in models:
                models.append(m)
        return models

    def generate_response(self, prompt: str, context: str = "", history: List[Dict[str, str]] = None) -> str:
        """
        Generates a contextual response using Gemini LLM with automatic multi-model fallback.
        """
        if not self.client:
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
        for model_name in self._get_models_to_try():
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=formatted_prompt
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                err_msg = str(e)
                logger.warning(f"Gemini model {model_name} failed: {err_msg}. Trying fallback...")
                last_error = e
                if any(code in err_msg for code in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "demand"]):
                    continue
                else:
                    break

        logger.error(f"All Gemini models exhausted. Final error: {last_error}")
        return "⚠️ The AI service is currently experiencing high global traffic. Please wait a few moments and try your question again."

    def stream_response(self, prompt: str, context: str = "", history: List[Dict[str, str]] = None):
        """
        Generator function yielding streaming response chunks from Gemini API with fallback.
        """
        if not self.client:
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
        for model_name in self._get_models_to_try():
            try:
                response_stream = self.client.models.generate_content_stream(
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
                logger.warning(f"Gemini streaming model {model_name} failed: {err_msg}")
                last_error = e
                if not streamed_any and any(code in err_msg for code in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "demand"]):
                    continue
                else:
                    break

        if not streamed_any:
            yield "⚠️ The AI service is currently experiencing high global traffic. Please wait a few moments and try again."

    def generate_summary_and_insights(self, document_text: str, focus: str = None) -> Dict[str, Any]:
        """
        Generates structured executive summary (3 bullet points) and suggested follow-up questions.
        Supports custom focus areas if provided.
        """
        if not self.client or not document_text.strip():
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
        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json"
            )
            response = self.client.models.generate_content(
                model=self.model,
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
            logger.error(f"Gemini API generate_summary_and_insights error: {e}")
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
                "What are the next steps mentioned in this document?"
            ]
        }


