from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Q
import json
import logging

from .decorators import validar_token_banco
from .models import TransaccionPagoMovil

# Importar modelos de Rifa
from Rifa.models import Cliente, Compra

logger = logging.getLogger('ballena')


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
            # Buscar cliente por cédula (id_cliente)
            pago_valido = False
            
            try:
                cliente = Cliente.objects.get(cedula=id_cliente)
                
                # Buscar compras pendientes del cliente con el monto indicado
                # Permitir un margen de diferencia pequeña (0.01) por posibles redondeos
                monto_decimal = float(monto)
                compras_pendientes = Compra.objects.filter(
                    idComprador__idCliente=cliente,
                    Estado=Compra.EstadoCompra.Pendiente
                ).filter(
                    Q(TotalPagado__gte=monto_decimal - 0.01) & 
                    Q(TotalPagado__lte=monto_decimal + 0.01)
                )
                
                if compras_pendientes.exists():
                    pago_valido = True
                    logger.info(f"Consulta R4: Cliente {id_cliente} tiene compra pendiente por {monto}")
                else:
                    logger.warning(f"Consulta R4: Cliente {id_cliente} no tiene compras pendientes por {monto}")
                    
            except Cliente.DoesNotExist:
                logger.warning(f"Consulta R4: Cliente con cédula {id_cliente} no encontrado")
                pago_valido = False
            except Exception as e:
                logger.error(f"Error en ConsultaView: {str(e)}")
                pago_valido = False
            
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
            # Buscar cliente por cédula (id_comercio)
            transaccion = None
            compra_actualizada = False
            
            try:
                cliente = Cliente.objects.get(cedula=id_comercio)
                monto_decimal = float(monto)
                
                # Buscar compra pendiente del cliente con el monto indicado
                compra = Compra.objects.filter(
                    idComprador__idCliente=cliente,
                    Estado=Compra.EstadoCompra.Pendiente
                ).filter(
                    Q(TotalPagado__gte=monto_decimal - 0.01) & 
                    Q(TotalPagado__lte=monto_decimal + 0.01)
                ).order_by('-FechaCompra').first()
                
                if compra:
                    # Actualizar compra a Pagado
                    compra.Estado = Compra.EstadoCompra.Pagado
                    compra.FechaEstado = timezone.now()
                    compra.save()
                    compra_actualizada = True
                    logger.info(f"Notifica R4: Compra {compra.Id} marcada como Pagada para cliente {id_comercio}")
                
            except Cliente.DoesNotExist:
                logger.warning(f"Notifica R4: Cliente con cédula {id_comercio} no encontrado")
            except Exception as e:
                logger.error(f"Error en NotificaView al actualizar compra: {str(e)}")
            
            # Actualizar o crear transacción
            try:
                # Intentar actualizar una transacción existente
                transaccion = TransaccionPagoMovil.objects.filter(
                    id_cliente=id_comercio, 
                    monto_consultado=monto, 
                    status='CONSULTADO'
                ).latest('timestamp_consulta')

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
                transaccion = TransaccionPagoMovil.objects.create(
                    id_cliente=id_comercio,
                    monto_notificado=monto,
                    referencia=referencia,
                    telefono_emisor=telefono_emisor,
                    banco_emisor=banco_emisor,
                    concepto=data.get('Concepto'),
                    status='CONFIRMADO',
                    timestamp_notificacion=timezone.now()
                )
            
            # --- Fin Lógica de Negocio ---

            # Confirmar al banco que recibimos la notificación
            return JsonResponse({"abono": True})

        except Exception as e:
            # Si algo falla, es crucial que el banco sepa que NO recibimos
            # return JsonResponse({"abono": False}) 
            # O mejor, loguear el error y retornar 500
            return JsonResponse({"error": str(e)}, status=500)

