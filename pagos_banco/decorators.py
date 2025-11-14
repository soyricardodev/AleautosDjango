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


def validar_ip_banco(view_func):
    """
    Decorador para validar que la IP del request esté en la whitelist del banco.
    En modo DEBUG, permite todas las IPs para facilitar pruebas locales.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # IPs permitidas del banco R4 Conecta
        allowed_ips = ['45.175.213.98', '200.74.203.91', '204.199.249.3']
        
        # En desarrollo, permitir todas las IPs
        if settings.DEBUG:
            return view_func(request, *args, **kwargs)
        
        # Obtener la IP real del cliente (considerando proxies)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        if ip not in allowed_ips:
            return JsonResponse({'error': 'IP no autorizada'}, status=403)
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

