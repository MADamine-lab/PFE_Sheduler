# scheduler/authentication.py
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

class CookieTokenAuthentication(TokenAuthentication):
    def authenticate(self, request):
        token = request.COOKIES.get("auth_token")
        if not token:
            return None  # ✅ No token = anonymous, don't raise exception
        try:
            return self.authenticate_credentials(token)
        except AuthenticationFailed:
            return None  # ✅ Invalid token = anonymous, don't block the request