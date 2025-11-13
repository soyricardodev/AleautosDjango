from functools import wraps
from django.http import JsonResponse
from django.conf import settings


def validar_token_banco(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        token_enviado = request.headers.get('Authorization')
        if token_enviado != settings.BANCO_UUID_TOKEN:
            return JsonResponse({'error': 'No autorizado'}, status=401)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

