from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json

from .decorators import validar_token_banco
from .models import TransaccionPagoMovil


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(validar_token_banco, name='dispatch')
class ConsultaView(View):
    """
    Endpoint: /api/r4consulta/
    Documentación (R4consulta): El banco pregunta si aceptamos un pago.
    """
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            id_cliente = data.get('IdCliente')
            monto = data.get('Monto')
            telefono_comercio = data.get('TelefonoComercio')

            # --- LÓGICA DE NEGOCIO (Validación) ---
            # TODO: Implementar la lógica para verificar si `id_cliente`
            # existe y si el `monto` es el esperado para un pedido pendiente.
            
            pago_valido = True  # Cambiar esto por la lógica real.
            
            # --- Fin Lógica de Negocio ---

            # Registrar el intento
            TransaccionPagoMovil.objects.create(
                id_cliente=id_cliente,
                monto_consultado=monto,
                telefono_comercio=telefono_comercio,
                status='CONSULTADO' if pago_valido else 'RECHAZADO'
            )

            if pago_valido:
                # Aceptar el pago
                return JsonResponse({"status": True})
            else:
                # Rechazar el pago
                return JsonResponse({"status": False})

        except json.JSONDecodeError:
            return JsonResponse({"error": "JSON inválido"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(validar_token_banco, name='dispatch')
class NotificaView(View):
    """
    Endpoint: /api/r4notifica/
    Documentación (R4notifica): El banco confirma que el pago fue exitoso.
    """
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            referencia = data.get('Referencia')
            monto = data.get('Monto')
            id_comercio = data.get('IdComercio')  # Este es nuestro RIF/Cédula
            telefono_emisor = data.get('TelefonoEmisor')
            banco_emisor = data.get('BancoEmisor')
            
            # --- LÓGICA DE NEGOCIO (Confirmación) ---
            # TODO: Buscar la transacción en la BD (quizás por `id_comercio` y `monto`
            # si la 'consulta' no se completó) y actualizarla.
            
            # Lo ideal es buscar la transacción que ya estaba "CONSULTADO"
            # y que coincide con el monto/teléfono/ID.
            
            try:
                # Intentar actualizar una transacción existente
                transaccion = TransaccionPagoMovil.objects.filter(
                    id_cliente=id_comercio, 
                    monto_consultado=monto, 
                    status='CONSULTADO'
                ).latest('timestamp_consulta')  # Tomar la más reciente que coincida

                transaccion.referencia = referencia
                transaccion.monto_notificado = monto
                transaccion.telefono_emisor = telefono_emisor
                transaccion.banco_emisor = banco_emisor
                transaccion.concepto = data.get('Concepto')
                transaccion.status = 'CONFIRMADO'
                transaccion.timestamp_notificacion = timezone.now()
                transaccion.save()
            
            except TransaccionPagoMovil.DoesNotExist:
                # Si no hubo consulta previa, crear un nuevo registro
                TransaccionPagoMovil.objects.create(
                    id_cliente=id_comercio,
                    monto_notificado=monto,
                    referencia=referencia,
                    telefono_emisor=telefono_emisor,
                    banco_emisor=banco_emisor,
                    concepto=data.get('Concepto'),
                    status='CONFIRMADO',  # Confirmado directamente
                    timestamp_notificacion=timezone.now()
                )

            # TODO: Implementar lógica para liberar el pedido/producto al cliente.
            
            # --- Fin Lógica de Negocio ---

            # Confirmar al banco que recibimos la notificación
            return JsonResponse({"abono": True})

        except Exception as e:
            # Si algo falla, es crucial que el banco sepa que NO recibimos
            # return JsonResponse({"abono": False}) 
            # O mejor, loguear el error y retornar 500
            return JsonResponse({"error": str(e)}, status=500)

