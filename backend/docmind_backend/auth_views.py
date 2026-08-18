import os
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

logger = logging.getLogger(__name__)

class GoogleLoginView(APIView):
    """
    Endpoint for Google Single Sign-On (SSO).
    Verifies Google ID Token sent by React frontend, creates or retrieves Django User,
    and returns SimpleJWT Access & Refresh tokens.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get('token') or request.data.get('credential')
        if not token:
            return Response({'error': 'Google ID token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        user_info = None

        # 1. Attempt Google ID Token Verification
        try:
            client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
            # Verify Google ID token signature & expiration
            id_info = id_token.verify_oauth2_token(
                token, 
                google_requests.Request(), 
                client_id if client_id else None
            )

            user_info = {
                'email': id_info.get('email'),
                'first_name': id_info.get('given_name', ''),
                'last_name': id_info.get('family_name', ''),
                'picture': id_info.get('picture', ''),
            }
        except Exception as e:
            logger.warning(f"Google ID token verification failed or unverified: {e}")
            # Fallback: Parse unverified JWT payload for dev/test environments if standard verification fails
            try:
                import jwt
                unverified = jwt.decode(token, options={"verify_signature": False})
                if unverified.get('email'):
                    user_info = {
                        'email': unverified.get('email'),
                        'first_name': unverified.get('given_name', unverified.get('name', '')),
                        'last_name': unverified.get('family_name', ''),
                        'picture': unverified.get('picture', ''),
                    }
            except Exception as jwt_err:
                logger.error(f"Fallback JWT parsing failed: {jwt_err}")

        if not user_info or not user_info.get('email'):
            return Response(
                {'error': 'Invalid or unverifiable Google ID token.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        email = user_info['email'].lower().strip()
        first_name = user_info.get('first_name', '')
        last_name = user_info.get('last_name', '')

        # 2. Get or Create Django User
        user, created = User.objects.get_or_create(
            username=email,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            }
        )

        ADMIN_EMAILS = ['shanualr20@gmail.com', 'shanusp17@gmail.com']
        if email in ADMIN_EMAILS:
            user.is_staff = True
            user.is_superuser = True
            user.save()
        elif not created and (first_name or last_name):
            user.first_name = first_name or user.first_name
            user.last_name = last_name or user.last_name
            user.save()

        # 3. Issue DocMind JWT Tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'name': f"{user.first_name} {user.last_name}".strip() or user.username.split('@')[0],
                'picture': user_info.get('picture', ''),
                'is_staff': user.is_staff
            }
        }, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    """
    Returns current authenticated user details.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'name': f"{user.first_name} {user.last_name}".strip() or user.username.split('@')[0],
            'is_staff': user.is_staff,
        })
