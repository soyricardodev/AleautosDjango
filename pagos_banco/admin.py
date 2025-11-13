from django.contrib import admin
from .models import TransaccionPagoMovil


@admin.register(TransaccionPagoMovil)
class TransaccionPagoMovilAdmin(admin.ModelAdmin):
    list_display = ('id_cliente', 'referencia', 'monto_consultado', 'monto_notificado', 'status', 'timestamp_consulta', 'timestamp_notificacion')
    list_filter = ('status', 'timestamp_consulta', 'timestamp_notificacion')
    search_fields = ('id_cliente', 'referencia', 'telefono_comercio', 'telefono_emisor')
    readonly_fields = ('timestamp_consulta', 'timestamp_notificacion')
    date_hierarchy = 'timestamp_consulta'

