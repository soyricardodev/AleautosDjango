from datetime import datetime, timedelta
import math
import os
import random
import re
import string
from celery import shared_task
import time
import urllib.request as request
import uuid
import requests as RR
import requests
from django import template
from django.http import HttpResponse, JsonResponse
from django.template import loader
from django.http import HttpResponse
from django.shortcuts import render
from .forms import (
    FirstFileForm,
    RifaForm,
    SecondFileForm,
    UploadFileForm,
    ReserveForm,
    UpdateOrderForm,
    CompradorForm,
)
from .models import (
    Logger,
    Comprador,
    LoggerAprobadoRechazo,
    NumeroRifaReservados,
    NumeroRifaReservadosOrdenes,
    NumerosCompra,
    OrdenesReservas,
    Rifa as RifaModel,
    NumeroRifaDisponibles,
    NumeroRifaDisponiblesArray,
    NumeroRifaComprados,
    NumeroRifaCompradosArray,
    Ordenes,
    Compra,
    Tasas,
    Settings,
    Cliente,
)
from django.core.paginator import Paginator
from django.db import transaction, IntegrityError
from django.core import serializers
from django.db.models import functions
from django.contrib.postgres.fields import ArrayField
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
import json
from django.contrib.postgres.fields.array import (
    ArrayLenTransform,
    SliceTransform,
    SliceTransformFactory,
    IndexTransform,
)
from django.conf import settings
from django.core.mail import send_mail
from django.core.mail import EmailMessage, get_connection
from django.template.loader import render_to_string
import boto3
from django.contrib.auth.decorators import login_required, permission_required
import pytz
from django.utils import timezone as django_timezone
from django.db.models.functions import Cast
from django.db.models import IntegerField
from django.db.models import F
import http.client
import logging
from django.shortcuts import render
import qrcode
from PIL import Image
from io import BytesIO
import base64

logger = logging.getLogger("ballena")


def index(request):
    template = loader.get_template("second.html")
    context = {}
    return HttpResponse(template.render(context, request))


def changeState(request):
    data = {}
    if request.method == "POST":
        dataX = json.load(request)
        idRifa = dataX["id"]
        logger.info(idRifa)

        rifa = RifaModel.objects.get(Id=idRifa)
        rifa.Estado = not rifa.Estado
        rifa.save()
        data["success"] = "true"
    return JsonResponse(data)


def changeExtension(request):
    data = {}
    if request.method == "POST":
        dataX = json.load(request)
        idRifa = dataX["id"]
        logger.info(idRifa)

        rifa = RifaModel.objects.get(Id=idRifa)
        rifa.Extension = not rifa.Extension
        rifa.save()
        data["success"] = "true"
    return JsonResponse(data)


# region "Numeros"
def SaveSettings(request):
    if request.method == "POST":
        data = json.load(request)
        # Solo resetear los settings que están siendo actualizados
        for x in data.keys():
            setting = Settings.objects.filter(code=x).first()
            if setting is not None:
                # Si el valor viene vacío o es None, establecerlo como None
                setting.valor = data[x] if data[x] and str(data[x]).strip() else None
                setting.save()
            else:
                # Si el setting no existe, crearlo
                Settings.objects.create(
                    code=x,
                    descripcion=f"Configuración para {x}",
                    valor=data[x] if data[x] and str(data[x]).strip() else None,
                )
        return JsonResponse(
            {"result": "Success", "message": "Preferencias actualizadas correctamente"}
        )
    return JsonResponse(
        {"result": "Error", "message": "Metodo no soportado"}, status=404
    )


def SaveComprador(request):
    if request.method == "POST":
        data = json.load(request)
        form = CompradorForm(data)
        print(form)
        print(form.is_valid())
        print(form.errors)
        if form.is_valid():
            comprador_id = form.cleaned_data.get("id")
            cliente_id = data.get("cliente_id")

            # Handle case where we're editing from cliente and comprador doesn't exist yet
            if cliente_id and not comprador_id:
                try:
                    cliente = Cliente.objects.get(id=cliente_id)
                    comprador = Comprador.objects.filter(idCliente=cliente).first()
                    if not comprador:
                        # Create new comprador for this cliente
                        comprador = Comprador()
                        comprador.idCliente = cliente
                    comprador.Nombre = form.cleaned_data["nombre"]
                    comprador.Correo = form.cleaned_data["correo"]
                    comprador.NumeroTlf = form.cleaned_data["telefono"]
                    comprador.Cedula = form.cleaned_data["cedula"]
                    comprador.save()

                    # Update User and Cliente data
                    user = cliente.user
                    # Update user email
                    if form.cleaned_data.get("correo"):
                        user.email = form.cleaned_data["correo"]
                    # Update user name (split nombre into first_name and last_name)
                    nombre_completo = form.cleaned_data.get("nombre", "").strip()
                    if nombre_completo:
                        partes_nombre = nombre_completo.split(" ", 1)
                        user.first_name = partes_nombre[0]
                        user.last_name = (
                            partes_nombre[1] if len(partes_nombre) > 1 else ""
                        )
                    user.save()

                    # Update cliente data
                    if form.cleaned_data.get("cedula"):
                        cliente.cedula = form.cleaned_data["cedula"]
                    if form.cleaned_data.get("telefono"):
                        cliente.telefono = form.cleaned_data["telefono"]
                    cliente.save()

                    # Update password if provided
                    password = form.cleaned_data.get("password")
                    if password and password.strip():
                        user.set_password(password)
                        user.save()

                    return JsonResponse(
                        {
                            "result": "Success",
                            "message": "Comprador guardado correctamente",
                        }
                    )
                except Cliente.DoesNotExist:
                    return JsonResponse(
                        {"result": "Error", "message": "Cliente no encontrado"},
                        status=404,
                    )
            elif comprador_id:
                # Existing comprador
                comprador = Comprador.objects.get(Id=comprador_id)
                comprador.Nombre = form.cleaned_data["nombre"]
                comprador.Correo = form.cleaned_data["correo"]
                comprador.NumeroTlf = form.cleaned_data["telefono"]
                comprador.Cedula = form.cleaned_data["cedula"]
                comprador.save()

                # Update User and Cliente if comprador has cliente associated
                if comprador.idCliente:
                    cliente = comprador.idCliente
                    user = cliente.user

                    # Update user email
                    if form.cleaned_data.get("correo"):
                        user.email = form.cleaned_data["correo"]

                    # Update user name (split nombre into first_name and last_name)
                    nombre_completo = form.cleaned_data.get("nombre", "").strip()
                    if nombre_completo:
                        partes_nombre = nombre_completo.split(" ", 1)
                        user.first_name = partes_nombre[0]
                        user.last_name = (
                            partes_nombre[1] if len(partes_nombre) > 1 else ""
                        )
                    user.save()

                    # Update cliente data
                    if form.cleaned_data.get("cedula"):
                        cliente.cedula = form.cleaned_data["cedula"]
                    if form.cleaned_data.get("telefono"):
                        cliente.telefono = form.cleaned_data["telefono"]
                    cliente.save()

                    # Update password if provided
                    password = form.cleaned_data.get("password")
                    if password and password.strip():
                        user.set_password(password)
                        user.save()

                return JsonResponse(
                    {"result": "Success", "message": "Comprador guardado correctamente"}
                )
            else:
                return JsonResponse(
                    {
                        "result": "Error",
                        "message": "Se requiere ID de comprador o cliente",
                    },
                    status=400,
                )
        else:
            return JsonResponse(
                {"result": "Error", "message": "Datos invalidos"}, status=400
            )
    return JsonResponse(
        {"result": "Error", "message": "Metodo no soportado"}, status=404
    )


def RifabyArray(request):
    data = {}
    page_number = request.GET.get("page")
    contain = request.GET.get("contain")

    if page_number is None:
        page_number = 1

    if contain is None:
        contain = "5"

    numeros = NumeroRifaDisponiblesArray.objects.get(id=1).Numeros[0:10]
    # numerosZ = NumeroRifaDisponiblesArray.objects.annotate(array_length=ArrayLenTransform('Numeros'), tags_slice=SliceTransform('Numeros', 0, 50)   ).get(id=1)
    # my_model = NumeroRifaDisponiblesArray.objects.annotate(sliced=SliceTransform('Numeros', 0, 40)).values_list('sliced', flat=True)
    # my_model= list(NumeroRifaDisponiblesArray.objects.raw(f'SELECT Id, "Numeros"[{(page_number-1)*0}:10], "idRifa_id", ARRAY_LENGTH("Numeros", 1) as array_length FROM "Rifa_numerorifadisponiblesarray" WHERE id = 1 {if contains==None "" else "AND " }'))
    # my_model= list(NumeroRifaDisponiblesArray.objects.raw(f'SELECT "un", "idRifa_id", id FROM ( select id, unnest("Numeros") as un, "idRifa_id" from public."Rifa_numerorifadisponiblesarray" ) x ;'))
    my_model = list(
        NumeroRifaDisponiblesArray.objects.raw(
            'Select  id, unnest("Numeros") as un, "idRifa_id" from "Rifa_numerorifadisponiblesarray"'
        )
    )
    md = [x.un for x in my_model if contain in x.un]

    #  numerosZ = NumeroRifaDisponiblesArray.objects.annotate( tags_slice=SliceTransform('Numeros', 0, 50)   ).get(id=1)

    #  slice_transform = functions.SliceTransformFactory('Numeros')
    # posts_with_tags_slice = NumeroRifaDisponiblesArray.objects.annotate(tags_slice=SliceTransformFactory(self='Numeros', start=0, end=50 ) )
    # n= NumeroRifaDisponiblesArray.objects.get(id=1)
    #  tags_slice = IndexTransform(1)
    # logger.info(my_model)
    # print a list number of elements

    # logger.info(my_model[0].array_length)

    cantidadRegistros = len(md)
    total_pages = cantidadRegistros / 10 + (cantidadRegistros % 10 != 0)

    data["data"] = md[(page_number - 1) * 10 : (page_number) * 10]
    data["total_pages"] = total_pages
    data["page_number"] = page_number
    data["cantidadRegistros"] = cantidadRegistros

    logger.info(data)
    # return HttpResponse(data)
    return JsonResponse(data)


def RifabyDisponibles(request):
    data = {}
    page_number = int(request.GET.get("page"))
    contain = request.GET.get("contain")
    idRifa = request.GET.get("idRifa")
    recordsByPage = int(request.GET.get("recordsByPage"))

    if idRifa is None:
        # return http response error
        return HttpResponse(status=400)

    if page_number is None:
        page_number = 1
    if recordsByPage is None:
        recordsByPage = 10
    if contain is None:
        contain = "6"

    cantidadRegistros = NumeroRifaDisponibles.objects.filter(
        idRifa=idRifa, Numero__contains=contain
    ).count()
    total_pages = cantidadRegistros / recordsByPage + (
        cantidadRegistros % recordsByPage != 0
    )

    numeros = list(
        NumeroRifaDisponibles.objects.annotate(
            numInt=Cast("Numero", output_field=IntegerField())
        )
        .filter(idRifa=idRifa, Numero__contains=contain)
        .order_by("numInt")[
            (page_number - 1) * recordsByPage : (page_number) * recordsByPage
        ]
        .values()
    )

    data["data"] = numeros
    data["page"] = page_number
    data["total_pages"] = math.trunc(total_pages)
    data["page_number"] = page_number
    data["cantidadRegistros"] = cantidadRegistros
    data["recordsByPage"] = recordsByPage

    logger.info(data)

    return JsonResponse(data)


def RifabyComprados(request):
    data = {}
    page_number = request.GET.get("page")
    contain = request.GET.get("contain")
    rifa = request.GET.get("rifa")

    if page_number is None:
        page_number = 1
    if contain is None:
        contain = "6"

    rifa = RifaModel.objects.get(Id=2)
    comprados = NumeroRifaComprados.objects.filter(idRifa=rifa.Id)
    comprados = ["1", "2", "5", "7"]

    nums = [
        str(number)
        for number in range(rifa.RangoInicial, rifa.RangoFinal + 1, rifa.Intervalo)
        if str(number) not in comprados
    ]

    cantidadRegistros = len(nums)
    total_pages = cantidadRegistros / 10 + (cantidadRegistros % 10 != 0)

    data["data"] = nums[(page_number - 1) * 10 : (page_number) * 10]
    data["total_pages"] = total_pages
    data["page_number"] = page_number
    data["cantidadRegistros"] = cantidadRegistros
    logger.info(data)

    return JsonResponse(data)


def VerificaBoletos(request):
    try:
        country_time_zone = pytz.timezone("America/Caracas")
        country_time = datetime.now(country_time_zone)
        logger.info(country_time.strftime("Date is %d-%m-%y and time is %H:%M:%S"))
        country_time_zone = pytz.timezone("America/Caracas")
        country_time = datetime.now(country_time_zone)
        data = json.load(request)
        cedula = data.get("cedula") or None
        correo = data.get("correo") or None
        id_rifa = data["Rifa"]

        Rifas = RifaModel.objects.filter(Estado=True).filter(Eliminada=False)
        Rifa = Rifas.filter(pk=id_rifa).first()
        compras = []
        numerosAprobados = []
        numerosPendientes = []
        print("verificador cedula: " + str(cedula))
        print("verificador correo: " + str(correo))

        if cedula is None and correo is None:
            return JsonResponse(
                {
                    "result": False,
                    "message": "¡Disculpe! Debe ingresar su cedula o correo para continuar",
                }
            )
        if cedula is not None:
            comprador = (
                Comprador.objects.filter(Cedula=cedula)
                .values("Nombre", "Cedula", "Correo")
                .first()
            )
            compras = list(
                Compra.objects.filter(idRifa=Rifa, idComprador__Cedula=cedula).values(
                    "Id"
                )
            )
            numerosAprobados = list(
                NumerosCompra.objects.filter(
                    idCompra__idRifa=Rifa,
                    idCompra__Estado=Compra.EstadoCompra.Pagado,
                    idCompra__idComprador__Cedula=cedula,
                ).values("Numero")
            )
            numerosPendientes = list(
                NumerosCompra.objects.filter(
                    idCompra__idRifa=Rifa,
                    idCompra__Estado=Compra.EstadoCompra.Pendiente,
                    idCompra__idComprador__Cedula=cedula,
                ).values("Numero")
            )

            context = {
                "cedula": cedula,
                "compras": compras,
                "comprador": comprador,
                "numerosAprobados": numerosAprobados,
                "numerosPendientes": numerosPendientes,
            }
            if len(compras) == 0:
                return JsonResponse(
                    {
                        "result": False,
                        "message": "¡Disculpe! No existe registro en nuestro sistema con esta cádula para esta rifa",
                    }
                )
            if len(numerosAprobados) <= 0 and len(numerosPendientes) <= 0:
                return JsonResponse(
                    {
                        "result": False,
                        "message": "Aun no tienes compras aprobadas en esta rifa",
                    }
                )
            return JsonResponse({"result": True, "data": context})
        if correo is not None:
            comprador = (
                Comprador.objects.filter(Correo=correo)
                .values("Nombre", "Cedula", "Correo")
                .first()
            )
            compras = list(
                Compra.objects.filter(idRifa=Rifa, idComprador__Correo=correo).values(
                    "Id"
                )
            )
            numerosAprobados = list(
                NumerosCompra.objects.filter(
                    idCompra__idRifa=Rifa,
                    idCompra__Estado=Compra.EstadoCompra.Pagado,
                    idCompra__idComprador__Correo=correo,
                ).values("Numero")
            )
            numerosPendientes = list(
                NumerosCompra.objects.filter(
                    idCompra__idRifa=Rifa,
                    idCompra__Estado=Compra.EstadoCompra.Pendiente,
                    idCompra__idComprador__Correo=correo,
                ).values("Numero")
            )

            context = {
                "cedula": cedula,
                "compras": compras,
                "comprador": comprador,
                "numerosAprobados": numerosAprobados,
                "numerosPendientes": numerosPendientes,
            }
            if len(compras) == 0:
                return JsonResponse(
                    {
                        "result": False,
                        "message": "¡Disculpe! No existe registro en nuestro sistema con este correo electrónico para esta rifa",
                    }
                )
            if len(numerosAprobados) <= 0 and len(numerosPendientes) <= 0:
                return JsonResponse(
                    {
                        "result": False,
                        "message": "Aun no tienes compras aprobadas en esta rifa",
                    }
                )
            return JsonResponse({"result": True, "data": context})
    except Exception as e:
        logger.info(e)
        return JsonResponse(
            {"result": False, "message": "Error al procesar la solicitud"}, status=400
        )


def RifabyCompradosArray(request):
    data = {}
    page_number = request.GET.get("page")
    contain = request.GET.get("contain")
    rifa = request.GET.get("rifa")

    if page_number is None:
        page_number = 1
    if contain is None:
        contain = "6"

    rifa = RifaModel.objects.get(Id=2)
    comprados = NumeroRifaCompradosArray.objects.get(idRifa=rifa.Id).Numeros

    nums = [
        str(number)
        for number in range(rifa.RangoInicial, rifa.RangoFinal + 1, rifa.Intervalo)
        if str(number) not in comprados
    ]

    cantidadRegistros = len(nums)
    total_pages = cantidadRegistros / 10 + (cantidadRegistros % 10 != 0)

    data["data"] = nums[(page_number - 1) * 10 : (page_number) * 10]
    data["total_pages"] = total_pages
    data["page_number"] = page_number
    data["cantidadRegistros"] = cantidadRegistros
    logger.info(data)

    return JsonResponse(data)


# endregion
# region "compra"


def CompraRifabyArrayDisponibles(request):
    comprados = ["2", "5", "7", "9"]

    disp = NumeroRifaDisponiblesArray.objects.get(idRifa=2)
    for x in comprados:
        disp.Numeros.remove(x)

    disp.save()
    return HttpResponse()


def CompraRifabyDisponibles(request):
    rifa = request.GET.get("rifa")

    if rifa is None:
        return HttpResponse("No rifa encontrada", status=400)

    comprados = ["2", "5", "7", "9"]
    disp = NumeroRifaDisponibles.objects.filter(idRifa=rifa, Numero__in=comprados)

    if disp.count() != len(comprados):
        logger.info(disp.count())
        logger.info(len(comprados))

        return HttpResponse("Hay numeros no disponibles", status=400)

    disp = NumeroRifaDisponibles.objects.filter(
        idRifa=rifa, Numero__in=comprados
    ).delete()

    return HttpResponse()


def CompraRifabyComprados(request):
    compradosL = ["2", "5", "7", "9", "66"]
    rifa = RifaModel.objects.get(Id=2)
    for x in compradosL:
        comprados = NumeroRifaComprados(idRifa=rifa, Numero=x)
        comprados.save()
    return HttpResponse()


def CompraRifabyCompradosArray(request):
    compradosL = ["2", "5", "7", "9", "66"]

    comprados = NumeroRifaCompradosArray.objects.get(idRifa=2)
    for x in compradosL:
        comprados.Numeros.append(x)
        logger.info(x)

    comprados.save()

    return HttpResponse()


# endregion
# region Consulta
def ConsultaRifabyDisponiplesOLD(request):
    num = request.GET.get("num")
    rifa = request.GET.get("rifa")

    if num is None or rifa is None:
        return HttpResponse(status=400)
    consultaNum = NumeroRifaDisponibles.objects.filter(Numero=num, idRifa=rifa).count()

    if consultaNum == 0:
        return JsonResponse({"result": False})
    else:
        return JsonResponse({"result": True})


def ConsultaRifabyDisponiples(request):
    nums = request.GET.get("num")
    rifa = request.GET.get("rifa")
    idorden = request.GET.get("orden")
    Orden = OrdenesReservas.objects.get(Id=idorden)
    numeroReserva = NumeroRifaReservadosOrdenes.objects.filter(idOrden=Orden)

    if nums is None or rifa is None:
        return JsonResponse(
            {"result": False, "data": "No se recibieron los parametros necesarios"}
        )
    nums = int(nums)

    consultaNum = NumeroRifaDisponibles.objects.filter(idRifa=rifa)
    rifaC = RifaModel.objects.get(Id=rifa)

    if (
        rifaC.TotalComprados + nums > rifaC.TotalNumeros
        or rifaC.TotalComprados == rifaC.TotalNumeros
    ):
        return JsonResponse(
            {
                "result": False,
                "data": "El numero de numeros a comprar es mayor a los disponibles",
            }
        )

    if consultaNum.count() == 0 or consultaNum.count() < nums:
        return JsonResponse(
            {
                "result": False,
                "data": "El numero de numeros a comprar es mayor a los disponibles",
            }
        )

    return JsonResponse({"result": True, "data": []})


def ConsultaRifabyDisponiplesTodos(request):
    rifa = request.GET.get("rifa")

    data = {}

    consultaNum = list(NumeroRifaDisponibles.objects.filter(idRifa=rifa).values())
    data["data"] = consultaNum
    return JsonResponse({"result": data})


def ConsultaRifabyDisponiplesLista(request):
    data = json.load(request)
    nums = data["Numbers"]
    rifa = data["Rifa"]
    if nums is None or rifa is None:
        return HttpResponse(status=400)

    consulta = ConsultaRifabyDisponiplesListaMethod(nums, rifa)
    return JsonResponse({"result": consulta["result"], "data": consulta["data"]})

    if nums is None or rifa is None:
        return HttpResponse(status=400)

    dataReturn = []
    if nums:
        for x in nums:
            consultaNum = NumeroRifaDisponibles.objects.filter(
                idRifa=rifa, Numero=x["num"]
            ).count()
            if consultaNum == 0:
                dataReturn.append(x)

    NumerosTomados = True if len(dataReturn) > 0 else False

    return JsonResponse({"result": NumerosTomados, "data": dataReturn})


def ConsultaRifabyDisponiplesListaV3(request):
    data = json.load(request)
    nums = data["Numbers"]
    rifa = data["Rifa"]
    if nums is None or rifa is None:
        return HttpResponse(status=400)
    rifaC = RifaModel.objects.get(Id=rifa)
    # si numero esta en el minimo maximo, y disponibles
    if nums > rifaC.MaxCompra:
        return JsonResponse(
            {
                "result": False,
                "data": "El numero de numeros a comprar es mayor rango permitido",
            }
        )
    if nums < rifaC.MinCompra:
        return JsonResponse(
            {
                "result": False,
                "data": "El numero de numeros a comprar es menor rango permitido",
            }
        )
    if nums > NumeroRifaDisponibles.objects.filter(idRifa=rifa).count():
        return JsonResponse(
            {
                "result": False,
                "data": "El numero de numeros a comprar es mayor a los disponibles",
            }
        )

    consultaNum = NumeroRifaDisponibles.objects.filter(idRifa=rifa)
    rifaC = RifaModel.objects.get(Id=rifa)

    if (
        rifaC.TotalComprados + nums > rifaC.TotalNumeros
        or rifaC.TotalComprados == rifaC.TotalNumeros
    ):
        return JsonResponse(
            {
                "result": False,
                "data": "El numero de numeros a comprar es mayor a los disponibles",
            }
        )

    if consultaNum.count() == 0 or consultaNum.count() < nums:
        return JsonResponse(
            {
                "result": False,
                "data": "El numero de numeros a comprar es mayor a los disponibles",
            }
        )

    return JsonResponse({"result": True, "data": []})


def ConsultaRifabyDisponiple(request):
    data = json.load(request)
    num = data["Number"]
    rifa = data["Rifa"]
    if num is None or rifa is None:
        return HttpResponse(status=400)

    consultaNum = NumeroRifaDisponibles.objects.filter(idRifa=rifa, Numero=num)

    if consultaNum.count() == 0:
        return JsonResponse(
            {"result": False, "data": "El numero no se encuentra disponible"}
        )

    return JsonResponse({"result": True, "data": []})


def ConsultaRifabyDisponiplesListaMethod(nums, rifa):
    dataReturn = []
    if nums:
        for x in nums:
            consultaNum = NumeroRifaDisponibles.objects.filter(
                idRifa=rifa, Numero=x["num"]
            ).count()
            if consultaNum == 0:
                dataReturn.append(x)

    NumerosTomados = True if len(dataReturn) > 0 else False
    return {"result": NumerosTomados, "data": dataReturn}


def ConsultaRifabyDisponiplesArray(request):
    return HttpResponse


def ConsultaRifabyComprados(request):
    return HttpResponse


def ConsultaRifabyCompradosArray(request):
    return HttpResponse


# endregion


# Save Compra
def CompraNumerosByDisponiblesV2(request):
    if request.method == "POST":
        # load form data
        numbers = request.POST.get("numbers")
        rifa = request.POST.get("idRifa")

        # get random numbers from numerosbydisponibles
        disp = NumeroRifaDisponibles.objects.filter(idRifa=rifa).order_by("?")[:numbers]


def CompraNumerosByDisponibles(request):
    if request.method == "POST":
        data = json.load(request)
        nums = data["Numbers"]
        rifaId = data["Rifa"]
        user = data["User"]

        logger.info(nums)
        logger.info(user)
        arrayNums = [x["num"] for x in nums]
        logger.info(arrayNums)

        if rifaId is None:
            return HttpResponse("No rifa encontrada", status=400)
        rifa = RifaModel.objects.get(Id=rifaId)
        comprados = nums
        disp = NumeroRifaDisponibles.objects.filter(idRifa=rifa, Numero__in=arrayNums)

        if disp.count() != len(arrayNums):
            logger.info(disp.count())
            logger.info(len(arrayNums))

            return HttpResponse("Hay numeros no disponibles", status=400)

        logger.info(disp.count())
        logger.info(len(arrayNums))
        try:
            with transaction.atomic():
                for x in disp:
                    x.delete()
                context = {
                    "nums": arrayNums,
                    "rifa": rifa,
                    "user": user,
                    "totalpago": len(arrayNums) * rifa.Precio,
                    "len": len(arrayNums),
                    "whatsapp_config": Settings.objects.filter(
                        code="PHONE_CLIENT"
                    ).first(),
                    "percent_config": Settings.objects.filter(
                        code="HIDE_TICKET_COUNT"
                    ).first(),
                }
                logger.info(context)
                body = render_to_string("Rifa/Correo.django", context)
                plain_message = body
                logger.info(user["Correo"])
                with get_connection(
                    host=settings.EMAIL_HOST,
                    port=settings.EMAIL_PORT,
                    username=settings.EMAIL_HOST_USER,
                    password=settings.EMAIL_HOST_PASSWORD,
                    use_tls=settings.EMAIL_USE_TLS,
                ) as connection:
                    subject = f"Felicidades por tu Compra {user['Nombre']}"
                    email_from = settings.EMAIL_HOST_USER
                    recipient_list = [user["Correo"]]
                    message = plain_message
                    email = EmailMessage(
                        subject,
                        message,
                        email_from,
                        recipient_list,
                        connection=connection,
                    )
                    email.content_subtype = "html"
                    email.send()
        except IntegrityError:
            return HttpResponse("Ocurrio un error", status=400)

    return HttpResponse("")


def CompraNumerosByDisponiblesMethod(dataM):
    data = dataM
    nums = data["Numbers"]
    rifaId = data["Rifa"]
    user = data["User"]

    logger.info(nums)
    logger.info(user)
    arrayNums = [x["num"] for x in nums]
    logger.info(arrayNums)

    if rifaId is None:
        return False
        return HttpResponse("No rifa encontrada", status=400)
    if len(list(RifaModel.objects.filter(Id=rifaId).values())) == 0:
        logger.info("No rifa encontrada")
        return False
        return HttpResponse("No rifa encontrada", status=400)

    rifa = RifaModel.objects.get(Id=rifaId)
    country_time_zone = pytz.timezone("America/Caracas")
    country_time = datetime.now(country_time_zone)
    if country_time >= rifa.FechaSorteo:
        if rifa.Extension == False:
            logger.info("La rifa a la que intenta comprar ya no esta disponible")
            return False
            return HttpResponse(
                "Error, la rifa a la que intenta comprar ya no esta disponible",
                status=400,
            )

    if len(list(data["Numbers"])) < rifa.MinCompra:
        logger.info(
            "Error,la cantidad de numeros a comprar es menor a la minima permitida "
        )
        return False
        return HttpResponse(
            "Error,la cantidad de numeros a comprar es menor a la minima permitida ",
            status=400,
        )

    comprados = nums
    disp = NumeroRifaDisponibles.objects.filter(idRifa=rifa, Numero__in=arrayNums)
    """  

        if disp.count() != len(arrayNums):
            logger.info(disp.count())
            logger.info(len(arrayNums))
            logger.info("Hay numeros no disponibles")
            return False
            return HttpResponse("Hay numeros no disponibles", status=400)
            """
    logger.info(disp.count())
    logger.info(len(arrayNums))
    try:
        with transaction.atomic():
            for x in disp:
                #  x.delete()
                logger.info(x)

            context = {
                "nums": arrayNums,
                "rifa": rifa,
                "reference": data["Orden"]["orden"],
                "user": user,
                "totalpago": len(arrayNums) * rifa.Precio,
                "len": len(arrayNums),
                "whatsapp_config": Settings.objects.filter(code="PHONE_CLIENT").first(),
                "percent_config": Settings.objects.filter(
                    code="HIDE_TICKET_COUNT"
                ).first(),
            }
            logger.info(context)
            rifa.TotalComprados = rifa.TotalComprados + len(arrayNums)
            rifa.save()
            body = render_to_string("Rifa/Correo.django", context)
            plain_message = body
            logger.info(user["Correo"])
            with get_connection(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                use_tls=settings.EMAIL_USE_TLS,
            ) as connection:
                subject = f"Felicidades por tu Compra {user['Nombre']}"
                email_from = settings.EMAIL_HOST_USER
                recipient_list = [user["Correo"]]
                message = plain_message
                email = EmailMessage(
                    subject, message, email_from, recipient_list, connection=connection
                )
                email.content_subtype = "html"
                email.send()
    except IntegrityError:
        logger.info("Ocurrio un error")
        return False

    return True


# function to send email


async def sendEmail(user, numeros):
    logger.info("aq")

    body = await EmailBody(user, numeros)
    plain_message = body
    logger.info(user["Correo"])
    with get_connection(
        host=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        username=settings.EMAIL_HOST_USER,
        password=settings.EMAIL_HOST_PASSWORD,
        use_tls=settings.EMAIL_USE_TLS,
    ) as connection:
        subject = f"Felicidades por tu Compra {user['Nombre']}"
        email_from = settings.EMAIL_HOST_USER
        recipient_list = [user["Correo"]]
        message = plain_message

    try:
        email = EmailMessage(
            subject, message, email_from, recipient_list, connection=connection
        )
        email.content_subtype = "html"
        email.send()
    except Exception as e:
        return HttpResponse("")

    return HttpResponse("")


async def EmailBody(user, nums):
    template = loader.get_template("Rifa/Correo.django")
    context = {
        "nums": nums,
        "user": user,
        "whatsapp_config": Settings.objects.filter(code="PHONE_CLIENT").first(),
        "percent_config": Settings.objects.filter(code="HIDE_TICKET_COUNT").first(),
    }

    return render_to_string("Rifa/Correo.django", context)
    template
    context = {"form": request}
    return HttpResponse(template.render(context, request))


# region S3
# method to upload to S3 and get link


def upload_to_s3(file, bucket_name, acl="public-read"):
    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

    try:
        s3.upload_fileobj(
            file,
            bucket_name,
            file.name,
            ExtraArgs={"ACL": acl, "ContentType": file.content_type},
        )
    except Exception as e:
        logger.info(f"Something Happened: {e}")
        return e

    return "{}{}".format(settings.AWS_S3_CUSTOM_DOMAIN, file.name)


# methond to call auth api y get token


def get_token():
    url = "https://apiplaza.celupagos.com/auth"
    data = {
        "username": settings.EKIIPAGO["username"],
        "platformId": settings.EKIIPAGO["platformId"],
        "password": settings.EKIIPAGO["password"],
    }
    # CRÍTICO: Usar sesión con context manager para cerrar conexión HTTP correctamente
    with requests.Session() as session:
        try:
            r = session.post(url, data=data, timeout=30)
            r.raise_for_status()
            return r.json()["access_token"]
        except Exception as e:
            logger.error(f"Error en get_token(): {str(e)}")
            raise


def ReenviarComprobante(request):
    if request.method == "POST":
        data = json.load(request)

        try:
            id = data["id"]
            CompraObj = Compra.objects.get(Id=id)
            arr = [
                x["Numero"]
                for x in NumerosCompra.objects.filter(idCompra=CompraObj).values(
                    "Numero"
                )
            ]
            logger.info(arr)
            context = {
                "nums": arr,
                "rifa": CompraObj.idRifa,
                "reference": CompraObj.Id,
                "user": CompraObj.idComprador,
                "totalpago": CompraObj.TotalPagado,
                "len": CompraObj.NumeroBoletos,
                "compra": CompraObj,
                "whatsapp_config": Settings.objects.filter(code="PHONE_CLIENT").first(),
                "percent_config": Settings.objects.filter(
                    code="HIDE_TICKET_COUNT"
                ).first(),
            }
            logger.info(context)
            texto = (
                f"¡Felicidades "
                + CompraObj.idComprador.Nombre
                + "! Tu compra ["
                + str(CompraObj.Id)
                + "] ha sido aprobada, puedes consultar tus boletos en el siguiente enlace, asegúrate de no compartirlo con nadie. "
                + settings.URL
                + "/Comprobante/"
                + str(CompraObj.hash)
            )
            numero = CompraObj.idComprador.NumeroTlf
            numero = re.sub(r"\s+", "", numero.strip())

            enviarWhatsapp(texto, numero)
            body = render_to_string("Rifa/Correo.django", context)
            plain_message = body
            with get_connection(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                use_tls=settings.EMAIL_USE_TLS,
            ) as connection:
                subject = f"Tu compra ha sido aprobada {CompraObj.idComprador.Nombre}"
                email_from = settings.EMAIL_HOST_USER
                recipient_list = [CompraObj.idComprador.Correo]
                message = plain_message
                email = EmailMessage(
                    subject, message, email_from, recipient_list, connection=connection
                )
                email.content_subtype = "html"
                email.send()
            return JsonResponse({"message": "Éxito", "status": 200}, status=200)
        except Exception as e:
            logger.info(4)

            logger.info(e)
            return JsonResponse({"message": "Error", "status": 400}, status=400)


@shared_task()
def sendEmail(nombre, correo, idRifa, compraId):
    Logger.objects.create(
        date=datetime.now(),
        description=f"Running Celery {correo} {idRifa} ",
        evento="Celery Correo",
    )
    rifa = RifaModel.objects.get(Id=idRifa)

    # validar compra
    compra = Compra.objects.get(Id=compraId)
    # get numeros compra
    arr = [
        x["Numero"]
        for x in NumerosCompra.objects.filter(idCompra=compra).values("Numero")
    ]
    # if 0 rechazar comprar
    if len(arr) == 0:
        compra.Estado = Compra.EstadoCompra.Rechazado
        compra.save()
        RifaC = RifaModel.objects.get(Id=compra.idRifa.Id)
        loggerRechazo = LoggerAprobadoRechazo.objects.create(
            date=datetime.now(),
            description=f"Compra Rechazada {compra.Id} 0 numeros",
            evento="Rechazada 0",
            idCompra=compra.Id,
        )
        loggerRechazo.save()
        compra.recuperado = True
        compra.save()
        body = render_to_string(
            "Rifa/CorreoRechazo.django",
            {
                "whatsapp_config": Settings.objects.filter(code="PHONE_CLIENT").first(),
                "percent_config": Settings.objects.filter(
                    code="HIDE_TICKET_COUNT"
                ).first(),
            },
        )
        print(settings.EMAIL_HOST_USER)
        print(settings.EMAIL_HOST_PASSWORD)
        plain_message = body
        with get_connection(
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_HOST_USER,
            password=settings.EMAIL_HOST_PASSWORD,
            use_tls=settings.EMAIL_USE_TLS,
        ) as connection:
            subject = f"Detalles sobre tu Compra {compra.idComprador.Nombre}"
            email_from = settings.EMAIL_HOST_USER
            recipient_list = [compra.idComprador.Correo]
            message = plain_message
            email = EmailMessage(
                subject, message, email_from, recipient_list, connection=connection
            )
            email.content_subtype = "html"
            email.send()

    body = render_to_string(
        "Rifa/CorreoCompra.django",
        {
            "rifa": rifa,
            "whatsapp_config": Settings.objects.filter(code="PHONE_CLIENT").first(),
            "percent_config": Settings.objects.filter(code="HIDE_TICKET_COUNT").first(),
        },
    )
    print(settings.EMAIL_HOST_USER)
    print(settings.EMAIL_HOST_PASSWORD)
    plain_message = body
    with get_connection(
        host=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        username=settings.EMAIL_HOST_USER,
        password=settings.EMAIL_HOST_PASSWORD,
        use_tls=settings.EMAIL_USE_TLS,
    ) as connection:
        subject = f"Felicidades por tu Compra {nombre}"
        email_from = settings.EMAIL_HOST_USER
        recipient_list = [correo]
        message = plain_message
        email = EmailMessage(
            subject, message, email_from, recipient_list, connection=connection
        )
        email.content_subtype = "html"
        email.send()


@permission_required("Rifa.change_compra", raise_exception=True)
def aprobarCompra(request):
    if request.method == "POST":
        try:
            with transaction.atomic():
                data = json.load(request)
                id = data["id"]
                logger.info(id)
                CompraObj = Compra.objects.get(Id=id)
                CompraObj.Estado = Compra.EstadoCompra.Pagado
                country_time_zone = pytz.timezone("America/Caracas")
                country_time = datetime.now(country_time_zone)

                CompraObj.FechaEstado = country_time
                CompraObj.save()

                # array numbers
                arr = [
                    x["Numero"]
                    for x in NumerosCompra.objects.filter(idCompra=CompraObj).values(
                        "Numero"
                    )
                ]
                logger.info(arr)

                # Actualizar TotalComprados y crear NumeroRifaComprados si no existen
                rifa = CompraObj.idRifa
                numeros_compra = NumerosCompra.objects.filter(idCompra=CompraObj)

                # Verificar si ya están en NumeroRifaComprados
                numeros_ya_comprados = NumeroRifaComprados.objects.filter(
                    idRifa=rifa, Numero__in=arr
                ).values_list("Numero", flat=True)

                # Crear registros solo para números que no están ya comprados
                numeros_a_agregar = []
                for num in arr:
                    if num not in numeros_ya_comprados:
                        NumeroRifaComprados.objects.create(idRifa=rifa, Numero=num)
                        numeros_a_agregar.append(num)

                # Actualizar TotalComprados solo si agregamos números nuevos
                if numeros_a_agregar:
                    rifa.TotalComprados = F("TotalComprados") + len(numeros_a_agregar)
                    rifa.save()
                    logger.info(
                        f"Aprobacion manual: Actualizados {len(numeros_a_agregar)} numeros en TotalComprados para rifa {rifa.Id}"
                    )
                logAprobado = LoggerAprobadoRechazo.objects.create(
                    date=datetime.now(),
                    description=f"Compra Aprobada {CompraObj.Id}",
                    evento="Aprobada",
                    idCompra=CompraObj,
                )
                logAprobado.save()
                context = {
                    "nums": arr,
                    "rifa": CompraObj.idRifa,
                    "reference": CompraObj.Id,
                    "user": CompraObj.idComprador,
                    "totalpago": CompraObj.TotalPagado,
                    "len": CompraObj.NumeroBoletos,
                    "compra": CompraObj,
                    "whatsapp_config": Settings.objects.filter(
                        code="PHONE_CLIENT"
                    ).first(),
                    "percent_config": Settings.objects.filter(
                        code="HIDE_TICKET_COUNT"
                    ).first(),
                }
                logger.info(context)
                logger.info(settings.URL)
                texto = (
                    f"¡Felicidades "
                    + CompraObj.idComprador.Nombre
                    + "! Tu compra ["
                    + str(CompraObj.Id)
                    + "] ha sido aprobada, puedes consultar tus boletos en el siguiente enlace, asegúrate de no compartirlo con nadie. "
                    + settings.URL
                    + "/Comprobante/"
                    + str(CompraObj.hash)
                )
                numero = CompraObj.idComprador.NumeroTlf
                numero = re.sub(r"\s+", "", numero.strip())
                # enviarWhatsapp(texto, numero)
                # body = render_to_string('Rifa/Correo.django', context)
                # plain_message = body
                # with get_connection(
                #     host=settings.EMAIL_HOST,
                #     port=settings.EMAIL_PORT,
                #     username=settings.EMAIL_HOST_USER,
                #     password=settings.EMAIL_HOST_PASSWORD,
                #     use_tls=settings.EMAIL_USE_TLS
                # ) as connection:
                #     subject = f'Tu compra ha sido aprobada {CompraObj.idComprador.Nombre}'
                #     email_from = settings.EMAIL_HOST_USER
                #     recipient_list = [CompraObj.idComprador.Correo]
                #     message = plain_message
                #     email = EmailMessage(subject, message, email_from,
                #                         recipient_list, connection=connection)
                #     email.content_subtype = 'html'
                #     email.send()
                #     base=""
                #     if settings.DEBUG==True:
                #      base= "http://127.0.0.1:8000/"
                #     else:
                #         base= settings.URL
                #     qr_text=base+"/Comprobante/"+str(CompraObj.hash)

                #     qr_image = qrcode.make(qr_text, box_size=15)

                #     img_dir = os.path.join(settings.MEDIA_ROOT, 'qrcode')
                #     os.makedirs(img_dir, exist_ok=True)  # Create the directory if it doesn't exist

                #     # Define the complete path to save the image
                #     img_path = os.path.join(img_dir, str(CompraObj.hash)+'.png')

                #     # Save the QR code image
                #     qr_image.save(img_path)
                #     CompraObj.qr=os.path.relpath(img_path, settings.MEDIA_ROOT)
                #     CompraObj.save()

                return JsonResponse({"message": "Éxito", "status": 200}, status=200)
            return JsonResponse({"message": "Error", "status": 400}, status=400)
        except Exception as e:
            logger.info(e)
            return JsonResponse({"message": "Error", "status": 400}, status=400)


def deleteComprobantes(request):
    compras = Compra.objects.filter(idRifa=18)
    for x in compras:
        # delete local file

        logger.info(
            "/opt/bitnami/projects/PROJECT/Proyecto-Ballena/proyectoBallena"
            + x.Comprobante.url
        )

        try:
            if os.path.exists(
                "/opt/bitnami/projects/PROJECT/Proyecto-Ballena/proyectoBallena"
                + x.Comprobante.url
            ):
                logger.info("file exist")
                os.remove(
                    "/opt/bitnami/projects/PROJECT/Proyecto-Ballena/proyectoBallena"
                    + x.Comprobante.url
                )
            # if file exist

        except Exception as e:
            logger.info(e)
            pass


def enviarWhatsapp(texto, numero):
    formatted_number = re.sub(r"[^0-9]", "", numero)
    # CRÍTICO: Usar sesión con context manager para cerrar conexión HTTP correctamente
    with requests.Session() as session:
        try:
            url = "http://api.message.sinvad.lat/api/Message/AddMessagestoQueue"
            payload = [
                {
                    "attachments": [],
                    "subject": "",
                    "to": [formatted_number],
                    "message": texto,
                    "typeMessage": 0,
                }
            ]

            headers = {
                "Content-Type": "application/json",
                "Authorization": "E37C6F0847DB4E6205787C8AE89AC670540DD97A86DB53ACB4BC6BE961C76D70A5CC68055CF2E1CCD35C45197DA398425CACEBA217E0D1529AFE8AA8EE754A73",
                "SiteAllowed": "NOURL",
                "UserName": "JALEXZANDER",
                "UserApp": "_LOGINVALUSER_",
            }

            res = session.post(url, headers=headers, json=payload, timeout=30)
            res.raise_for_status()
            logger.info(res.text)
        except Exception as e:
            logger.error(f"Error en enviarWhatsapp(): {str(e)}")
            return
    return


def generate_random_text(length):
    letters = string.ascii_letters
    return "".join(random.choice(letters) for i in range(length))


def testWhatsapp():
    conn = None
    try:
        conn = http.client.HTTPConnection("sinvadmessage.sytes.net", 80)
        # ramdom unique text
        random_text = generate_random_text(10)

        payload = [
            {
                "attachments": [],
                "subject": "",
                "to": ["04147945595"],
                "message": random_text,
                "typeMessage": 0,
            }
        ]

        headers = {
            "Content-Type": "application/json",
            "Authorization": "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJOT1VSTCIsInVzciI6IkpBTEVYWkFOREVSIiwiZXhwIjo2NDAwMDk3MjgwMDAwMDAwMDAsImR0YiI6IlNJTlZBRF9NRVNTQUdFX0pBTEVYWkFOREVSIiwiY2JvIjoiIiwicHJjIjoiXCJ7XFxcIkFMTFxcXCI6ZmFsc2UsXFxcIkRBU0hCT0FSRFxcXCI6ZmFsc2UsXFxcIlNLVVxcXCI6ZmFsc2UsXFxcIkNMQVNJRklDQVRJT05TXFxcIjpmYWxzZSxcXFwiUFJFU0VOVEFUSU9OU1xcXCI6ZmFsc2UsXFxcIlRBWEVTXFxcIjpmYWxzZSxcXFwiV0hBUkVIT1VTRVxcXCI6ZmFsc2UsXFxcIkNMSUVOVFNcXFwiOmZhbHNlLFxcXCJTRUxMRVJTXFxcIjpmYWxzZSxcXFwiUEFZTUVOVENPTkRJVElPTlNcXFwiOmZhbHNlLFxcXCJPUkRFUlNcXFwiOmZhbHNlLFxcXCJQQVlNRU5UU1xcXCI6ZmFsc2UsXFxcIkdFTlRPS0VOVkFMSURBVElPTlxcXCI6ZmFsc2UsXFxcIk1FU1NBR0VTXFxcIjp0cnVlfVwiIn0.3RC49sXJ4I_z8dmHwU7xt9_trgvOamJjSkMLaupOIkF-6y2n27R9yuNXXAFbxQlMgQh27QwIWaqqLuB9Flsdig",
            "SiteAllowed": "NOURL",
            "UserName": "JALEXZANDER",
            "UserApp": "_LOGINVALUSER_",
        }

        conn.request(
            "POST", "/api/Message/AddMessagestoQueue", json.dumps(payload), headers
        )

        res = conn.getresponse()
        data = res.read()
        return data.decode("utf-8")
    except Exception as e:
        return str(e)
    finally:
        # CRÍTICO: Cerrar la conexión HTTP siempre, incluso si hay error
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def rechazarCompra(request):
    if request.method == "POST":
        with transaction.atomic():  # create comprador
            data = json.load(request)
            id = data["id"]
            logger.info(id)
            CompraObj = (
                Compra.objects.select_for_update()
                .exclude(Estado=Compra.EstadoCompra.Rechazado)
                .filter(Id=id)
            )
            if len(CompraObj) == 0:
                raise Exception("Compra no encontrada")
            CompraObj = CompraObj[0]
            CompraObj.Estado = Compra.EstadoCompra.Rechazado
            country_time_zone = pytz.timezone("America/Caracas")
            country_time = datetime.now(country_time_zone)

            CompraObj.FechaEstado = country_time
            CompraObj.save()
            RifaC = RifaModel.objects.get(Id=CompraObj.idRifa.Id)
            numerosCompra = NumerosCompra.objects.filter(idCompra=CompraObj)
            loggerRechazo = LoggerAprobadoRechazo.objects.create(
                date=datetime.now(),
                description=f"Compra Rechazada {CompraObj.Id}",
                evento="Rechazada",
                idCompra=CompraObj,
            )
            loggerRechazo.save()
            for x in numerosCompra:
                logger.info(x.Numero)
                NumeroRifaDisponibles.objects.create(Numero=x.Numero, idRifa=RifaC)
            RifaC.TotalComprados = F("TotalComprados") - CompraObj.NumeroBoletos
            RifaC.save()
            CompraObj.recuperado = True
            CompraObj.save()
            body = render_to_string(
                "Rifa/CorreoRechazo.django",
                {
                    "whatsapp_config": Settings.objects.filter(
                        code="PHONE_CLIENT"
                    ).first(),
                    "percent_config": Settings.objects.filter(
                        code="HIDE_TICKET_COUNT"
                    ).first(),
                },
            )
            logger.info(settings.EMAIL_HOST_USER)
            logger.info(settings.EMAIL_HOST_PASSWORD)
            plain_message = body
            with get_connection(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                use_tls=settings.EMAIL_USE_TLS,
            ) as connection:
                subject = f"Detalles sobre tu Compra {CompraObj.idComprador.Nombre}"
                email_from = settings.EMAIL_HOST_USER
                recipient_list = [CompraObj.idComprador.Correo]
                message = plain_message
                email = EmailMessage(
                    subject, message, email_from, recipient_list, connection=connection
                )
                email.content_subtype = "html"
                email.send()
            return JsonResponse({"message": "Éxito", "status": 200}, status=200)


def ComprarRifaOld(request):
    if request.method == "POST":
        # form uploadfile
        form = UploadFileForm(request.POST, request.FILES)
        logger.info(f"Archivos {request.FILES}")
        logger.info(f"Campos {request.POST}")
        logger.info(f"nombre {request.POST.get('nombre')}")
        logger.info(
            f"Formulario válido {form.is_valid()}",
        )
        logger.info(f"Formulario válido {form.errors}")
        if form.is_valid():
            idRifa = form.cleaned_data["idRifa"]
            try:
                try:
                    rifa = RifaModel.objects.get(Id=idRifa)
                except:
                    return HttpResponse(
                        "Error, la rifa a la que intenta comprar no existe", status=400
                    )
                # valida estado y publicacion
                if rifa.Estado == False or rifa.Eliminada == True:
                    return JsonResponse(
                        {"message": "Rifa no dispoible", "status": 422}, status=422
                    )
                # valida rifa fecha
                country_time_zone = pytz.timezone("America/Caracas")
                country_time = datetime.now(country_time_zone)
                if country_time >= rifa.FechaSorteo:
                    if rifa.Extension == False:
                        return JsonResponse(
                            {"message": "Rifa expirada", "status": 422}, status=422
                        )
                if (
                    form.cleaned_data["numeros"] < rifa.MinCompra
                    or form.cleaned_data["numeros"] > rifa.MaxCompra
                ):
                    return JsonResponse(
                        {"message": "Cantidad invalida", "status": 422}, status=422
                    )

                if (
                    form.cleaned_data["numeros"]
                    > NumeroRifaDisponibles.objects.filter(idRifa=idRifa).count()
                ):
                    return JsonResponse(
                        {"message": "Hay numeros no disponibles", "status": 422},
                        status=422,
                    )

                # validate file size 4mb
                if request.FILES["file"].size > 4194304:
                    return JsonResponse(
                        {"message": "Archivo muy grande", "status": 422}, status=422
                    )
                # validate file extension pdf and images
                if (
                    not request.FILES["file"].name.endswith(".pdf")
                    and not request.FILES["file"].name.endswith(".jpg")
                    and not request.FILES["file"].name.endswith(".png")
                    and not request.FILES["file"].name.endswith(".jpeg")
                ):
                    return JsonResponse(
                        {"message": "Archivo no valido", "status": 422}, status=422
                    )
                # validate distint referece
                #    if Compra.objects.filter(Referencia=form.cleaned_data['referencia']).count() > 0:
                #       return JsonResponse({"message": "Referencia ya existe", "status": 422}, status=422)

                with transaction.atomic():  # create comprador
                    comprador = Comprador()
                    comprador.Nombre = form.cleaned_data["nombre"]
                    comprador.Correo = form.cleaned_data["correo"]
                    comprador.NumeroTlf = form.cleaned_data["numeroTlf"]
                    # comprador.Direccion=form.cleaned_data['direccion']
                    comprador.Cedula = form.cleaned_data["cedula"]
                    comprador.save()

                    # save file locally

                    # get random numbers from numerosbydisponibles
                    idRifa = form.cleaned_data["idRifa"]
                    disp = NumeroRifaDisponibles.objects.filter(
                        idRifa=form.cleaned_data["idRifa"]
                    ).order_by("?")[: form.cleaned_data["numeros"]]

                    # create compra
                    compra = Compra()
                    compra.idComprador = comprador
                    compra.idRifa = RifaModel.objects.get(
                        Id=form.cleaned_data["idRifa"]
                    )
                    compra.Comprobante = request.FILES["file"]
                    # last tasa
                    compra.TasaBS = Tasas.objects.latest("id").tasa
                    compra.Referencia = form.cleaned_data["referencia"]
                    compra.FechaCompra
                    country_time_zone = pytz.timezone("America/Caracas")
                    country_time = datetime.now(country_time_zone)
                    compra.FechaCompra = country_time
                    compra.NumeroBoletos = form.cleaned_data["numeros"]
                    compra.TotalPagado = (
                        form.cleaned_data["numeros"] * compra.idRifa.Precio
                    )
                    compra.save()
                    for x in disp:
                        NumeroRifaComprados.objects.create(
                            idRifa=RifaModel.objects.get(Id=idRifa), Numero=x.Numero
                        )
                        NumerosCompra.objects.create(idCompra=compra, Numero=x.Numero)
                        NumeroRifaDisponibles.objects.get(
                            idRifa=idRifa, Numero=x.Numero
                        ).delete()
                    rifa.TotalComprados = (
                        F("TotalComprados") + form.cleaned_data["numeros"]
                    )
                    rifa.save()
                    body = render_to_string(
                        "Rifa/CorreoCompra.django",
                        {
                            "rifa": rifa,
                            "whatsapp_config": Settings.objects.filter(
                                code="PHONE_CLIENT"
                            ).first(),
                            "percent_config": Settings.objects.filter(
                                code="HIDE_TICKET_COUNT"
                            ).first(),
                        },
                    )
                    logger.info(settings.EMAIL_HOST_USER)
                    logger.info(settings.EMAIL_HOST_PASSWORD)
                    plain_message = body
                    with get_connection(
                        host=settings.EMAIL_HOST,
                        port=settings.EMAIL_PORT,
                        username=settings.EMAIL_HOST_USER,
                        password=settings.EMAIL_HOST_PASSWORD,
                        use_tls=settings.EMAIL_USE_TLS,
                    ) as connection:
                        subject = (
                            f"Felicidades por tu Compra {form.cleaned_data['nombre']}"
                        )
                        email_from = settings.EMAIL_HOST_USER
                        recipient_list = [form.cleaned_data["correo"]]
                        message = plain_message
                        email = EmailMessage(
                            subject,
                            message,
                            email_from,
                            recipient_list,
                            connection=connection,
                        )
                        email.content_subtype = "html"
                        email.send()
                    return JsonResponse({"message": "Éxito", "status": 200}, status=200)
            except Exception as ex:
                logger.info(ex)
                return JsonResponse(
                    {"message": "Error en el servidor", "status": 500}, status=500
                )
        else:
            return JsonResponse(
                {
                    "errors": form.errors.as_json(),
                    "message": "error de validacion",
                    "status": 422,
                },
                status=422,
            )


def registerlog(request):
    # wait 50 seconds
    time.sleep(5)
    # NONCE = str(int(time.time() * 1000))
    # Logger.objects.create(date=datetime.now(), description=f"Probando Estres{NONCE} ")
    jeje.delay()
    return JsonResponse({"message": "Éxito", "status": 200}, status=200)


@shared_task
def jeje():
    time.sleep(10)
    NONCE = str(int(time.time() * 1000))
    Logger.objects.create(
        date=datetime.now(), description=f"Probando Celery {NONCE}", evento="Celery"
    )


def ComprarRifa(request):
    # CRÍTICO: Cerrar conexiones de BD en caso de error para evitar acumulación
    try:
        if request.method == "POST":
            # form uploadfile
            form = SecondFileForm(request.POST, request.FILES)
            country_time_zone = pytz.timezone("America/Caracas")
            country_time = datetime.now(country_time_zone)
            if form.is_valid():
                try:
                    idOrden = form.cleaned_data["idOrden"]

                    try:
                        print(country_time - timedelta(minutes=10))

                        ordenes = OrdenesReservas.objects.filter(
                            date__gte=country_time - timedelta(minutes=10)
                        )
                        orden = ordenes.get(Id=idOrden)
                    except:
                        return JsonResponse(
                            {"message": "Error, la orden no existe", "status": 400},
                            status=422,
                        )

                    # if orden is more than 10 min error
                    if orden.date <= country_time - timedelta(minutes=10):
                        return JsonResponse(
                            {"message": "Error, la orden ha expirado", "status": 422},
                            status=422,
                        )

                    rifa = RifaModel.objects.get(Id=orden.idRifa.Id)

                    # validate file size 4mb
                    if request.FILES["file"].size > 4194304:
                        return JsonResponse(
                            {"message": "Archivo muy grande", "status": 422}, status=422
                        )

                    if (
                        not request.FILES["file"].name.endswith(".pdf")
                        and not request.FILES["file"].name.endswith(".jpg")
                        and not request.FILES["file"].name.endswith(".png")
                        and not request.FILES["file"].name.endswith(".jpeg")
                    ):
                        return JsonResponse(
                            {"message": "Archivo no valido", "status": 422}, status=422
                        )

                    with transaction.atomic():  # create comprador
                        # Verificar si hay un cliente autenticado vinculado a esta orden
                        cliente = None
                        if request.user.is_authenticated and hasattr(
                            request.user, "cliente"
                        ):
                            cliente = request.user.cliente
                            # Buscar si ya existe un Comprador para este cliente
                            comprador_existente = Comprador.objects.filter(
                                idCliente=cliente
                            ).first()
                            if comprador_existente:
                                comprador = comprador_existente
                                # Actualizar datos si es necesario
                                comprador.Nombre = orden.customer_name
                                comprador.Correo = orden.customer_email
                                comprador.NumeroTlf = orden.customer_phone
                                comprador.Cedula = orden.customer_identification
                                comprador.save()
                            else:
                                comprador = Comprador()
                                comprador.Nombre = orden.customer_name
                                comprador.Correo = orden.customer_email
                                comprador.NumeroTlf = orden.customer_phone
                                comprador.Cedula = orden.customer_identification
                                comprador.idCliente = cliente
                                comprador.save()
                        else:
                            # Crear comprador sin cliente (invitado)
                            comprador = Comprador()
                            comprador.Nombre = orden.customer_name
                            comprador.Correo = orden.customer_email
                            comprador.NumeroTlf = orden.customer_phone
                            comprador.Cedula = orden.customer_identification
                            comprador.save()

                        # save file locally

                        # get random numbers from numerosbydisponibles
                        disp = NumeroRifaReservadosOrdenes.objects.filter(
                            idOrden=idOrden
                        )
                        totalNum = disp.count()

                        numerosForm = form.cleaned_data["Cantidad"]
                        logger.info(form.cleaned_data["Cantidad"])
                        logger.info(totalNum)
                        logger.info(numerosForm)

                        if totalNum != numerosForm:
                            return JsonResponse(
                                {
                                    "message": "Error en su solicitud por favor, recargue la pagina y vuelva a intentar",
                                    "status": 422,
                                },
                                status=422,
                            )
                        # create compra
                        compra = Compra()
                        compra.idComprador = comprador
                        compra.idRifa = RifaModel.objects.get(Id=rifa.Id)
                        compra.Comprobante = request.FILES["file"]
                        # last tasa
                        compra.TasaBS = Tasas.objects.latest("id").tasa
                        compra.Referencia = form.cleaned_data["referencia"]
                        compra.MetodoPago = form.cleaned_data["tipoPago"]
                        compra.FechaCompra
                        country_time_zone = pytz.timezone("America/Caracas")
                        if request.user.is_authenticated:
                            compra.author = request.user
                        country_time = datetime.now(country_time_zone)
                        compra.FechaEstado = country_time
                        compra.FechaCompra = country_time
                        compra.NumeroBoletos = totalNum
                        compra.TotalPagado = totalNum * compra.idRifa.Precio
                        compra.TotalPagadoAlt = totalNum * compra.idRifa.PrecioAlt
                        compra.save()
                        logger.info(f"compra guardada as: {compra}")

                        # OPTIMIZACIÓN: Usar bulk_create para reducir consultas y evitar RifaModel.objects.get() en loop
                        numeros_comprados_list = []
                        numeros_compra_list = []
                        numeros_a_eliminar = []
                        for x in disp:
                            numeros_comprados_list.append(
                                NumeroRifaComprados(idRifa=rifa, Numero=x.Numero)
                            )
                            numeros_compra_list.append(
                                NumerosCompra(idCompra=compra, Numero=x.Numero)
                            )
                            numeros_a_eliminar.append(x.Numero)

                        # Bulk create para reducir consultas
                        NumeroRifaComprados.objects.bulk_create(numeros_comprados_list)
                        NumerosCompra.objects.bulk_create(numeros_compra_list)
                        # Bulk delete para reducir consultas
                        NumeroRifaReservadosOrdenes.objects.filter(
                            idOrden=idOrden, Numero__in=numeros_a_eliminar
                        ).delete()
                        rifa.TotalComprados = F("TotalComprados") + totalNum

                        orden.completada = True
                        orden.save()
                        rifa.save()
                        #   transaction.on_commit(lambda: validateCompra(compra))
                        # transaction.on_commit(lambda: sendEmail.delay(comprador.Nombre, comprador.Correo, rifa.Id, compra.Id))

                        numeros_apartados = [x.Numero for x in disp]
                        return JsonResponse(
                            {
                                "message": "Éxito",
                                "status": 200,
                                "numeros": numeros_apartados,
                            },
                            status=200,
                        )
                except Exception as ex:
                    logger.info(ex)
                    print(ex)
                    return JsonResponse(
                        {
                            "message": "Error en el servidor",
                            "status": 500,
                            "err": f"{ex}",
                        },
                        status=500,
                    )
            else:
                return JsonResponse(
                    {
                        "errors": form.errors.as_json(),
                        "message": "error de validacion",
                        "status": 422,
                    },
                    status=422,
                )
    except Exception as e:
        logger.error(f"Error en ComprarRifa: {str(e)}")
        # CRÍTICO: Cerrar conexiones en caso de error
        try:
            from django.db import connections

            for alias in connections:
                try:
                    connections[alias].close()
                except:
                    pass
        except:
            pass
        return JsonResponse(
            {"message": "Error interno del servidor", "status": 500}, status=500
        )


def sss(request):
    try:
        country_time_zone = pytz.timezone("America/Caracas")
        country_time = datetime.now(country_time_zone)
        # get NumeroRifaReservados with more of 15 minutes in date field
        numeros = NumeroRifaReservadosOrdenes.objects.filter(
            date__lte=country_time - timedelta(minutes=16)
        )
        Logger.objects.create(
            date=country_time,
            description=f"Ejecutando Cron {list(numeros)} reservados recuperados",
        )

        for x in numeros:
            NumeroRifaDisponibles.objects.create(Numero=x.Numero, idRifa=x.idRifa)

        numeros.delete()
    except Exception as ex:
        logger.info(ex)
        print(ex)
        return JsonResponse(
            {"message": "Error en el servidor", "status": 500, "err": f"{ex}"},
            status=500,
        )

    return JsonResponse({"message": "ok", "status": 200}, status=200)


def validateCompra(compra):
    return


def CheckPay(request):
    if request.method == "POST":
        # agregar validaciones
        data = json.load(request)
        token = get_token()
        url = f"https://apiplaza.celupagos.com/payment/searchTransaction?reference={data['Orden']['reference']}&mode=Integration"
        response = get_data(url, token)
        logger.info(response)
        logger.info(response["codigoHttp"])
        logger.info(response["codigoHttp"] != 200)

        if response["codigoHttp"] != 200:
            res = json.dumps(response)
            return HttpResponse(res, content_type="application/json")

            return HttpResponse(f"Error {response['clientMessage']}", status=400)

        if (
            response["status"] != "PENDIENTE"
            and response["status"] != "SIMULACION_APROBADA"
        ):
            res = json.dumps(response)
            return HttpResponse(res, content_type="application/json")

            return HttpResponse(f"Error, Pago sin completar", status=400)

        logger.info(data["Orden"]["reference"])
        logger.info(data["Orden"]["orden"])

        orden = Ordenes.objects.get(reference=data["Orden"]["orden"])

        compra = Compra.objects.get(idOrden=orden)

        if str(compra.Estado) != Compra.EstadoCompra.Pendiente.value:
            return HttpResponse("Error, Pago ya realizado", status=400)

        compra.Estado = compra.EstadoCompra.Pagado
        compra.save()

        for num in data["Numbers"]:
            NumeroRifaComprados.objects.create(
                idRifa=RifaModel.objects.get(Id=data["Rifa"]), Numero=num["num"]
            )
            NumerosCompra.objects.create(idCompra=compra, Numero=num["num"])
            NumeroRifaReservados.objects.get(
                idRifa=RifaModel.objects.get(Id=data["Rifa"]),
                Numero=num["num"],
                idOrden=orden,
            ).delete()

        res = json.dumps(response)
        comprado = CompraNumerosByDisponiblesMethod(data)
        if comprado == False:
            return HttpResponse(
                "Error, Ocurrio un problema con su solicitud, intente nuevamente, comuniquese si necesita ayuda",
                status=400,
            )

        return HttpResponse(res, content_type="application/json")


# method to pass auth token api to get data
def get_data(url, token):
    # CRÍTICO: Usar sesión con context manager para cerrar conexión HTTP correctamente
    with requests.Session() as session:
        try:
            r = session.get(
                url, headers={"Authorization": "Bearer " + token}, timeout=30
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"Error en get_data(): {str(e)}")
            raise


# method to post data to auth api


def post_data(url, data, token):
    # CRÍTICO: Usar sesión con context manager para cerrar conexión HTTP correctamente
    with requests.Session() as session:
        try:
            r = session.post(
                url, data=data, headers={"Authorization": "Bearer " + token}, timeout=30
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"Error en post_data(): {str(e)}")
            raise


def createOrderOld(request):
    if request.method == "POST":
        data = json.load(request)
        # valida Rifa existe
        try:
            rifa = RifaModel.objects.get(Id=data["Rifa"])
        except:
            return HttpResponse(
                "Error, la rifa a la que intenta comprar no existe", status=400
            )
        # valida estado y publicacion
        if rifa.Estado == False or rifa.Eliminada == True:
            return HttpResponse(
                "Error, la rifa a la que intenta comprar no existe", status=400
            )

        # valida rifa fecha
        country_time_zone = pytz.timezone("America/Caracas")
        country_time = datetime.now(country_time_zone)
        if country_time >= rifa.FechaSorteo:
            if rifa.Extension == False:
                return HttpResponse(
                    "Error, la rifa a la que intenta comprar ya no esta disponible",
                    status=400,
                )
        # valida Numeros
        consulta = ConsultaRifabyDisponiplesListaMethod(data["Numbers"], rifa.Id)
        if consulta["result"] == True:
            return HttpResponse(
                "Error, Hay numeros no disponibles en sus seleccion ", status=400
            )
        logger.info(len(list(data["Numbers"])))
        if len(list(data["Numbers"])) < rifa.MinCompra:
            return HttpResponse(
                "Error,la cantidad de numeros a comprar es menor a la minima permitida ",
                status=400,
            )
        # calculo total

        total = rifa.Precio * len(list(data["Numbers"]))

        comprador = Comprador()
        orden = Ordenes()
        compra = Compra()

        try:
            with transaction.atomic():
                comprador.Nombre = data["User"]["Nombre"]
                comprador.Correo = data["User"]["Correo"]
                comprador.NumeroTlf = data["User"]["Telefono"]
                comprador.Direccion = data["User"]["Direccion"]
                comprador.Cedula = data["User"]["Ci"]

                orden.amount = total
                orden.reference = uuid.uuid4().hex + "-" + str(rifa.Id)
                orden.customer_name = data["Buyer"]["Name"]
                orden.customer_phone = data["Buyer"]["Tlf"]
                orden.customer_email = data["Buyer"]["Correo"]
                orden.customer_identification = data["Buyer"]["Ci"]
                orden.customer_bank = data["Buyer"]["Banco"]
                orden.description = f"Compra de Numeros de rifa Fecha: {datetime.now()} Rifa: {rifa.Nombre} Numeros: {list(x['num'] for x in data['Numbers'])} Total: {total} aleautos1"

                comprador.save()
                orden.save()
                compra.idRifa = rifa
                compra.FechaCompra = country_time
                compra.idComprador = comprador
                compra.idOrden = orden
                compra.NumeroBoletos = len(list(data["Numbers"]))
                compra.TotalPagado = total
                compra.TasaBS = get_data(
                    "https://apiplazaqa.celupagos.com/rate", get_token()
                )["rate"]
                compra.save()
                for x in data["Numbers"]:
                    NumeroRifaReservados.objects.create(
                        idRifa=rifa, Numero=x["num"], date=country_time, idOrden=orden
                    )
                    NumeroRifaDisponibles.objects.get(
                        idRifa=rifa, Numero=x["num"]
                    ).delete()

        except Exception as ex:
            return HttpResponse(ex)

        logger.info(data)
        url = "https://apiplaza.celupagos.com/payment/createOrder"
        token = get_token()
        data = {
            "amount": orden.amount,
            "currency": "USD",
            "description": orden.description,
            "paymentType": "P2C",
            "channel": "PAYMENT_BUTTON",
            "customer_email": orden.customer_email,
            "reference": orden.reference,
            "customer_name": orden.customer_name,
            "customer_phone": orden.customer_phone,
            "customer_identification": orden.customer_identification,
            "customer_bank": orden.customer_bank,
        }
        logger.info(data)

        r = post_data(url, data, token)
        r["orden"] = orden.reference

        logger.info(r)

        res = json.dumps(r)
        logger.info(res)
        logger.info(r["codigoHttp"])
        logger.info(r["systemMessage"])
        logger.info(r["clientMessage"])

        #  if r['codigoHttp']!=200:

        #   return   HttpResponse(f"Error {r['clientMessage']}", status=400)

        return HttpResponse(res, content_type="application/json")
    return HttpResponse("Error", status=400)


def reserveNumbers(request):
    # CRÍTICO: Cerrar conexiones de BD en caso de error para evitar acumulación
    try:
        if request.method == "POST":
            form = ReserveForm(request.POST)
            logger.info(f"Campos {request.POST}")
            logger.info(f"Formulario válido {form.is_valid()}")
            logger.info(f"Formulario válido {form.errors}")
            if form.is_valid():
                idRifa = form.cleaned_data["idRifa"]
                try:
                    rifa = RifaModel.objects.get(Id=idRifa)
                except:
                    return HttpResponse(
                        "Error, la rifa a la que intenta comprar no existe", status=400
                    )

                # valida estado y publicacion
                if rifa.Estado == False or rifa.Eliminada == True:
                    return JsonResponse(
                        {"message": "Rifa no dispoible", "status": 422}, status=422
                    )

                # valida rifa fecha
                country_time_zone = pytz.timezone("America/Caracas")
                country_time = datetime.now(country_time_zone)

                if rifa.FechaSorteo != None:
                    if country_time >= rifa.FechaSorteo:
                        if rifa.Extension == False:
                            return JsonResponse(
                                {"message": "Rifa expirada", "status": 422}, status=422
                            )

                if (
                    form.cleaned_data["numeros"] < rifa.MinCompra
                    or form.cleaned_data["numeros"] > rifa.MaxCompra
                ):
                    return JsonResponse(
                        {"message": "Cantidad invalida", "status": 422}, status=422
                    )

                if (
                    form.cleaned_data["numeros"]
                    > NumeroRifaDisponibles.objects.filter(idRifa=idRifa).count()
                ):
                    return JsonResponse(
                        {"message": "No hay disponibles suficientes", "status": 422},
                        status=422,
                    )

                total = rifa.Precio * form.cleaned_data["numeros"]
                boletos = form.cleaned_data["boletos"] or None

                if boletos != None:
                    boletos = boletos.split(",")
                else:
                    boletos = []

                random_numbers = form.cleaned_data["numeros"] - len(boletos)

                if random_numbers < 0:
                    return JsonResponse(
                        {
                            "message": "Error, numeros reservados mayor a la cantidad de boletos",
                            "status": 422,
                        },
                        status=422,
                    )

                try:
                    with transaction.atomic():
                        orden = OrdenesReservas()

                        disp = (
                            NumeroRifaDisponibles.objects.exclude(Numero__in=boletos)
                            .filter(idRifa=form.cleaned_data["idRifa"])
                            .order_by("?")[:random_numbers]
                        )

                        orden.date = country_time
                        orden.customer_name = "Reserva"
                        orden.customer_phone = "Reserva"
                        orden.customer_identification = "Reserva"
                        orden.amount = total
                        orden.idRifa = rifa
                        orden.description = f"Compra de Numeros de rifa Fecha: {datetime.now()} Rifa: {rifa.Nombre} Numeros: {list(x.Numero for x in disp)} Boletos: {boletos} Total: {total} aleautos1"

                        orden.save()
                        if len(boletos) > 0:
                            # OPTIMIZACIÓN: Verificar todos los boletos de una vez
                            boletos_disponibles = set(
                                NumeroRifaDisponibles.objects.filter(
                                    idRifa=rifa, Numero__in=boletos
                                ).values_list("Numero", flat=True)
                            )

                            # Verificar que todos los boletos solicitados estén disponibles
                            boletos_no_disponibles = set(boletos) - boletos_disponibles
                            if boletos_no_disponibles:
                                return JsonResponse(
                                    {
                                        "message": f"Error, números no disponibles: {', '.join(map(str, boletos_no_disponibles))}",
                                        "status": 422,
                                    },
                                    status=422,
                                )

                            # OPTIMIZACIÓN: Bulk create para todas las reservas de boletos específicos
                            reservados_boletos_list = []
                            for num in boletos_disponibles:
                                reservados_boletos_list.append(
                                    NumeroRifaReservadosOrdenes(
                                        idRifa=rifa,
                                        Numero=num,
                                        date=country_time,
                                        idOrden=orden,
                                    )
                                )

                            if reservados_boletos_list:
                                NumeroRifaReservadosOrdenes.objects.bulk_create(
                                    reservados_boletos_list
                                )

                                # OPTIMIZACIÓN: Bulk delete para eliminar todos los boletos reservados
                                NumeroRifaDisponibles.objects.filter(
                                    idRifa=rifa, Numero__in=list(boletos_disponibles)
                                ).delete()

                        # OPTIMIZACIÓN: Verificar todos los números de una vez antes de procesar
                        numeros_disp = [x.Numero for x in disp]
                        numeros_ya_reservados = set(
                            NumeroRifaReservadosOrdenes.objects.filter(
                                idRifa=rifa, Numero__in=numeros_disp
                            ).values_list("Numero", flat=True)
                        )

                        if numeros_ya_reservados:
                            return JsonResponse(
                                {
                                    "message": "Error procesando su solicitud, intente nuevamente",
                                    "status": 500,
                                },
                                status=500,
                            )

                        # OPTIMIZACIÓN: Usar bulk_create para reducir consultas
                        reservados_list = []
                        for x in disp:
                            reservados_list.append(
                                NumeroRifaReservadosOrdenes(
                                    idRifa=rifa,
                                    Numero=x.Numero,
                                    date=country_time,
                                    idOrden=orden,
                                )
                            )

                        NumeroRifaReservadosOrdenes.objects.bulk_create(reservados_list)

                        # OPTIMIZACIÓN: Bulk delete para reducir consultas
                        NumeroRifaDisponibles.objects.filter(
                            idRifa=rifa, Numero__in=numeros_disp
                        ).delete()

                        # Verificar que se crearon correctamente
                        if NumeroRifaReservadosOrdenes.objects.filter(
                            idRifa=rifa, Numero__in=numeros_disp, idOrden=orden
                        ).count() != len(numeros_disp):
                            return JsonResponse(
                                {
                                    "message": "Error procesando su solicitud, intente nuevamente",
                                    "status": 500,
                                },
                                status=500,
                            )

                except Exception as ex:
                    logger.info(ex)
                    print(ex)
                    return JsonResponse(
                        {"message": "Ops! Vuelve a intentarlo", "status": 500},
                        status=500,
                    )

                serialized_object = serializers.serialize(
                    "json",
                    [
                        orden,
                    ],
                )
                return JsonResponse(
                    {"message": "Éxito", "status": 200, "orden": serialized_object},
                    status=200,
                )
            return JsonResponse(
                {
                    "errors": form.errors.as_json(),
                    "message": "error de validacion",
                    "status": 422,
                },
                status=422,
            )
    except Exception as e:
        logger.error(f"Error en reserveNumbers: {str(e)}")
        # CRÍTICO: Cerrar conexiones en caso de error
        try:
            from django.db import connections

            for alias in connections:
                try:
                    connections[alias].close()
                except:
                    pass
        except:
            pass
        return JsonResponse(
            {"message": "Error interno del servidor", "status": 500}, status=500
        )


def updateOrder(request):
    # CRÍTICO: Cerrar conexiones de BD en caso de error para evitar acumulación
    try:
        if request.method == "POST":
            form = UpdateOrderForm(request.POST)
            logger.info(f"Campos {request.POST}")
            logger.info(f"nombre {request.POST.get('nombre')}")
            logger.info(f"Formulario válido {form.is_valid()}")
            logger.info(f"Formulario válido {form.errors}")
            if form.is_valid():
                idRifa = form.cleaned_data["idRifa"]
                try:
                    rifa = RifaModel.objects.get(Id=idRifa)
                except:
                    return HttpResponse(
                        "Error, la rifa a la que intenta comprar no existe", status=400
                    )
                # valida estado y publicacion
                if rifa.Estado == False or rifa.Eliminada == True:
                    return JsonResponse(
                        {"message": "Rifa no disponible", "status": 422}, status=422
                    )
                # valida rifa fecha
                country_time_zone = pytz.timezone("America/Caracas")
                country_time = datetime.now(country_time_zone)
                if rifa.FechaSorteo != None:
                    if country_time >= rifa.FechaSorteo:
                        if rifa.Extension == False:
                            return JsonResponse(
                                {"message": "Rifa expirada", "status": 422}, status=422
                            )

                try:
                    with transaction.atomic():
                        orden = OrdenesReservas.objects.filter(
                            Id=form.cleaned_data["idOrden"]
                        )
                        if orden.count() == 0:
                            return JsonResponse(
                                {"message": "Error, la orden no existe", "status": 422},
                                status=422,
                            )

                        orden = orden.first()

                        if orden.date <= country_time - timedelta(minutes=10):
                            return JsonResponse(
                                {
                                    "message": "Error, la orden ha expirado vuelva a intentarlo",
                                    "status": 422,
                                },
                                status=422,
                            )

                        orden.customer_name = form.cleaned_data["nombre"]
                        orden.customer_phone = form.cleaned_data["numeroTlf"]
                        orden.customer_email = form.cleaned_data["correo"]
                        orden.customer_identification = form.cleaned_data["cedula"]

                        orden.save()

                except Exception as ex:
                    logger.info(ex)
                    print(ex)
                    return JsonResponse(
                        {"message": "Ops! Vuelve a intentarlo", "status": 500},
                        status=500,
                    )

                serialized_object = serializers.serialize(
                    "json",
                    [
                        orden,
                    ],
                )
                return JsonResponse(
                    {"message": "Éxito", "status": 200, "orden": serialized_object},
                    status=200,
                )
            else:
                return JsonResponse(
                    {
                        "errors": form.errors.as_json(),
                        "message": "error de validacion",
                        "status": 422,
                    },
                    status=422,
                )
    except Exception as e:
        logger.error(f"Error en updateOrder: {str(e)}")
        # CRÍTICO: Cerrar conexiones en caso de error
        try:
            from django.db import connections

            for alias in connections:
                try:
                    connections[alias].close()
                except:
                    pass
        except:
            pass
        return JsonResponse(
            {"message": "Error interno del servidor", "status": 500}, status=500
        )


def createOrder(request):
    # CRÍTICO: Cerrar conexiones de BD en caso de error para evitar acumulación
    try:
        if request.method == "POST":
            form = FirstFileForm(request.POST)
            logger.info(f"Campos {request.POST}")
            logger.info(f"nombre {request.POST.get('nombre')}")
            logger.info(f"Formulario válido {form.is_valid()}")
            logger.info(f"Formulario válido {form.errors}")
            if form.is_valid():
                idRifa = form.cleaned_data["idRifa"]
                try:
                    rifa = RifaModel.objects.get(Id=idRifa)
                except:
                    return HttpResponse(
                        "Error, la rifa a la que intenta comprar no existe", status=400
                    )
                # valida estado y publicacion
                if rifa.Estado == False or rifa.Eliminada == True:
                    return JsonResponse(
                        {"message": "Rifa no dispoible", "status": 422}, status=422
                    )
                # valida rifa fecha
                country_time_zone = pytz.timezone("America/Caracas")
                country_time = datetime.now(country_time_zone)
                if rifa.FechaSorteo != None:
                    if country_time >= rifa.FechaSorteo:
                        if rifa.Extension == False:
                            return JsonResponse(
                                {"message": "Rifa expirada", "status": 422}, status=422
                            )
                if (
                    form.cleaned_data["numeros"] < rifa.MinCompra
                    or form.cleaned_data["numeros"] > rifa.MaxCompra
                ):
                    return JsonResponse(
                        {"message": "Cantidad invalida", "status": 422}, status=422
                    )

                if (
                    form.cleaned_data["numeros"]
                    > NumeroRifaDisponibles.objects.filter(idRifa=idRifa).count()
                ):
                    return JsonResponse(
                        {"message": "No hay disponibles suficientes", "status": 422},
                        status=422,
                    )

                total = rifa.Precio * form.cleaned_data["numeros"]

                # Si el usuario está autenticado como cliente, usar sus datos
                cliente = None
                if request.user.is_authenticated and hasattr(request.user, "cliente"):
                    cliente = request.user.cliente
                    nombre = (
                        f"{request.user.first_name} {request.user.last_name}".strip()
                        or request.user.username
                    )
                    correo = request.user.email
                    cedula = cliente.cedula
                    telefono = cliente.telefono
                else:
                    # Usar datos del formulario (invitado)
                    nombre = form.cleaned_data["nombre"]
                    correo = form.cleaned_data["correo"]
                    cedula = form.cleaned_data["cedula"]
                    telefono = form.cleaned_data["numeroTlf"]

                try:
                    with transaction.atomic():
                        orden = OrdenesReservas()

                        disp = NumeroRifaDisponibles.objects.filter(
                            idRifa=form.cleaned_data["idRifa"]
                        ).order_by("?")[: form.cleaned_data["numeros"]]

                        orden.date = country_time
                        orden.amount = total
                        orden.customer_name = nombre
                        orden.customer_phone = telefono
                        orden.customer_email = correo
                        orden.customer_identification = cedula
                        orden.idRifa = rifa
                        orden.description = f"Compra de Numeros de rifa Fecha: {datetime.now()} Rifa: {rifa.Nombre} Numeros: {list(x.Numero for x in disp)} Total: {total} aleautos1"

                        orden.save()
                        # OPTIMIZACIÓN: Verificar todos los números de una vez antes de procesar
                        numeros_disp = [x.Numero for x in disp]
                        numeros_ya_reservados = set(
                            NumeroRifaReservadosOrdenes.objects.filter(
                                idRifa=rifa, Numero__in=numeros_disp
                            ).values_list("Numero", flat=True)
                        )

                        if numeros_ya_reservados:
                            return JsonResponse(
                                {
                                    "message": "Error procesando su solicitud, intente nuevamente",
                                    "status": 500,
                                },
                                status=500,
                            )

                        # OPTIMIZACIÓN: Usar bulk_create para reducir consultas
                        reservados_list = []
                        for x in disp:
                            reservados_list.append(
                                NumeroRifaReservadosOrdenes(
                                    idRifa=rifa,
                                    Numero=x.Numero,
                                    date=country_time,
                                    idOrden=orden,
                                )
                            )

                        NumeroRifaReservadosOrdenes.objects.bulk_create(reservados_list)

                        # OPTIMIZACIÓN: Bulk delete para reducir consultas
                        NumeroRifaDisponibles.objects.filter(
                            idRifa=rifa, Numero__in=numeros_disp
                        ).delete()

                        # Verificar que se crearon correctamente
                        if NumeroRifaReservadosOrdenes.objects.filter(
                            idRifa=rifa, Numero__in=numeros_disp, idOrden=orden
                        ).count() != len(numeros_disp):
                            return JsonResponse(
                                {
                                    "message": "Error procesando su solicitud, intente nuevamente",
                                    "status": 500,
                                },
                                status=500,
                            )

                except Exception as ex:
                    logger.info(ex)
                    print(ex)
                    return JsonResponse(
                        {"message": "Ops! Vuelve a intentarlo", "status": 500},
                        status=500,
                    )
                serialized_object = serializers.serialize(
                    "json",
                    [
                        orden,
                    ],
                )
                return JsonResponse(
                    {"message": "Éxito", "status": 200, "orden": serialized_object},
                    status=200,
                )
            return JsonResponse(
                {
                    "errors": form.errors.as_json(),
                    "message": "error de validacion",
                    "status": 422,
                },
                status=422,
            )
    except Exception as e:
        logger.error(f"Error en createOrder: {str(e)}")
        # CRÍTICO: Cerrar conexiones en caso de error
        try:
            from django.db import connections

            for alias in connections:
                try:
                    connections[alias].close()
                except:
                    pass
        except:
            pass
        return JsonResponse(
            {"message": "Error interno del servidor", "status": 500}, status=500
        )


def consultOrder(request):
    if request.method == "GET":
        data = json.load(request)

        url = f"https://apiplaza.celupagos.com/payment/searchTransaction?reference={data['reference']}&mode=Integration"
        token = get_token()
        r = get_data(url, token)
        return HttpResponse(json.dumps(r), content_type="application/json")
    return HttpResponse("Error", status=400)


@login_required(login_url="/inicia-sesion/")
def createOrderPagoMovilR4(request):
    """
    Endpoint para crear orden de pago móvil R4 automáticamente con datos del cliente autenticado
    """
    # CRÍTICO: Cerrar conexiones de BD en caso de error para evitar acumulación
    try:
        if request.method == "POST":
            try:
                # Verificar que el usuario tenga un cliente asociado
                if not request.user.is_authenticated or not hasattr(
                    request.user, "cliente"
                ):
                    return JsonResponse(
                        {
                            "message": "Debes tener una cuenta de cliente para pagar con pago móvil",
                            "status": 403,
                        },
                        status=403,
                    )

                cliente = request.user.cliente
                data = json.loads(request.body) if request.body else {}

                idRifa = data.get("idRifa")
                cantidad = data.get("cantidad", 1)
                numeros_seleccionados = data.get(
                    "numeros", []
                )  # Lista de números específicos si los hay

                if not idRifa:
                    return JsonResponse(
                        {"message": "ID de rifa requerido", "status": 422}, status=422
                    )

                try:
                    rifa = RifaModel.objects.get(Id=idRifa)
                except RifaModel.DoesNotExist:
                    return JsonResponse(
                        {"message": "La rifa no existe", "status": 422}, status=422
                    )

                # Validar estado y publicación
                if rifa.Estado == False or rifa.Eliminada == True:
                    return JsonResponse(
                        {"message": "Rifa no disponible", "status": 422}, status=422
                    )

                # Validar fecha
                country_time_zone = pytz.timezone("America/Caracas")
                country_time = datetime.now(country_time_zone)
                if rifa.FechaSorteo != None:
                    if country_time >= rifa.FechaSorteo:
                        if rifa.Extension == False:
                            return JsonResponse(
                                {"message": "Rifa expirada", "status": 422}, status=422
                            )

                # Validar cantidad
                if cantidad < rifa.MinCompra or cantidad > rifa.MaxCompra:
                    return JsonResponse(
                        {"message": "Cantidad inválida", "status": 422}, status=422
                    )

                # Validar disponibilidad
                disponibles = NumeroRifaDisponibles.objects.filter(
                    idRifa=idRifa
                ).count()
                if cantidad > disponibles:
                    return JsonResponse(
                        {"message": "No hay disponibles suficientes", "status": 422},
                        status=422,
                    )

                # Calcular total
                total = rifa.Precio * cantidad
                totalAlt = (
                    rifa.PrecioAlt * cantidad
                    if hasattr(rifa, "PrecioAlt") and rifa.PrecioAlt
                    else None
                )

                # Obtener datos del cliente
                nombre = (
                    f"{request.user.first_name} {request.user.last_name}".strip()
                    or request.user.username
                )
                correo = request.user.email
                cedula = cliente.cedula
                telefono = cliente.telefono

                try:
                    with transaction.atomic():
                        # Crear orden
                        orden = OrdenesReservas()
                        orden.date = country_time
                        orden.amount = total
                        orden.customer_name = nombre
                        orden.customer_phone = telefono
                        orden.customer_email = correo
                        orden.customer_identification = cedula
                        orden.idRifa = rifa
                        # Guardar la orden primero para tener el ID
                        orden.save()

                        # Reservar números
                        numeros_reservados = []
                        # OPTIMIZACIÓN: Verificar disponibilidad de números específicos de una vez
                        if numeros_seleccionados and len(numeros_seleccionados) > 0:
                            # Verificar todos los números específicos de una vez
                            disponibles_especificos = set(
                                NumeroRifaDisponibles.objects.filter(
                                    idRifa=rifa, Numero__in=numeros_seleccionados
                                ).values_list("Numero", flat=True)
                            )

                            # Reservar números específicos disponibles
                            reservados_list = []
                            for num in numeros_seleccionados:
                                if num in disponibles_especificos:
                                    reservados_list.append(
                                        NumeroRifaReservadosOrdenes(
                                            idRifa=rifa,
                                            Numero=num,
                                            date=country_time,
                                            idOrden=orden,
                                        )
                                    )
                                    numeros_reservados.append(num)

                            if reservados_list:
                                NumeroRifaReservadosOrdenes.objects.bulk_create(
                                    reservados_list
                                )
                                NumeroRifaDisponibles.objects.filter(
                                    idRifa=rifa, Numero__in=numeros_reservados
                                ).delete()

                            # Si faltan números, reservar aleatorios
                            faltantes = cantidad - len(numeros_reservados)
                            if faltantes > 0:
                                disp = NumeroRifaDisponibles.objects.filter(
                                    idRifa=rifa
                                ).order_by("?")[:faltantes]
                                numeros_aleatorios = [x.Numero for x in disp]
                                reservados_aleatorios = []
                                for x in disp:
                                    reservados_aleatorios.append(
                                        NumeroRifaReservadosOrdenes(
                                            idRifa=rifa,
                                            Numero=x.Numero,
                                            date=country_time,
                                            idOrden=orden,
                                        )
                                    )
                                    numeros_reservados.append(x.Numero)

                                if reservados_aleatorios:
                                    NumeroRifaReservadosOrdenes.objects.bulk_create(
                                        reservados_aleatorios
                                    )
                                    NumeroRifaDisponibles.objects.filter(
                                        idRifa=rifa, Numero__in=numeros_aleatorios
                                    ).delete()
                        else:
                            # Reservar números aleatorios
                            disp = NumeroRifaDisponibles.objects.filter(
                                idRifa=rifa
                            ).order_by("?")[:cantidad]
                            numeros_aleatorios = [x.Numero for x in disp]
                            reservados_list = []
                            for x in disp:
                                reservados_list.append(
                                    NumeroRifaReservadosOrdenes(
                                        idRifa=rifa,
                                        Numero=x.Numero,
                                        date=country_time,
                                        idOrden=orden,
                                    )
                                )
                                numeros_reservados.append(x.Numero)

                            if reservados_list:
                                NumeroRifaReservadosOrdenes.objects.bulk_create(
                                    reservados_list
                                )
                                NumeroRifaDisponibles.objects.filter(
                                    idRifa=rifa, Numero__in=numeros_aleatorios
                                ).delete()

                        # Actualizar la descripción de la orden con los números reservados
                        orden.description = f"Compra de Numeros de rifa Fecha: {datetime.now()} Rifa: {rifa.Nombre} Numeros: {numeros_reservados} Total: {total} aleautos1"
                        orden.save()

                        # Obtener o crear comprador
                        comprador_existente = Comprador.objects.filter(
                            idCliente=cliente
                        ).first()
                        if comprador_existente:
                            comprador = comprador_existente
                            comprador.Nombre = nombre
                            comprador.Correo = correo
                            comprador.NumeroTlf = telefono
                            comprador.Cedula = cedula
                            comprador.save()
                        else:
                            comprador = Comprador()
                            comprador.Nombre = nombre
                            comprador.Correo = correo
                            comprador.NumeroTlf = telefono
                            comprador.Cedula = cedula
                            comprador.idCliente = cliente
                            comprador.save()

                        # Crear compra con estado Pendiente y método PagoMovil
                        compra = Compra()
                        compra.idComprador = comprador
                        compra.idRifa = rifa
                        compra.TasaBS = (
                            Tasas.objects.latest("id").tasa
                            if Tasas.objects.exists()
                            else None
                        )
                        compra.MetodoPago = Compra.MetodoPagoOpciones.PagoMovil
                        compra.Estado = Compra.EstadoCompra.Pendiente
                        compra.NumeroBoletos = cantidad
                        compra.TotalPagado = total
                        compra.TotalPagadoAlt = totalAlt
                        compra.FechaCompra = country_time
                        compra.FechaEstado = country_time
                        compra.author = request.user
                        compra.save()

                        # OPTIMIZACIÓN: Crear números de compra usando bulk_create
                        numeros_compra_list = []
                        for num in numeros_reservados:
                            numeros_compra_list.append(
                                NumerosCompra(idCompra=compra, Numero=num)
                            )
                        if numeros_compra_list:
                            NumerosCompra.objects.bulk_create(numeros_compra_list)

                        serialized_orden = serializers.serialize(
                            "json",
                            [
                                orden,
                            ],
                        )
                        serialized_compra = serializers.serialize(
                            "json",
                            [
                                compra,
                            ],
                        )

                        return JsonResponse(
                            {
                                "message": "Orden creada exitosamente",
                                "status": 200,
                                "orden": serialized_orden,
                                "compra": serialized_compra,
                                "numeros": numeros_reservados,
                                "monto": float(total),
                            },
                            status=200,
                        )

                except Exception as ex:
                    logger.error(f"Error en createOrderPagoMovilR4: {str(ex)}")
                    import traceback

                    logger.error(traceback.format_exc())
                    return JsonResponse(
                        {"message": "Error al procesar la solicitud", "status": 500},
                        status=500,
                    )

            except json.JSONDecodeError:
                return JsonResponse(
                    {"message": "JSON inválido", "status": 400}, status=400
                )
            except Exception as e:
                logger.error(f"Error en createOrderPagoMovilR4: {str(e)}")
                # CRÍTICO: Cerrar conexiones en caso de error
                try:
                    from django.db import connections

                    for alias in connections:
                        try:
                            connections[alias].close()
                        except:
                            pass
                except:
                    pass
                return JsonResponse(
                    {"message": "Error en el servidor", "status": 500}, status=500
                )
        else:
            return JsonResponse(
                {"message": "Método no permitido", "status": 405}, status=405
            )
    except Exception as e:
        logger.error(f"Error en createOrderPagoMovilR4: {str(e)}")
        # CRÍTICO: Cerrar conexiones en caso de error
        try:
            from django.db import connections

            for alias in connections:
                try:
                    connections[alias].close()
                except:
                    pass
        except:
            pass
        return JsonResponse(
            {"message": "Error interno del servidor", "status": 500}, status=500
        )


@login_required(login_url="/inicia-sesion/")
def verificarPagoR4(request):
    """
    Endpoint para verificar si el pago fue confirmado por R4
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body) if request.body else {}
            idCompra = data.get("idCompra")

            if not idCompra:
                return JsonResponse(
                    {"message": "ID de compra requerido", "status": 422}, status=422
                )

            try:
                compra = Compra.objects.get(Id=idCompra)
            except Compra.DoesNotExist:
                return JsonResponse(
                    {"message": "La compra no existe", "status": 422}, status=422
                )

            # Verificar que la compra pertenezca al usuario autenticado
            if compra.idComprador and compra.idComprador.idCliente:
                if compra.idComprador.idCliente.user != request.user:
                    return JsonResponse(
                        {
                            "message": "No tienes permiso para verificar esta compra",
                            "status": 403,
                        },
                        status=403,
                    )

            # Verificar que la compra esté en estado Pendiente
            if compra.Estado != Compra.EstadoCompra.Pendiente:
                return JsonResponse(
                    {
                        "message": "La compra ya fue procesada",
                        "status": 200,
                        "compra_estado": compra.Estado,
                        "pago_confirmado": compra.Estado == Compra.EstadoCompra.Pagado,
                    },
                    status=200,
                )

            # Verificar que sea método PagoMovil
            if compra.MetodoPago != Compra.MetodoPagoOpciones.PagoMovil:
                return JsonResponse(
                    {"message": "Esta compra no es de pago móvil", "status": 422},
                    status=422,
                )

            # Buscar transacciones de pago móvil relacionadas con esta compra
            from pagos_banco.models import TransaccionPagoMovil

            # Buscar por idCompra directamente
            transacciones = TransaccionPagoMovil.objects.filter(idCompra=compra)

            # Si no hay transacciones vinculadas, buscar por cédula y monto
            if not transacciones.exists() and compra.idComprador:
                cedula = compra.idComprador.Cedula
                monto = float(compra.TotalPagado) if compra.TotalPagado else None

                if cedula and monto:
                    transacciones = TransaccionPagoMovil.objects.filter(
                        id_cliente=cedula,
                        monto_notificado__gte=monto - 0.01,
                        monto_notificado__lte=monto + 0.01,
                        status="CONFIRMADO",
                    ).order_by("-timestamp_notificacion")

            # Verificar si hay alguna transacción confirmada
            transaccion_confirmada = transacciones.filter(status="CONFIRMADO").first()

            if transaccion_confirmada:
                # Actualizar compra a Pagado
                country_time_zone = pytz.timezone("America/Caracas")
                country_time = datetime.now(country_time_zone)

                compra.Estado = Compra.EstadoCompra.Pagado
                compra.FechaEstado = country_time
                compra.Referencia = transaccion_confirmada.referencia
                compra.save()

                # Vincular la transacción con la compra si no está vinculada
                if not transaccion_confirmada.idCompra:
                    transaccion_confirmada.idCompra = compra
                    transaccion_confirmada.save()

                return JsonResponse(
                    {
                        "message": "Pago confirmado exitosamente",
                        "status": 200,
                        "pago_confirmado": True,
                        "referencia": transaccion_confirmada.referencia,
                        "fecha_confirmacion": transaccion_confirmada.timestamp_notificacion.isoformat()
                        if transaccion_confirmada.timestamp_notificacion
                        else None,
                    },
                    status=200,
                )
            else:
                # Verificar si hay transacciones pendientes o consultadas
                transaccion_pendiente = transacciones.filter(
                    status__in=["PENDIENTE", "CONSULTADO"]
                ).first()

                if transaccion_pendiente:
                    return JsonResponse(
                        {
                            "message": "Esperando confirmación del banco",
                            "status": 200,
                            "pago_confirmado": False,
                            "estado_transaccion": transaccion_pendiente.status,
                        },
                        status=200,
                    )
                else:
                    return JsonResponse(
                        {
                            "message": "No se ha encontrado ninguna transacción. Realiza el pago móvil y vuelve a verificar.",
                            "status": 200,
                            "pago_confirmado": False,
                        },
                        status=200,
                    )

        except json.JSONDecodeError:
            return JsonResponse({"message": "JSON inválido", "status": 400}, status=400)
        except Exception as e:
            logger.error(f"Error en verificarPagoR4: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            return JsonResponse(
                {"message": "Error en el servidor", "status": 500}, status=500
            )

    return JsonResponse({"message": "Método no permitido", "status": 405}, status=405)


@login_required(login_url="/inicia-sesion/")
def rechazarCompraTimeout(request, id):
    """
    Endpoint para rechazar una compra cuando expira el timeout de 5 minutos.
    Libera los números reservados para que otros puedan comprarlos.
    """
    try:
        # Validar que la compra existe
        try:
            compra = Compra.objects.get(Id=id)
        except Compra.DoesNotExist:
            return JsonResponse(
                {"message": "La compra no existe", "status": 404}, status=404
            )

        # Validar que la compra pertenece al usuario autenticado
        if compra.idComprador and compra.idComprador.idCliente:
            if compra.idComprador.idCliente.user != request.user:
                return JsonResponse(
                    {
                        "message": "No tienes permiso para rechazar esta compra",
                        "status": 403,
                    },
                    status=403,
                )
        else:
            return JsonResponse(
                {"message": "Esta compra no está asociada a un cliente", "status": 403},
                status=403,
            )

        # Validar que la compra está en estado Pendiente
        if compra.Estado != Compra.EstadoCompra.Pendiente:
            return JsonResponse(
                {"message": "Esta compra ya fue procesada", "status": 400}, status=400
            )

        # Validar que sea método PagoMovil
        if compra.MetodoPago != Compra.MetodoPagoOpciones.PagoMovil:
            return JsonResponse(
                {"message": "Esta compra no es de pago móvil", "status": 400},
                status=400,
            )

        with transaction.atomic():
            # Buscar la orden asociada por rifa, fecha y monto
            # La orden debe estar relacionada con los números reservados
            numeros_compra = NumerosCompra.objects.filter(idCompra=compra)
            numeros_list = [nc.Numero for nc in numeros_compra]

            # Buscar la orden que tiene estos números reservados
            orden = None
            if numeros_list:
                numeros_reservados = NumeroRifaReservadosOrdenes.objects.filter(
                    idRifa=compra.idRifa, Numero__in=numeros_list
                ).first()

                if numeros_reservados:
                    orden = numeros_reservados.idOrden

            # Rechazar la compra
            compra.Estado = Compra.EstadoCompra.Rechazado
            country_time_zone = pytz.timezone("America/Caracas")
            country_time = datetime.now(country_time_zone)
            compra.FechaEstado = country_time
            compra.recuperado = True
            compra.save()

            # Liberar números reservados
            if orden:
                numeros_reservados = NumeroRifaReservadosOrdenes.objects.filter(
                    idOrden=orden
                )
                for num_reservado in numeros_reservados:
                    # Liberar el número a disponibles
                    NumeroRifaDisponibles.objects.create(
                        Numero=num_reservado.Numero, idRifa=compra.idRifa
                    )
                # Eliminar las reservas
                numeros_reservados.delete()

            # Actualizar contador de la rifa
            rifa = compra.idRifa
            rifa.TotalComprados = F("TotalComprados") - compra.NumeroBoletos
            rifa.save()

            logger.info(f"Compra {compra.Id} rechazada por timeout, números liberados")

            return JsonResponse(
                {"message": "Compra rechazada y números liberados", "status": 200},
                status=200,
            )

    except Exception as e:
        logger.error(f"Error en rechazarCompraTimeout: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return JsonResponse(
            {"message": "Error en el servidor", "status": 500}, status=500
        )


def marcarComprasExpiradas():
    """
    Marca compras pendientes de PagoMovil que tienen más de 5 minutos como expiradas.
    Libera los números reservados asociados.
    """
    try:
        from django.utils import timezone

        # Calcular el tiempo límite (5 minutos atrás)
        tiempo_limite = timezone.now() - timedelta(minutes=5)

        # Buscar compras pendientes de PagoMovil con más de 5 minutos
        # OPTIMIZACIÓN: Limitar resultados y usar select_related para evitar múltiples consultas
        compras_expiradas_qs = Compra.objects.filter(
            Estado=Compra.EstadoCompra.Pendiente,
            MetodoPago=Compra.MetodoPagoOpciones.PagoMovil,
            FechaCompra__lt=tiempo_limite,
        ).select_related("idRifa")[:100]  # Limitar a 100 para evitar sobrecarga

        # Evaluar QuerySet una sola vez
        compras_expiradas = list(compras_expiradas_qs)

        for compra in compras_expiradas:
            try:
                with transaction.atomic():
                    # Marcar como caducado
                    compra.Estado = Compra.EstadoCompra.Caducado
                    country_time_zone = pytz.timezone("America/Caracas")
                    country_time = datetime.now(country_time_zone)
                    compra.FechaEstado = country_time
                    compra.save()

                    # Buscar la orden asociada para liberar números
                    # OPTIMIZACIÓN: Usar values_list para obtener solo los números necesarios
                    numeros_list = list(
                        NumerosCompra.objects.filter(idCompra=compra).values_list(
                            "Numero", flat=True
                        )
                    )

                    orden = None
                    if numeros_list:
                        # Obtener la primera orden de reserva (si existe)
                        numeros_reservados_obj = (
                            NumeroRifaReservadosOrdenes.objects.filter(
                                idRifa=compra.idRifa, Numero__in=numeros_list
                            )
                            .select_related("idOrden")
                            .first()
                        )

                        if numeros_reservados_obj:
                            orden = numeros_reservados_obj.idOrden

                    # Liberar números reservados
                    if orden:
                        # OPTIMIZACIÓN: Obtener todos los números reservados de una vez
                        numeros_reservados_list = list(
                            NumeroRifaReservadosOrdenes.objects.filter(
                                idOrden=orden
                            ).values_list("Numero", flat=True)
                        )

                        # Crear todos los números disponibles en bulk
                        if numeros_reservados_list:
                            numeros_disponibles = [
                                NumeroRifaDisponibles(Numero=num, idRifa=compra.idRifa)
                                for num in numeros_reservados_list
                            ]
                            NumeroRifaDisponibles.objects.bulk_create(
                                numeros_disponibles, ignore_conflicts=True
                            )

                        # Eliminar las reservas
                        NumeroRifaReservadosOrdenes.objects.filter(
                            idOrden=orden
                        ).delete()

                    logger.info(
                        f"Compra {compra.Id} marcada como expirada automáticamente"
                    )
            except Exception as e:
                logger.error(
                    f"Error al marcar compra {compra.Id} como expirada: {str(e)}"
                )
                continue

        return compras_expiradas.count()
    except Exception as e:
        logger.error(f"Error en marcarComprasExpiradas: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return 0


@login_required(login_url="/inicia-sesion/")
def verificar_pago_manual(request, id):
    """
    Endpoint para verificación manual del pago cuando el usuario presiona "Ya pagué".
    Incluye rate limiting y optimizaciones para evitar sobrecarga de conexiones.
    """
    # CRÍTICO: Rate limiting simple usando cache para evitar múltiples requests simultáneos
    # Usar cache si está disponible, sino usar un diccionario en memoria (solo para desarrollo)
    use_cache = False
    cache_key = None
    cache = None

    try:
        from django.core.cache import cache

        cache_key = f"verificar_pago_{id}_{request.user.id}"

        # Verificar si hay una verificación en progreso (últimos 3 segundos)
        if cache.get(cache_key):
            return JsonResponse(
                {
                    "message": "Ya hay una verificación en progreso. Por favor espera unos segundos.",
                    "status": 429,
                    "rate_limited": True,
                },
                status=429,
            )

        # Marcar que hay una verificación en progreso (3 segundos de cooldown)
        cache.set(cache_key, True, 3)
        use_cache = True
    except:
        # Si no hay cache configurado, usar un diccionario simple (solo para desarrollo)
        # En producción debería tener cache configurado
        if not hasattr(verificar_pago_manual, "_rate_limit_dict"):
            verificar_pago_manual._rate_limit_dict = {}

        cache_key = f"{id}_{request.user.id}"
        import time

        now = time.time()

        # Limpiar entradas antiguas (más de 3 segundos)
        verificar_pago_manual._rate_limit_dict = {
            k: v
            for k, v in verificar_pago_manual._rate_limit_dict.items()
            if now - v < 3
        }

        if cache_key in verificar_pago_manual._rate_limit_dict:
            return JsonResponse(
                {
                    "message": "Ya hay una verificación en progreso. Por favor espera unos segundos.",
                    "status": 429,
                    "rate_limited": True,
                },
                status=429,
            )

        verificar_pago_manual._rate_limit_dict[cache_key] = now

    try:
        # Validar que la compra existe con select_related para evitar consultas adicionales
        try:
            compra = Compra.objects.select_related(
                "idComprador", "idComprador__idCliente", "idComprador__idCliente__user"
            ).get(Id=id)
        except Compra.DoesNotExist:
            if use_cache:
                cache.delete(cache_key)
            else:
                verificar_pago_manual._rate_limit_dict.pop(cache_key, None)
            return JsonResponse(
                {"message": "La compra no existe", "status": 404}, status=404
            )

        # Validar que la compra pertenece al usuario autenticado
        if compra.idComprador and compra.idComprador.idCliente:
            if compra.idComprador.idCliente.user != request.user:
                if use_cache:
                    cache.delete(cache_key)
                else:
                    verificar_pago_manual._rate_limit_dict.pop(cache_key, None)
                return JsonResponse(
                    {
                        "message": "No tienes permiso para consultar esta compra",
                        "status": 403,
                    },
                    status=403,
                )
        else:
            if use_cache:
                cache.delete(cache_key)
            else:
                verificar_pago_manual._rate_limit_dict.pop(cache_key, None)
            return JsonResponse(
                {"message": "Esta compra no está asociada a un cliente", "status": 403},
                status=403,
            )

        # Mapear estados numéricos a nombres legibles
        estado_map = {
            int(Compra.EstadoCompra.Pendiente.value): "Pendiente",
            int(Compra.EstadoCompra.Cancelado.value): "Cancelado",
            int(Compra.EstadoCompra.Pagado.value): "Pagado",
            int(Compra.EstadoCompra.Rechazado.value): "Rechazado",
            int(Compra.EstadoCompra.Caducado.value): "Caducado",
        }

        # Importar modelo de transacciones
        from pagos_banco.models import TransaccionPagoMovil

        # Convertir estado a entero para comparación segura
        estado_compra = int(compra.Estado) if compra.Estado else None
        estado_pagado = int(Compra.EstadoCompra.Pagado.value)
        estado_pendiente = int(Compra.EstadoCompra.Pendiente.value)
        estado_rechazado = int(Compra.EstadoCompra.Rechazado.value)

        # OPTIMIZACIÓN: Obtener transacción en una sola consulta
        transaccion = (
            TransaccionPagoMovil.objects.filter(idCompra=compra)
            .order_by("-timestamp_consulta", "-timestamp_notificacion")
            .first()
        )
        estado_transaccion = None
        if transaccion:
            estado_transaccion = transaccion.status

        # Determinar el estado descriptivo
        estado_descriptivo = "esperando_pago"

        if estado_compra == estado_pagado:
            estado_descriptivo = "pago_confirmado"
        elif estado_compra == estado_rechazado:
            estado_descriptivo = "pago_rechazado"
        elif estado_compra == estado_pendiente:
            if transaccion:
                if transaccion.status == "CONFIRMADO":
                    estado_descriptivo = "esperando_pago"
                elif transaccion.status == "CONSULTADO":
                    estado_descriptivo = "validando_pago"
                elif transaccion.status == "RECHAZADO":
                    estado_descriptivo = "pago_rechazado"
                else:
                    estado_descriptivo = "esperando_pago"

        estado_nombre = estado_map.get(estado_compra, "Desconocido")
        pago_confirmado = estado_compra == estado_pagado

        # Si la compra está pagada, obtener los números
        numeros = []
        if pago_confirmado:
            numeros_compra = NumerosCompra.objects.filter(idCompra=compra).values_list(
                "Numero", flat=True
            )
            numeros = list(numeros_compra)

        # Limpiar cache key
        if use_cache:
            cache.delete(cache_key)
        else:
            verificar_pago_manual._rate_limit_dict.pop(cache_key, None)

        return JsonResponse(
            {
                "status": estado_nombre,
                "compra_estado": compra.Estado,
                "pago_confirmado": pago_confirmado,
                "id_compra": compra.Id,
                "estado_descriptivo": estado_descriptivo,
                "estado_transaccion": estado_transaccion,
                "numeros": numeros,
            },
            status=200,
        )

    except Exception as e:
        if use_cache:
            cache.delete(cache_key)
        else:
            verificar_pago_manual._rate_limit_dict.pop(cache_key, None)
        logger.error(f"Error en verificar_pago_manual: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        # CRÍTICO: Cerrar conexiones en caso de error
        try:
            from django.db import connections

            for alias in connections:
                try:
                    connections[alias].close()
                except:
                    pass
        except:
            pass
        return JsonResponse(
            {"message": "Error en el servidor", "status": 500}, status=500
        )


@login_required(login_url="/inicia-sesion/")
def compra_status(request, id):
    """
    Endpoint para polling del estado de una compra.
    DEPRECADO: Usar verificar_pago_manual en su lugar.
    Retorna el estado actual de la compra para verificación automática.
    """
    try:
        # OPTIMIZACIÓN: No llamar marcarComprasExpiradas() en cada request
        # Esto debe ejecutarse en un cron job, no en cada polling request
        # marcarComprasExpiradas()  # COMENTADO para evitar sobrecarga de conexiones

        # Validar que la compra existe con select_related para evitar consultas adicionales
        try:
            compra = Compra.objects.select_related(
                "idComprador", "idComprador__idCliente", "idComprador__idCliente__user"
            ).get(Id=id)
        except Compra.DoesNotExist:
            return JsonResponse(
                {"message": "La compra no existe", "status": 404}, status=404
            )

        # Validar que la compra pertenece al usuario autenticado
        if compra.idComprador and compra.idComprador.idCliente:
            if compra.idComprador.idCliente.user != request.user:
                return JsonResponse(
                    {
                        "message": "No tienes permiso para consultar esta compra",
                        "status": 403,
                    },
                    status=403,
                )
        else:
            # Si la compra no tiene cliente asociado, no permitir acceso
            return JsonResponse(
                {"message": "Esta compra no está asociada a un cliente", "status": 403},
                status=403,
            )

        # Mapear estados numéricos a nombres legibles (usar valores enteros como claves)
        estado_map = {
            int(Compra.EstadoCompra.Pendiente.value): "Pendiente",
            int(Compra.EstadoCompra.Cancelado.value): "Cancelado",
            int(Compra.EstadoCompra.Pagado.value): "Pagado",
            int(Compra.EstadoCompra.Rechazado.value): "Rechazado",
            int(Compra.EstadoCompra.Caducado.value): "Caducado",
        }

        # Importar modelo de transacciones
        from pagos_banco.models import TransaccionPagoMovil

        # DEBUG: Log información de la compra
        logger.info(
            f"compra_status DEBUG - Compra ID: {compra.Id}, Estado RAW: {compra.Estado}, Tipo: {type(compra.Estado)}"
        )

        # Convertir estado a entero para comparación segura
        estado_compra = int(compra.Estado) if compra.Estado else None
        # Obtener valores de TextChoices para comparación
        estado_pagado = int(Compra.EstadoCompra.Pagado.value)
        estado_pendiente = int(Compra.EstadoCompra.Pendiente.value)
        estado_rechazado = int(Compra.EstadoCompra.Rechazado.value)

        logger.info(
            f"compra_status DEBUG - Estado convertido: {estado_compra}, Pagado={estado_pagado}, Pendiente={estado_pendiente}, Rechazado={estado_rechazado}"
        )
        logger.info(
            f"compra_status DEBUG - Comparación Pagado: {estado_compra} == {estado_pagado} = {estado_compra == estado_pagado}"
        )

        # OPTIMIZACIÓN: Obtener transacción en una sola consulta, no usar .exists() y .first() por separado
        transaccion = (
            TransaccionPagoMovil.objects.filter(idCompra=compra)
            .order_by("-timestamp_consulta", "-timestamp_notificacion")
            .first()
        )
        estado_transaccion = None
        if transaccion:
            estado_transaccion = transaccion.status
            logger.info(
                f"compra_status DEBUG - Transacción encontrada: ID={transaccion.id}, Status={transaccion.status}, idCompra={transaccion.idCompra_id}"
            )
        else:
            logger.info(
                f"compra_status DEBUG - No hay transacciones vinculadas a compra {compra.Id}"
            )

        # Determinar el estado descriptivo basado en el estado de la compra PRIMERO
        estado_descriptivo = "esperando_pago"  # Por defecto

        # Si la compra ya está pagada, confirmada
        if estado_compra == estado_pagado:
            estado_descriptivo = "pago_confirmado"
            logger.info(
                f"compra_status DEBUG - Compra {compra.Id} está PAGADA, estado_descriptivo = pago_confirmado"
            )
        # Si la compra está rechazada
        elif estado_compra == estado_rechazado:
            estado_descriptivo = "pago_rechazado"
            logger.info(f"compra_status DEBUG - Compra {compra.Id} está RECHAZADA")
        # Si la compra está pendiente, buscar transacciones vinculadas DIRECTAMENTE
        elif estado_compra == estado_pendiente:
            logger.info(f"compra_status DEBUG - Compra {compra.Id} está PENDIENTE")
            if (
                transaccion
            ):  # Usar la transacción ya obtenida, no hacer consulta adicional
                estado_transaccion = transaccion.status

                if transaccion.status == "CONFIRMADO":
                    # Si hay una transacción confirmada vinculada, la compra debería estar pagada
                    # Pero si la compra sigue pendiente, algo está mal, mantener esperando_pago
                    estado_descriptivo = "esperando_pago"
                    logger.warning(
                        f"compra_status DEBUG - Compra {compra.Id} está PENDIENTE pero tiene transacción CONFIRMADO - INCONSISTENCIA"
                    )
                elif transaccion.status == "CONSULTADO":
                    estado_descriptivo = "validando_pago"
                    logger.info(
                        f"compra_status DEBUG - Compra {compra.Id} tiene transacción CONSULTADO, estado_descriptivo = validando_pago"
                    )
                elif transaccion.status == "RECHAZADO":
                    estado_descriptivo = "pago_rechazado"
                    logger.info(
                        f"compra_status DEBUG - Compra {compra.Id} tiene transacción RECHAZADO"
                    )
                else:
                    estado_descriptivo = "esperando_pago"
                    logger.info(
                        f"compra_status DEBUG - Compra {compra.Id} tiene transacción con status {transaccion.status}, estado_descriptivo = esperando_pago"
                    )
            else:
                # No hay transacciones vinculadas, definitivamente está esperando pago
                estado_descriptivo = "esperando_pago"
                logger.info(
                    f"compra_status DEBUG - Compra {compra.Id} PENDIENTE sin transacciones, estado_descriptivo = esperando_pago"
                )
        else:
            logger.warning(
                f"compra_status DEBUG - Compra {compra.Id} tiene estado desconocido: {estado_compra}"
            )

        estado_nombre = estado_map.get(estado_compra, "Desconocido")
        pago_confirmado = estado_compra == estado_pagado

        # Si la compra está pagada, obtener los números
        numeros = []
        if pago_confirmado:
            numeros_compra = NumerosCompra.objects.filter(idCompra=compra).values_list(
                "Numero", flat=True
            )
            numeros = list(numeros_compra)
            logger.info(
                f"compra_status DEBUG - Compra {compra.Id} pagada, números obtenidos: {len(numeros)}"
            )

        logger.info(
            f"compra_status DEBUG - RESULTADO FINAL: estado_nombre={estado_nombre}, pago_confirmado={pago_confirmado}, estado_descriptivo={estado_descriptivo}, estado_transaccion={estado_transaccion}, numeros={len(numeros)}"
        )

        return JsonResponse(
            {
                "status": estado_nombre,
                "compra_estado": compra.Estado,
                "pago_confirmado": pago_confirmado,
                "id_compra": compra.Id,
                "estado_descriptivo": estado_descriptivo,
                "estado_transaccion": estado_transaccion,
                "numeros": numeros,  # Agregar números cuando está pagada
            },
            status=200,
        )

    except Exception as e:
        logger.error(f"Error en compra_status: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return JsonResponse(
            {"message": "Error en el servidor", "status": 500}, status=500
        )


# endregion
@login_required(login_url="/Login/")
def deleteComprobantes(request):
    # compras id > 0
    compras = Compra.objects.filter(Id__gt=0)
    for x in compras:
        # delete local file

        try:
            x.Comprobante.delete()
            os.remove(x.Comprobante.path)

        except Exception as e:
            logger.info(e)
            pass


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, NumeroRifaDisponibles):
            return obj.__dict__
        return json.JSONEncoder.default(self, obj)


class ViewPaginatorMixin(object):
    min_limit = 1
    max_limit = 10

    def paginate(self, object_list, page=1, limit=10, **kwargs):
        try:
            page = int(page)
            if page < 1:
                page = 1
        except (TypeError, ValueError):
            page = 1

        try:
            limit = int(limit)
            if limit < self.min_limit:
                limit = self.min_limit
            if limit > self.max_limit:
                limit = self.max_limit
        except (ValueError, TypeError):
            limit = self.max_limit

        paginator = Paginator(object_list, limit)
        try:
            objects = paginator.page(page)
        except PageNotAnInteger:
            objects = paginator.page(1)
        except EmptyPage:
            objects = paginator.page(paginator.num_pages)
        data = {
            "previous_page": objects.has_previous()
            and objects.previous_page_number()
            or None,
            "next_page": objects.has_next() and objects.next_page_number() or None,
            "data": list(objects),
        }
        return data
