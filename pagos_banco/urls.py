from django.urls import path
from .views import ConsultaView, NotificaView

urlpatterns = [
    path('r4consulta/', ConsultaView.as_view(), name='banco_consulta'),
    path('r4notifica/', NotificaView.as_view(), name='banco_notifica'),
]

