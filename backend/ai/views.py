import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ai.services import GeminiProvider

class AIConfigView(APIView):
    """
    Endpoint for checking and updating AI Provider configuration.
    """
    def get(self, request):
        provider = GeminiProvider()
        has_key = bool(provider.api_key)
        mode = "Live (Gemini 2.5 Flash)" if has_key else "Demo Mode (Mock Answers)"
        return Response({
            "has_api_key": has_key,
            "mode": mode,
            "model": provider.model,
            "masked_key": f"***{provider.api_key[-4:]}" if (has_key and len(provider.api_key) > 4) else None
        })

    def post(self, request):
        api_key = request.data.get('api_key')
        if not api_key:
            return Response({"error": "api_key is required"}, status=status.HTTP_400_BAD_REQUEST)

        test_provider = GeminiProvider(api_key=api_key)
        if not test_provider.client:
            return Response({"error": "Invalid API Key format or client initialization failure."}, status=status.HTTP_400_BAD_REQUEST)

        os.environ["GEMINI_API_KEY"] = api_key
        return Response({"message": "API key successfully configured.", "has_api_key": True}, status=status.HTTP_200_OK)

