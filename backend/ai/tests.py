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
        provider = GeminiProvider(api_key=None)
        service = LLMService(provider=provider)

        result = service.summarize_document(self.sample_text)

        self.assertIn("executive_summary", result)
        self.assertIn("suggested_questions", result)
        self.assertIsInstance(result["executive_summary"], list)
        self.assertIsInstance(result["suggested_questions"], list)
        self.assertGreater(len(result["executive_summary"]), 0)
        self.assertGreater(len(result["suggested_questions"]), 0)

    def test_provider_answer_question(self):
        provider = GeminiProvider(api_key=None)
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

