from django.urls import path, re_path
from .views import ConsultaView, NotificaView

urlpatterns = [
    # Aceptar tanto con como sin barra final para evitar problemas con APPEND_SLASH
    re_path(r'^r4consulta/?$', ConsultaView.as_view(), name='banco_consulta'),
    re_path(r'^r4notifica/?$', NotificaView.as_view(), name='banco_notifica'),
]

