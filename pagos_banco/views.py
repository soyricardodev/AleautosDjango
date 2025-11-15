from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Q
import json
import logging
import re

from .decorators import validar_token_banco, validar_ip_banco
from .models import TransaccionPagoMovil

# Importar modelos de Rifa
from Rifa.models import Cliente, Compra, NumerosCompra, NumeroRifaComprados, Rifa
from django.conf import settings
from django.db.models import F
from django.db import transaction

logger = logging.getLogger('ballena')


def normalizar_telefono(telefono):
    """
    Normaliza un número de teléfono para comparación:
    - Quita espacios, guiones, paréntesis, etc.
    - Solo deja números
    - Convierte a string
    """
    if not telefono:
        return None
    # Convertir a string y quitar espacios
    telefono_str = str(telefono).strip()
    # Quitar todos los caracteres que no sean números
    telefono_normalizado = re.sub(r'[^0-9]', '', telefono_str)
    return telefono_normalizado if telefono_normalizado else None


def comparar_telefonos(telefono1, telefono2):
    """
    Compara dos teléfonos normalizados.
    Retorna True si coinciden, False en caso contrario.
    """
    tel1_norm = normalizar_telefono(telefono1)
    tel2_norm = normalizar_telefono(telefono2)
    
    if not tel1_norm or not tel2_norm:
        return False
    
    # Comparar los últimos 10 dígitos (para manejar códigos de país)
    # Si tienen menos de 10 dígitos, comparar completos
    if len(tel1_norm) >= 10 and len(tel2_norm) >= 10:
        return tel1_norm[-10:] == tel2_norm[-10:]
    else:
        return tel1_norm == tel2_norm


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(validar_token_banco, name='dispatch')
@method_decorator(validar_ip_banco, name='dispatch')
class ConsultaView(View):
    """
    Endpoint: /api/r4consulta/
    Documentación (R4consulta): El banco pregunta si aceptamos un pago.
    """
    def post(self, request, *args, **kwargs):
        try:
            # ===== DEBUG EXHAUSTIVO: Datos recibidos del banco =====
            body_raw = request.body.decode('utf-8') if request.body else 'EMPTY'
            url_completa = request.build_absolute_uri()
            metodo = request.method
            path_info = request.path
            query_string = request.META.get('QUERY_STRING', '')
            
            print("\n" + "="*100)
            print("[CONSULTA R4] REPORTE EXHAUSTIVO PARA EL BANCO")
            print("="*100)
            print(f"[URL COMPLETA] {url_completa}")
            print(f"[PATH] {path_info}")
            print(f"[QUERY STRING] {query_string if query_string else '(vacio)'}")
            print(f"[METODO HTTP] {metodo}")
            print(f"[IP REMOTA] {request.META.get('REMOTE_ADDR')}")
            print(f"[IP REAL (X-Forwarded-For)] {request.META.get('HTTP_X_FORWARDED_FOR', 'No presente')}")
            print(f"[TODOS LOS HEADERS]")
            for key, value in request.headers.items():
                print(f"   {key}: {value}")
            print(f"[BODY RAW (bytes)] {request.body}")
            print(f"[BODY RAW (string)] {body_raw}")
            print(f"[BODY LENGTH] {len(request.body) if request.body else 0} bytes")
            
            data = json.loads(request.body)
            print(f"[JSON PARSEADO COMPLETO]")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print(f"[ANALISIS DE CAMPOS]")
            
            id_cliente = data.get('IdCliente')
            monto = data.get('Monto')
            telefono_comercio = data.get('TelefonoComercio')
            
            print(f"   IdCliente: {repr(id_cliente)} (tipo: {type(id_cliente).__name__}, presente: {id_cliente is not None})")
            print(f"   Monto: {repr(monto)} (tipo: {type(monto).__name__}, presente: {monto is not None})")
            print(f"   TelefonoComercio: {repr(telefono_comercio)} (tipo: {type(telefono_comercio).__name__}, presente: {telefono_comercio is not None})")
            print(f"[TODAS LAS CLAVES EN EL JSON] {list(data.keys())}")
            print(f"[TOTAL DE CAMPOS] {len(data)}")
            print(f"[TIMESTAMP] {timezone.now().isoformat()}")
            print("="*100 + "\n")
            
            # Logging también
            logger.info(f"Consulta R4: URL={url_completa}, Method={metodo}, IP={request.META.get('REMOTE_ADDR')}, Body={body_raw}, Cliente={id_cliente}, Monto={monto}, Keys={list(data.keys())}")

            # --- LÓGICA DE NEGOCIO (Validación) ---
            # IMPORTANTE: IdCliente en R4consulta es el RIF del COMERCIO, no del cliente
            # El banco pregunta: "¿Debo aceptar este pago de este monto?"
            # Debemos validar:
            # 1. Que IdCliente coincida con nuestro RIF del comercio
            # 2. Que haya una compra pendiente esperando ese monto
            pago_valido = False
            
            try:
                # 1. VALIDAR que IdCliente sea nuestro RIF del comercio
                rif_comercio_recibido = str(id_cliente).strip() if id_cliente else ""
                # Normalizar: quitar prefijo J- si viene
                if rif_comercio_recibido.upper().startswith('J-'):
                    rif_comercio_recibido = rif_comercio_recibido[2:]
                
                rif_comercio_nuestro = str(settings.R4_COMERCIO_RIF).strip()
                
                if rif_comercio_recibido != rif_comercio_nuestro:
                    logger.warning(f"Consulta R4: [RECHAZADO] IdCliente {id_cliente} no coincide con nuestro RIF {rif_comercio_nuestro}")
                    print(f"[VALIDACION FALLIDA] IdCliente {id_cliente} no coincide con nuestro RIF {rif_comercio_nuestro}")
                    pago_valido = False
                else:
                    # 2. BUSCAR compras pendientes de PagoMovil por MONTO
                    # (No por cliente, porque no sabemos quién va a pagar aún)
                    monto_decimal = float(monto)
                    compras_pendientes = Compra.objects.filter(
                        Estado=Compra.EstadoCompra.Pendiente,
                        MetodoPago=Compra.MetodoPagoOpciones.PagoMovil
                    ).filter(
                        Q(TotalPagado__gte=monto_decimal - 0.01) & 
                        Q(TotalPagado__lte=monto_decimal + 0.01)
                    ).order_by('-FechaCompra')
                    
                    if compras_pendientes.exists():
                        pago_valido = True
                        compra = compras_pendientes.first()
                        cliente_nombre = compra.idComprador.Nombre if compra.idComprador else "N/A"
                        logger.info(f"Consulta R4: [ACEPTADO] RIF {id_cliente} valido, Compra #{compra.Id} pendiente, Monto {monto}, Cliente: {cliente_nombre}")
                        print(f"[PAGO ACEPTADO] Compra #{compra.Id} pendiente por monto {monto}")
                    else:
                        logger.warning(f"Consulta R4: [RECHAZADO] No hay compras pendientes por monto {monto} para RIF {id_cliente}")
                        print(f"[NO HAY COMPRAS PENDIENTES] para monto {monto}")
                        pago_valido = False
                    
            except ValueError as e:
                logger.error(f"Consulta R4: [ERROR] Monto invalido: {str(e)}")
                print(f"[ERROR] Monto invalido - {str(e)}")
                pago_valido = False
            except Exception as e:
                logger.error(f"Consulta R4: [ERROR] {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                print(f"[ERROR] {str(e)}")
                pago_valido = False
            
            # --- Fin Lógica de Negocio ---

            # Registrar el intento
            try:
                TransaccionPagoMovil.objects.create(
                    id_cliente=id_cliente,
                    monto_consultado=monto,
                    telefono_comercio=telefono_comercio,
                    status='CONSULTADO' if pago_valido else 'RECHAZADO'
                )
            except Exception as e:
                logger.error(f"Consulta R4: Error al crear registro: {str(e)}")

            # Responder al banco según la documentación R4
            if pago_valido:
                return JsonResponse({"status": True})
            else:
                return JsonResponse({"status": False})

        except json.JSONDecodeError as e:
            logger.error(f"Consulta R4: JSON inválido - {str(e)}")
            return JsonResponse({"error": "JSON inválido"}, status=400)
        except Exception as e:
            logger.error(f"Consulta R4: Error inesperado - {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(validar_token_banco, name='dispatch')
@method_decorator(validar_ip_banco, name='dispatch')
class NotificaView(View):
    """
    Endpoint: /api/r4notifica/
    Documentación (R4notifica): El banco confirma que el pago fue exitoso.
    """
    def post(self, request, *args, **kwargs):
        try:
            # ===== DEBUG EXHAUSTIVO: Datos recibidos del banco =====
            body_raw = request.body.decode('utf-8') if request.body else 'EMPTY'
            url_completa = request.build_absolute_uri()
            metodo = request.method
            path_info = request.path
            query_string = request.META.get('QUERY_STRING', '')
            
            print("\n" + "="*100)
            print("[NOTIFICA R4] REPORTE EXHAUSTIVO PARA EL BANCO")
            print("="*100)
            print(f"[URL COMPLETA] {url_completa}")
            print(f"[PATH] {path_info}")
            print(f"[QUERY STRING] {query_string if query_string else '(vacio)'}")
            print(f"[METODO HTTP] {metodo}")
            print(f"[IP REMOTA] {request.META.get('REMOTE_ADDR')}")
            print(f"[IP REAL (X-Forwarded-For)] {request.META.get('HTTP_X_FORWARDED_FOR', 'No presente')}")
            print(f"[TODOS LOS HEADERS]")
            for key, value in request.headers.items():
                print(f"   {key}: {value}")
            print(f"[BODY RAW (bytes)] {request.body}")
            print(f"[BODY RAW (string)] {body_raw}")
            print(f"[BODY LENGTH] {len(request.body) if request.body else 0} bytes")
            
            data = json.loads(request.body)
            print(f"[JSON PARSEADO COMPLETO]")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print(f"[ANALISIS DE CAMPOS]")
            
            # Campos según documentación R4notifica
            id_comercio = data.get('IdComercio')  # RIF del comercio (requerido)
            telefono_comercio = data.get('TelefonoComercio')  # Teléfono del comercio (requerido)
            telefono_emisor = data.get('TelefonoEmisor')  # Teléfono de origen del pago (requerido)
            concepto = data.get('Concepto')  # Motivo del pago (opcional)
            banco_emisor = data.get('BancoEmisor')  # Código del banco del pago (requerido)
            monto = data.get('Monto')  # Monto con decimales separados por punto (requerido)
            fecha_hora = data.get('FechaHora')  # Fecha y hora (requerido)
            referencia = data.get('Referencia')  # Referencia interbancaria (requerido)
            codigo_red = data.get('CodigoRed')  # Código de respuesta de la red interbancaria (requerido)
            
            print(f"   IdComercio: {repr(id_comercio)} (tipo: {type(id_comercio).__name__}, presente: {id_comercio is not None})")
            print(f"   TelefonoComercio: {repr(telefono_comercio)} (tipo: {type(telefono_comercio).__name__}, presente: {telefono_comercio is not None})")
            print(f"   TelefonoEmisor: {repr(telefono_emisor)} (tipo: {type(telefono_emisor).__name__}, presente: {telefono_emisor is not None})")
            print(f"   Concepto: {repr(concepto)} (tipo: {type(concepto).__name__}, presente: {concepto is not None})")
            print(f"   BancoEmisor: {repr(banco_emisor)} (tipo: {type(banco_emisor).__name__}, presente: {banco_emisor is not None})")
            print(f"   Monto: {repr(monto)} (tipo: {type(monto).__name__}, presente: {monto is not None})")
            print(f"   FechaHora: {repr(fecha_hora)} (tipo: {type(fecha_hora).__name__}, presente: {fecha_hora is not None})")
            print(f"   Referencia: {repr(referencia)} (tipo: {type(referencia).__name__}, presente: {referencia is not None})")
            print(f"   CodigoRed: {repr(codigo_red)} (tipo: {type(codigo_red).__name__}, presente: {codigo_red is not None})")
            print(f"[TODAS LAS CLAVES EN EL JSON] {list(data.keys())}")
            print(f"[TOTAL DE CAMPOS] {len(data)}")
            print(f"[TIMESTAMP] {timezone.now().isoformat()}")
            print("="*100 + "\n")
            
            # Logging también
            logger.info(f"Notifica R4: URL={url_completa}, Method={metodo}, IP={request.META.get('REMOTE_ADDR')}, Body={body_raw}, IdComercio={id_comercio}, Monto={monto}, Referencia={referencia}, Keys={list(data.keys())}")
            
            # --- LÓGICA DE NEGOCIO (Confirmación) ---
            # Según documentación: validar IdComercio, referencia, banco y monto antes de abonar
            abono_valido = False
            transaccion = None
            compra_actualizada = False
            compra = None
            
            try:
                # 1. VALIDAR IdComercio: Debe coincidir con nuestro RIF del comercio
                rif_comercio_recibido = str(id_comercio).strip() if id_comercio else ""
                # Normalizar: quitar prefijo J- si viene
                if rif_comercio_recibido.upper().startswith('J-'):
                    rif_comercio_recibido = rif_comercio_recibido[2:]
                
                rif_comercio_nuestro = str(settings.R4_COMERCIO_RIF).strip()
                
                if rif_comercio_recibido != rif_comercio_nuestro:
                    logger.warning(f"Notifica R4: [RECHAZADO] IdComercio {id_comercio} no coincide con nuestro RIF {rif_comercio_nuestro}")
                    print(f"[VALIDACION FALLIDA] IdComercio {id_comercio} no coincide con nuestro RIF {rif_comercio_nuestro}")
                    return JsonResponse({"abono": False})
                
                logger.info(f"Notifica R4: [OK] IdComercio valido: {id_comercio}")
                print(f"[OK] IdComercio valido: {id_comercio}")
                
                # 2. VALIDAR campos requeridos
                if not monto or not referencia or not banco_emisor:
                    logger.warning(f"Notifica R4: [RECHAZADO] Campos requeridos faltantes: Monto={monto}, Referencia={referencia}, BancoEmisor={banco_emisor}")
                    print(f"[VALIDACION FALLIDA] Campos requeridos faltantes")
                    return JsonResponse({"abono": False})
                
                # 3. BUSCAR compras pendientes por MONTO y TELÉFONO (OBLIGATORIO)
                # CRÍTICO: Validar SIEMPRE por monto Y teléfono para evitar asignación incorrecta
                monto_decimal = float(monto)
                
                # Normalizar teléfono del banco
                telefono_banco_normalizado = normalizar_telefono(telefono_emisor)
                
                # VALIDACIÓN CRÍTICA: El teléfono es OBLIGATORIO para validar el pago
                if not telefono_banco_normalizado:
                    logger.error(f"Notifica R4: [RECHAZADO] Teléfono del emisor es obligatorio para validar el pago. Monto: {monto}")
                    print(f"[VALIDACION FALLIDA] Teléfono del emisor es obligatorio")
                    return JsonResponse({"abono": False})
                
                # Buscar compras pendientes por monto
                compras_pendientes = Compra.objects.filter(
                    Estado=Compra.EstadoCompra.Pendiente,
                    MetodoPago=Compra.MetodoPagoOpciones.PagoMovil
                ).filter(
                    Q(TotalPagado__gte=monto_decimal - 0.01) & 
                    Q(TotalPagado__lte=monto_decimal + 0.01)
                ).select_related('idComprador').order_by('-FechaCompra')
                
                # Buscar compra que coincida por monto Y teléfono
                compra = None
                compras_coincidentes = []
                
                for compra_candidata in compras_pendientes:
                    if compra_candidata.idComprador and compra_candidata.idComprador.NumeroTlf:
                        telefono_compra_normalizado = normalizar_telefono(compra_candidata.idComprador.NumeroTlf)
                        if comparar_telefonos(telefono_banco_normalizado, telefono_compra_normalizado):
                            compras_coincidentes.append(compra_candidata)
                
                # Si hay múltiples compras con el mismo monto y teléfono, tomar la más reciente
                if compras_coincidentes:
                    compra = compras_coincidentes[0]  # Ya están ordenadas por FechaCompra descendente
                    logger.info(f"Notifica R4: [OK] Compra encontrada por monto Y telefono: #{compra.Id}, Tel banco: {telefono_emisor}, Tel compra: {compra.idComprador.NumeroTlf}")
                    print(f"[OK] Compra encontrada por monto Y telefono: #{compra.Id}")
                else:
                    # CRÍTICO: Si no hay coincidencia de teléfono, RECHAZAR el pago
                    # Esto previene que un pago se asigne al usuario incorrecto
                    logger.error(f"Notifica R4: [RECHAZADO] No se encontro compra pendiente con monto {monto} Y telefono {telefono_emisor}. El teléfono debe coincidir exactamente.")
                    print(f"[VALIDACION FALLIDA] No se encontro compra con monto {monto} Y telefono {telefono_emisor}")
                    
                    # Log adicional para debugging: mostrar qué compras pendientes hay
                    if compras_pendientes.exists():
                        logger.warning(f"Notifica R4: [DEBUG] Compras pendientes encontradas por monto {monto}:")
                        for compra_debug in compras_pendientes[:5]:  # Mostrar máximo 5
                            tel_compra = compra_debug.idComprador.NumeroTlf if compra_debug.idComprador else 'N/A'
                            logger.warning(f"  - Compra #{compra_debug.Id}: Teléfono {tel_compra} (no coincide con {telefono_emisor})")
                    
                    return JsonResponse({"abono": False})
                
                # Validación de seguridad: compra debe existir
                if not compra:
                    logger.error(f"Notifica R4: [ERROR CRÍTICO] Compra es None después de validación. Esto no debería ocurrir.")
                    return JsonResponse({"abono": False})
                
                logger.info(f"Notifica R4: [OK] Compra encontrada: #{compra.Id}, Cliente: {compra.idComprador.Nombre if compra.idComprador else 'N/A'}")
                print(f"[OK] Compra encontrada: #{compra.Id}")
                
                # 4. VALIDAR referencia, banco y monto (según documentación)
                # La referencia debe ser única y válida
                if referencia:
                    # Verificar si ya existe una compra con esta referencia (evitar duplicados)
                    compra_existente_ref = Compra.objects.filter(Referencia=referencia, Estado=Compra.EstadoCompra.Pagado).exclude(Id=compra.Id).first()
                    if compra_existente_ref:
                        logger.warning(f"Notifica R4: [RECHAZADO] Referencia {referencia} ya fue usada en compra #{compra_existente_ref.Id}")
                        print(f"[VALIDACION FALLIDA] Referencia {referencia} ya fue usada")
                        return JsonResponse({"abono": False})
                
                # 5. Si todas las validaciones pasan, actualizar compra a Pagado
                with transaction.atomic():
                    compra.Estado = Compra.EstadoCompra.Pagado
                    compra.FechaEstado = timezone.now()
                    compra.Referencia = referencia
                    compra.save()
                    compra_actualizada = True
                    abono_valido = True
                    
                    # Actualizar TotalComprados y crear NumeroRifaComprados
                    # Obtener los números de la compra
                    numeros_compra = NumerosCompra.objects.filter(idCompra=compra)
                    
                    # Verificar si ya están en NumeroRifaComprados
                    rifa = compra.idRifa
                    numeros_ya_comprados = NumeroRifaComprados.objects.filter(
                        idRifa=rifa,
                        Numero__in=[nc.Numero for nc in numeros_compra]
                    ).values_list('Numero', flat=True)
                    
                    # Crear registros solo para números que no están ya comprados
                    numeros_a_agregar = []
                    for num_compra in numeros_compra:
                        if num_compra.Numero not in numeros_ya_comprados:
                            NumeroRifaComprados.objects.create(
                                idRifa=rifa,
                                Numero=num_compra.Numero
                            )
                            numeros_a_agregar.append(num_compra.Numero)
                    
                    # Actualizar TotalComprados solo si agregamos números nuevos
                    if numeros_a_agregar:
                        rifa.TotalComprados = F('TotalComprados') + len(numeros_a_agregar)
                        rifa.save()
                        logger.info(f"Notifica R4: Actualizados {len(numeros_a_agregar)} numeros en TotalComprados para rifa {rifa.Id}")
                    
                    # Liberar números reservados si existen
                    from Rifa.models import NumeroRifaReservadosOrdenes, NumeroRifaDisponibles
                    numeros_reservados = NumeroRifaReservadosOrdenes.objects.filter(
                        idRifa=rifa,
                        Numero__in=[nc.Numero for nc in numeros_compra]
                    )
                    if numeros_reservados.exists():
                        numeros_reservados.delete()
                        logger.info(f"Notifica R4: Numeros reservados liberados para compra {compra.Id}")
                
                cliente_nombre = compra.idComprador.Nombre if compra.idComprador else "N/A"
                logger.info(f"Notifica R4: [PAGADA] COMPRA #{compra.Id} PAGADA - Cliente: {cliente_nombre}, Monto: {monto}, Ref: {referencia}")
                print(f"[PAGADA] COMPRA #{compra.Id} MARCADA COMO PAGADA - Cliente: {cliente_nombre}")
                
            except ValueError as e:
                logger.error(f"Notifica R4: [ERROR] Monto invalido: {str(e)}")
                print(f"[ERROR] Monto invalido - {str(e)}")
                return JsonResponse({"abono": False})
            except Exception as e:
                logger.error(f"Notifica R4: [ERROR] inesperado: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                print(f"[ERROR] inesperado: {str(e)}")
                return JsonResponse({"abono": False})
            
            # Actualizar o crear transacción
            if abono_valido:
                try:
                    # Buscar transacción existente de la consulta previa
                    transacciones_existentes = TransaccionPagoMovil.objects.filter(
                        monto_consultado=monto, 
                        status='CONSULTADO'
                    ).order_by('-timestamp_consulta')
                    
                    if transacciones_existentes.exists():
                        transaccion = transacciones_existentes.first()
                        transaccion.referencia = referencia
                        transaccion.monto_notificado = monto
                        transaccion.telefono_emisor = telefono_emisor
                        transaccion.banco_emisor = banco_emisor
                        transaccion.concepto = concepto
                        transaccion.status = 'CONFIRMADO'
                        transaccion.timestamp_notificacion = timezone.now()
                        # Vincular con la compra si existe y no está vinculada
                        if compra_actualizada and compra and not transaccion.idCompra:
                            transaccion.idCompra = compra
                        transaccion.save()
                        logger.info(f"Notifica R4: Transacción {transaccion.id} actualizada")
                    else:
                        # Si no hubo consulta previa, crear un nuevo registro
                        # Usar cédula del comprador si existe
                        id_cliente_transaccion = None
                        if compra and compra.idComprador and compra.idComprador.Cedula:
                            id_cliente_transaccion = compra.idComprador.Cedula
                        
                        transaccion = TransaccionPagoMovil.objects.create(
                            id_cliente=id_cliente_transaccion,
                            monto_notificado=monto,
                            referencia=referencia,
                            telefono_emisor=telefono_emisor,
                            banco_emisor=banco_emisor,
                            concepto=concepto,
                            status='CONFIRMADO',
                            timestamp_notificacion=timezone.now()
                        )
                        # Vincular con la compra si existe
                        if compra_actualizada and compra:
                            transaccion.idCompra = compra
                            transaccion.save()
                        logger.info(f"Notifica R4: Nueva transaccion {transaccion.id} creada")
                except Exception as e:
                    logger.error(f"Notifica R4: [ERROR] Error al actualizar/crear transaccion: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    # No retornar error aquí, ya validamos el pago
            
            # --- Fin Lógica de Negocio ---

            # Responder al banco según documentación R4
            if abono_valido:
                return JsonResponse({"abono": True})
            else:
                return JsonResponse({"abono": False})

        except json.JSONDecodeError as e:
            logger.error(f"Notifica R4: JSON inválido - {str(e)}")
            return JsonResponse({"error": "JSON inválido"}, status=400)
        except Exception as e:
            # Si algo falla, es crucial que el banco sepa que NO recibimos
            logger.error(f"Notifica R4: Error inesperado - {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)

