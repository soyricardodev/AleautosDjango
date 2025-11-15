from datetime import datetime, timedelta
import fnmatch
import re
from asgiref.sync import sync_to_async
import json
from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template import loader
from .forms import RifaForm, VerificaForm, CompradorForm, RegistroClienteForm, LoginClienteForm
from .models import Compra, NumeroRifaComprados, NumeroRifaReservados, NumeroRifaReservadosOrdenes, NumerosCompra,UsuarioStats, Rifa as RifaModel, NumeroRifaDisponibles, NumeroRifaDisponiblesArray, NumeroRifaCompradosArray, PremiosRifa, Tasas, ReenviosMasivos, Settings, Comprador, Cliente
from django.core.paginator import Paginator
from django.db import transaction, IntegrityError
from .apis import get_token, get_data
from django.core.mail import EmailMessage, get_connection
import pytz
from django.utils.dateparse import parse_datetime
from django.db.models import Q
from django.db.models import Avg, Count, Sum
from django.template.loader import render_to_string, get_template
from io import BytesIO
from xhtml2pdf  import pisa
import xlwt
from .templatetags.Filter import reversoEstado,reversoMetodoPago
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.forms import AuthenticationForm #add this
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import F
import http.client
from .utils import generate_slug
import logging
logger = logging.getLogger('ballena')
import requests
from lxml import html
from bs4 import BeautifulSoup
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.db.models import Max, Case, When
from django.db.models import IntegerField
from dateutil.relativedelta import relativedelta 
# Create your views here.

def handle404(request, exception):
    logger.warning("404")
    template = loader.get_template('Rifa/NotFound.html')
    Rifas=RifaModel.objects.filter(Estado=True).filter(Eliminada=False)
    Rifa=Rifas.last()
    context = {
        "Rifa":Rifa,
    }
    return render(request,'Rifa/NotFound.html', context)
    return HttpResponseNotFound(content=template.render(context, request), content_type='text/html; charset=utf-8', status=404)


def handle500(request, ex=None):
    logger.info("500")
    logger.info(ex)
    logger.info(request)
    data = {}
    return render(request,'Rifa/NotFound.html', data)
    logger.info("404")
    template = loader.get_template('Rifa/NotFound.html')
    Rifas=RifaModel.objects.filter(Estado=True).filter(Eliminada=False)
    Rifa=Rifas.last()
    context = {
        "Rifa":Rifa,
    }
    return render(request,'Rifa/NotFound.html', context)
    return HttpResponseNotFound(content=template.render(context, request), content_type='text/html; charset=utf-8', status=404)
def index(request):
    try:
        template = loader.get_template("Rifa/Index.django")
        tasa = Tasas.objects.last()
        Rifas=RifaModel.objects.filter(Estado=True).filter(Eliminada=False)
        Rifa=Rifas.last()
        Rifas=Rifas.order_by("-Id")[1:]
        paginator = Paginator(Rifas, 6)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        numDisp = NumeroRifaDisponibles.objects.filter(idRifa=Rifa).count() if Rifa else 0
        whatsapp_config=Settings.objects.filter(code="PHONE_CLIENT").first()
        percent_config=Settings.objects.filter(code="HIDE_TICKET_COUNT").first()
        zelle_condition_type_config=Settings.objects.filter(code="ZELLE_CONDITION_TYPE").first()
        zelle_min_value_config=Settings.objects.filter(code="ZELLE_MIN_VALUE").first()
        zelle_email_config=Settings.objects.filter(code="ZELLE_EMAIL").first()

        time_remaining = None
        if Rifa != None:
          if Rifa.FechaSorteo:
            now = timezone.now()
            time_difference = (Rifa.FechaSorteo - now).total_seconds()
            if time_difference > 1:
                time_remaining = int(time_difference)
      
        context = {
            "Rifa":Rifa,
            "Rifas":page_obj,
            "tasa":tasa,
            'numDisp':numDisp,
            'time_remaining':time_remaining,
            'whatsapp_config':whatsapp_config,
            'percent_config':percent_config,
            'zelle_condition_type':zelle_condition_type_config,
            'zelle_min_value':zelle_min_value_config,
            'zelle_email':zelle_email_config,
        }
        return HttpResponse(template.render(context, request))
    except Exception as e:
        logger.error(f"Error en vista index: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # Retornar una respuesta de error o redirigir
        return HttpResponse(f"Error cargando la página: {str(e)}", status=500)
@login_required(login_url="/Login/")
@permission_required('Rifa.view_compra', raise_exception=True)
def Dashboard(request):
    template = loader.get_template("Rifa/Dashboard.django")
    Rifas=RifaModel.objects.filter(Estado=True).filter(Eliminada=False)
    ComprasLista=Compra.objects.all().order_by("-Id")[0:8]
    Rifa=Rifas.last()
    totalNumeros=0
    totalComprados=0
    totalDisponibles=0
    if Rifa is not None:
        totalNumeros=Rifa.TotalNumeros
        totalComprados=Rifa.TotalComprados
        totalDisponibles=Rifa.TotalNumeros-totalComprados

    numerosRifa=NumeroRifaDisponibles.objects.filter(idRifa=Rifa).count()

    #total de compras
    totalCompras=Compra.objects.filter(idRifa=Rifa).count()
    totalComprasAprobadas=Compra.objects.filter(idRifa=Rifa).filter(Estado=Compra.EstadoCompra.Pagado).count()
    totalComprasRechazadas=Compra.objects.filter(idRifa=Rifa).filter(Estado=Compra.EstadoCompra.Rechazado).count()
    totalComprasPendientes=Compra.objects.filter(idRifa=Rifa).filter(Estado=Compra.EstadoCompra.Pendiente).count()
    totalPendientes=NumeroRifaReservadosOrdenes.objects.all().count()



    ########################3
    stats=UsuarioStats.objects.last()



    #########################

    context = {
        "Rifa":Rifa,
        "Compras":ComprasLista,
        "totalDisponibles":totalDisponibles,
        "totalCompras":totalComprados,
        "totalPendientes":totalPendientes,
        "d1":stats.dNuevo if stats != None else 0,
        "d2":stats.dRecurrente if stats != None else 0,
        "s1":stats.sNuevo if stats != None else 0,
        "s2":stats.sRecurrente if stats != None else 0,
        "m1":stats.mNuevo if stats != None else 0,
        "m2":stats.mRecurrente if stats != None else 0
        


    }
    return HttpResponse(template.render(context, request))


def Login(request):
    try:
        if request.user.is_authenticated:
            return redirect("/")
        if request.session.get("mensaje"):
                msg = request.session.get("mensaje")
                request.session.flush()
        template = loader.get_template("Rifa/Login.html")
        Rifas=RifaModel.objects.filter(Estado=True).filter(Eliminada=False)
        Rifa=Rifas.last()
        msg=""
        if request.method == 'POST':
            username = request.POST.get('username', '')
            password = request.POST.get('password', '')
            logger.info(f"Intento de login - Username: {username}")
            
            # Verificar si el usuario existe
            try:
                user_exists = User.objects.filter(username=username).exists()
                logger.info(f"Usuario existe en BD: {user_exists}")
            except Exception as e:
                logger.error(f"Error verificando usuario: {e}")
                msg = "Error de conexión a la base de datos"
            else:
                if user_exists:
                    user = authenticate(request, username=username, password=password)
                    logger.info(f"Resultado de authenticate: {user}")
                    if user is not None:
                        login(request, user)
                        logger.info(f"Login exitoso para {username}")
                        return redirect("Dashboard")
                    else:
                        logger.warning(f"Autenticación fallida para {username} - contraseña incorrecta")
                        msg="Usuario o clave invalidos!"
                else:
                    logger.warning(f"Usuario {username} no existe en la BD")
                    msg="Usuario o clave invalidos!"

        context = {
            "Rifa":Rifa,
            "msg": msg,
        }
        return HttpResponse(template.render(context, request))
    except Exception as e:
        logger.error(f"Error en vista Login: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return HttpResponse(f"Error en el login: {str(e)}", status=500)


def registro_cliente(request):
    """Vista para registro de clientes en /registrate/"""
    # Si ya está autenticado, redirigir
    if request.user.is_authenticated:
        # Verificar si es cliente o admin
        if hasattr(request.user, 'cliente'):
            return redirect("/")
        else:
            # Es admin, redirigir al dashboard
            return redirect("Dashboard")
    
    template = loader.get_template("Rifa/registro_cliente.html")
    Rifas = RifaModel.objects.filter(Estado=True).filter(Eliminada=False)
    Rifa = Rifas.last()
    msg = ""
    error = None
    
    if request.method == 'POST':
        form = RegistroClienteForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Crear usuario
                    user = User.objects.create_user(
                        username=form.cleaned_data['correo'],  # Usar correo como username
                        email=form.cleaned_data['correo'],
                        password=form.cleaned_data['password'],
                        first_name=form.cleaned_data['nombre'].split()[0] if form.cleaned_data['nombre'].split() else '',
                        last_name=' '.join(form.cleaned_data['nombre'].split()[1:]) if len(form.cleaned_data['nombre'].split()) > 1 else ''
                    )
                    
                    # Crear cliente
                    cliente = Cliente.objects.create(
                        user=user,
                        cedula=form.cleaned_data['cedula'],
                        telefono=form.cleaned_data['telefono']
                    )
                    
                    # Auto-login
                    login(request, user)
                    
                    # Redirigir según contexto
                    next_url = request.GET.get('next', '/')
                    return redirect(next_url)
            except Exception as e:
                logger.error(f"Error al registrar cliente: {str(e)}")
                error = "Ocurrió un error al registrar. Por favor intenta nuevamente."
        else:
            error = "Por favor corrige los errores en el formulario."
    else:
        form = RegistroClienteForm()
    
    context = {
        "Rifa": Rifa,
        "form": form,
        "msg": msg,
        "error": error,
    }
    return HttpResponse(template.render(context, request))


def inicio_sesion_cliente(request):
    """Vista para inicio de sesión de clientes en /inicia-sesion/"""
    # Si ya está autenticado, redirigir
    if request.user.is_authenticated:
        if hasattr(request.user, 'cliente'):
            # Si hay un parámetro next, redirigir allí, sino al inicio
            next_url = request.GET.get('next', '/')
            return redirect(next_url)
        else:
            return redirect("Dashboard")
    
    template = loader.get_template("Rifa/inicio_sesion_cliente.html")
    Rifas = RifaModel.objects.filter(Estado=True).filter(Eliminada=False)
    Rifa = Rifas.last()
    msg = ""
    error = None
    
    if request.method == 'POST':
        form = LoginClienteForm(request.POST)
        if form.is_valid():
            usuario_input = form.cleaned_data['usuario']
            password = form.cleaned_data['password']
            
            # Intentar autenticar por correo o cédula
            user = None
            
            # Primero intentar por correo (username)
            try:
                user = User.objects.get(email=usuario_input)
            except User.DoesNotExist:
                pass
            
            # Si no se encontró por correo, intentar por cédula
            if user is None:
                try:
                    cliente = Cliente.objects.get(cedula=usuario_input)
                    user = cliente.user
                except Cliente.DoesNotExist:
                    pass
            
            # Si encontramos un usuario, verificar contraseña
            if user:
                user = authenticate(request, username=user.username, password=password)
                if user is not None:
                    # Verificar que sea un cliente, no un admin
                    if hasattr(user, 'cliente'):
                        login(request, user)
                        next_url = request.GET.get('next', '/')
                        return redirect(next_url)
                    else:
                        error = "Esta cuenta es de administrador. Usa /Login/ para acceder."
                else:
                    error = "Contraseña incorrecta."
            else:
                error = "No se encontró una cuenta con esa cédula o correo."
        else:
            error = "Por favor completa todos los campos."
    else:
        form = LoginClienteForm()
    
    context = {
        "Rifa": Rifa,
        "form": form,
        "msg": msg,
        "error": error,
    }
    return HttpResponse(template.render(context, request))


def cerrar_sesion_cliente(request):
    """Vista para cerrar sesión de clientes"""
    logout(request)
    return redirect("/")


@login_required(login_url="/inicia-sesion/")
def mi_perfil(request):
    """
    Vista para mostrar el perfil del cliente autenticado con sus compras y números ganadores
    """
    # Verificar que el usuario tenga un cliente asociado
    if not hasattr(request.user, 'cliente'):
        return redirect('registro_cliente')
    
    try:
        cliente = request.user.cliente
        template = loader.get_template("Rifa/mi_perfil.html")
        
        # Obtener rifa activa
        rifas_activas = RifaModel.objects.filter(Estado=True, Eliminada=False).order_by('-Id')
        rifa_activa = rifas_activas.first()
        
        # Obtener todas las compras pagadas del cliente para la rifa activa
        compras_pagadas = []
        todos_los_numeros = []
        
        if rifa_activa:
            # Buscar compras pagadas del cliente para esta rifa
            compras = Compra.objects.filter(
                idRifa=rifa_activa,
                idComprador__idCliente=cliente,
                Estado=Compra.EstadoCompra.Pagado
            ).order_by('-FechaCompra')
            
            for compra in compras:
                numeros_compra = NumerosCompra.objects.filter(idCompra=compra).values_list('Numero', flat=True)
                numeros_list = list(numeros_compra)
                compras_pagadas.append({
                    'compra': compra,
                    'numeros': numeros_list,
                    'cantidad': len(numeros_list),
                    'fecha': compra.FechaCompra,
                    'monto': compra.TotalPagado
                })
                todos_los_numeros.extend(numeros_list)
        
        # Obtener información del comprador
        comprador = Comprador.objects.filter(idCliente=cliente).first()
        
        context = {
            'cliente': cliente,
            'comprador': comprador,
            'rifa_activa': rifa_activa,
            'compras_pagadas': compras_pagadas,
            'todos_los_numeros': sorted(todos_los_numeros, key=lambda x: int(x) if x.isdigit() else 0),
            'total_numeros': len(todos_los_numeros),
            'total_compras': len(compras_pagadas)
        }
        
        return HttpResponse(template.render(context, request))
        
    except Exception as e:
        logger.error(f"Error en mi_perfil: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # En caso de error, mostrar página de error en lugar de redirigir
        from django.http import HttpResponseServerError
        return HttpResponseServerError("Error al cargar el perfil. Por favor intenta de nuevo.")


def export_pdf(template, context):
    template = get_template(template)
 #   template=get_template("Rifa/Componentes/tableDialog.html")
    html = template.render(context)
    result = BytesIO()
    pdf=pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type="application/pdf")
    return None

@login_required(login_url="/Login/")
def dialogCompra(request):
    #get compra
    data = json.load(request)
    id=data["id"]
    logger.info(id)
    CompraObj=Compra.objects.get(Id=id)
    nums=NumerosCompra.objects.filter(idCompra=CompraObj)
    numsCount=nums.count()
    
    template = loader.get_template("Rifa/Componentes/tableDialogDetalleCompra.django")
    context = {
        "Compra":CompraObj,
        "numsCount":numsCount,
        "Numeros":nums,
    }
    return HttpResponse(template.render(context, request))

@login_required(login_url="/Login/")
def compradorDialog(request):
    #get compra
    data = json.load(request)
    comprador = None
    tiene_cliente = False
    cliente_id = None
    
    # Check if we received cliente or comprador parameter
    if "cliente" in data:
        cliente_id = data["cliente"]
        try:
            cliente = Cliente.objects.get(id=cliente_id)
            # Find associated Comprador
            comprador = Comprador.objects.filter(idCliente=cliente).first()
            if comprador:
                tiene_cliente = True
                comprador_id = comprador.Id
            else:
                # Create temporary comprador data from cliente for display
                # We'll need to create the comprador when saving
                tiene_cliente = True
                comprador_id = None
                form_data = {
                    "nombre": cliente.user.get_full_name() or cliente.user.username,
                    "cedula": cliente.cedula,
                    "correo": cliente.user.email,
                    "telefono": cliente.telefono,
                }
                template = loader.get_template("Rifa/Componentes/comprador.django")
                context = {
                    "CompradorId": None,
                    "ClienteId": cliente_id,
                    "form": CompradorForm(initial=form_data),
                    "tiene_cliente": tiene_cliente,
                    "cliente_id": cliente_id,
                }
                return HttpResponse(template.render(context, request))
        except Cliente.DoesNotExist:
            return JsonResponse({"error": "Cliente no encontrado"}, status=404)
    elif "comprador" in data:
        comprador_id = data["comprador"]
        logger.info(comprador_id)
        comprador = Comprador.objects.get(Id=comprador_id)
        if comprador.idCliente:
            tiene_cliente = True
            cliente_id = comprador.idCliente.id
    else:
        return JsonResponse({"error": "Se requiere 'comprador' o 'cliente' en el request"}, status=400)
    
    form_data = {
        "nombre":comprador.Nombre,
        "cedula":comprador.Cedula,
        "correo":comprador.Correo,
        "telefono":comprador.NumeroTlf,
    }
    
    template = loader.get_template("Rifa/Componentes/comprador.django")
    context = {
        "CompradorId":comprador_id,
        "form":CompradorForm(initial=form_data),
        "tiene_cliente": tiene_cliente,
        "cliente_id": cliente_id,
    }
    return HttpResponse(template.render(context, request))

@login_required(login_url="/Login/")
@permission_required('Rifa.add_rifa', raise_exception=True)
def dialogSettings(request):
    whatsapp_config=Settings.objects.filter(code="PHONE_CLIENT").first()
    percent_config=Settings.objects.filter(code="HIDE_TICKET_COUNT").first()
    zelle_condition_type_config=Settings.objects.filter(code="ZELLE_CONDITION_TYPE").first()
    zelle_min_value_config=Settings.objects.filter(code="ZELLE_MIN_VALUE").first()
    zelle_email_config=Settings.objects.filter(code="ZELLE_EMAIL").first()
    
    template = loader.get_template("Rifa/Componentes/settings.django")
    context = {
        "whatsapp":whatsapp_config,
        "percent":percent_config,
        "zelle_condition_type":zelle_condition_type_config,
        "zelle_min_value":zelle_min_value_config,
        "zelle_email":zelle_email_config,
    }
    return HttpResponse(template.render(context, request))

@login_required(login_url="/Login/")
def dialogReenvioCorreo(request):
    #get compra
    data = json.load(request)
    id=data["id"]
    logger.info(f"id de rifa {id}")
    RifaObj=RifaModel.objects.get(Id=id)
    
    template = loader.get_template("Rifa/Componentes/modalReenvioCorreo.django")
    data = ReenviosMasivos.objects.all().order_by("-id")[:15]
    proceso = ReenviosMasivos.objects.filter(estado=0).count() > 0
    logger.info(f"objetos {data}")
    lista = list(data)
    context = {
        "Rifa":RifaObj,
        "ReenvioData":lista,
        "EnProceso":proceso,
        "UltimoReenvio":lista[0] if len(lista) > 0 else None,
    }
    return HttpResponse(template.render(context, request))

@login_required(login_url="/Login/")
def tableNumList(request):
    #get compra
    data = json.load(request)
    id=data["id"]
    logger.info(id)
    CompraObj=Compra.objects.get(Id=id)
    
    template = loader.get_template("Rifa/Componentes/tableDialogNumList.django")
    context = {
        "Compra":CompraObj,
        "Numeros":NumerosCompra.objects.filter(idCompra=CompraObj),
    }
    return HttpResponse(template.render(context, request))


@login_required(login_url="/Login/")
def tableDialogBuscaNumero(request,  id=None):
    data = json.load(request)
    numero=data["numero"]
    pagina=data["page"]
    ComprasLista=Compra.objects.all()
    if id!=None:
            ComprasLista=Compra.objects.filter(idRifa=id)
    
    if numero!= None and numero!="":
                    ComprasLista=ComprasLista.filter(Q(NumerosCompra__Numero__iexact=numero) )

    logger.info(ComprasLista)
    template = loader.get_template("Rifa/Componentes/tableDialogBuscaNumero.django")
    
    ComprasLista=ComprasLista.order_by("-Id")
    paginator = Paginator(ComprasLista, 4)
    page_obj = paginator.get_page(pagina)

    context = {
        "Compras":ComprasLista,
        "compras_paginadas": page_obj
    }
    return HttpResponse(template.render(context, request))
            

@login_required(login_url="/Login/")
def tableDialog(request,  id=None):
    data = json.load(request)
    grupo=data["grupo"]
    valor=data["valor"]
    pagina=data["page"]
    ComprasLista=Compra.objects.all()
    if id!=None:
            ComprasLista=ComprasLista.filter(idRifa=id)
    if grupo!= None and grupo!="":
                    #if grupo!="0":
                     #   ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Pagado)
                    if grupo=="1":
                          ComprasLista=ComprasLista.filter(idComprador__Correo=valor )
                    if grupo=="2":
                       ComprasLista=ComprasLista.filter(idComprador__Cedula=valor)
                    if grupo=="3":
                         ComprasLista=ComprasLista.filter(idComprador__Nombre=valor )
    texto = request.session['textoBusqueda'] if 'textoBusqueda' in request.session else None
    estado = request.session['Estado'] if 'Estado' in request.session else None
    grupoCookie = request.session['grupo'] if 'grupo' in request.session else None
    dateInicio = request.session['dateInicio'] if 'dateInicio' in request.session else None
    dateFinal = request.session['dateFinal'] if 'dateFinal' in request.session else None
    '''if grupo!= None and grupo!="" and grupo!="0":
        estado=None
        texto=None
        dateFinal=None
        dateInicio=None'''
    if estado!= None and estado!="":
        if estado=="1":
         ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Pendiente)
        if estado=="2":
         ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Cancelado)
        if estado=="3":
         ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Pagado)
        if estado=="4":
                ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Rechazado)

    if texto!= None and texto!="":
        ComprasLista=ComprasLista.filter(Q(idComprador__Nombre__icontains=texto)| Q(idRifa__Nombre__icontains=texto ) | Q(idComprador__Cedula__icontains=texto ))
    if dateInicio != None and dateInicio!="":
        dateI=parse_datetime(dateInicio)
        fechaI=dateInicio
        ComprasLista=ComprasLista.filter(FechaCompra__gte=dateI)

    if dateFinal != None and dateFinal!="":
        dateF=parse_datetime(dateFinal)
        fechaF=dateFinal
        ComprasLista=ComprasLista.filter(FechaCompra__lte=dateF)
    template = loader.get_template("Rifa/Componentes/tableDialogGrupoCompras.django")
    
    ComprasLista=ComprasLista.order_by("-Id")
    paginator = Paginator(ComprasLista, 4)
    page_obj = paginator.get_page(pagina)

    context = {
        "Compras":ComprasLista,
        "compras_paginadas": page_obj,
        'grupo':grupo,
        'valor':valor,
    }
    return HttpResponse(template.render(context, request))

# convert tableDialog to pdf
@login_required(login_url="/Login/")
def tableDialogPDF(request,  id=None):
    data = json.load(request)
    grupo=data["grupo"]
    valor=data["valor"]
    tipo=data["tipo"]
    logger.info(data)
    ComprasLista=Compra.objects.all()
    if id!=None:
            ComprasLista=ComprasLista.filter(idRifa=id)
    if tipo==2:
     logger.info("entro2")
     
     if grupo!= None and grupo!="":
                    #if grupo!="0":
                     #   ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Pagado)
                    if grupo=="1":
                          ComprasLista=ComprasLista.filter(idComprador__Correo=valor )
                    if grupo=="2":
                       ComprasLista=ComprasLista.filter(idComprador__Cedula=valor)
                    if grupo=="3":
                         ComprasLista=ComprasLista.filter(idComprador__Nombre=valor )
     grupo='0'
     ComprasLista=ComprasLista.order_by("-Id")

    if tipo==1:
        logger.info("entro")
        texto = request.session['textoBusqueda'] if 'textoBusqueda' in request.session else None
        estado = request.session['Estado'] if 'Estado' in request.session else None
        grupoCookie = request.session['grupo'] if 'grupo' in request.session else None
        dateInicio = request.session['dateInicio'] if 'dateInicio' in request.session else None
        dateFinal = request.session['dateFinal'] if 'dateFinal' in request.session else None
        '''if grupo!= None and grupo!="" and grupo!="0":
            estado=None
            texto=None
            dateFinal=None
            dateInicio=None'''
        if estado!= None and estado!="":
         if estado=="1":
            ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Pendiente)
         if estado=="2":
            ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Cancelado)
         if estado=="3":
            ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Pagado)
        if estado=="4":
                    ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Rechazado)

        if texto!= None and texto!="":
         ComprasLista=ComprasLista.filter(Q(idComprador__Nombre__icontains=texto)| Q(idRifa__Nombre__icontains=texto ) | Q(idComprador__Cedula__icontains=texto ))
        if dateInicio != None and dateInicio!="":
          dateI=parse_datetime(dateInicio)
          fechaI=dateInicio
          ComprasLista=ComprasLista.filter(FechaCompra__gte=dateI)

        if dateFinal != None and dateFinal!="":
          dateF=parse_datetime(dateFinal)
          fechaF=dateFinal
          ComprasLista=ComprasLista.filter(FechaCompra__lte=dateF)

        if grupo!= None and grupo!="":
         #if grupo!="0":
          #  ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Pagado)
         if grupo=="1":
            logger.info("grupo")

            ComprasLista=ComprasLista.values('idComprador__Correo').annotate(head_count=Count('idComprador__Correo'), totalNumeros=Sum('NumeroBoletos'), totalPagadoS=Sum('TotalPagado')).values('idComprador__Correo','head_count','totalNumeros', 'totalPagadoS')
         if grupo=="2":
            ComprasLista=ComprasLista.values('idComprador__Cedula').annotate(head_count=Count('idComprador__Cedula'),totalNumeros=Sum('NumeroBoletos'), totalPagadoS=Sum('TotalPagado')).values('idComprador__Cedula','head_count', 'totalNumeros', 'totalPagadoS')
         if grupo=="3":
            ComprasLista=ComprasLista.values('idComprador__Nombre').annotate(head_count=Count('idComprador__Nombre'),totalNumeros=Sum('NumeroBoletos'), totalPagadoS=Sum('TotalPagado')).values('idComprador__Nombre','head_count','totalNumeros', 'totalPagadoS')
         if grupo!="0":
           logger.info(list(ComprasLista))
           logger.info(len(list(ComprasLista)))

        if grupo=='1' or grupo=='2' or grupo=='3':
            ComprasLista=ComprasLista.order_by("-totalNumeros")
        else:
            ComprasLista=ComprasLista.order_by("-Id")   

        

    context = {
        "Compras":ComprasLista,
         'grupo':grupo,
        'valor':valor,
    }
    pdf = export_pdf("Rifa/Componentes/tableDialogPDF.html", context)
    return HttpResponse(pdf, content_type="application/pdf")

#export tableDialog to excel
@login_required(login_url="/Login/")
def tableDialogExcel(request,  id=None):
    data = json.load(request)
    grupo=data["grupo"]
    valor=data["valor"]
    tipo=data["tipo"]
    logger.info(data)
    texto = request.session['textoBusqueda'] if 'textoBusqueda' in request.session else None
    estado = request.session['Estado'] if 'Estado' in request.session else None
    grupoCookie = request.session['grupo'] if 'grupo' in request.session else None
    dateInicio = request.session['dateInicio'] if 'dateInicio' in request.session else None
    dateFinal = request.session['dateFinal'] if 'dateFinal' in request.session else None

    ComprasLista=Compra.objects.all()
    if id!=None:
            ComprasLista=ComprasLista.filter(idRifa=id)
    if tipo==2:
     if grupo!= None and grupo!="":
                    #if grupo!="0":
                     #   ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Pagado)
                    if grupo=="1":
                          ComprasLista=ComprasLista.filter(idComprador__Correo=valor )
                    if grupo=="2":
                       ComprasLista=ComprasLista.filter(idComprador__Cedula=valor)
                    if grupo=="3":
                         ComprasLista=ComprasLista.filter(idComprador__Nombre=valor )
     grupo='0'
     ComprasLista=ComprasLista.order_by("-Id")
    
    if tipo==1:
        logger.info("entro")
        texto = request.session['textoBusqueda'] if 'textoBusqueda' in request.session else None
        estado = request.session['Estado'] if 'Estado' in request.session else None
        grupoCookie = request.session['grupo'] if 'grupo' in request.session else None
        dateInicio = request.session['dateInicio'] if 'dateInicio' in request.session else None
        dateFinal = request.session['dateFinal'] if 'dateFinal' in request.session else None
        '''if grupo!= None and grupo!="" and grupo!="0":
            estado=None
            texto=None
            dateFinal=None
            dateInicio=None'''
        if estado!= None and estado!="":
         if estado=="1":
            ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Pendiente)
         if estado=="2":
            ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Cancelado)
         if estado=="3":
            ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Pagado)
        if estado=="4":
                    ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Rechazado)

        if texto!= None and texto!="":
         ComprasLista=ComprasLista.filter(Q(idComprador__Nombre__icontains=texto)| Q(idRifa__Nombre__icontains=texto ) | Q(idComprador__Cedula__icontains=texto ))
        if dateInicio != None and dateInicio!="":
          dateI=parse_datetime(dateInicio)
          fechaI=dateInicio
          ComprasLista=ComprasLista.filter(FechaCompra__gte=dateI)

        if dateFinal != None and dateFinal!="":
          dateF=parse_datetime(dateFinal)
          fechaF=dateFinal
          ComprasLista=ComprasLista.filter(FechaCompra__lte=dateF)

        if grupo!= None and grupo!="":
         #if grupo!="0":
           # ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Pagado)
         if grupo=="1":
            logger.info("grupo")

            ComprasLista=ComprasLista.values('idComprador__Correo').annotate(head_count=Count('idComprador__Correo'), totalNumeros=Sum('NumeroBoletos'), totalPagadoS=Sum('TotalPagado')).values('idComprador__Correo','head_count','totalNumeros', 'totalPagadoS')
         if grupo=="2":
            ComprasLista=ComprasLista.values('idComprador__Cedula').annotate(head_count=Count('idComprador__Cedula'),totalNumeros=Sum('NumeroBoletos'), totalPagadoS=Sum('TotalPagado')).values('idComprador__Cedula','head_count', 'totalNumeros', 'totalPagadoS')
         if grupo=="3":
            ComprasLista=ComprasLista.values('idComprador__Nombre').annotate(head_count=Count('idComprador__Nombre'),totalNumeros=Sum('NumeroBoletos'), totalPagadoS=Sum('TotalPagado')).values('idComprador__Nombre','head_count','totalNumeros', 'totalPagadoS')
         if grupo!="0":
           logger.info(list(ComprasLista))
           logger.info(len(list(ComprasLista)))

        if grupo=='1' or grupo=='2' or grupo=='3':
            ComprasLista=ComprasLista.order_by("-totalNumeros")
        else:
            ComprasLista=ComprasLista.order_by("-Id")   


    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="users.xls"'

    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Users Data') # this will make a sheet named Users Data

    # Sheet header, first row
    row_num = 0

    font_style = xlwt.XFStyle()
    font_style.font.bold = True
    if tipo==1 and ( grupo=='1' or grupo=='2' or grupo=='3'):
        columns = ['Grupo', 'Total Numeros', 'Total Pagado', 'Total Registros' ]
    else:
     columns = ['Id', 'Fecha Compra', 'Rifa', 'Estado de Pago','Fecha actualización','Nombre Comprador','Cedula Comprador', 'Correo Comprador', 'Tlf Comprador', 'Metodo de Pago', 'Total Pagado', 'Numero de Boletos', 'Referencia','Usuario', 'Boleto' ]

    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style) # at 0 row 0 column 

    # Sheet body, remaining rows
    font_style = xlwt.XFStyle()
    rows = ComprasLista
    #('idComprador__Correo','head_count','totalNumeros', 'totalPagadoS'
    if tipo==1 and ( grupo=='1' or grupo=='2' or grupo=='3'):
        for row in rows:
            row_num += 1
            if grupo=='1':
                string = row['idComprador__Correo']
            if grupo=='2':
                string = row['idComprador__Cedula']
            if grupo=='3':
                string = row['idComprador__Nombre']

            ws.write(row_num, 0, string, font_style)
            ws.write(row_num, 1, row['head_count'], font_style)
            ws.write(row_num, 2, row['totalNumeros'], font_style)
            ws.write(row_num, 3, row['totalPagadoS'], font_style)
     
    else:
     for row in rows:
        for numero in row.NumerosCompra.all():
            row_num += 1
            ws.write(row_num, 0, row.Id, font_style)

            
            string = row.FechaCompra.strftime("%Y-%m-%d %H:%M:%S")  if row.FechaCompra is not None else "   "
            string2 = row.FechaEstado.strftime("%Y-%m-%d %H:%M:%S") if row.FechaEstado is not None else "   "

            ws.write(row_num, 1, string, font_style)
            ws.write(row_num, 2, row.idRifa.Nombre, font_style)
            ws.write(row_num, 3, reversoEstado(row.Estado), font_style)
            ws.write(row_num, 4, string2, font_style)

            ws.write(row_num, 5, row.idComprador.Nombre, font_style)
            ws.write(row_num, 6, row.idComprador.Cedula, font_style)
            ws.write(row_num, 7, row.idComprador.Correo, font_style)
            ws.write(row_num, 8, row.idComprador.NumeroTlf, font_style)
            ws.write(row_num, 9, reversoMetodoPago(row.MetodoPago), font_style)
            totalPagado = f'Bs. {row.TotalPagado}' if row.MetodoPago == 3 else f'$ {row.TotalPagadoAlt}'
            ws.write(row_num, 10, totalPagado, font_style)
            ws.write(row_num, 11, row.NumeroBoletos, font_style)
            ref = row.Referencia if row.Referencia is not None else "   "

            ws.write(row_num, 12, ref, font_style)

            username = row.author.username if row.author is not None else "Cliente de rifas"
            ws.write(row_num, 13, username, font_style)
            ws.write(row_num, 14, numero.Numero, font_style)



    wb.save(response)

    return response
@login_required(login_url="/Login/")
@permission_required('Rifa.view_compra', raise_exception=True)
def Historial(request, id=None):
    is_cookie_set = 0
    texto=None
    estado=None
    grupo=None
    pay_type=0
    dateInicio=None
    dateFinal=None
    numeroBusquedaTotal=None
    RifaHistorial = None
    if 'Estado' in request.session or 'textoBusqueda' in  request.session or 'pay_type' in  request.session or 'dateInicio' in request.session or 'dateFinal' in request.session or 'grupo' in request.session or 'numeroBusquedaTotal' in request.session:
        texto = request.session['textoBusqueda'] if 'textoBusqueda' in request.session else None
        estado = request.session['Estado'] if 'Estado' in request.session else None
        grupo = request.session['grupo'] if 'grupo' in request.session else None
        pay_type = int(request.session['pay_type']) if 'pay_type' in request.session else None
        dateInicio = request.session['dateInicio'] if 'dateInicio' in request.session else None
        dateFinal = request.session['dateFinal'] if 'dateFinal' in request.session else None
        numeroBusquedaTotal = request.session['numeroBusquedaTotal'] if 'numeroBusquedaTotal' in request.session else None

        is_cookie_set = 1
    ComprasLista=Compra.objects.all()

    if id!=None:
            ComprasLista=ComprasLista.filter(idRifa=id)
            RifaHistorial = RifaModel.objects.get(Id=int(id))

    if request.method == 'GET':
        logger.info('get')
        logger.info(is_cookie_set)
        logger.info(request.GET.get('page'))

        if request.GET.get('page')==None:
          is_cookie_set = 0
          request.session['Estado']=None
          request.session['textoBusqueda']=None
          request.session['dateInicio']=None
          request.session['dateFinal']=None
          request.session['dateFinal']=None
          request.session['grupo']=None
          request.session['pay_type']=0
          request.session['numeroBusquedaTotal']=None
          texto=None
          estado=None
          grupo=None
          pay_type=0
          dateInicio=None
          dateFinal=None
          numeroBusquedaTotal=None
        logger.info(estado)
        logger.info(grupo)

        
        if (is_cookie_set == 1): 
             '''if grupo!= None and grupo!="" :
                if grupo!="0":
                    estado=None
                    texto=None
                    dateFinal=None
                    dateInicio=None'''
             if estado!= None and estado!="":
                if estado=="1":
                    ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Pendiente)
                if estado=="2":
                    ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Cancelado)
                if estado=="3":
                    ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Pagado)
                if estado=="4":
                    ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Rechazado)
                if estado=="5":
                    ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Caducado)
                request.session['Estado'] = estado

             if texto!= None and texto!="":
                ComprasLista=ComprasLista.filter(Q(Id__icontains=texto)| Q(idComprador__Nombre__icontains=texto)| Q(idRifa__Nombre__icontains=texto ) | Q(idComprador__Cedula__icontains=texto ) | Q(Referencia__icontains=texto) | Q(idComprador__Correo__icontains=texto))
                request.session['textoBusqueda'] = texto

             if pay_type != 0 and pay_type!=None:
                request.session['pay_type'] = pay_type
                ComprasLista=ComprasLista.filter(MetodoPago=pay_type)

             if dateInicio != None and dateInicio!="":
                dateI=parse_datetime(dateInicio)
                fechaI=dateInicio
                request.session['dateInicio'] = fechaI
                ComprasLista=ComprasLista.filter(FechaCompra__gte=dateI)

             if dateFinal != None and dateFinal!="":
                    dateF=parse_datetime(dateFinal)
                    fechaF=dateFinal
                    request.session['dateFinal'] = fechaF
                    ComprasLista=ComprasLista.filter(FechaCompra__lte=dateF)

             if grupo!= None and grupo!="":
                   # if grupo!="0":
                    #    ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Pagado)
                    if grupo=="1":
                        ComprasLista=ComprasLista.values('idComprador__Correo').annotate(head_count=Count('idComprador__Correo'), totalNumeros=Sum('NumeroBoletos'), totalPagadoS=Sum('TotalPagado')).values('idComprador__Correo','head_count','totalNumeros', 'totalPagadoS')
                    if grupo=="2":
                        ComprasLista=ComprasLista.values('idComprador__Cedula').annotate(head_count=Count('idComprador__Cedula'),totalNumeros=Sum('NumeroBoletos'), totalPagadoS=Sum('TotalPagado')).values('idComprador__Cedula','head_count', 'totalNumeros', 'totalPagadoS')
                    if grupo=="3":
                        ComprasLista=ComprasLista.values('idComprador__Nombre').annotate(head_count=Count('idComprador__Nombre'),totalNumeros=Sum('NumeroBoletos'), totalPagadoS=Sum('TotalPagado')).values('idComprador__Nombre','head_count','totalNumeros', 'totalPagadoS')
                    if grupo!="0" and numeroBusquedaTotal!=None and numeroBusquedaTotal!="" :
                        ComprasLista=ComprasLista.filter(totalNumeros=numeroBusquedaTotal)
                        logger.info(len(list(ComprasLista)))


    if request.method == "POST":
        logger.info('post')

        logger.info(request.POST['dateFinal'])
        logger.info( request.session)
        if (is_cookie_set == 1): 
          request.session['Estado']=None
          request.session['textoBusqueda']=None
          request.session['dateInicio']=None
          request.session['dateFinal']=None
          request.session['dateFinal']=None
          request.session['grupo']=None
          request.session['pay_type']=0
          request.session['numeroBusquedaTotal']=None

        grupo=request.POST.get('grupo')
        pay_type=int(request.POST.get('pay_type'))
        estado=request.POST.get('Estado') 
        texto=request.POST.get('textoBusqueda')
        dateFinal=request.POST.get('dateFinal')
        dateInicio=request.POST.get('dateInicio')
        numeroBusquedaTotal=request.POST.get('numeroBusquedaTotal')

        '''if grupo!= None and grupo!="" and grupo!="0":
            estado=None
            texto=None
            dateFinal=None
            dateInicio=None'''
        
        
        if estado!= None and estado!="":
         if estado=="1":
            ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Pendiente)
         if estado=="2":
            ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Cancelado)
         if estado=="3":
            ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Pagado)
         if estado=="4":
                    ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Rechazado)
         if estado=="5":
                    ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Caducado)
         request.session['Estado'] = estado

        if texto!= None and texto!="":
         ComprasLista=ComprasLista.filter(Q(Id__icontains=texto) | Q(idComprador__Nombre__icontains=texto)| Q(idRifa__Nombre__icontains=texto ) | Q(idComprador__Cedula__icontains=texto ) | Q(Referencia__icontains=texto) | Q(Referencia__icontains=texto) | Q(idComprador__Correo__icontains=texto))
         request.session['textoBusqueda'] = texto
        if pay_type != 0 and pay_type!=None:
          request.session['pay_type'] = pay_type
          ComprasLista=ComprasLista.filter(MetodoPago=pay_type)
        if dateInicio != None and dateInicio!="":
          dateI=parse_datetime(dateInicio)
          fechaI=dateInicio
          request.session['dateInicio'] = fechaI
          ComprasLista=ComprasLista.filter(FechaCompra__gte=dateI)

        if dateFinal != None and dateFinal!="":
          dateF=parse_datetime(dateFinal)
          fechaF=dateFinal
          request.session['dateFinal'] = fechaF
          ComprasLista=ComprasLista.filter(FechaCompra__lte=dateF)

        if grupo!= None and grupo!="":
         #if grupo!="0":
          #  ComprasLista=ComprasLista.filter(Estado=Compra.EstadoCompra.Pagado)
         if grupo=="1":
            logger.info("grupo")

            ComprasLista=ComprasLista.values('idComprador__Correo').annotate(head_count=Count('idComprador__Correo'), totalNumeros=Sum('NumeroBoletos'), totalPagadoS=Sum('TotalPagado')).values('idComprador__Correo','head_count','totalNumeros', 'totalPagadoS')
         if grupo=="2":
            ComprasLista=ComprasLista.values('idComprador__Cedula').annotate(head_count=Count('idComprador__Cedula'),totalNumeros=Sum('NumeroBoletos'), totalPagadoS=Sum('TotalPagado')).values('idComprador__Cedula','head_count', 'totalNumeros', 'totalPagadoS')
         if grupo=="3":
            ComprasLista=ComprasLista.values('idComprador__Nombre').annotate(head_count=Count('idComprador__Nombre'),totalNumeros=Sum('NumeroBoletos'), totalPagadoS=Sum('TotalPagado')).values('idComprador__Nombre','head_count','totalNumeros', 'totalPagadoS')
         if grupo!="0" and numeroBusquedaTotal!=None and numeroBusquedaTotal!="" :
            logger.info('toy aqui')
            logger.info(numeroBusquedaTotal)

            ComprasLista=ComprasLista.filter(totalNumeros=numeroBusquedaTotal)

         request.session['grupo'] = grupo



    template = loader.get_template("Rifa/Historial.django")
    Rifas=RifaModel.objects.filter(Estado=True).filter(Eliminada=False)
    Rifa=Rifas.last()

    if grupo== None or grupo=="":
        ComprasLista=ComprasLista.order_by("-Id")
    if grupo=='0':
        ComprasLista=ComprasLista.order_by("-Id")
        numeroBusquedaTotal=None
        request.session['numeroBusquedaTotal']=None

    logger.info(numeroBusquedaTotal)
    if grupo=='1' or grupo=='2' or grupo=='3':
        ComprasLista=ComprasLista.order_by("-totalNumeros")

    paginator = Paginator(ComprasLista, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    if estado==None :
      estado="0"
    if texto==None  :
      texto=""
    if grupo==None  :
      grupo="0"
    if numeroBusquedaTotal==None  :
        numeroBusquedaTotal=""
    context = {
        "Rifa":Rifa,
        "RifaHistorial":RifaHistorial,
        "Compras":page_obj,
        "Estado":estado,
        "textoBusqueda":texto,
        "dateInicio":dateInicio,
        "dateFinal":dateFinal,
        "pay_type":pay_type,
        "grupo":grupo,
        'id':id,
        "numeroBusquedaTotal":numeroBusquedaTotal,


    }
    return HttpResponse(template.render(context, request))

@login_required(login_url="/Login/")
@permission_required('Rifa.view_compra', raise_exception=True)
def Usuarios(request):
    texto = None
    dateInicio = None
    dateFinal = None
    
    # Check session for existing filters
    if 'textoBusquedaUsuarios' in request.session or 'dateInicioUsuarios' in request.session or 'dateFinalUsuarios' in request.session:
        texto = request.session.get('textoBusquedaUsuarios')
        dateInicio = request.session.get('dateInicioUsuarios')
        dateFinal = request.session.get('dateFinalUsuarios')
    
    # Get all Cliente objects (registered users)
    ClientesLista = Cliente.objects.all().select_related('user').order_by('-fecha_registro')
    
    if request.method == 'GET':
        # Clear filters if not paginating
        if request.GET.get('page') is None:
            request.session['textoBusquedaUsuarios'] = None
            request.session['dateInicioUsuarios'] = None
            request.session['dateFinalUsuarios'] = None
            texto = None
            dateInicio = None
            dateFinal = None
        else:
            # Apply filters from session
            if texto and texto.strip():
                ClientesLista = ClientesLista.filter(
                    Q(user__first_name__icontains=texto) |
                    Q(user__last_name__icontains=texto) |
                    Q(user__username__icontains=texto) |
                    Q(user__email__icontains=texto) |
                    Q(cedula__icontains=texto) |
                    Q(telefono__icontains=texto)
                )
            
            if dateInicio and dateInicio.strip():
                dateI = parse_datetime(dateInicio)
                if dateI:
                    ClientesLista = ClientesLista.filter(fecha_registro__gte=dateI)
            
            if dateFinal and dateFinal.strip():
                dateF = parse_datetime(dateFinal)
                if dateF:
                    ClientesLista = ClientesLista.filter(fecha_registro__lte=dateF)
    
    if request.method == 'POST':
        # Clear previous session filters
        request.session['textoBusquedaUsuarios'] = None
        request.session['dateInicioUsuarios'] = None
        request.session['dateFinalUsuarios'] = None
        
        texto = request.POST.get('textoBusqueda')
        dateInicio = request.POST.get('dateInicio')
        dateFinal = request.POST.get('dateFinal')
        
        # Apply search filter
        if texto and texto.strip():
            ClientesLista = ClientesLista.filter(
                Q(user__first_name__icontains=texto) |
                Q(user__last_name__icontains=texto) |
                Q(user__username__icontains=texto) |
                Q(user__email__icontains=texto) |
                Q(cedula__icontains=texto) |
                Q(telefono__icontains=texto)
            )
            request.session['textoBusquedaUsuarios'] = texto
        
        # Apply date filters
        if dateInicio and dateInicio.strip():
            dateI = parse_datetime(dateInicio)
            if dateI:
                ClientesLista = ClientesLista.filter(fecha_registro__gte=dateI)
                request.session['dateInicioUsuarios'] = dateInicio
        
        if dateFinal and dateFinal.strip():
            dateF = parse_datetime(dateFinal)
            if dateF:
                ClientesLista = ClientesLista.filter(fecha_registro__lte=dateF)
                request.session['dateFinalUsuarios'] = dateFinal
    
    # Pagination
    paginator = Paginator(ClientesLista, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Default values for template
    if texto is None:
        texto = ""
    if dateInicio is None:
        dateInicio = ""
    if dateFinal is None:
        dateFinal = ""
    
    template = loader.get_template("Rifa/Usuarios.django")
    context = {
        "Usuarios": page_obj,
        "textoBusqueda": texto,
        "dateInicio": dateInicio,
        "dateFinal": dateFinal,
    }
    return HttpResponse(template.render(context, request))
@login_required(login_url="/Login/")
@permission_required('Rifa.view_rifa', raise_exception=True)
def ListaRifas(request):
    is_cookie_set = 0
    nombre = None
    estado = None
    dateInicio = None
    dateFinal = None
    orderBy = '1'
    if 'Estado' in request.session or 'Nombre' in request.session:
        nombre = request.session['Nombre'] if 'Nombre' in request.session else None
        estado = request.session['Estado'] if 'Estado' in request.session else None
        dateInicio = request.session['dateInicio'] if 'dateInicio' in request.session else None
        dateFinal = request.session['dateFinal'] if 'dateFinal' in request.session else None
        orderBy = request.session['orderBy'] if 'orderBy' in request.session else '1'
        is_cookie_set = 1

    Rifas = RifaModel.objects.all()
    Rifas = Rifas.filter(Eliminada=False).order_by("-Id")
    Rifa = Rifas.filter(Estado=True).filter(Eliminada=False).last()

    if request.method == "POST":
        logger.info(request.POST)
        if (is_cookie_set == 1):
            request.session['Nombre'] = None
            request.session['Estado'] = None

        nombre = request.POST.get('Nombre')
        estado = request.POST.get('Estado')
        dateInicio = request.POST.get('dateInicio')
        dateFinal = request.POST.get('dateFinal')
        orderBy = request.POST.get('orderBy')

        if estado != None and estado !="":
            if estado == "0":
                country_time_zone = pytz.timezone('America/Caracas')
                country_time = datetime.now(country_time_zone)
                Rifas = Rifas.filter(FechaSorteo__gte=country_time)
            if estado == "1":
                country_time_zone = pytz.timezone('America/Caracas')
                country_time = datetime.now(country_time_zone)
                Rifas = Rifas.filter(FechaSorteo__lt=country_time)
            request.session['Estado'] = estado

        if nombre != None and nombre !="":
            Rifas = Rifas.filter(Nombre__icontains=nombre)
            request.session['Nombre'] = nombre

        if dateInicio != None and dateInicio !="":
            dateI=parse_datetime(dateInicio)
            Rifas = Rifas.filter(FechaSorteo__gte=dateI)
            request.session['dateInicio'] = dateInicio

        if dateFinal != None and dateFinal !="":
            dateF=parse_datetime(dateFinal)
            Rifas = Rifas.filter(FechaSorteo__lte=dateF)
            request.session['dateFinal'] = dateFinal

        if orderBy != None and orderBy !="":
            if orderBy == "0":
                Rifas = Rifas.order_by("Id")
            if orderBy == "1":
                Rifas = Rifas.order_by("-Id")
            request.session['orderBy'] = orderBy

    if request.method == 'GET':
        if request.GET.get('page') == None:
            logger.info("entro")
            is_cookie_set = 0
            request.session['Nombre'] = None
            request.session['Estado'] = None
            request.session['dateInicio'] = None
            request.session['dateFinal'] = None
            request.session['orderBy'] = None
            nombre = ""
            estado = "2"
            dateInicio = ""
            dateFinal = ""
            orderBy = "1"

        if (is_cookie_set == 1):
            if estado != None and estado !="":
                if estado == "0":
                    country_time_zone = pytz.timezone('America/Caracas')
                    country_time = datetime.now(country_time_zone)
                    Rifas = Rifas.filter(FechaSorteo__gte=country_time)
                if estado == "1":
                    country_time_zone = pytz.timezone('America/Caracas')
                    country_time = datetime.now(country_time_zone)
                    Rifas = Rifas.filter(FechaSorteo__lt=country_time)

                if nombre != None and nombre !="":
                    Rifas = Rifas.filter(Nombre__icontains=nombre)

                if dateInicio != None and dateInicio !="":
                    dateI=parse_datetime(dateInicio)
                    Rifas = Rifas.filter(FechaSorteo__gte=dateI)

                if dateFinal != None and dateFinal !="":
                    dateF=parse_datetime(dateFinal)
                    Rifas = Rifas.filter(FechaSorteo__lte=dateF)

                if orderBy != None and orderBy !="":
                    if orderBy == "0":
                        Rifas = Rifas.order_by("Id")
                    if orderBy == "1":
                        Rifas = Rifas.order_by("-Id")

    template = loader.get_template("Rifa/ListaRifa.django")
    page_number = request.GET.get('page')
    paginator = Paginator(Rifas, 8)
    page_obj = paginator.get_page(page_number)

    if nombre == None  :
        nombre = ""
    if estado == None :
        estado = "2"
    if dateInicio == None :
        dateInicio = ""
    if dateFinal == None :
        dateFinal = ""
    if orderBy == None :
        orderBy = "1"
    context = {
        "Rifa": Rifa,
        "Rifas": page_obj,
        "Estado": estado,
        "Nombre": nombre,
        "dateInicio": dateInicio,
        "dateFinal": dateFinal,
        "orderBy": orderBy,
    }
    return HttpResponse(template.render(context, request))
import json
@login_required(login_url="/Login/")
def deleteRifa(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        id = data['id']
        Rifa = RifaModel.objects.get(Id=int(id))
        if Rifa.Estado == True:
            return JsonResponse({'status': 'error', 'message': 'No se puede eliminar una rifa activa'})
        #filter Compra by idRifa foreing key
        compras = Compra.objects.filter(idRifa_id=int(id))
        if compras.count() > 0:
            return JsonResponse({'status': 'error', 'message': 'No se puede eliminar una rifa con compras'})
        Rifa.Eliminada = True
        Rifa.Estado = False
        Rifa.save()
        return JsonResponse({'status': 'success', 'message': 'Rifa Eliminada'})
    
@login_required(login_url="/Login/")
def insertVideoRifa(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        id = data['id']
        url = data['url']
        Rifa = RifaModel.objects.get(Id=int(id))
        Rifa.Video = url
        Rifa.save()
        return JsonResponse({'status': 'success', 'message': 'Rifa Actualizada'})

@login_required(login_url="/Login/")
def copyRifa(request):
    if request.method == 'POST':
        ###Encontramos la rifa
        data = json.loads(request.body)
        id = data['id']
        Rifa = RifaModel.objects.get(Id=int(id))

        ###Creamos la rifa nueva
        new_rifa = RifaModel()
        
        ###Revisar que el nombre sea nuevo
        rifas_nombres_parecidos = RifaModel.objects.all().filter(
            Nombre__startswith=Rifa.Nombre).count()
        new_rifa.Nombre = Rifa.Nombre+f"({rifas_nombres_parecidos+1})"

        ###Para el nombre de enlace hay que hacer un detalle
        rifas_parecidas = RifaModel.objects.all().filter(
            NombreEnlace__icontains=Rifa.NombreEnlace).count()
        new_rifa.NombreEnlace = Rifa.NombreEnlace+f"-{rifas_parecidas+1}"

        ###Copio los detalles de la rifa anterior
        new_rifa.Intervalo = Rifa.Intervalo
        if Rifa.ModoPorcentaje == False:
         new_rifa.FechaSorteo = Rifa.FechaSorteo
        else:
            new_rifa.FechaSorteo = None
        new_rifa.PorcentajeActivacion=Rifa.PorcentajeActivacion
        new_rifa.ModoPorcentaje=Rifa.ModoPorcentaje
        new_rifa.DiasFecha=Rifa.DiasFecha
        new_rifa.MinCompra = Rifa.MinCompra
        new_rifa.MaxCompra = Rifa.MaxCompra
        new_rifa.RangoInicial = Rifa.RangoInicial
        new_rifa.RangoFinal = Rifa.RangoFinal
        new_rifa.Precio = Rifa.Precio
        new_rifa.Banner = Rifa.Banner
        new_rifa.Descripcion = Rifa.Descripcion
        new_rifa.Resumen = Rifa.Resumen
        new_rifa.Estado = False
        new_rifa.Eliminada = False
        new_rifa.TotalNumeros = Rifa.TotalNumeros
        new_rifa.TotalComprados = 0
        new_rifa.save()

        zerroFill=str(new_rifa.RangoFinal).__len__()
        country_time_zone = pytz.timezone('America/Caracas')
        country_time = datetime.now(country_time_zone)
        new_rifa.fechaCreacion=country_time

        ###Aca termina el modelo de rifa
        numDisp = NumeroRifaDisponiblesArray(idRifa=new_rifa, Numeros= [ '{:0{}d}'.format(number,zerroFill) for number in range(new_rifa.RangoInicial, new_rifa.RangoFinal+1, new_rifa.Intervalo)]  )
        compradosbyArray=NumeroRifaCompradosArray(idRifa=new_rifa, Numeros= []  )
        #for in range
        numDispList=[]
        total=0
        for i in range(new_rifa.RangoInicial, new_rifa.RangoFinal+1, new_rifa.Intervalo):
            numDispList.append(NumeroRifaDisponibles(idRifa=new_rifa, Numero='{:0{}d}'.format(i,zerroFill)    ))
            total+=1
        new_rifa.TotalNumeros=total
        try:
            with transaction.atomic():
                new_rifa.save()
                numDisp.save()
                compradosbyArray.save()
                NumeroRifaDisponibles.objects.bulk_create(numDispList)
                #Premios
                logger.info(f'Rifa model premios {Rifa.PremiosRifa.all()}')
                logger.info(f'Premios count {Rifa.PremiosRifa.all().count()}')
                if Rifa.PremiosRifa.all().count() > 0 :
                    for premio in Rifa.PremiosRifa.all():
                        logger.info(premio)
                        premio = PremiosRifa(idRifa=new_rifa, Nombre=premio.Nombre, Descripcion=premio.Descripcion, FotoPremio=premio.FotoPremio, Orden=premio.Orden)
                        premio.save()
        except IntegrityError as e:
            logger.info(f'Integrity error {e}')
            return JsonResponse({'status': 'error', 'message': 'Error guardando la rifa'}, status=500)
        except Exception as e:
            logger.info(f'Error {e}')
            return JsonResponse({'status': 'error', 'message': 'Error guardando la rifa'}, status=500)
        ###Enviamos la respuesta
        return JsonResponse({'status': 'success', 'message': 'Rifa Copiada'})

@login_required(login_url="/Login/")
@permission_required('Rifa.add_rifa', raise_exception=True)
def Rifa(request):
    template = loader.get_template("Rifa/RifaCreate.django")
    if request.method == 'POST':
        logger.info(request.POST)
        modo_porcentaje = request.POST.get('ModoPorcentaje')
        form = RifaForm(request.POST, request.FILES)
        logger.info(request.FILES)
        logger.info(request.POST)
        logger.info(form)
        

        # check if form data is valid
        if form.is_valid():
            cantidad_boletos = int(request.POST.get('Cantidad') or 0)
            estado_rifa = request.POST.get('Estatus') == '1'
            print(cantidad_boletos,estado_rifa)
            # save the form data to model
            #form.save()
            rifa=form.save(commit=False)
            
            rifa.RangoFinal = cantidad_boletos - 1
            rifa.RangoInicial = 0
            rifa.Intervalo = 1
            rifa.Extension = True
            rifa.Estado = estado_rifa
            rifa.Descripcion = rifa.Resumen
            if rifa.PorcentajeActivacion == '' or rifa.PorcentajeActivacion is None:
                rifa.PorcentajeActivacion = 0
            if rifa.DiasFecha == '' or rifa.DiasFecha is None:
                rifa.DiasFecha = 0
            if (rifa.FechaSorteo == '' or rifa.FechaSorteo is None) and modo_porcentaje is None:
                rifa.FechaSorteo = datetime.now(pytz.timezone('America/Caracas')) + relativedelta(years=1)
            if rifa.ModoPorcentaje == True:
             rifa.FechaSorteo=None
            zerroFill=str(rifa.RangoFinal).__len__()
            country_time_zone = pytz.timezone('America/Caracas')
            country_time = datetime.now(country_time_zone)
            ## fecha sorteo is being
            rifa.fechaCreacion=country_time
            # set a slug if its necessary
            rifa.NombreEnlace = generate_slug(rifa.Nombre, RifaModel)
            numDisp = NumeroRifaDisponiblesArray(idRifa=rifa, Numeros= [ '{:0{}d}'.format(number,zerroFill) for number in range(rifa.RangoInicial, rifa.RangoFinal+1, rifa.Intervalo)]  )
            compradosbyArray=NumeroRifaCompradosArray(idRifa=rifa, Numeros= []  )
            #for in range
            numDispList=[]
            total=0
            for i in range(rifa.RangoInicial, rifa.RangoFinal+1, rifa.Intervalo):
                numDispList.append(NumeroRifaDisponibles(idRifa=rifa, Numero='{:0{}d}'.format(i,zerroFill)    ))
                total+=1
            
            rifa.TotalNumeros=total
            #Aca va la pagina a la cual se redirecciona en caso de exito
            # template = loader.get_template("Rifa/ListaRifa.django")
            try:
                with transaction.atomic():
                    rifa.save()
                    numDisp.save()
                    compradosbyArray.save()
                    NumeroRifaDisponibles.objects.bulk_create(numDispList)
                # for i in range(rifa.RangoInicial, rifa.RangoFinal+1, rifa.Intervalo):
                #  NumeroRifaDisponibles.objects.create(idRifa=rifa, Numero=i)
                    #Premios
                    if 'PremioDescripcion[]' in request.POST:
                        descripcionlist = request.POST.getlist('PremioDescripcion[]')
                        imagenlist = request.FILES.getlist('PremioImagen[]')
                        for num in range(len(descripcionlist)):
                            if descripcionlist[num] != '':
                                logger.info(descripcionlist[num])
                                premio = PremiosRifa(idRifa=rifa, Nombre=descripcionlist[num], FotoPremio=imagenlist[num], Orden=num)
                                premio.save()
            except IntegrityError as e:
                print(e)
                return HttpResponse("Error")
            return redirect("ListaRifas")
            #NumeroRifaDisponibles.objects.bulk_create(numDispList)
    else:
         form = RifaForm(initial={"Intervalo":1, "RangoInicial":0, "RangoFinal":9999})
        
    Rifas=RifaModel.objects.all()
    Rifa=Rifas.filter(Estado=True).filter(Eliminada=False).last()
    context = {
        "form":form,
        "Rifa":Rifa
    }
    return HttpResponse(template.render(context, request))

@login_required(login_url="/Login/")
@permission_required('Rifa.change_rifa', raise_exception=True)
def RifaEdit(request, id):
    template = loader.get_template("Rifa/RifaEdit.django")
    rif=None
    rif_old_name = ""
    if id!=None:
        rif=RifaModel.objects.get(Id=id)
        form = RifaForm(instance=rif)
        rif_old_name = rif.Nombre
        if rif.Estado:
            return redirect("ListaRifas")
    else:
        form = RifaForm(None)
    if request.method == 'POST':
        logger.info(request.POST)
        initial_form = {}
        modo_porcentaje = request.POST.get('ModoPorcentaje')
        form = RifaForm(request.POST, request.FILES, instance=rif)
        print(initial_form, form.data.update(), form.data, modo_porcentaje)
        logger.info(request.FILES)
        logger.info(request.POST)
        cantidad_boletos = int(request.POST.get('Cantidad') or 0)
        estado_rifa = request.POST.get('Estatus') == '1'
        print(cantidad_boletos,estado_rifa)

        # check if form data is valid
        if form.is_valid():
            # save the form data to model
            #form.save()
            rifa=form.save(commit=False)
            rifa.RangoFinal = cantidad_boletos - 1
            rifa.RangoInicial = 0
            rifa.Intervalo = 1
            rifa.Descripcion = rifa.Resumen
            if rifa.PorcentajeActivacion == '' or rifa.PorcentajeActivacion is None:
                rifa.PorcentajeActivacion = 0
            if rifa.DiasFecha == '' or rifa.DiasFecha is None:
                rifa.DiasFecha = 0
            if (rifa.FechaSorteo == '' or rifa.FechaSorteo is None) and modo_porcentaje is None:
                rifa.FechaSorteo = datetime.now(pytz.timezone('America/Caracas')) + relativedelta(years=1)
            if rifa.ModoPorcentaje == True:
             rifa.FechaSorteo=None
            zerroFill=str(rifa.RangoFinal).__len__()
            country_time_zone = pytz.timezone('America/Caracas')
            country_time = datetime.now(country_time_zone)
            rifa.fechaCreacion=country_time
            logger.info(f" - views - RifaEdit - {rifa.Nombre} vs {rif_old_name}")
            if rifa.Nombre != rif_old_name:
                rifa.NombreEnlace = generate_slug(rifa.Nombre, RifaModel)
            logger.info(rif.Estado == False and rif.TotalComprados == 0)
            if rif.Estado == False and rif.TotalComprados == 0:
                oldNumDispArray = NumeroRifaDisponiblesArray.objects.filter(idRifa=rif)
                if oldNumDispArray.count() > 0:
                    logger.info(f'i found some objects, like {oldNumDispArray.count()}')
                    oldNumDispArray.delete()
                oldNumDisp = NumeroRifaDisponibles.objects.filter(idRifa=rif)
                if oldNumDisp.count() > 0:
                    logger.info(f'i found some objects, like {oldNumDisp.count()}')
                    oldNumDisp.delete()
                numDisp = NumeroRifaDisponiblesArray(idRifa=rifa, Numeros= [ '{:0{}d}'.format(number,zerroFill) for number in range(rifa.RangoInicial, rifa.RangoFinal+1, rifa.Intervalo)]  )
                compradosbyArray=NumeroRifaCompradosArray(idRifa=rifa, Numeros= []  )
                #for in range
                numDispList=[]
                total=0
                rifa.Estado = estado_rifa
                #comprobar que la rifa este activa, si esta activa
                #no puedes editar este apartado, en caso de que no
                #borro todos los nros anteriores y que el Array se 
                #llene desde cero
                for i in range(rifa.RangoInicial, rifa.RangoFinal+1, rifa.Intervalo):
                    numDispList.append(NumeroRifaDisponibles(idRifa=rifa, Numero='{:0{}d}'.format(i,zerroFill)    ))
                    total+=1
                
                rifa.TotalNumeros=total
                #Aca va la pagina a la cual se redirecciona en caso de exito
                # template = loader.get_template("Rifa/ListaRifa.django")
                try:
                    with transaction.atomic():
                        rifa.save()
                        numDisp.save()
                        compradosbyArray.save()
                        if len(numDispList) > 0:
                            NumeroRifaDisponibles.objects.bulk_create(numDispList)
                    # for i in range(rifa.RangoInicial, rifa.RangoFinal+1, rifa.Intervalo):
                    #  NumeroRifaDisponibles.objects.create(idRifa=rifa, Numero=i)
                except IntegrityError as e:
                    print(e)
                    return HttpResponse("Error")
                #Premios
                if 'PremioDescripcion[]' in request.POST and 'PremioImagen[]' in request.FILES:
                    descripcionlist = request.POST.getlist('PremioDescripcion[]')
                    imagenlist = request.FILES.getlist('PremioImagen[]')
                    for num in range(len(descripcionlist)):
                        if descripcionlist[num] != '':
                            logger.info(descripcionlist[num])
                            premio_viejo = PremiosRifa.objects.filter(Nombre=descripcionlist[num], idRifa=rifa)
                            if not premio_viejo:   
                                premio = PremiosRifa(
                                    idRifa=rifa, 
                                    Nombre=descripcionlist[num], 
                                    FotoPremio=imagenlist[num], 
                                    Orden=num)
                                premio.save()
                return redirect("ListaRifas")
            #NumeroRifaDisponibles.objects.bulk_create(numDispList)
        
    Rifas=RifaModel.objects.all()
    Rifa=Rifas.filter(Estado=True).filter(Eliminada=False).last()
    context = {
        "form":form,
        "cantidad": rif.RangoFinal + 1,
        "precio": rif.Precio,
        "Rifa":Rifa,
        "rif":rif
    }
    return HttpResponse(template.render(context, request))
@login_required(login_url="/Login/")
def PremiosDelete(request, id):
    rif=None
    if id!=None:
        rif=RifaModel.objects.get(Id=id)
        if rif:
            rif.PremiosRifa.all().delete()
        return JsonResponse({"result":"success"})
    else:
        return HttpResponse("Error")
    
    template = loader.get_template("Rifa/RifaCreate.django")
    Rifas=RifaModel.objects.filter(Estado=True).filter(Eliminada=False)
    Rifa=Rifas.last()
    context = {
        "Rifa":Rifa
    }
    return HttpResponse(template.render(context, request))
def vistaCompra(request, name):
    if request.method == "GET":
        if name == None:
            # return error 404
            return HttpResponseNotFound()
        else: 
            try:
                
                CompraObj = Compra.objects.filter(Estado=Compra.EstadoCompra.Pagado).get(hash=name)
                # array numbers
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
                return render(request, 'Rifa/CorreoComprobante.django', context)
            except :
                return HttpResponseNotFound()

def VerificadorRifa(request,name):
 try:
    country_time_zone = pytz.timezone('America/Caracas')
    country_time = datetime.now(country_time_zone)
    logger.info(country_time.strftime("Date is %d-%m-%y and time is %H:%M:%S"))
    country_time_zone = pytz.timezone('America/Caracas')
    country_time = datetime.now(country_time_zone)

    template = loader.get_template("Rifa/Verificador.django")
    Rifas=RifaModel.objects.filter(Estado=True).filter(Eliminada=False)
    Rifa=Rifas.get(NombreEnlace=name)
    compras = []
    numerosAprobados = []
    numerosPendientes = []
    correo = None
    if request.method == "GET":
        form = VerificaForm(request.GET)
        if form.is_valid():
            correo = form.cleaned_data['correo']
            print('verificador: ' + correo)
            compras = Compra.objects.filter(idRifa=Rifa).filter(idComprador__Correo=correo)
            numerosAprobados = NumerosCompra.objects.filter(idCompra__idRifa=Rifa).filter(idCompra__Estado=Compra.EstadoCompra.Pagado).filter(idCompra__idComprador__Correo=correo)
            numerosPendientes = NumerosCompra.objects.filter(idCompra__idRifa=Rifa).filter(idCompra__Estado=Compra.EstadoCompra.Pendiente).filter(idCompra__idComprador__Correo=correo)
        
    context = {
        "id":id,
        "Rifa":Rifa,
        "correo":correo,
        "compras":compras,
        "numerosAprobados":numerosAprobados,
        "numerosPendientes":numerosPendientes,
    }
    return HttpResponse(template.render(context, request))
 except Exception as e:
        logger.info(e)
        print(e)
        raise e
        return HttpResponseNotFound('<h1>Page not found</h1>')
 

def DetallesRifa(request,name):
 try:
    tasa = Tasas.objects.last()
    country_time_zone = pytz.timezone('America/Caracas')
    country_time = datetime.now(country_time_zone)
    logger.info(country_time.strftime("Date is %d-%m-%y and time is %H:%M:%S"))
    country_time_zone = pytz.timezone('America/Caracas')
    country_time = datetime.now(country_time_zone)

    template = loader.get_template("Rifa/Detalles.django")
    Rifas=RifaModel.objects.filter(Estado=True).filter(Eliminada=False)
    Rifa=Rifas.last()
    RifaD=Rifas.get(NombreEnlace=name)
    premios=PremiosRifa.objects.filter(idRifa=RifaD)
    numDisp = NumeroRifaDisponibles.objects.filter(idRifa=RifaD).count()
    noDisponible=False
    if RifaD.FechaSorteo!=None:
        if country_time>=RifaD.FechaSorteo:
            if RifaD.Extension==False:
             noDisponible=True
    if RifaD.FechaSorteo==None:
        if RifaD.TotalComprados==RifaD.TotalNumeros or numDisp==0: 
            noDisponible=True
# numeros compra grupo by compra id
  #  grupoNumeros=NumerosCompra.objects.filter(idCompra__idRifa=RifaD).values('idCompra__Id').annotate(total=Count('Numero'))
   # grupoNumeros=grupoNumeros.filter(total__lt=F('idCompra__NumeroBoletos'))
   # logger.info(grupoNumeros.count())
   # for x in grupoNumeros:
    #    logger.info(x['idCompra__Id'])
        
    whatsapp_config=Settings.objects.filter(code="PHONE_CLIENT").first()
    percent_config=Settings.objects.filter(code="HIDE_TICKET_COUNT").first()
    zelle_condition_type_config=Settings.objects.filter(code="ZELLE_CONDITION_TYPE").first()
    zelle_min_value_config=Settings.objects.filter(code="ZELLE_MIN_VALUE").first()
    zelle_email_config=Settings.objects.filter(code="ZELLE_EMAIL").first()

    context = {
        "id":id,
        "Rifa":Rifa,
        "RifaD":RifaD,
        "premios":premios,
        "noDisponible":noDisponible,
        "tasa":tasa,
        'numDisp':numDisp,
        'whatsapp_config':whatsapp_config,
        'percent_config':percent_config,
        'zelle_condition_type':zelle_condition_type_config,
        'zelle_min_value':zelle_min_value_config,
        'zelle_email':zelle_email_config,
    }
    return HttpResponse(template.render(context, request))
 except Exception as e:
        logger.info(e)
        raise e
        return HttpResponseNotFound('<h1>Page not found</h1>')
 
@login_required(login_url="/Login/")
def PreviewRifa(request,name):
 try:
    tasa = Tasas.objects.last()
    country_time_zone = pytz.timezone('America/Caracas')
    country_time = datetime.now(country_time_zone)
    logger.info(country_time.strftime("Date is %d-%m-%y and time is %H:%M:%S"))
    country_time_zone = pytz.timezone('America/Caracas')
    country_time = datetime.now(country_time_zone)

    template = loader.get_template("Rifa/Preview.django")
    Rifas=RifaModel.objects.all()
    Rifa=Rifas.last()
    RifaD=Rifas.get(NombreEnlace=name)
    premios=PremiosRifa.objects.filter(idRifa=RifaD)
    numDisp = NumeroRifaDisponibles.objects.filter(idRifa=RifaD).count()
    noDisponible=False
    if RifaD.FechaSorteo!=None:

     if country_time>=RifaD.FechaSorteo:
        if RifaD.Extension==False:
         noDisponible=True
    if RifaD.FechaSorteo!=None:

     if RifaD.TotalComprados==RifaD.TotalNumeros or numDisp==0: 
        noDisponible=True
# numeros compra grupo by compra id
  #  grupoNumeros=NumerosCompra.objects.filter(idCompra__idRifa=RifaD).values('idCompra__Id').annotate(total=Count('Numero'))
   # grupoNumeros=grupoNumeros.filter(total__lt=F('idCompra__NumeroBoletos'))
   # logger.info(grupoNumeros.count())
   # for x in grupoNumeros:
    #    logger.info(x['idCompra__Id'])
    
    whatsapp_config=Settings.objects.filter(code="PHONE_CLIENT").first()
    percent_config=Settings.objects.filter(code="HIDE_TICKET_COUNT").first()
    zelle_condition_type_config=Settings.objects.filter(code="ZELLE_CONDITION_TYPE").first()
    zelle_min_value_config=Settings.objects.filter(code="ZELLE_MIN_VALUE").first()
    zelle_email_config=Settings.objects.filter(code="ZELLE_EMAIL").first()

    context = {
        "id":id,
        "Rifa":Rifa,
        "RifaD":RifaD,
        "premios":premios,
        "noDisponible":noDisponible,
        "tasa":tasa,
        'numDisp':numDisp,
        'whatsapp_config':whatsapp_config,
        'percent_config':percent_config,
        'zelle_condition_type':zelle_condition_type_config,
        'zelle_min_value':zelle_min_value_config,
        'zelle_email':zelle_email_config,
    }
    return HttpResponse(template.render(context, request))
 except Exception as e:
        logger.info(e)
        raise e
        return HttpResponseNotFound('<h1>Page not found</h1>')
@login_required(login_url="/Login/")
def recuperaNumeros2 (request):
        RifaC=RifaModel.objects.get(Id=15)
        
        RifaCompras=Compra.objects.filter(Estado=Compra.EstadoCompra.Rechazado)

        x=sum(  x.NumeroBoletos for x in RifaCompras)
        logger.info(x)
        logger.info(RifaC.TotalComprados)

        numerosDIsponibles=NumeroRifaDisponibles.objects.filter(idRifa=RifaC)
        logger.info(numerosDIsponibles.count())
        #35 compras
        compraL=Compra.objects.filter(idRifa=RifaC).filter(Estado=Compra.EstadoCompra.Rechazado).filter(recuperado=False)
        for compraLast in compraL:
            numerosCompra=NumerosCompra.objects.filter(idCompra=compraLast)
            for x in numerosCompra:
                logger.info(x.Numero)
                NumeroRifaDisponibles.objects.create(Numero=x.Numero, idRifa=RifaC)
                RifaC.TotalComprados=RifaC.TotalComprados-1
                RifaC.save()
            compraLast.recuperado=True
            compraLast.save()


        numerosDIsponibles=NumeroRifaDisponibles.objects.filter(idRifa=RifaC)
        logger.info(numerosDIsponibles.count())

def recuperaNumeros (request):
    RifaC=RifaModel.objects.get(Id=20)
        
    RifaCompras=Compra.objects.filter(idRifa=RifaC).filter(Estado=Compra.EstadoCompra.Pagado)
    x=0
    for  CompraObj in RifaCompras:
        logger.info(x)
        x+=1
        try:
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
        except Exception as e:
         logger.info(e)
         return HttpResponse("Error")
         




      

    logger.info(RifaCompras.count())

def loopReenvio(ReenvioObj, RifaCompras, x):
    for CompraObj in RifaCompras:
        logger.info('Vamos por el número', x)
        if (x % 20 == 0):
            logger.info('actualizar el estado del modelo')
            # Acá actualizo el contador
            ReenvioObj.ultimo = x
            ReenvioObj.save()
        x += 1
        try:
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
        except Exception as e:
            logger.info(e)
            logger.info('actualizar el estado del modelo')
            # Acá actualizo el contador
            ReenvioObj.ultimo = x
            ReenvioObj.estado = 2
            ReenvioObj.save()
            return JsonResponse({"message": f"Error en la solicitud, se enviaron: {x} correos"}, safe=False, status=500)
    # Aca actualizo al valor del monto completado
    ReenvioObj.ultimo = x
    ReenvioObj.estado = 1
    ReenvioObj.save()


def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]

def enviarWhatsapp( RifaCompras, x):
    try:
        #separe in  batch of 100
        for batch_of_RifaCompras in batch(RifaCompras, 100):
            #print batch
            logger.info(batch_of_RifaCompras)
            conn = http.client.HTTPConnection("http://api.message.sinvad.lat",80)

            payload = [
             
            ]
            for CompraObj in batch_of_RifaCompras:
                 logger.info(f'CompraObj {CompraObj}')
                 texto="Felicidades "+CompraObj.idComprador.Nombre+" tu compra ["+str(CompraObj.Id)+"] ha sido aprobada, puedes consultar tus numeros en el siguiente enlace, asegurate de no compartirlo con nadie "+settings.URL+"/Comprobante/"+str(CompraObj.hash)
                 numero=CompraObj.idComprador.NumeroTlf
                 numero = re.sub(r'\s+', '', numero.strip())
                 numero = re.sub(r'[^0-9]', '', numero)
                 
                 payload.append(   {
                "attachments": [],
                "subject": "",
                "to": [numero],
                "message": texto,
                "typeMessage": 0
            })


            headers = {
                'Content-Type': "application/json",
                'Authorization': "9D6D0FB7079198C0C958A541D4D9BEBB7C58531F02D33679D1C7B50053C350586682AC095A3150C7CA1B9CC578F914EAF4CF64EB1E02313E2552EF6495B92AE5",
                'SiteAllowed': "NOURL",
                'UserName': "JALEXZANDER",
                "UserApp": "_LOGINVALUSER_",
            }

            conn.request("POST", "/api/Message/AddMessagestoQueue", json.dumps(payload), headers)

            res = conn.getresponse()
            data = res.read()

            logger.info(data.decode("utf-8"))
    except Exception as e:
        logger.info(e)
        return
    return

@login_required(login_url="/Login/")
def reenvioMasivo (request):
    if request.method == 'POST':
        data = json.load(request)
        id = data["id"]
        logger.info(f'Rifa para reenvio de correos {id}')
        RifaC=RifaModel.objects.get(Id=id)
        RifaCompras=Compra.objects.filter(idRifa=RifaC).filter(Estado=Compra.EstadoCompra.Pagado)
        #Primero que nada que la rifa tenga compras
        if (RifaCompras.count() > 0):
            #Vamos a revisar que no haya una rifa a medias
            ReenvioObj = ReenviosMasivos.objects.filter(
                idRifa=RifaC, estado=2).last()
            logger.info(f'Último reenvio masivo realizado {ReenvioObj}')
            if ReenvioObj and ReenvioObj.ultimo > 0:
                x = ReenvioObj.ultimo
                RifaCompras=RifaCompras[x:]
            else:
                #Aca creo el objeto de la BD de reenvio masivo
                ReenvioObj = ReenviosMasivos(total=RifaCompras.count(), idRifa=RifaC)
                ReenvioObj.save()
                x=0
                #enviarWhatsapp( RifaCompras, x)

            #funcion asincrona
                
            loopReenvio(ReenvioObj, RifaCompras, x)
            
            logger.info(f'Cantidad de correos a enviar {RifaCompras.count()}')
            return JsonResponse({"message": f"Solicitud procesada con éxito, cantidad correos a enviar: {(RifaCompras.count())}"}, safe=False, status=200)

        else:
            return HttpResponse("No hay compras en esta rifa")
    else:
        data = ReenviosMasivos.objects.all().order_by("-id")[:15].values()
        logger.info(f'objetos {data}')
        return JsonResponse({"data":list(data)}, safe=False, status=200)


@login_required(login_url="/Login/")
def reenvioMasivoWS (request):
    if request.method == 'POST':

        data = json.load(request)
        id = data["id"]
        logger.info(f'Rifa para reenvio de ws {id}')
        RifaC=RifaModel.objects.get(Id=id)
        RifaCompras=Compra.objects.filter(idRifa=RifaC).filter(Estado=Compra.EstadoCompra.Pagado)
        #Primero que nada que la rifa tenga compras
        if (RifaCompras.count() > 0):
            x=0
            enviarWhatsapp( RifaCompras, x)
            
            return JsonResponse({"message": f"Solicitud procesada con éxito"}, safe=False, status=200)


        else:
            return HttpResponse("No hay compras en esta rifa")
    else:
        data = ReenviosMasivos.objects.all().order_by("-id")[:15].values()
        logger.info(f'objetos {data}')
        return JsonResponse({"data":list(data)}, safe=False, status=200)

def CompraRifa(request,name):
    tasa = Tasas.objects.last()
    country_time_zone = pytz.timezone('America/Caracas')
    country_time = datetime.now(country_time_zone)
    logger.info(country_time.strftime("Date is %d-%m-%y and time is %H:%M:%S"))
    country_time_zone = pytz.timezone('America/Caracas')
    country_time = datetime.now(country_time_zone)
    
    Rifas=RifaModel.objects.filter(Estado=True).filter(Eliminada=False)

    RifaC=Rifas.get(NombreEnlace=name)
    Rifa=Rifas.filter(Estado=True).filter(Eliminada=False).last()


    #35 compras
  
    if RifaC.FechaSorteo != None:
        if country_time>=RifaC.FechaSorteo:
            template = loader.get_template("Rifa/RifaExpirada.html")
            context = {
                "Rifa":Rifa
            }
            if RifaC.Extension==False:
             return HttpResponse(template.render(context, request))

    #cantidad de numers disponibles
    numDisp = NumeroRifaDisponibles.objects.filter(idRifa=RifaC).count()
    logger.info(numDisp)

    if RifaC.TotalComprados==RifaC.TotalNumeros or numDisp==0: 
        template = loader.get_template("Rifa/RifaCompletada.html")
        context = {
            "Rifa":Rifa
        }
        return HttpResponse(template.render(context, request))

    
    template = loader.get_template("Rifa/Compra.html") 
   
    context = {
        "id":id,
        "Rifa":Rifa,
        "RifaC":RifaC,
        "tasa":tasa,
        'numDisp':numDisp
    }
    return HttpResponse(template.render(context, request))

def terminos(request):
    template = loader.get_template("Rifa/terminos.django")
    Rifas=RifaModel.objects.filter(Estado=True).filter(Eliminada=False)
    Rifa=Rifas.last()
    context = {
        "Rifa":Rifa,
    }
    return HttpResponse(template.render(context, request))


def privacidad(request):
    template = loader.get_template("Rifa/privacidad.html")
    Rifas=RifaModel.objects.filter(Estado=True).filter(Eliminada=False)
    Rifa=Rifas.last()
    context = {
        "Rifa":Rifa,
    }
    return HttpResponse(template.render(context, request))