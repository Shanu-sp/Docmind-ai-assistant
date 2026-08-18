import logging
from typing import List, Dict, Any
from .gemini import GeminiProvider

logger = logging.getLogger(__name__)

class LLMService:
    """
    Unified LLM service layer orchestrating AI tasks (chat response, streaming, summarization)
    through concrete provider implementations with multi-model fallback.
    """

    def __init__(self, provider=None):
        self.provider = provider or GeminiProvider()

    def answer_question(self, prompt: str, context: str = "", history: List[Dict[str, str]] = None) -> str:
        """
        Answers a user query given document context and chat history.
        """
        return self.provider.generate_response(prompt=prompt, context=context, history=history)

    def stream_question(self, prompt: str, context: str = "", history: List[Dict[str, str]] = None):
        """
        Streams response tokens for real-time chat interactions.
        """
        return self.provider.stream_response(prompt=prompt, context=context, history=history)

    def summarize_document(self, document_text: str, focus: str = None) -> Dict[str, Any]:
        """
        Generates structured executive summary and suggested prompt questions.
        """
        return self.provider.generate_summary_and_insights(document_text=document_text, focus=focus)


# Alias for backward compatibility
GeminiAIService = LLMService