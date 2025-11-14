from django.db import models


class TransaccionPagoMovil(models.Model):
    STATUS_CHOICES = [
        ('PENDIENTE', 'Pendiente de Pago'),
        ('CONSULTADO', 'Consultado por Banco'),
        ('RECHAZADO', 'Rechazado por Comercio'),
        ('CONFIRMADO', 'Pago Confirmado'),
        ('ERROR', 'Error'),
    ]

    # Datos de la Consulta
    id_cliente = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    monto_consultado = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    telefono_comercio = models.CharField(max_length=15, blank=True, null=True)
    timestamp_consulta = models.DateTimeField(auto_now_add=True)

    # Datos de la Notificación
    referencia = models.CharField(max_length=30, blank=True, null=True, unique=True, db_index=True)
    monto_notificado = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    telefono_emisor = models.CharField(max_length=15, blank=True, null=True)
    banco_emisor = models.CharField(max_length=10, blank=True, null=True)
    concepto = models.CharField(max_length=100, blank=True, null=True)
    timestamp_notificacion = models.DateTimeField(null=True, blank=True)

    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDIENTE')
    
    # Relación con Compra
    idCompra = models.ForeignKey('Rifa.Compra', on_delete=models.SET_NULL, null=True, blank=True, related_name='transacciones_pago_movil', db_index=True)

    def __str__(self):
        return f"{self.id_cliente} - {self.referencia} - {self.status}"

