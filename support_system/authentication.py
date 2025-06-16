from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import User

class APIKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header:
            return None

        api_key = auth_header

        # If the header starts with "Api-Key ", remove the prefix
        if api_key.startswith('Api-Key '):
            api_key = api_key.split(' ', 1)[1]

        return self.authenticate_key(api_key)

    def authenticate_key(self, api_key):
        try:
            user = User.objects.get(api_key=api_key)
            if not user.is_active:
                raise AuthenticationFailed('Пользователь неактивен')
            return (user, None)
        except User.DoesNotExist:
            raise AuthenticationFailed('Неверный API ключ')

    def authenticate_header(self, request):
        return 'Api-Key' 