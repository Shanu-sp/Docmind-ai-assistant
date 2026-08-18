from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from ai.services import GeminiProvider

class AIConfigView(APIView):
    """
    Endpoint for checking and updating AI Provider configuration.
    Read is allowed for all authenticated users; write is restricted to Admins.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        provider = GeminiProvider()
        has_key = bool(provider.api_keys)
        mode = f"Live ({provider.model}) - {len(provider.api_keys)} Keys Pooled" if has_key else "Demo Mode (Mock Answers)"
        masked = f"***{provider.api_key[-4:]}" if (provider.api_key and len(provider.api_key) > 4) else None
        return Response({
            "has_api_key": has_key,
            "mode": mode,
            "model": provider.model,
            "keys_count": len(provider.api_keys),
            "masked_key": masked,
            "is_admin": request.user.is_staff
        })

    def post(self, request):
        if not request.user.is_staff:
            return Response({"error": "Only DocMind administrators can modify AI configurations."}, status=status.HTTP_403_FORBIDDEN)

        api_key = request.data.get('api_key')
        if not api_key:
            return Response({"error": "api_key is required"}, status=status.HTTP_400_BAD_REQUEST)

        test_provider = GeminiProvider(api_key=api_key)
        if not test_provider.client:
            return Response({"error": "Invalid API Key format or client initialization failure."}, status=status.HTTP_400_BAD_REQUEST)

        import os
        os.environ["GEMINI_API_KEY"] = api_key
        return Response({"message": "API key successfully configured.", "has_api_key": True}, status=status.HTTP_200_OK)


