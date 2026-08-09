from abc import ABC, abstractmethod
from typing import List, Dict, Any

class LLMProvider(ABC):
    """
    Abstract Base Class for LLM Providers.
    Decouples application logic from specific LLM vendors (Gemini, OpenAI, Claude, local Ollama).
    """

    @abstractmethod
    def generate_response(self, prompt: str, context: str = "", history: List[Dict[str, str]] = None) -> str:
        """
        Generate a response given a user prompt, optional document context, and chat history.
        """
        pass

    @abstractmethod
    def generate_summary_and_insights(self, document_text: str) -> Dict[str, Any]:
        """
        Generate executive summary and dynamic suggested follow-up questions from extracted text.
        Returns a dict:
        {
            "executive_summary": [str, str, str],
            "suggested_questions": [str, str, str]
        }
        """
        pass

