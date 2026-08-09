import logging
from typing import List, Dict, Any, Optional
from .base import LLMProvider
from .gemini import GeminiProvider

logger = logging.getLogger(__name__)

class LLMService:
    """
    High-level application service for AI tasks.
    Delegates generation to the configured LLMProvider.
    """

    def __init__(self, provider: Optional[LLMProvider] = None, api_key: Optional[str] = None):
        self.provider = provider or GeminiProvider(api_key=api_key)

    def summarize_document(self, document_text: str, focus: Optional[str] = None) -> Dict[str, Any]:
        """
        Summarizes extracted document text and generates dynamic follow-up questions.
        Supports custom focus areas.
        """
        if not document_text or not document_text.strip():
            return {
                "executive_summary": ["Document contains no readable text."],
                "suggested_questions": ["Is this document empty or scanned without OCR?"]
            }

        if hasattr(self.provider, 'generate_summary_and_insights'):
            try:
                return self.provider.generate_summary_and_insights(document_text, focus=focus)
            except TypeError:
                return self.provider.generate_summary_and_insights(document_text)

        return self.provider.generate_summary_and_insights(document_text)

    def answer_question(self, prompt: str, context: str = "", history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Answers user prompt based on document context and chat history.
        """
        if not prompt or not prompt.strip():
            return "Please provide a valid question."

        return self.provider.generate_response(prompt=prompt, context=context, history=history)

    def stream_question(self, prompt: str, context: str = "", history: Optional[List[Dict[str, str]]] = None):
        """
        Yields streaming completion tokens for real-time user response generation.
        """
        if not prompt or not prompt.strip():
            yield "Please provide a valid question."
            return

        if hasattr(self.provider, 'stream_response'):
            yield from self.provider.stream_response(prompt=prompt, context=context, history=history)
        else:
            yield self.provider.generate_response(prompt=prompt, context=context, history=history)

