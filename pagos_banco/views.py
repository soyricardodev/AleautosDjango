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

logger = logging.getLogger("ballena")


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
    telefono_normalizado = re.sub(r"[^0-9]", "", telefono_str)
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


# @method_decorator(validar_ip_banco, name="dispatch")
@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(validar_token_banco, name="dispatch")
class ConsultaView(View):
    """
    Endpoint: /api/r4consulta/
    Documentación (R4consulta): El banco pregunta si aceptamos un pago.
    """

    def post(self, request, *args, **kwargs):
        try:
            # ===== DEBUG EXHAUSTIVO: Datos recibidos del banco =====
            body_raw = request.body.decode("utf-8") if request.body else "EMPTY"
            url_completa = request.build_absolute_uri()
            metodo = request.method
            path_info = request.path
            query_string = request.META.get("QUERY_STRING", "")

            print("\n" + "=" * 100)
            print("[CONSULTA R4] REPORTE EXHAUSTIVO PARA EL BANCO")
            print("=" * 100)
            print(f"[URL COMPLETA] {url_completa}")
            print(f"[PATH] {path_info}")
            print(f"[QUERY STRING] {query_string if query_string else '(vacio)'}")
            print(f"[METODO HTTP] {metodo}")
            print(f"[IP REMOTA] {request.META.get('REMOTE_ADDR')}")
            print(
                f"[IP REAL (X-Forwarded-For)] {request.META.get('HTTP_X_FORWARDED_FOR', 'No presente')}"
            )
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

            id_cliente = data.get("IdCliente")
            monto = data.get("Monto")
            telefono_comercio = data.get("TelefonoComercio")

            print(
                f"   IdCliente: {repr(id_cliente)} (tipo: {type(id_cliente).__name__}, presente: {id_cliente is not None})"
            )
            print(
                f"   Monto: {repr(monto)} (tipo: {type(monto).__name__}, presente: {monto is not None})"
            )
            print(
                f"   TelefonoComercio: {repr(telefono_comercio)} (tipo: {type(telefono_comercio).__name__}, presente: {telefono_comercio is not None})"
            )
            print(f"[TODAS LAS CLAVES EN EL JSON] {list(data.keys())}")
            print(f"[TOTAL DE CAMPOS] {len(data)}")
            print(f"[TIMESTAMP] {timezone.now().isoformat()}")
            print("=" * 100 + "\n")

            # Logging también
            logger.info(
                f"Consulta R4: URL={url_completa}, Method={metodo}, IP={request.META.get('REMOTE_ADDR')}, Body={body_raw}, Cliente={id_cliente}, Monto={monto}, Keys={list(data.keys())}"
            )

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
                if rif_comercio_recibido.upper().startswith("J-"):
                    rif_comercio_recibido = rif_comercio_recibido[2:]

                rif_comercio_nuestro = str(settings.R4_COMERCIO_RIF).strip()

                if rif_comercio_recibido != rif_comercio_nuestro:
                    logger.warning(
                        f"Consulta R4: [RECHAZADO] IdCliente {id_cliente} no coincide con nuestro RIF {rif_comercio_nuestro}"
                    )
                    print(
                        f"[VALIDACION FALLIDA] IdCliente {id_cliente} no coincide con nuestro RIF {rif_comercio_nuestro}"
                    )
                    pago_valido = False
                else:
                    # 2. BUSCAR compras pendientes de PagoMovil por MONTO
                    # (No por cliente, porque no sabemos quién va a pagar aún)
                    monto_decimal = float(monto)
                    compras_pendientes = (
                        Compra.objects.filter(
                            Estado=Compra.EstadoCompra.Pendiente,
                            MetodoPago=Compra.MetodoPagoOpciones.PagoMovil,
                        )
                        .filter(
                            Q(TotalPagado__gte=monto_decimal - 0.01)
                            & Q(TotalPagado__lte=monto_decimal + 0.01)
                        )
                        .order_by("-FechaCompra")
                    )

                    if compras_pendientes.exists():
                        pago_valido = True
                        compra = compras_pendientes.first()
                        cliente_nombre = (
                            compra.idComprador.Nombre if compra.idComprador else "N/A"
                        )
                        logger.info(
                            f"Consulta R4: [ACEPTADO] RIF {id_cliente} valido, Compra #{compra.Id} pendiente, Monto {monto}, Cliente: {cliente_nombre}"
                        )
                        print(
                            f"[PAGO ACEPTADO] Compra #{compra.Id} pendiente por monto {monto}"
                        )
                    else:
                        logger.warning(
                            f"Consulta R4: [RECHAZADO] No hay compras pendientes por monto {monto} para RIF {id_cliente}"
                        )
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
                    status="CONSULTADO" if pago_valido else "RECHAZADO",
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


# @method_decorator(validar_ip_banco, name="dispatch")
@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(validar_token_banco, name="dispatch")
class NotificaView(View):
    """
    Endpoint: /api/r4notifica/
    Documentación (R4notifica): El banco confirma que el pago fue exitoso.
    """

    def post(self, request, *args, **kwargs):
        # CRÍTICO: Cerrar conexiones de BD en caso de error para evitar acumulación
        try:
            # OPTIMIZACIÓN: Reducir logging excesivo - solo logging esencial
            body_raw = request.body.decode("utf-8") if request.body else "EMPTY"
            data = json.loads(request.body)

            # Campos según documentación R4notifica
            id_comercio = data.get("IdComercio")  # RIF del comercio (requerido)
            telefono_comercio = data.get(
                "TelefonoComercio"
            )  # Teléfono del comercio (requerido)
            telefono_emisor = data.get(
                "TelefonoEmisor"
            )  # Teléfono de origen del pago (requerido)
            concepto = data.get("Concepto")  # Motivo del pago (opcional)
            banco_emisor = data.get(
                "BancoEmisor"
            )  # Código del banco del pago (requerido)
            monto = data.get(
                "Monto"
            )  # Monto con decimales separados por punto (requerido)
            fecha_hora = data.get("FechaHora")  # Fecha y hora (requerido)
            referencia = data.get("Referencia")  # Referencia interbancaria (requerido)
            codigo_red = data.get(
                "CodigoRed"
            )  # Código de respuesta de la red interbancaria (requerido)

            # ===== LOGGING EXHAUSTIVO PARA DEBUGGING =====
            logger.info("=" * 100)
            logger.info("[NOTIFICA R4] INICIO DE PROCESAMIENTO")
            logger.info("=" * 100)
            logger.info(f"[REQUEST] IP={request.META.get('REMOTE_ADDR')}")
            logger.info(
                f"[REQUEST] X-Forwarded-For={request.META.get('HTTP_X_FORWARDED_FOR', 'No presente')}"
            )
            logger.info(f"[REQUEST] Method={request.method}")
            logger.info(f"[REQUEST] Path={request.path}")
            logger.info(f"[BODY RAW] {body_raw[:500]}...")  # Primeros 500 caracteres
            logger.info(f"[DATOS RECIBIDOS]")
            logger.info(f"  - IdComercio: {id_comercio}")
            logger.info(f"  - TelefonoComercio: {telefono_comercio}")
            logger.info(f"  - TelefonoEmisor: {telefono_emisor}")
            logger.info(f"  - Concepto: {concepto}")
            logger.info(f"  - BancoEmisor: {banco_emisor}")
            logger.info(f"  - Monto: {monto}")
            logger.info(f"  - FechaHora: {fecha_hora}")
            logger.info(f"  - Referencia: {referencia}")
            logger.info(f"  - CodigoRed: {codigo_red}")

            # --- LÓGICA DE NEGOCIO (Confirmación) ---
            # Según documentación: validar IdComercio, referencia, banco y monto antes de abonar
            abono_valido = False
            transaccion = None
            compra_actualizada = False
            compra = None

            try:
                # 1. VALIDAR IdComercio: Debe coincidir con nuestro RIF del comercio
                logger.info("[PASO 1] Validando IdComercio...")
                rif_comercio_recibido = str(id_comercio).strip() if id_comercio else ""
                # Normalizar: quitar prefijo J- si viene
                if rif_comercio_recibido.upper().startswith("J-"):
                    rif_comercio_recibido = rif_comercio_recibido[2:]

                rif_comercio_nuestro = str(settings.R4_COMERCIO_RIF).strip()
                logger.info(
                    f"[PASO 1] RIF recibido (normalizado): {rif_comercio_recibido}"
                )
                logger.info(f"[PASO 1] RIF nuestro: {rif_comercio_nuestro}")

                if rif_comercio_recibido != rif_comercio_nuestro:
                    logger.warning(
                        f"[PASO 1] [RECHAZADO] IdComercio {id_comercio} no coincide con nuestro RIF {rif_comercio_nuestro}"
                    )
                    return JsonResponse({"abono": False})

                logger.info(f"[PASO 1] [OK] IdComercio valido: {id_comercio}")

                # 2. VALIDAR campos requeridos
                logger.info("[PASO 2] Validando campos requeridos...")
                if not monto or not referencia or not banco_emisor:
                    logger.warning(
                        f"[PASO 2] [RECHAZADO] Campos requeridos faltantes: Monto={monto}, Referencia={referencia}, BancoEmisor={banco_emisor}"
                    )
                    return JsonResponse({"abono": False})
                logger.info(f"[PASO 2] [OK] Campos requeridos presentes")

                # 3. OPTIMIZACIÓN: BUSCAR compras pendientes por MONTO y TELÉFONO directamente
                # Buscar solo compras del cliente con ese teléfono, no todas las compras
                logger.info(
                    "[PASO 3] Buscando compras pendientes por monto y teléfono..."
                )
                monto_decimal = float(monto)

                # Normalizar teléfono del banco
                telefono_banco_normalizado = normalizar_telefono(telefono_emisor)
                logger.info(f"[PASO 3] Teléfono emisor original: {telefono_emisor}")
                logger.info(
                    f"[PASO 3] Teléfono emisor normalizado: {telefono_banco_normalizado}"
                )

                # VALIDACIÓN CRÍTICA: El teléfono es OBLIGATORIO para validar el pago
                if not telefono_banco_normalizado:
                    logger.error(
                        f"[PASO 3] [RECHAZADO] Teléfono del emisor es obligatorio para validar el pago. Monto: {monto}"
                    )
                    return JsonResponse({"abono": False})

                # OPTIMIZACIÓN: Buscar compras pendientes por monto que tengan comprador
                # Luego filtrar por teléfono normalizado (más eficiente que buscar todas)
                compras_pendientes_qs = (
                    Compra.objects.filter(
                        Estado=Compra.EstadoCompra.Pendiente,
                        MetodoPago=Compra.MetodoPagoOpciones.PagoMovil,
                        idComprador__isnull=False,  # Solo compras con comprador
                    )
                    .filter(
                        Q(TotalPagado__gte=monto_decimal - 0.01)
                        & Q(TotalPagado__lte=monto_decimal + 0.01)
                    )
                    .select_related("idComprador")
                    .order_by("-FechaCompra")
                )

                # Evaluar QuerySet y normalizar teléfonos en memoria
                compras_pendientes = list(compras_pendientes_qs)
                logger.info(
                    f"[PASO 3] Compras pendientes encontradas por monto: {len(compras_pendientes)}"
                )

                # Buscar compra que coincida por teléfono normalizado
                compra = None
                compras_verificadas = 0

                # Iterar sobre la lista en memoria (no sobre QuerySet)
                for compra_candidata in compras_pendientes:
                    compras_verificadas += 1
                    if (
                        compra_candidata.idComprador
                        and compra_candidata.idComprador.NumeroTlf
                    ):
                        telefono_compra_normalizado = normalizar_telefono(
                            compra_candidata.idComprador.NumeroTlf
                        )
                        logger.debug(
                            f"[PASO 3] Verificando compra #{compra_candidata.Id}: "
                            f"Tel BD={compra_candidata.idComprador.NumeroTlf}, "
                            f"Tel normalizado={telefono_compra_normalizado}"
                        )
                        if comparar_telefonos(
                            telefono_banco_normalizado, telefono_compra_normalizado
                        ):
                            compra = compra_candidata
                            logger.info(
                                f"[PASO 3] [OK] Compra encontrada: #{compra.Id} "
                                f"(Tel banco: {telefono_emisor}, Tel compra: {compra.idComprador.NumeroTlf})"
                            )
                            break  # Encontrar la primera coincidencia (ya está ordenada por fecha descendente)

                logger.info(
                    f"[PASO 3] Total compras verificadas: {compras_verificadas}"
                )

                if compra:
                    logger.info(
                        f"[PASO 3] [OK] Compra encontrada por monto Y telefono: #{compra.Id}"
                    )
                else:
                    # CRÍTICO: Si no hay coincidencia de teléfono, RECHAZAR el pago
                    logger.error(
                        f"[PASO 3] [RECHAZADO] No se encontro compra pendiente con monto {monto} Y telefono {telefono_emisor}. "
                        f"El teléfono debe coincidir exactamente."
                    )

                    # Log exhaustivo para debugging: mostrar todas las compras pendientes
                    if compras_pendientes:
                        logger.warning(
                            f"[PASO 3] [DEBUG] Compras pendientes encontradas por monto {monto} (mostrando todas):"
                        )
                        for idx, compra_debug in enumerate(compras_pendientes, 1):
                            tel_compra = (
                                compra_debug.idComprador.NumeroTlf
                                if compra_debug.idComprador
                                else "N/A"
                            )
                            tel_compra_norm = (
                                normalizar_telefono(tel_compra)
                                if tel_compra != "N/A"
                                else "N/A"
                            )
                            logger.warning(
                                f"  [{idx}] Compra #{compra_debug.Id}: "
                                f"Tel BD={tel_compra}, "
                                f"Tel normalizado={tel_compra_norm}, "
                                f"Cliente={compra_debug.idComprador.Nombre if compra_debug.idComprador else 'N/A'}, "
                                f"Fecha={compra_debug.FechaCompra}"
                            )
                    else:
                        logger.warning(
                            f"[PASO 3] [DEBUG] No hay compras pendientes por monto {monto}"
                        )

                    return JsonResponse({"abono": False})

                # Validación de seguridad: compra debe existir
                if not compra:
                    logger.error(
                        f"[PASO 3] [ERROR CRÍTICO] Compra es None después de validación. Esto no debería ocurrir."
                    )
                    return JsonResponse({"abono": False})

                logger.info(
                    f"[PASO 3] [OK] Compra encontrada: #{compra.Id}, "
                    f"Cliente: {compra.idComprador.Nombre if compra.idComprador else 'N/A'}, "
                    f"Monto compra: {compra.TotalPagado}, "
                    f"Fecha compra: {compra.FechaCompra}"
                )

                # 4. VALIDAR referencia, banco y monto (según documentación)
                logger.info("[PASO 4] Validando referencia...")
                # La referencia debe ser única y válida
                if referencia:
                    # Verificar si ya existe una compra con esta referencia (evitar duplicados)
                    compra_existente_ref = (
                        Compra.objects.filter(
                            Referencia=referencia, Estado=Compra.EstadoCompra.Pagado
                        )
                        .exclude(Id=compra.Id)
                        .first()
                    )
                    if compra_existente_ref:
                        logger.warning(
                            f"[PASO 4] [RECHAZADO] Referencia {referencia} ya fue usada en compra #{compra_existente_ref.Id}"
                        )
                        return JsonResponse({"abono": False})
                    logger.info(
                        f"[PASO 4] [OK] Referencia {referencia} es válida y única"
                    )

                # 5. Si todas las validaciones pasan, actualizar compra a Pagado
                logger.info("[PASO 5] Actualizando compra a Pagado...")
                with transaction.atomic():
                    compra.Estado = Compra.EstadoCompra.Pagado
                    compra.FechaEstado = timezone.now()
                    compra.Referencia = referencia
                    compra.save()
                    compra_actualizada = True
                    abono_valido = True
                    logger.info(
                        f"[PASO 5] [OK] Compra #{compra.Id} actualizada a Pagado. "
                        f"Referencia: {referencia}, FechaEstado: {compra.FechaEstado}"
                    )

                    # OPTIMIZACIÓN CRÍTICA: Actualizar TotalComprados y crear NumeroRifaComprados
                    logger.info("[PASO 5.1] Procesando números de la compra...")
                    # Evaluar QuerySet una sola vez con values_list para evitar múltiples evaluaciones
                    rifa = compra.idRifa
                    logger.info(f"[PASO 5.1] Rifa ID: {rifa.Id if rifa else 'N/A'}")

                    numeros_compra_lista = list(
                        NumerosCompra.objects.filter(idCompra=compra).values_list(
                            "Numero", flat=True
                        )
                    )
                    logger.info(
                        f"[PASO 5.1] Números en compra: {len(numeros_compra_lista)} - {numeros_compra_lista[:10]}..."
                    )

                    if numeros_compra_lista:
                        # OPTIMIZACIÓN: Verificar números ya comprados con una sola query
                        numeros_ya_comprados = set(
                            NumeroRifaComprados.objects.filter(
                                idRifa=rifa, Numero__in=numeros_compra_lista
                            ).values_list("Numero", flat=True)
                        )
                        logger.info(
                            f"[PASO 5.1] Números ya comprados: {len(numeros_ya_comprados)}"
                        )

                        # OPTIMIZACIÓN: Usar bulk_create en lugar de create() individual
                        # Esto reduce de N queries a 1 query
                        numeros_a_agregar = [
                            NumeroRifaComprados(idRifa=rifa, Numero=num)
                            for num in numeros_compra_lista
                            if num not in numeros_ya_comprados
                        ]

                        if numeros_a_agregar:
                            NumeroRifaComprados.objects.bulk_create(numeros_a_agregar)
                            rifa.TotalComprados = F("TotalComprados") + len(
                                numeros_a_agregar
                            )
                            rifa.save()
                            logger.info(
                                f"[PASO 5.1] [OK] Actualizados {len(numeros_a_agregar)} numeros en TotalComprados para rifa {rifa.Id}. "
                                f"TotalComprados ahora: {rifa.TotalComprados}"
                            )
                        else:
                            logger.info(
                                f"[PASO 5.1] [INFO] Todos los números ya estaban comprados"
                            )
                    else:
                        logger.warning(
                            f"[PASO 5.1] [WARNING] No hay números asociados a esta compra"
                        )

                    # OPTIMIZACIÓN: Liberar números reservados si existen
                    logger.info("[PASO 5.2] Liberando números reservados...")
                    # Usar filter().delete() directamente en lugar de verificar existencia primero
                    from Rifa.models import (
                        NumeroRifaReservadosOrdenes,
                        NumeroRifaDisponibles,
                    )

                    if numeros_compra_lista:
                        numeros_eliminados = NumeroRifaReservadosOrdenes.objects.filter(
                            idRifa=rifa, Numero__in=numeros_compra_lista
                        ).delete()
                        if numeros_eliminados[0] > 0:
                            logger.info(
                                f"[PASO 5.2] [OK] {numeros_eliminados[0]} numeros reservados liberados para compra {compra.Id}"
                            )
                        else:
                            logger.info(
                                f"[PASO 5.2] [INFO] No había números reservados para liberar"
                            )
                    else:
                        logger.info(
                            f"[PASO 5.2] [INFO] No hay números para liberar (lista vacía)"
                        )

                cliente_nombre = (
                    compra.idComprador.Nombre if compra.idComprador else "N/A"
                )
                logger.info("=" * 100)
                logger.info(
                    f"[NOTIFICA R4] [PAGADA] COMPRA #{compra.Id} PAGADA EXITOSAMENTE"
                )
                logger.info(f"  - Cliente: {cliente_nombre}")
                logger.info(f"  - Monto: {monto}")
                logger.info(f"  - Referencia: {referencia}")
                logger.info(f"  - Banco: {banco_emisor}")
                logger.info(f"  - Teléfono: {telefono_emisor}")
                logger.info("=" * 100)

            except ValueError as e:
                logger.error("=" * 100)
                logger.error(f"[NOTIFICA R4] [ERROR] Monto invalido: {str(e)}")
                logger.error(f"[ERROR] Monto recibido: {monto}")
                logger.error("=" * 100)
                # CRÍTICO: Cerrar conexiones de BD en caso de error
                try:
                    from django.db import connections

                    for alias in connections:
                        try:
                            connections[alias].close()
                        except:
                            pass
                except:
                    pass
                return JsonResponse({"abono": False})
            except Exception as e:
                logger.error("=" * 100)
                logger.error(f"[NOTIFICA R4] [ERROR] inesperado: {str(e)}")
                import traceback

                logger.error(traceback.format_exc())
                logger.error("=" * 100)
                # CRÍTICO: Cerrar conexiones de BD en caso de error
                try:
                    from django.db import connections

                    for alias in connections:
                        try:
                            connections[alias].close()
                        except:
                            pass
                except:
                    pass
                return JsonResponse({"abono": False})

            # Actualizar o crear transacción
            logger.info("[PASO 6] Actualizando/creando transacción...")
            if abono_valido:
                try:
                    # Buscar transacción existente de la consulta previa
                    transacciones_existentes = TransaccionPagoMovil.objects.filter(
                        monto_consultado=monto, status="CONSULTADO"
                    ).order_by("-timestamp_consulta")

                    logger.info(
                        f"[PASO 6] Transacciones existentes encontradas: {transacciones_existentes.count()}"
                    )

                    if transacciones_existentes.exists():
                        transaccion = transacciones_existentes.first()
                        logger.info(
                            f"[PASO 6] Actualizando transacción existente ID: {transaccion.id}"
                        )
                        transaccion.referencia = referencia
                        transaccion.monto_notificado = monto
                        transaccion.telefono_emisor = telefono_emisor
                        transaccion.banco_emisor = banco_emisor
                        transaccion.concepto = concepto
                        transaccion.status = "CONFIRMADO"
                        transaccion.timestamp_notificacion = timezone.now()
                        # Vincular con la compra si existe y no está vinculada
                        if compra_actualizada and compra and not transaccion.idCompra:
                            transaccion.idCompra = compra
                            logger.info(
                                f"[PASO 6] Transacción vinculada con compra #{compra.Id}"
                            )
                        transaccion.save()
                        logger.info(
                            f"[PASO 6] [OK] Transacción {transaccion.id} actualizada exitosamente"
                        )
                    else:
                        # Si no hubo consulta previa, crear un nuevo registro
                        logger.info("[PASO 6] Creando nueva transacción...")
                        # Usar cédula del comprador si existe
                        id_cliente_transaccion = None
                        if compra and compra.idComprador and compra.idComprador.Cedula:
                            id_cliente_transaccion = compra.idComprador.Cedula
                            logger.info(
                                f"[PASO 6] ID Cliente para transacción: {id_cliente_transaccion}"
                            )

                        transaccion = TransaccionPagoMovil.objects.create(
                            id_cliente=id_cliente_transaccion,
                            monto_notificado=monto,
                            referencia=referencia,
                            telefono_emisor=telefono_emisor,
                            banco_emisor=banco_emisor,
                            concepto=concepto,
                            status="CONFIRMADO",
                            timestamp_notificacion=timezone.now(),
                        )
                        # Vincular con la compra si existe
                        if compra_actualizada and compra:
                            transaccion.idCompra = compra
                            transaccion.save()
                            logger.info(
                                f"[PASO 6] Transacción vinculada con compra #{compra.Id}"
                            )
                        logger.info(
                            f"[PASO 6] [OK] Nueva transaccion {transaccion.id} creada exitosamente"
                        )
                except Exception as e:
                    logger.error(
                        f"[PASO 6] [ERROR] Error al actualizar/crear transaccion: {str(e)}"
                    )
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
            # CRÍTICO: Cerrar conexiones de BD en caso de error
            try:
                from django.db import connections

                for alias in connections:
                    try:
                        connections[alias].close()
                    except:
                        pass
            except:
                pass
            return JsonResponse({"error": "JSON inválido"}, status=400)
        except Exception as e:
            # Si algo falla, es crucial que el banco sepa que NO recibimos
            logger.error(f"Notifica R4: Error inesperado - {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            # CRÍTICO: Cerrar conexiones de BD en caso de error
            try:
                from django.db import connections

                for alias in connections:
                    try:
                        connections[alias].close()
                    except:
                        pass
            except:
                pass
            return JsonResponse({"error": str(e)}, status=500)
