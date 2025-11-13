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
from django import template
from django.http import HttpResponse, JsonResponse
from django.template import loader
from django.http import HttpResponse
from django.shortcuts import render
from .forms import FirstFileForm, RifaForm, SecondFileForm, UploadFileForm, ReserveForm, UpdateOrderForm, CompradorForm
from .models import Logger, Comprador,LoggerAprobadoRechazo, NumeroRifaReservados, NumeroRifaReservadosOrdenes, NumerosCompra, OrdenesReservas, Rifa as RifaModel, NumeroRifaDisponibles, NumeroRifaDisponiblesArray, NumeroRifaComprados, NumeroRifaCompradosArray, Ordenes, Compra, Tasas, Settings, Cliente
from django.core.paginator import Paginator
from django.db import transaction, IntegrityError
from django.core import serializers
from django.db.models import functions
from django.contrib.postgres.fields import ArrayField
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
import json
from django.contrib.postgres.fields.array import ArrayLenTransform, SliceTransform, SliceTransformFactory, IndexTransform
from django.conf import settings
from django.core.mail import send_mail
from django.core.mail import EmailMessage, get_connection
from django.template.loader import render_to_string
import boto3
from django.contrib.auth.decorators import login_required, permission_required
import pytz
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

logger = logging.getLogger('ballena')

def index(request):
    template = loader.get_template("second.html")
    context = {
    }
    return HttpResponse(template.render(context, request))


def changeState(request):
    data = {}
    if request.method == 'POST':
        dataX = json.load(request)
        idRifa = dataX['id']
        logger.info(idRifa)

        rifa = RifaModel.objects.get(Id=idRifa)
        rifa.Estado = not rifa.Estado
        rifa.save()
        data['success'] = 'true'
    return JsonResponse(data)


def changeExtension(request):
    data = {}
    if request.method == 'POST':
        dataX = json.load(request)
        idRifa = dataX['id']
        logger.info(idRifa)

        rifa = RifaModel.objects.get(Id=idRifa)
        rifa.Extension = not rifa.Extension
        rifa.save()
        data['success'] = 'true'
    return JsonResponse(data)
# region "Numeros"
def SaveSettings(request):
    if request.method == 'POST':
        data = json.load(request)
        settings = Settings.objects.all()
        settings.update(valor=None)
        for x in data.keys():
            setting = Settings.objects.filter(code=x).first()
            if setting is not None:
                setting.valor = data[x]
                setting.save()
        return JsonResponse({"result": 'Success', "message": "Preferencias actualizadas correctamente"})
    return JsonResponse({"result": 'Error', "message": "Metodo no soportado"}, status=404)

def SaveComprador(request):
    if request.method == 'POST':
        data = json.load(request)
        form = CompradorForm(data)
        print(form)
        print(form.is_valid())
        print(form.errors)
        if form.is_valid():
            id = form.cleaned_data['id']
            comprador = Comprador.objects.get(Id=id)
            comprador.Nombre = form.cleaned_data['nombre']
            comprador.Correo = form.cleaned_data['correo']
            comprador.NumeroTlf = form.cleaned_data['telefono']
            comprador.Cedula = form.cleaned_data['cedula']
            comprador.save()
            return JsonResponse({"result": 'Success', "message": "Comprador guardado correctamente"})
        else:
            return JsonResponse({"result": 'Error', "message": "Datos invalidos"}, status=400)
    return JsonResponse({"result": 'Error', "message": "Metodo no soportado"}, status=404)

def RifabyArray(request):
    data = {}
    page_number = request.GET.get('page')
    contain = request.GET.get('contain')

    if page_number is None:
        page_number = 1

    if contain is None:
        contain = '5'

    numeros = NumeroRifaDisponiblesArray.objects.get(id=1).Numeros[0:10]
    # numerosZ = NumeroRifaDisponiblesArray.objects.annotate(array_length=ArrayLenTransform('Numeros'), tags_slice=SliceTransform('Numeros', 0, 50)   ).get(id=1)
    # my_model = NumeroRifaDisponiblesArray.objects.annotate(sliced=SliceTransform('Numeros', 0, 40)).values_list('sliced', flat=True)
    # my_model= list(NumeroRifaDisponiblesArray.objects.raw(f'SELECT Id, "Numeros"[{(page_number-1)*0}:10], "idRifa_id", ARRAY_LENGTH("Numeros", 1) as array_length FROM "Rifa_numerorifadisponiblesarray" WHERE id = 1 {if contains==None "" else "AND " }'))
    # my_model= list(NumeroRifaDisponiblesArray.objects.raw(f'SELECT "un", "idRifa_id", id FROM ( select id, unnest("Numeros") as un, "idRifa_id" from public."Rifa_numerorifadisponiblesarray" ) x ;'))
    my_model = list(NumeroRifaDisponiblesArray.objects.raw(
        'Select  id, unnest("Numeros") as un, "idRifa_id" from "Rifa_numerorifadisponiblesarray"'))
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

    data['data'] = md[(page_number-1)*10:(page_number)*10]
    data['total_pages'] = total_pages
    data['page_number'] = page_number
    data['cantidadRegistros'] = cantidadRegistros

    logger.info(data)
    # return HttpResponse(data)
    return JsonResponse(data)


def RifabyDisponibles(request):
    data = {}
    page_number = int(request.GET.get('page'))
    contain = request.GET.get('contain')
    idRifa = request.GET.get('idRifa')
    recordsByPage = int(request.GET.get('recordsByPage'))

    if idRifa is None:
        # return http response error
        return HttpResponse(status=400)

    if page_number is None:
        page_number = 1
    if recordsByPage is None:
        recordsByPage = 10
    if contain is None:
        contain = '6'

    cantidadRegistros = NumeroRifaDisponibles.objects.filter(
        idRifa=idRifa, Numero__contains=contain).count()
    total_pages = cantidadRegistros / recordsByPage + \
        (cantidadRegistros % recordsByPage != 0)

    numeros = list(NumeroRifaDisponibles.objects.annotate(numInt=Cast('Numero', output_field=IntegerField())).filter(
        idRifa=idRifa, Numero__contains=contain).order_by('numInt')[(page_number-1)*recordsByPage:(page_number)*recordsByPage].values())

    data['data'] = numeros
    data['page'] = page_number
    data['total_pages'] = math.trunc(total_pages)
    data['page_number'] = page_number
    data['cantidadRegistros'] = cantidadRegistros
    data['recordsByPage'] = recordsByPage

    logger.info(data)

    return JsonResponse(data)


def RifabyComprados(request):
    data = {}
    page_number = request.GET.get('page')
    contain = request.GET.get('contain')
    rifa = request.GET.get('rifa')

    if page_number is None:
        page_number = 1
    if contain is None:
        contain = '6'

    rifa = RifaModel.objects.get(Id=2)
    comprados = NumeroRifaComprados.objects.filter(idRifa=rifa.Id)
    comprados = ['1', '2', '5', '7']

    nums = [str(number) for number in range(rifa.RangoInicial,
                                            rifa.RangoFinal+1, rifa.Intervalo) if str(number) not in comprados]

    cantidadRegistros = len(nums)
    total_pages = cantidadRegistros / 10 + (cantidadRegistros % 10 != 0)

    data['data'] = nums[(page_number-1)*10:(page_number)*10]
    data['total_pages'] = total_pages
    data['page_number'] = page_number
    data['cantidadRegistros'] = cantidadRegistros
    logger.info(data)

    return JsonResponse(data)

def VerificaBoletos(request):
  try:
    country_time_zone = pytz.timezone('America/Caracas')
    country_time = datetime.now(country_time_zone)
    logger.info(country_time.strftime("Date is %d-%m-%y and time is %H:%M:%S"))
    country_time_zone = pytz.timezone('America/Caracas')
    country_time = datetime.now(country_time_zone)
    data = json.load(request)
    cedula = data.get("cedula") or None
    correo = data.get("correo") or None
    id_rifa = data["Rifa"]

    Rifas=RifaModel.objects.filter(Estado=True).filter(Eliminada=False)
    Rifa=Rifas.filter(pk=id_rifa).first()
    compras = []
    numerosAprobados = []
    numerosPendientes = []
    print('verificador cedula: ' + str(cedula))
    print('verificador correo: ' + str(correo))

    if cedula is None and correo is None:
        return JsonResponse({"result": False, "message": '¡Disculpe! Debe ingresar su cedula o correo para continuar'})
    if cedula is not None:
        comprador = Comprador.objects.filter(Cedula=cedula).values('Nombre','Cedula','Correo').first()
        compras = list(Compra.objects.filter(idRifa=Rifa, idComprador__Cedula=cedula).values('Id'))
        numerosAprobados = list(NumerosCompra.objects.filter(idCompra__idRifa=Rifa, idCompra__Estado=Compra.EstadoCompra.Pagado, idCompra__idComprador__Cedula=cedula).values('Numero'))
        numerosPendientes = list(NumerosCompra.objects.filter(idCompra__idRifa=Rifa, idCompra__Estado=Compra.EstadoCompra.Pendiente, idCompra__idComprador__Cedula=cedula).values('Numero'))
            
        context = {
            "cedula": cedula,
            "compras": compras,
            "comprador": comprador,
            "numerosAprobados": numerosAprobados,
            "numerosPendientes": numerosPendientes,
        }
        if len(compras) == 0:
            return JsonResponse({"result": False, "message": '¡Disculpe! No existe registro en nuestro sistema con esta cádula para esta rifa'})
        if len(numerosAprobados) <= 0 and len(numerosPendientes) <= 0:
            return JsonResponse({"result": False, "message": 'Aun no tienes compras aprobadas en esta rifa'})
        return JsonResponse({"result": True, "data": context})
    if correo is not None:
        comprador = Comprador.objects.filter(Correo=correo).values('Nombre','Cedula','Correo').first()
        compras = list(Compra.objects.filter(idRifa=Rifa, idComprador__Correo=correo).values('Id'))
        numerosAprobados = list(NumerosCompra.objects.filter(idCompra__idRifa=Rifa, idCompra__Estado=Compra.EstadoCompra.Pagado, idCompra__idComprador__Correo=correo).values('Numero'))
        numerosPendientes = list(NumerosCompra.objects.filter(idCompra__idRifa=Rifa, idCompra__Estado=Compra.EstadoCompra.Pendiente, idCompra__idComprador__Correo=correo).values('Numero'))
            
        context = {
            "cedula": cedula,
            "compras": compras,
            "comprador": comprador,
            "numerosAprobados": numerosAprobados,
            "numerosPendientes": numerosPendientes,
        }
        if len(compras) == 0:
            return JsonResponse({"result": False, "message": '¡Disculpe! No existe registro en nuestro sistema con este correo electrónico para esta rifa'})
        if len(numerosAprobados) <= 0 and len(numerosPendientes) <= 0:
            return JsonResponse({"result": False, "message": 'Aun no tienes compras aprobadas en esta rifa'})
        return JsonResponse({"result": True, "data": context})
  except Exception as e:
    logger.info(e)
    return JsonResponse({"result": False, "message": 'Error al procesar la solicitud'}, status=400)
 
def RifabyCompradosArray(request):

    data = {}
    page_number = request.GET.get('page')
    contain = request.GET.get('contain')
    rifa = request.GET.get('rifa')

    if page_number is None:
        page_number = 1
    if contain is None:
        contain = '6'

    rifa = RifaModel.objects.get(Id=2)
    comprados = NumeroRifaCompradosArray.objects.get(idRifa=rifa.Id).Numeros

    nums = [str(number) for number in range(rifa.RangoInicial,
                                            rifa.RangoFinal+1, rifa.Intervalo) if str(number) not in comprados]

    cantidadRegistros = len(nums)
    total_pages = cantidadRegistros / 10 + (cantidadRegistros % 10 != 0)

    data['data'] = nums[(page_number-1)*10:(page_number)*10]
    data['total_pages'] = total_pages
    data['page_number'] = page_number
    data['cantidadRegistros'] = cantidadRegistros
    logger.info(data)

    return JsonResponse(data)
# endregion
# region "compra"


def CompraRifabyArrayDisponibles(request):
    comprados = ['2', '5', '7', '9']

    disp = NumeroRifaDisponiblesArray.objects.get(idRifa=2)
    for x in comprados:
        disp.Numeros.remove(x)

    disp.save()
    return HttpResponse()


def CompraRifabyDisponibles(request):
    rifa = request.GET.get('rifa')

    if rifa is None:
        return HttpResponse("No rifa encontrada", status=400)

    comprados = ['2', '5', '7', '9']
    disp = NumeroRifaDisponibles.objects.filter(
        idRifa=rifa, Numero__in=comprados)

    if disp.count() != len(comprados):
        logger.info(disp.count())
        logger.info(len(comprados))

        return HttpResponse("Hay numeros no disponibles", status=400)

    disp = NumeroRifaDisponibles.objects.filter(
        idRifa=rifa, Numero__in=comprados).delete()

    return HttpResponse()


def CompraRifabyComprados(request):
    compradosL = ['2', '5', '7', '9', '66']
    rifa = RifaModel.objects.get(Id=2)
    for x in compradosL:
        comprados = NumeroRifaComprados(idRifa=rifa,  Numero=x)
        comprados.save()
    return HttpResponse()


def CompraRifabyCompradosArray(request):
    compradosL = ['2', '5', '7', '9', '66']

    comprados = NumeroRifaCompradosArray.objects.get(idRifa=2)
    for x in compradosL:
        comprados.Numeros.append(x)
        logger.info(x)

    comprados.save()

    return HttpResponse()


# endregion
# region Consulta
def ConsultaRifabyDisponiplesOLD(request):
    num = request.GET.get('num')
    rifa = request.GET.get('rifa')

    if num is None or rifa is None:
        return HttpResponse(status=400)
    consultaNum = NumeroRifaDisponibles.objects.filter(
        Numero=num, idRifa=rifa).count()

    if consultaNum == 0:
        return JsonResponse({"result": False})
    else:
        return JsonResponse({"result": True})

def ConsultaRifabyDisponiples(request):
    nums= request.GET.get('num')
    rifa = request.GET.get('rifa')
    idorden = request.GET.get('orden')
    Orden =OrdenesReservas.objects.get(Id=idorden)
    numeroReserva=NumeroRifaReservadosOrdenes.objects.filter(idOrden=Orden)
    
    
    if nums is None or rifa is None:
        return JsonResponse({"result": False, "data": 'No se recibieron los parametros necesarios'})
    nums=int(nums)
    
    consultaNum = NumeroRifaDisponibles.objects.filter( idRifa=rifa)
    rifaC = RifaModel.objects.get(Id=rifa)

    if rifaC.TotalComprados+ nums>rifaC.TotalNumeros or rifaC.TotalComprados==rifaC.TotalNumeros:
        return JsonResponse({"result": False, "data": 'El numero de numeros a comprar es mayor a los disponibles'})



    if  consultaNum.count() == 0 or consultaNum.count()<nums:
        return JsonResponse({"result": False, "data": 'El numero de numeros a comprar es mayor a los disponibles'})
    
    return JsonResponse({"result": True, "data": []})



def ConsultaRifabyDisponiplesTodos(request):
    rifa = request.GET.get('rifa')

    data = {}

    consultaNum = list(
        NumeroRifaDisponibles.objects.filter(idRifa=rifa).values())
    data['data'] = consultaNum
    return JsonResponse({"result": data})


def ConsultaRifabyDisponiplesLista(request):
    data = json.load(request)
    nums = data["Numbers"]
    rifa = data["Rifa"]
    if nums is None or rifa is None:
        return HttpResponse(status=400)

    consulta = ConsultaRifabyDisponiplesListaMethod(nums, rifa)
    return JsonResponse({"result": consulta['result'], "data": consulta['data']})

    if nums is None or rifa is None:
        return HttpResponse(status=400)

    dataReturn = []
    if nums:
        for x in nums:
            consultaNum = NumeroRifaDisponibles.objects.filter(
                idRifa=rifa, Numero=x['num']).count()
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
        return JsonResponse({"result": False, "data": 'El numero de numeros a comprar es mayor rango permitido'})
    if nums < rifaC.MinCompra:
        return JsonResponse({"result": False, "data": 'El numero de numeros a comprar es menor rango permitido'})
    if nums > NumeroRifaDisponibles.objects.filter(idRifa=rifa).count():
        return JsonResponse({"result": False, "data": 'El numero de numeros a comprar es mayor a los disponibles'})
    
    consultaNum = NumeroRifaDisponibles.objects.filter(idRifa=rifa)
    rifaC = RifaModel.objects.get(Id=rifa)

    if rifaC.TotalComprados+ nums>rifaC.TotalNumeros or rifaC.TotalComprados==rifaC.TotalNumeros:
        return JsonResponse({"result": False, "data": 'El numero de numeros a comprar es mayor a los disponibles'})

    if  consultaNum.count() == 0 or consultaNum.count()<nums:
        return JsonResponse({"result": False, "data": 'El numero de numeros a comprar es mayor a los disponibles'})

    return JsonResponse({"result": True, "data": []})

def ConsultaRifabyDisponiple(request):
    data = json.load(request)
    num = data["Number"]
    rifa = data["Rifa"]
    if num is None or rifa is None:
        return HttpResponse(status=400)
    
    consultaNum = NumeroRifaDisponibles.objects.filter(idRifa=rifa, Numero=num)

    if  consultaNum.count() == 0:
        return JsonResponse({"result": False, "data": 'El numero no se encuentra disponible'})

    return JsonResponse({"result": True, "data": []})


def ConsultaRifabyDisponiplesListaMethod(nums, rifa):

    dataReturn = []
    if nums:
        for x in nums:
            consultaNum = NumeroRifaDisponibles.objects.filter(
                idRifa=rifa, Numero=x['num']).count()
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
        numbers = request.POST.get('numbers')
        rifa = request.POST.get('idRifa')

    # get random numbers from numerosbydisponibles
        disp = NumeroRifaDisponibles.objects.filter(
            idRifa=rifa).order_by('?')[:numbers]


def CompraNumerosByDisponibles(request):
    if request.method == "POST":
        data = json.load(request)
        nums = data["Numbers"]
        rifaId = data["Rifa"]
        user = data["User"]

        logger.info(nums)
        logger.info(user)
        arrayNums = [x['num'] for x in nums]
        logger.info(arrayNums)

        if rifaId is None:
            return HttpResponse("No rifa encontrada", status=400)
        rifa = RifaModel.objects.get(Id=rifaId)
        comprados = nums
        disp = NumeroRifaDisponibles.objects.filter(
            idRifa=rifa, Numero__in=arrayNums)

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
                    "whatsapp_config":Settings.objects.filter(code="PHONE_CLIENT").first(),
                    "percent_config":Settings.objects.filter(code="HIDE_TICKET_COUNT").first(),
                }
                logger.info(context)
                body = render_to_string('Rifa/Correo.django', context)
                plain_message = body
                logger.info(user["Correo"])
                with get_connection(
                    host=settings.EMAIL_HOST,
                    port=settings.EMAIL_PORT,
                    username=settings.EMAIL_HOST_USER,
                    password=settings.EMAIL_HOST_PASSWORD,
                    use_tls=settings.EMAIL_USE_TLS
                ) as connection:
                    subject = f'Felicidades por tu Compra {user["Nombre"]}'
                    email_from = settings.EMAIL_HOST_USER
                    recipient_list = [user["Correo"]]
                    message = plain_message
                    email = EmailMessage(
                        subject, message, email_from, recipient_list, connection=connection)
                    email.content_subtype = 'html'
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
    arrayNums = [x['num'] for x in nums]
    logger.info(arrayNums)

    if rifaId is None:
        return False
        return HttpResponse("No rifa encontrada", status=400)
    if len(list(RifaModel.objects.filter(Id=rifaId).values())) == 0:
        logger.info("No rifa encontrada")
        return False
        return HttpResponse("No rifa encontrada", status=400)

    rifa = RifaModel.objects.get(Id=rifaId)
    country_time_zone = pytz.timezone('America/Caracas')
    country_time = datetime.now(country_time_zone)
    if country_time >= rifa.FechaSorteo:
         if rifa.Extension==False:
            logger.info("La rifa a la que intenta comprar ya no esta disponible")
            return False
            return HttpResponse("Error, la rifa a la que intenta comprar ya no esta disponible", status=400)

    if len(list(data["Numbers"])) < rifa.MinCompra:
        logger.info("Error,la cantidad de numeros a comprar es menor a la minima permitida ")
        return False
        return HttpResponse("Error,la cantidad de numeros a comprar es menor a la minima permitida ", status=400)

    comprados = nums
    disp = NumeroRifaDisponibles.objects.filter(
        idRifa=rifa, Numero__in=arrayNums)
    '''  

        if disp.count() != len(arrayNums):
            logger.info(disp.count())
            logger.info(len(arrayNums))
            logger.info("Hay numeros no disponibles")
            return False
            return HttpResponse("Hay numeros no disponibles", status=400)
            '''
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
                "whatsapp_config":Settings.objects.filter(code="PHONE_CLIENT").first(),
                "percent_config":Settings.objects.filter(code="HIDE_TICKET_COUNT").first(),
            }
            logger.info(context)
            rifa.TotalComprados = rifa.TotalComprados+len(arrayNums)
            rifa.save()
            body = render_to_string('Rifa/Correo.django', context)
            plain_message = body
            logger.info(user["Correo"])
            with get_connection(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                use_tls=settings.EMAIL_USE_TLS
            ) as connection:
                subject = f'Felicidades por tu Compra {user["Nombre"]}'
                email_from = settings.EMAIL_HOST_USER
                recipient_list = [user["Correo"]]
                message = plain_message
                email = EmailMessage(
                    subject, message, email_from, recipient_list, connection=connection)
                email.content_subtype = 'html'
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
        use_tls=settings.EMAIL_USE_TLS
    ) as connection:
        subject = f'Felicidades por tu Compra {user["Nombre"]}'
        email_from = settings.EMAIL_HOST_USER
        recipient_list = [user["Correo"]]
        message = plain_message

    try:

        email = EmailMessage(subject, message, email_from,
                             recipient_list, connection=connection)
        email.content_subtype = 'html'
        email.send()
    except Exception as e:
        return HttpResponse("")

    return HttpResponse("")


async def EmailBody(user, nums):
    template = loader.get_template('Rifa/Correo.django')
    context = {
        "nums": nums,
        "user": user,
        "whatsapp_config":Settings.objects.filter(code="PHONE_CLIENT").first(),
        "percent_config":Settings.objects.filter(code="HIDE_TICKET_COUNT").first(),
    }

    return render_to_string('Rifa/Correo.django', context)
    template
    context = {
        "form": request
    }
    return HttpResponse(template.render(context, request))

# region S3
# method to upload to S3 and get link


def upload_to_s3(file, bucket_name, acl="public-read"):
    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )

    try:
        s3.upload_fileobj(
            file,
            bucket_name,
            file.name,
            ExtraArgs={
                "ACL": acl,
                "ContentType": file.content_type
            }
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
        "password": settings.EKIIPAGO["password"]
    }
    r = RR.post(url, data=data)
    return r.json()["access_token"]

def ReenviarComprobante(request):
    if request.method == "POST":
        data = json.load(request)

        try:
            id = data["id"]
            CompraObj = Compra.objects.get(Id=id)
            arr = [x['Numero'] for x in NumerosCompra.objects.filter(
                idCompra=CompraObj).values('Numero')]
            logger.info(arr)
            context = {
                "nums": arr,
                "rifa": CompraObj.idRifa,
                "reference": CompraObj.Id,
                "user": CompraObj.idComprador,
                "totalpago": CompraObj.TotalPagado,
                "len": CompraObj.NumeroBoletos,
                "compra": CompraObj,
                "whatsapp_config":Settings.objects.filter(code="PHONE_CLIENT").first(),
                "percent_config":Settings.objects.filter(code="HIDE_TICKET_COUNT").first(),
            }
            logger.info(context)
            texto=f"¡Felicidades "+CompraObj.idComprador.Nombre+"! Tu compra ["+str(CompraObj.Id)+"] ha sido aprobada, puedes consultar tus boletos en el siguiente enlace, asegúrate de no compartirlo con nadie. "+settings.URL+"/Comprobante/"+str(CompraObj.hash)
            numero = CompraObj.idComprador.NumeroTlf
            numero = re.sub(r'\s+', '', numero.strip())

            enviarWhatsapp(texto, numero)
            body = render_to_string('Rifa/Correo.django', context)
            plain_message = body
            with get_connection(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                use_tls=settings.EMAIL_USE_TLS
            ) as connection:
                subject = f'Tu compra ha sido aprobada {CompraObj.idComprador.Nombre}'
                email_from = settings.EMAIL_HOST_USER
                recipient_list = [CompraObj.idComprador.Correo]
                message = plain_message
                email = EmailMessage(subject, message, email_from,
                                    recipient_list, connection=connection)
                email.content_subtype = 'html'
                email.send()
            return JsonResponse({"message": "Éxito", "status": 200}, status=200)
        except Exception as e:
                logger.info(4)

                logger.info(e)
                return JsonResponse({"message": "Error", "status": 400}, status=400)
@shared_task()
def sendEmail(nombre, correo, idRifa, compraId):
              Logger.objects.create(date=datetime.now(), description=f"Running Celery {correo} {idRifa} ", evento="Celery Correo")
              rifa = RifaModel.objects.get(Id=idRifa)

              # validar compra
              compra=Compra.objects.get(Id=compraId)
              # get numeros compra
              arr = [x['Numero'] for x in NumerosCompra.objects.filter( idCompra=compra).values('Numero')] 
              # if 0 rechazar comprar
              if len(arr)==0:
                    compra.Estado = Compra.EstadoCompra.Rechazado
                    compra.save()
                    RifaC=RifaModel.objects.get(Id=compra.idRifa.Id)
                    loggerRechazo=LoggerAprobadoRechazo.objects.create(date=datetime.now(), description=f"Compra Rechazada {compra.Id} 0 numeros", evento="Rechazada 0", idCompra=compra.Id)
                    loggerRechazo.save()
                    compra.recuperado=True
                    compra.save()
                    body = render_to_string('Rifa/CorreoRechazo.django', {
                        "whatsapp_config":Settings.objects.filter(code="PHONE_CLIENT").first(),
                        "percent_config":Settings.objects.filter(code="HIDE_TICKET_COUNT").first(),
                    })
                    print(settings.EMAIL_HOST_USER)
                    print(settings.EMAIL_HOST_PASSWORD)
                    plain_message = body
                    with get_connection(
                        host=settings.EMAIL_HOST,
                        port=settings.EMAIL_PORT,
                        username=settings.EMAIL_HOST_USER,
                        password=settings.EMAIL_HOST_PASSWORD,
                        use_tls=settings.EMAIL_USE_TLS
                    ) as connection:
                        subject = f'Detalles sobre tu Compra {compra.idComprador.Nombre}'
                        email_from = settings.EMAIL_HOST_USER 
                        recipient_list = [compra.idComprador.Correo]
                        message = plain_message
                        email = EmailMessage(subject, message, email_from,
                                            recipient_list, connection=connection)
                        email.content_subtype = 'html'
                        email.send()
                    
                  

              

              body = render_to_string('Rifa/CorreoCompra.django', {"rifa": rifa, "whatsapp_config":Settings.objects.filter(code="PHONE_CLIENT").first(),"percent_config":Settings.objects.filter(code="HIDE_TICKET_COUNT").first(),})
              print(settings.EMAIL_HOST_USER)
              print(settings.EMAIL_HOST_PASSWORD)
              plain_message = body
              with get_connection(
                        host=settings.EMAIL_HOST,
                        port=settings.EMAIL_PORT,
                        username=settings.EMAIL_HOST_USER,
                        password=settings.EMAIL_HOST_PASSWORD,
                        use_tls=settings.EMAIL_USE_TLS
                    ) as connection:
                        subject = f'Felicidades por tu Compra {nombre}'
                        email_from = settings.EMAIL_HOST_USER
                        recipient_list = [correo]
                        message = plain_message
                        email = EmailMessage(
                            subject, message, email_from, recipient_list, connection=connection)
                        email.content_subtype = 'html'
                        email.send()

@permission_required('Rifa.change_compra', raise_exception=True)          
def aprobarCompra(request):
    if request.method == "POST":
        try:
            with transaction.atomic():
                data = json.load(request)
                id = data["id"]
                logger.info(id)
                CompraObj = Compra.objects.get(Id=id)
                CompraObj.Estado = Compra.EstadoCompra.Pagado
                country_time_zone = pytz.timezone('America/Caracas')
                country_time = datetime.now(country_time_zone)
  
                CompraObj.FechaEstado=country_time
                CompraObj.save()
                # array numbers
                arr = [x['Numero'] for x in NumerosCompra.objects.filter(
                    idCompra=CompraObj).values('Numero')]
                logger.info(arr)
                logAprobado=LoggerAprobadoRechazo.objects.create(date=datetime.now(), description=f"Compra Aprobada {CompraObj.Id}", evento="Aprobada", idCompra=CompraObj)
                logAprobado.save()
                context = {
                    "nums": arr,
                    "rifa": CompraObj.idRifa,
                    "reference": CompraObj.Id,
                    "user": CompraObj.idComprador,
                    "totalpago": CompraObj.TotalPagado,
                    "len": CompraObj.NumeroBoletos,
                    "compra": CompraObj,
                    "whatsapp_config":Settings.objects.filter(code="PHONE_CLIENT").first(),
                    "percent_config":Settings.objects.filter(code="HIDE_TICKET_COUNT").first(),
                }
                logger.info(context)
                logger.info(settings.URL)
                texto=f"¡Felicidades "+CompraObj.idComprador.Nombre+"! Tu compra ["+str(CompraObj.Id)+"] ha sido aprobada, puedes consultar tus boletos en el siguiente enlace, asegúrate de no compartirlo con nadie. "+settings.URL+"/Comprobante/"+str(CompraObj.hash)
                numero = CompraObj.idComprador.NumeroTlf
                numero = re.sub(r'\s+', '', numero.strip())
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
    compras=Compra.objects.filter(idRifa=18)
    for x in compras:
        #delete local file
        
        logger.info("/opt/bitnami/projects/PROJECT/Proyecto-Ballena/proyectoBallena"+x.Comprobante.url)

        try:
            if os.path.exists("/opt/bitnami/projects/PROJECT/Proyecto-Ballena/proyectoBallena"+x.Comprobante.url):
                logger.info("file exist")
                os.remove("/opt/bitnami/projects/PROJECT/Proyecto-Ballena/proyectoBallena"+x.Comprobante.url)
            # if file exist
            
        except Exception as e:
            logger.info(e)
            pass

def enviarWhatsapp(texto, numero):
    formatted_number = re.sub(r'[^0-9]', '', numero)
    try:
        '''
        conn = http.client.HTTPConnection("http://api.message.sinvad.lat",80)

        payload = [
            {
                "attachments": [],
                "subject": "",
                "to": [numero],
                "message": texto,
                "typeMessage": 0
            }
        ]

        headers = {
            'Content-Type': "application/json",
            'Authorization': "E37C6F0847DB4E6205787C8AE89AC670540DD97A86DB53ACB4BC6BE961C76D70A5CC68055CF2E1CCD35C45197DA398425CACEBA217E0D1529AFE8AA8EE754A73",
            'SiteAllowed': "NOURL",
            'UserName': "JALEXZANDER",
            "UserApp": "_LOGINVALUSER_",

        }

        conn.request("POST", "/api/Message/AddMessagestoQueue", json.dumps(payload), headers)

        res = conn.getresponse()
        print(res)
        data = res.read()
        '''
        url="http://api.message.sinvad.lat/api/Message/AddMessagestoQueue"
        payload = [
            {
                "attachments": [],
                "subject": "",
                "to": [formatted_number],
                "message": texto,
                "typeMessage": 0
            }
        ]

        headers = {
            'Content-Type': "application/json",
            'Authorization': "E37C6F0847DB4E6205787C8AE89AC670540DD97A86DB53ACB4BC6BE961C76D70A5CC68055CF2E1CCD35C45197DA398425CACEBA217E0D1529AFE8AA8EE754A73",
            'SiteAllowed': "NOURL",
            'UserName': "JALEXZANDER",
            "UserApp": "_LOGINVALUSER_",

        }

        res=RR.post(url, headers=headers, json=payload)

        logger.info(res.text)
    except Exception as e:
        logger.info(e)
        return
    return

def generate_random_text(length): 
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for i in range(length))


def testWhatsapp():
    try:
        conn = http.client.HTTPConnection("sinvadmessage.sytes.net",80)
        # ramdom unique text
        random_text = generate_random_text(10) 

        payload = [
            {
                "attachments": [],
                "subject": "",
                "to": ['04147945595'],
                "message": random_text,
                "typeMessage": 0
            }
        ]

        headers = {
            'Content-Type': "application/json",
            'Authorization': "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJOT1VSTCIsInVzciI6IkpBTEVYWkFOREVSIiwiZXhwIjo2NDAwMDk3MjgwMDAwMDAwMDAsImR0YiI6IlNJTlZBRF9NRVNTQUdFX0pBTEVYWkFOREVSIiwiY2JvIjoiIiwicHJjIjoiXCJ7XFxcIkFMTFxcXCI6ZmFsc2UsXFxcIkRBU0hCT0FSRFxcXCI6ZmFsc2UsXFxcIlNLVVxcXCI6ZmFsc2UsXFxcIkNMQVNJRklDQVRJT05TXFxcIjpmYWxzZSxcXFwiUFJFU0VOVEFUSU9OU1xcXCI6ZmFsc2UsXFxcIlRBWEVTXFxcIjpmYWxzZSxcXFwiV0hBUkVIT1VTRVxcXCI6ZmFsc2UsXFxcIkNMSUVOVFNcXFwiOmZhbHNlLFxcXCJTRUxMRVJTXFxcIjpmYWxzZSxcXFwiUEFZTUVOVENPTkRJVElPTlNcXFwiOmZhbHNlLFxcXCJPUkRFUlNcXFwiOmZhbHNlLFxcXCJQQVlNRU5UU1xcXCI6ZmFsc2UsXFxcIkdFTlRPS0VOVkFMSURBVElPTlxcXCI6ZmFsc2UsXFxcIk1FU1NBR0VTXFxcIjp0cnVlfVwiIn0.3RC49sXJ4I_z8dmHwU7xt9_trgvOamJjSkMLaupOIkF-6y2n27R9yuNXXAFbxQlMgQh27QwIWaqqLuB9Flsdig",
            'SiteAllowed': "NOURL",
            'UserName': "JALEXZANDER",
            "UserApp": "_LOGINVALUSER_",

        }

        conn.request("POST", "/api/Message/AddMessagestoQueue", json.dumps(payload), headers)

        res = conn.getresponse()
        data = res.read()

        return(data.decode("utf-8"))
    except Exception as e:
        return(e)


def rechazarCompra(request):
    if request.method == "POST":
      with transaction.atomic():  # create comprador
        data = json.load(request)
        id = data["id"]
        logger.info(id)
        CompraObj = Compra.objects.select_for_update().exclude(Estado=Compra.EstadoCompra.Rechazado).filter(Id=id)
        if len(CompraObj) == 0:
            raise Exception("Compra no encontrada")
        CompraObj=CompraObj[0]
        CompraObj.Estado = Compra.EstadoCompra.Rechazado
        country_time_zone = pytz.timezone('America/Caracas')
        country_time = datetime.now(country_time_zone)
  
        CompraObj.FechaEstado=country_time
        CompraObj.save()
        RifaC=RifaModel.objects.get(Id=CompraObj.idRifa.Id)
        numerosCompra=NumerosCompra.objects.filter(idCompra=CompraObj)
        loggerRechazo=LoggerAprobadoRechazo.objects.create(date=datetime.now(), description=f"Compra Rechazada {CompraObj.Id}", evento="Rechazada", idCompra=CompraObj)
        loggerRechazo.save()
        for x in numerosCompra:
                logger.info(x.Numero)
                NumeroRifaDisponibles.objects.create(Numero=x.Numero, idRifa=RifaC)
        RifaC.TotalComprados=F('TotalComprados')-CompraObj.NumeroBoletos
        RifaC.save()
        CompraObj.recuperado=True
        CompraObj.save()
        body = render_to_string('Rifa/CorreoRechazo.django', {
            "whatsapp_config":Settings.objects.filter(code="PHONE_CLIENT").first(),
            "percent_config":Settings.objects.filter(code="HIDE_TICKET_COUNT").first(),
        })
        logger.info(settings.EMAIL_HOST_USER)
        logger.info(settings.EMAIL_HOST_PASSWORD)
        plain_message = body
        with get_connection(
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_HOST_USER,
            password=settings.EMAIL_HOST_PASSWORD,
            use_tls=settings.EMAIL_USE_TLS
        ) as connection:
            subject = f'Detalles sobre tu Compra {CompraObj.idComprador.Nombre}'
            email_from = settings.EMAIL_HOST_USER 
            recipient_list = [CompraObj.idComprador.Correo]
            message = plain_message
            email = EmailMessage(subject, message, email_from,
                                 recipient_list, connection=connection)
            email.content_subtype = 'html'
            email.send()
        return JsonResponse({"message": "Éxito", "status": 200}, status=200)


def ComprarRifaOld(request):
    if request.method == "POST":
        # form uploadfile
        form = UploadFileForm(request.POST, request.FILES)
        logger.info(f"Archivos {request.FILES}")
        logger.info(f"Campos {request.POST}")
        logger.info(f"nombre {request.POST.get('nombre')}")
        logger.info(f"Formulario válido {form.is_valid()}",)
        logger.info(f"Formulario válido {form.errors}")
        if form.is_valid():
            idRifa = form.cleaned_data['idRifa']
            try:
                try:
                    rifa = RifaModel.objects.get(Id=idRifa)
                except:
                    return HttpResponse("Error, la rifa a la que intenta comprar no existe", status=400)
                # valida estado y publicacion
                if rifa.Estado == False or rifa.Eliminada == True:
                    return JsonResponse({"message": "Rifa no dispoible", "status": 422}, status=422)
                # valida rifa fecha
                country_time_zone = pytz.timezone('America/Caracas')
                country_time = datetime.now(country_time_zone)
                if country_time >= rifa.FechaSorteo:
                  if rifa.Extension==False:

                    return JsonResponse({"message": "Rifa expirada", "status": 422}, status=422)
                if form.cleaned_data['numeros'] < rifa.MinCompra or form.cleaned_data['numeros'] > rifa.MaxCompra:
                    return JsonResponse({"message": "Cantidad invalida", "status": 422}, status=422)
                
                
                if form.cleaned_data['numeros'] > NumeroRifaDisponibles.objects.filter(idRifa=idRifa).count():
                    return JsonResponse({"message": "Hay numeros no disponibles", "status": 422}, status=422)
                
                #validate file size 4mb
                if request.FILES['file'].size > 4194304 :
                    return JsonResponse({"message": "Archivo muy grande", "status": 422}, status=422)
                #validate file extension pdf and images
                if not request.FILES['file'].name.endswith('.pdf') and not request.FILES['file'].name.endswith('.jpg') and not request.FILES['file'].name.endswith('.png') and not request.FILES['file'].name.endswith('.jpeg'):
                    return JsonResponse({"message": "Archivo no valido", "status": 422}, status=422)
                #validate distint referece
            #    if Compra.objects.filter(Referencia=form.cleaned_data['referencia']).count() > 0:
             #       return JsonResponse({"message": "Referencia ya existe", "status": 422}, status=422)                
                
                with transaction.atomic():  # create comprador
                    comprador = Comprador()
                    comprador.Nombre = form.cleaned_data['nombre']
                    comprador.Correo = form.cleaned_data['correo']
                    comprador.NumeroTlf = form.cleaned_data['numeroTlf']
                    # comprador.Direccion=form.cleaned_data['direccion']
                    comprador.Cedula = form.cleaned_data['cedula']
                    comprador.save()

                    # save file locally

                    # get random numbers from numerosbydisponibles
                    idRifa = form.cleaned_data['idRifa']
                    disp = NumeroRifaDisponibles.objects.filter(
                        idRifa=form.cleaned_data['idRifa']).order_by('?')[:form.cleaned_data['numeros']]

                    # create compra
                    compra = Compra()
                    compra.idComprador = comprador
                    compra.idRifa = RifaModel.objects.get(
                        Id=form.cleaned_data['idRifa'])
                    compra.Comprobante = request.FILES['file']
                    # last tasa
                    compra.TasaBS = Tasas.objects.latest('id').tasa
                    compra.Referencia = form.cleaned_data['referencia']
                    compra.FechaCompra
                    country_time_zone = pytz.timezone('America/Caracas')
                    country_time = datetime.now(country_time_zone)
                    compra.FechaCompra = country_time
                    compra.NumeroBoletos = form.cleaned_data['numeros']
                    compra.TotalPagado = form.cleaned_data['numeros'] * \
                        compra.idRifa.Precio
                    compra.save()
                    for x in disp:
                        NumeroRifaComprados.objects.create(
                            idRifa=RifaModel.objects.get(Id=idRifa), Numero=x.Numero)
                        NumerosCompra.objects.create(
                            idCompra=compra, Numero=x.Numero)
                        NumeroRifaDisponibles.objects.get(
                            idRifa=idRifa, Numero=x.Numero).delete()
                    rifa.TotalComprados = F("TotalComprados")  + \
                        form.cleaned_data['numeros']
                    rifa.save()
                    body = render_to_string('Rifa/CorreoCompra.django', {"rifa": rifa,"whatsapp_config":Settings.objects.filter(code="PHONE_CLIENT").first(),"percent_config":Settings.objects.filter(code="HIDE_TICKET_COUNT").first()})
                    logger.info(settings.EMAIL_HOST_USER)
                    logger.info(settings.EMAIL_HOST_PASSWORD)
                    plain_message = body
                    with get_connection(
                        host=settings.EMAIL_HOST,
                        port=settings.EMAIL_PORT,
                        username=settings.EMAIL_HOST_USER,
                        password=settings.EMAIL_HOST_PASSWORD,
                        use_tls=settings.EMAIL_USE_TLS
                    ) as connection:
                        subject = f'Felicidades por tu Compra {form.cleaned_data["nombre"]}'
                        email_from = settings.EMAIL_HOST_USER
                        recipient_list = [form.cleaned_data["correo"]]
                        message = plain_message
                        email = EmailMessage(
                            subject, message, email_from, recipient_list, connection=connection)
                        email.content_subtype = 'html'
                        email.send()
                    return JsonResponse({"message": "Éxito", "status": 200}, status=200)
            except Exception as ex:
                logger.info(ex)
                return JsonResponse({"message": "Error en el servidor", "status": 500}, status=500)
        else:
            return JsonResponse({"errors": form.errors.as_json(), "message": "error de validacion", "status": 422}, status=422)
def registerlog (request):
  # wait 50 seconds
  time.sleep(5)
  #NONCE = str(int(time.time() * 1000))
  #Logger.objects.create(date=datetime.now(), description=f"Probando Estres{NONCE} ")
  jeje.delay( )
  return JsonResponse({"message": "Éxito", "status": 200}, status=200)

@shared_task
def jeje():
    time.sleep(10)
    NONCE = str(int(time.time() * 1000))
    Logger.objects.create(date=datetime.now(), description=f"Probando Celery {NONCE}", evento="Celery")

def ComprarRifa(request):
    if request.method == "POST":
        # form uploadfile
        form = SecondFileForm(request.POST, request.FILES)
        country_time_zone = pytz.timezone('America/Caracas')
        country_time = datetime.now(country_time_zone)
        if form.is_valid():
            idOrden = form.cleaned_data['idOrden']

            try:
                try:
                    print(country_time-timedelta(minutes=10))

                    ordenes= OrdenesReservas.objects.filter(date__gte=country_time-timedelta(minutes=10))
                    orden = ordenes.get(Id=idOrden)
                except:
                    return JsonResponse({"message": "Error, la orden no existe", "status": 400}, status=422)
                
                
                # if orden is more than 10 min error
                if orden.date <= country_time-timedelta(minutes=10):
                    return JsonResponse({"message": "Error, la orden ha expirado", "status": 422}, status=422)
                
                


                
                rifa = RifaModel.objects.get(Id=orden.idRifa.Id)
              
                
                #validate file size 4mb
                if request.FILES['file'].size > 4194304 :
                    return JsonResponse({"message": "Archivo muy grande", "status": 422}, status=422)
                
                if not request.FILES['file'].name.endswith('.pdf') and not request.FILES['file'].name.endswith('.jpg') and not request.FILES['file'].name.endswith('.png') and not request.FILES['file'].name.endswith('.jpeg'):
                    return JsonResponse({"message": "Archivo no valido", "status": 422}, status=422)
                
                with transaction.atomic():  # create comprador
                    # Verificar si hay un cliente autenticado vinculado a esta orden
                    cliente = None
                    if request.user.is_authenticated and hasattr(request.user, 'cliente'):
                        cliente = request.user.cliente
                        # Buscar si ya existe un Comprador para este cliente
                        comprador_existente = Comprador.objects.filter(idCliente=cliente).first()
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
                        idOrden=idOrden)
                    totalNum=disp.count()

                    numerosForm=form.cleaned_data['Cantidad'] 
                    logger.info(form.cleaned_data['Cantidad'] )
                    logger.info(totalNum)
                    logger.info(numerosForm)

                    if totalNum != numerosForm:
                        return JsonResponse({"message": "Error en su solicitud por favor, recargue la pagina y vuelva a intentar", "status": 422}, status=422)
                    # create compra
                    compra = Compra()
                    compra.idComprador = comprador
                    compra.idRifa = RifaModel.objects.get(
                        Id=rifa.Id)
                    compra.Comprobante = request.FILES['file']
                    # last tasa
                    compra.TasaBS = Tasas.objects.latest('id').tasa
                    compra.Referencia = form.cleaned_data['referencia']
                    compra.MetodoPago = form.cleaned_data['tipoPago']
                    compra.FechaCompra
                    country_time_zone = pytz.timezone('America/Caracas')
                    if(request.user.is_authenticated):
                        compra.author=request.user
                    country_time = datetime.now(country_time_zone)
                    compra.FechaEstado=country_time
                    compra.FechaCompra = country_time
                    compra.NumeroBoletos = totalNum
                    compra.TotalPagado = totalNum* \
                        compra.idRifa.Precio
                    compra.TotalPagadoAlt = totalNum* \
                        compra.idRifa.PrecioAlt
                    compra.save()
                    logger.info(f"compra guardada as: {compra}")

                    for x in disp:
                        NumeroRifaComprados.objects.create(
                            idRifa=RifaModel.objects.get(Id=rifa.Id), Numero=x.Numero)
                        NumerosCompra.objects.create(
                            idCompra=compra, Numero=x.Numero)
                        NumeroRifaReservadosOrdenes.objects.get(
                            idOrden=idOrden, Numero=x.Numero).delete()
                    rifa.TotalComprados = F("TotalComprados")  + \
                        totalNum
                    
                    orden.completada=True
                    orden.save()
                    rifa.save()
                 #   transaction.on_commit(lambda: validateCompra(compra))
                    # transaction.on_commit(lambda: sendEmail.delay(comprador.Nombre, comprador.Correo, rifa.Id, compra.Id))
      
                    numeros_apartados = [x.Numero for x in disp]
                    return JsonResponse({"message": "Éxito", "status": 200, "numeros": numeros_apartados}, status=200)
            except Exception as ex:
                logger.info(ex)
                print(ex)
                return JsonResponse({"message": "Error en el servidor", "status": 500 , "err":f"{ex}"}, status=500)
        else:
            return JsonResponse({"errors": form.errors.as_json(), "message": "error de validacion", "status": 422}, status=422)


def sss(request):
    try:
        country_time_zone = pytz.timezone('America/Caracas')
        country_time = datetime.now(country_time_zone)
        # get NumeroRifaReservados with more of 15 minutes in date field
        numeros=NumeroRifaReservadosOrdenes.objects.filter(date__lte=country_time-timedelta(minutes=16))
        Logger.objects.create(date=country_time, description=f"Ejecutando Cron {list(numeros)} reservados recuperados")
        
        for x in numeros:
            NumeroRifaDisponibles.objects.create(Numero=x.Numero, idRifa=x.idRifa)
        
        numeros.delete()
    except Exception as ex:
                    logger.info(ex)
                    print(ex)
                    return JsonResponse({"message": "Error en el servidor", "status": 500 , "err":f"{ex}"}, status=500)

    return JsonResponse({ "message": "ok", "status": 200}, status=200)



def validateCompra(compra):
    
    return
 
def CheckPay(request):
    if request.method == "POST":
        # agregar validaciones
        data = json.load(request)
        token = get_token()
        url=f'https://apiplaza.celupagos.com/payment/searchTransaction?reference={data["Orden"]["reference"]}&mode=Integration'
        response= get_data(url, token)
        logger.info(response)
        logger.info(response['codigoHttp'])
        logger.info(response['codigoHttp'] != 200)

        if response['codigoHttp'] != 200:
            res = json.dumps(response)
            return HttpResponse(res, content_type="application/json")

            return HttpResponse(f"Error {response['clientMessage']}", status=400)

        if response['status'] != "PENDIENTE" and response['status'] != "SIMULACION_APROBADA":
            res = json.dumps(response)
            return HttpResponse(res, content_type="application/json")

            return HttpResponse(f"Error, Pago sin completar", status=400)

        logger.info(data["Orden"]["reference"])
        logger.info(data["Orden"]['orden'])

        orden = Ordenes.objects.get(reference=data["Orden"]["orden"])

        compra = Compra.objects.get(idOrden=orden)

        if str(compra.Estado) != Compra.EstadoCompra.Pendiente.value:
            return HttpResponse("Error, Pago ya realizado", status=400)

        compra.Estado = compra.EstadoCompra.Pagado
        compra.save()

        for num in data["Numbers"]:
            NumeroRifaComprados.objects.create(
                idRifa=RifaModel.objects.get(Id=data['Rifa']), Numero=num['num'])
            NumerosCompra.objects.create(idCompra=compra, Numero=num['num'])
            NumeroRifaReservados.objects.get(idRifa=RifaModel.objects.get(
                Id=data['Rifa']), Numero=num['num'], idOrden=orden).delete()

        res = json.dumps(response)
        comprado = CompraNumerosByDisponiblesMethod(data)
        if comprado == False:
            return HttpResponse("Error, Ocurrio un problema con su solicitud, intente nuevamente, comuniquese si necesita ayuda", status=400)

        return HttpResponse(res, content_type="application/json")


# method to pass auth token api to get data
def get_data(url, token):
    r = RR.get(url, headers={"Authorization": "Bearer " + token})
    return r.json()

# method to post data to auth api


def post_data(url, data, token):
    r = RR.post(url, data=data, headers={"Authorization": "Bearer " + token})
    return r.json()


def createOrderOld(request):
    if request.method == "POST":
        data = json.load(request)
        # valida Rifa existe
        try:
            rifa = RifaModel.objects.get(Id=data["Rifa"])
        except:
            return HttpResponse("Error, la rifa a la que intenta comprar no existe", status=400)
        # valida estado y publicacion
        if rifa.Estado == False or rifa.Eliminada == True:
            return HttpResponse("Error, la rifa a la que intenta comprar no existe", status=400)

      # valida rifa fecha
        country_time_zone = pytz.timezone('America/Caracas')
        country_time = datetime.now(country_time_zone)
        if country_time >= rifa.FechaSorteo:
         if rifa.Extension==False:

            return HttpResponse("Error, la rifa a la que intenta comprar ya no esta disponible", status=400)
        # valida Numeros
        consulta = ConsultaRifabyDisponiplesListaMethod(
            data["Numbers"], rifa.Id)
        if consulta["result"] == True:
            return HttpResponse("Error, Hay numeros no disponibles en sus seleccion ", status=400)
        logger.info(len(list(data["Numbers"])))
        if len(list(data["Numbers"])) < rifa.MinCompra:
            return HttpResponse("Error,la cantidad de numeros a comprar es menor a la minima permitida ", status=400)
        # calculo total

        total = rifa.Precio*len(list(data["Numbers"]))

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
                orden.reference = uuid.uuid4().hex + "-"+str(rifa.Id)
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
                    'https://apiplazaqa.celupagos.com/rate', get_token())['rate']
                compra.save()
                for x in data["Numbers"]:
                    NumeroRifaReservados.objects.create(
                        idRifa=rifa, Numero=x['num'], date=country_time, idOrden=orden)
                    NumeroRifaDisponibles.objects.get(
                        idRifa=rifa, Numero=x['num']).delete()

        except Exception as ex:
            return HttpResponse(ex)

        logger.info(data)
        url = 'https://apiplaza.celupagos.com/payment/createOrder'
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
        r['orden'] = orden.reference

        logger.info(r)

        res = json.dumps(r)
        logger.info(res)
        logger.info(r['codigoHttp'])
        logger.info(r['systemMessage'])
        logger.info(r['clientMessage'])

      #  if r['codigoHttp']!=200:

       #   return   HttpResponse(f"Error {r['clientMessage']}", status=400)

        return HttpResponse(res, content_type="application/json")
    return HttpResponse("Error", status=400)

def reserveNumbers(request):
  if request.method == "POST":
    form = ReserveForm(request.POST)
    logger.info(f"Campos {request.POST}")
    logger.info(f"Formulario válido {form.is_valid()}")
    logger.info(f"Formulario válido {form.errors}")
    if form.is_valid():
        idRifa = form.cleaned_data['idRifa']
        try:
            rifa = RifaModel.objects.get(Id=idRifa)
        except:
            return HttpResponse("Error, la rifa a la que intenta comprar no existe", status=400)
        
        # valida estado y publicacion
        if rifa.Estado == False or rifa.Eliminada == True:
            return JsonResponse({"message": "Rifa no dispoible", "status": 422}, status=422)
        
        # valida rifa fecha
        country_time_zone = pytz.timezone('America/Caracas')
        country_time = datetime.now(country_time_zone)

        if rifa.FechaSorteo != None:
            if country_time >= rifa.FechaSorteo:
                if rifa.Extension==False:
                    return JsonResponse({"message": "Rifa expirada", "status": 422}, status=422)
                
        if form.cleaned_data['numeros'] < rifa.MinCompra or form.cleaned_data['numeros'] > rifa.MaxCompra:
            return JsonResponse({"message": "Cantidad invalida", "status": 422}, status=422)
        
        if form.cleaned_data['numeros'] > NumeroRifaDisponibles.objects.filter(idRifa=idRifa).count():
            return JsonResponse({"message": "No hay disponibles suficientes", "status": 422}, status=422)

        total = rifa.Precio*form.cleaned_data['numeros']
        boletos = form.cleaned_data['boletos'] or None

        if boletos != None:
            boletos = boletos.split(",")
        else:
            boletos = []

        random_numbers = form.cleaned_data['numeros'] - len(boletos)

        if random_numbers < 0:
            return JsonResponse({"message": "Error, numeros reservados mayor a la cantidad de boletos", "status": 422}, status=422)
        
        try:
            with transaction.atomic():
                orden = OrdenesReservas()

                disp = NumeroRifaDisponibles.objects.exclude(Numero__in=boletos).filter(
                idRifa=form.cleaned_data['idRifa']).order_by('?')[:random_numbers]

                orden.date=country_time
                orden.customer_name = 'Reserva'
                orden.customer_phone = 'Reserva'
                orden.customer_identification = 'Reserva'
                orden.amount = total
                orden.idRifa = rifa
                orden.description = f"Compra de Numeros de rifa Fecha: {datetime.now()} Rifa: {rifa.Nombre} Numeros: {list(x.Numero for x in disp)} Boletos: {boletos} Total: {total} aleautos1"

                orden.save()
                if len(boletos) > 0:
                    for x in boletos:
                        if NumeroRifaDisponibles.objects.filter(idRifa=rifa, Numero=x).count() == 0:
                            return JsonResponse({"message": "Error, numero no disponible", "status": 422}, status=422)
                        NumeroRifaReservadosOrdenes.objects.create(
                            idRifa=rifa, Numero=x, date=country_time, idOrden=orden)
                        NumeroRifaDisponibles.objects.get(
                            idRifa=rifa, Numero=x).delete()
                        if NumeroRifaReservadosOrdenes.objects.filter(idRifa=rifa, Numero=x, idOrden=orden).count() == 0:
                            return JsonResponse({"message": "Error procesando su solicitud, intente nuevamente", "status": 500}, status=500)

                for x in disp:
                    if NumeroRifaReservadosOrdenes.objects.filter(idRifa=rifa, Numero=x.Numero).count() > 0:
                        return JsonResponse({"message": "Error procesando su solicitud, intente nuevamente", "status": 500}, status=500)
                    NumeroRifaReservadosOrdenes.objects.create(
                        idRifa=rifa, Numero=x.Numero, date=country_time, idOrden=orden)
                    NumeroRifaDisponibles.objects.get(
                        idRifa=rifa, Numero=x.Numero).delete()
                    if NumeroRifaReservadosOrdenes.objects.filter(idRifa=rifa, Numero=x.Numero, idOrden=orden).count() == 0:
                        return JsonResponse({"message": "Error procesando su solicitud, intente nuevamente", "status": 500}, status=500)

        except Exception as ex:
                logger.info(ex)
                print (ex)
                return JsonResponse({"message": "Ops! Vuelve a intentarlo", "status": 500}, status=500)

        serialized_object = serializers.serialize('json', [orden,])
        return JsonResponse({"message": "Éxito", "status": 200, "orden":serialized_object}, status=200)
    return JsonResponse({"errors": form.errors.as_json(), "message": "error de validacion", "status": 422}, status=422)
  
def updateOrder(request):
  if request.method == "POST":
    form = UpdateOrderForm(request.POST)
    logger.info(f"Campos {request.POST}")
    logger.info(f"nombre {request.POST.get('nombre')}")
    logger.info(f"Formulario válido {form.is_valid()}")
    logger.info(f"Formulario válido {form.errors}")
    if form.is_valid():
        idRifa = form.cleaned_data['idRifa']
        try:
            rifa = RifaModel.objects.get(Id=idRifa)
        except:
            return HttpResponse("Error, la rifa a la que intenta comprar no existe", status=400)
        # valida estado y publicacion
        if rifa.Estado == False or rifa.Eliminada == True:
            return JsonResponse({"message": "Rifa no disponible", "status": 422}, status=422)
        # valida rifa fecha
        country_time_zone = pytz.timezone('America/Caracas')
        country_time = datetime.now(country_time_zone)
        if rifa.FechaSorteo != None:
         if country_time >= rifa.FechaSorteo:
          if rifa.Extension==False:
            return JsonResponse({"message": "Rifa expirada", "status": 422}, status=422)

        try:
            with transaction.atomic():
                orden = OrdenesReservas.objects.filter(Id=form.cleaned_data['idOrden'])
                if orden.count() == 0:
                    return JsonResponse({"message": "Error, la orden no existe", "status": 422}, status=422)
                
                orden = orden.first()

                if orden.date <= country_time - timedelta(minutes=10):
                    return JsonResponse({"message": "Error, la orden ha expirado vuelva a intentarlo", "status": 422}, status=422)

                orden.customer_name = form.cleaned_data['nombre']
                orden.customer_phone = form.cleaned_data['numeroTlf']
                orden.customer_email = form.cleaned_data['correo']
                orden.customer_identification =form.cleaned_data['cedula']

                orden.save()

        except Exception as ex:
                logger.info(ex)
                print (ex)
                return JsonResponse({"message": "Ops! Vuelve a intentarlo", "status": 500}, status=500)

        serialized_object = serializers.serialize('json', [orden,])
        return JsonResponse({"message": "Éxito", "status": 200, "orden":serialized_object}, status=200)
    return JsonResponse({"errors": form.errors.as_json(), "message": "error de validacion", "status": 422}, status=422)
  
def createOrder(request):
  if request.method == "POST":
    form = FirstFileForm(request.POST)
    logger.info(f"Campos {request.POST}")
    logger.info(f"nombre {request.POST.get('nombre')}")
    logger.info(f"Formulario válido {form.is_valid()}")
    logger.info(f"Formulario válido {form.errors}")
    if form.is_valid():
        idRifa = form.cleaned_data['idRifa']
        try:
            rifa = RifaModel.objects.get(Id=idRifa)
        except:
            return HttpResponse("Error, la rifa a la que intenta comprar no existe", status=400)
        # valida estado y publicacion
        if rifa.Estado == False or rifa.Eliminada == True:
            return JsonResponse({"message": "Rifa no dispoible", "status": 422}, status=422)
        # valida rifa fecha
        country_time_zone = pytz.timezone('America/Caracas')
        country_time = datetime.now(country_time_zone)
        if rifa.FechaSorteo != None:
         if country_time >= rifa.FechaSorteo:
          if rifa.Extension==False:
            return JsonResponse({"message": "Rifa expirada", "status": 422}, status=422)
        if form.cleaned_data['numeros'] < rifa.MinCompra or form.cleaned_data['numeros'] > rifa.MaxCompra:
            return JsonResponse({"message": "Cantidad invalida", "status": 422}, status=422)
        
        
        if form.cleaned_data['numeros'] > NumeroRifaDisponibles.objects.filter(idRifa=idRifa).count():
            return JsonResponse({"message": "No hay disponibles suficientes", "status": 422}, status=422)

        total = rifa.Precio*form.cleaned_data['numeros'] 

        # Si el usuario está autenticado como cliente, usar sus datos
        cliente = None
        if request.user.is_authenticated and hasattr(request.user, 'cliente'):
            cliente = request.user.cliente
            nombre = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
            correo = request.user.email
            cedula = cliente.cedula
            telefono = cliente.telefono
        else:
            # Usar datos del formulario (invitado)
            nombre = form.cleaned_data['nombre']
            correo = form.cleaned_data['correo']
            cedula = form.cleaned_data['cedula']
            telefono = form.cleaned_data['numeroTlf']

        try:
            with transaction.atomic():
                orden = OrdenesReservas()

                disp = NumeroRifaDisponibles.objects.filter(
                idRifa=form.cleaned_data['idRifa']).order_by('?')[:form.cleaned_data['numeros']]

             
                orden.date=country_time
                orden.amount = total
                orden.customer_name = nombre
                orden.customer_phone = telefono
                orden.customer_email = correo
                orden.customer_identification = cedula
                orden.idRifa = rifa
                orden.description = f"Compra de Numeros de rifa Fecha: {datetime.now()} Rifa: {rifa.Nombre} Numeros: {list(x.Numero for x in disp)} Total: {total} aleautos1"

                orden.save()
                for x in disp:
                    if NumeroRifaReservadosOrdenes.objects.filter(idRifa=rifa, Numero=x.Numero).count() > 0:
                        return JsonResponse({"message": "Error procesando su solicitud, intente nuevamente", "status": 500}, status=500)
                    NumeroRifaReservadosOrdenes.objects.create(
                        idRifa=rifa, Numero=x.Numero, date=country_time, idOrden=orden)
                    NumeroRifaDisponibles.objects.get(
                        idRifa=rifa, Numero=x.Numero).delete()
                    if NumeroRifaReservadosOrdenes.objects.filter(idRifa=rifa, Numero=x.Numero, idOrden=orden).count() == 0:
                        return JsonResponse({"message": "Error procesando su solicitud, intente nuevamente", "status": 500}, status=500)
                    
                        

        except Exception as ex:
                logger.info(ex)
                print (ex)
                return JsonResponse({"message": "Ops! Vuelve a intentarlo", "status": 500}, status=500)
        serialized_object = serializers.serialize('json', [orden,])
        return JsonResponse({"message": "Éxito", "status": 200, "orden":serialized_object}, status=200)
        return HttpResponse(res, content_type="application/json")
    return JsonResponse({"errors": form.errors.as_json(), "message": "error de validacion", "status": 422}, status=422)

def consultOrder(request):
    if request.method == "GET":
        data = json.load(request)

        url =  f'https://apiplaza.celupagos.com/payment/searchTransaction?reference={data["reference"]}&mode=Integration' 
        token = get_token()
        r = get_data(url, token)
        return HttpResponse(json.dumps(r), content_type="application/json")
    return HttpResponse("Error", status=400)


# endregion
@login_required(login_url="/Login/")
def deleteComprobantes(request):
    #compras id > 0
    compras = Compra.objects.filter(Id__gt=0)
    for x in compras:
        #delete local file

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
            'previous_page': objects.has_previous() and objects.previous_page_number() or None,
            'next_page': objects.has_next() and objects.next_page_number() or None,
            'data': list(objects)
        }
        return data
