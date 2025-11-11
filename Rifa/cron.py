import pytz
from .models import Compra, Comprador, Logger, NumerosCompra, OrdenesReservas,Rifa as RifaModel, NumeroRifaReservados, NumeroRifaDisponibles, NumeroRifaReservadosOrdenes, Tasas, UsuarioStats
from datetime import datetime, timedelta, timezone
import requests
from lxml import html
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.mail import send_mail
from django.core.mail import EmailMessage, get_connection
from django.template.loader import render_to_string
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.db.models import Max, Case, When
from django.db.models import IntegerField
import logging
logger = logging.getLogger('ballena')

def horario():
  Logger.objects.create(date=datetime.now(), description=f"Ejecutando Cron 1")
  response = requests.get('https://www.bcv.org.ve/', verify=False)
  soup = BeautifulSoup(response.text, 'html.parser')
  dolar=soup.find(id="dolar").text
  #spli lines and remove white empty lines
  dolar=dolar.splitlines()
  dolar=list(filter(None, dolar))
  dolar=dolar[1]
  print(dolar)
  Logger.objects.create(date=datetime.now(), description=f"Ejecutando Cron 2{dolar}")

  #tasa to float
  dolar=float(dolar.replace(",","."))

  Tasas.objects.create(date=datetime.now(), tasa=dolar)

  return
def recuperaNumeros():
  country_time_zone = pytz.timezone('America/Caracas')
  country_time = datetime.now(country_time_zone)
  # get NumeroRifaReservados with more of 15 minutes in date field
  numeros=NumeroRifaReservadosOrdenes.objects.filter(date__lte=country_time-timedelta(minutes=7))

  Logger.objects.create(date=country_time, description=f"Ejecutando Cron {list(numeros)} reservados recuperados")
  
  numerosOrden=numeros.values_list('idOrden', flat=True).distinct()
  
  Logger.objects.create(date=country_time, description=f"Ejecutando Cron {list(numerosOrden)} ordenes ")

  for x in numerosOrden:
      Logger.objects.create(date=country_time, description=f"Ejecutando Cron {x} orden caducada ")
      
      orden= OrdenesReservas.objects.get(Id=x)
      comprador = Comprador()
      comprador.Nombre = orden.customer_name
      comprador.Correo = orden.customer_email
      comprador.NumeroTlf = orden.customer_phone
      # comprador.Direccion=form.cleaned_data['direccion']
      comprador.Cedula = orden.customer_identification
      comprador.save()
      disp = NumeroRifaReservadosOrdenes.objects.filter(
          idOrden=orden.Id)
      totalNum=disp.count()
      compra = Compra()
      compra.idComprador = comprador
      compra.Estado=Compra.EstadoCompra.Caducado
      compra.idRifa = RifaModel.objects.get(
          Id=orden.idRifa.Id)
      compra.FechaCompra = country_time
      compra.NumeroBoletos = totalNum
      compra.TotalPagado = totalNum* \
          compra.idRifa.Precio
      compra.TotalPagadoAlt = totalNum* \
          compra.idRifa.PrecioAlt
      compra.save()
      #ogger.info(f"compra guardada as: {compra}")

      for x in disp:
          NumerosCompra.objects.create(
              idCompra=compra, Numero=x.Numero)
          

  for x in numeros:
    NumeroRifaDisponibles.objects.create(Numero=x.Numero, idRifa=x.idRifa)
  
  numeros.delete()

def validaFechaSorte():

  #get rifas with FechaSorteo is None
  rifas=RifaModel.objects.filter(FechaSorteo=None)
  for rifa in rifas:
    if rifa.ModoPorcentaje == True:
      comprados=rifa.TotalComprados
      totales=rifa.TotalNumeros
      # Porcentaje de números vendidos = (Número de números comprados / Número total de números) * 100
      porcentaje= (comprados/totales)*100
      Logger.objects.create(date=datetime.now(), description=f"Ejecutando validaFechaSortem asisgnando fecha ModoPorcentaje {rifa.Nombre} {rifa.PorcentajeActivacion} {rifa.DiasFecha}  {porcentaje}%")

      if porcentaje >= rifa.PorcentajeActivacion:
        rifa.FechaSorteo=datetime.now()+timedelta(days=rifa.DiasFecha)
        rifa.save()
  
  return

def Stats():
  country_time_zone = pytz.timezone('America/Caracas')
  country_time = datetime.now(country_time_zone)
  
  ComprasListaA=Compra.objects.all().filter(Estado=Compra.EstadoCompra.Pagado)


  one_week_ago = timezone.now() - timezone.timedelta(days=7)
  print(one_week_ago)

  ComprasLista1=ComprasListaA.values('idComprador__Cedula').annotate(head_count=Count('idComprador__Cedula'), totalNumeros=Sum('NumeroBoletos'), last_order=Max('FechaCompra'), orders_last_week=Sum(Case( When(FechaCompra__gte=one_week_ago, then=1),default=0,output_field=IntegerField()))).values('idComprador__Cedula','head_count','totalNumeros', 'orders_last_week')
  print(ComprasLista1.count())

  s1=ComprasLista1.filter(head_count__lte=1, orders_last_week__gte=1)
  print(s1.count())
  s2=ComprasLista1.filter(head_count__gte=2,orders_last_week__gte=1)
  print(s2)



  one_month_ago = timezone.now() - timezone.timedelta(days=30)
  print(one_month_ago)
  ComprasLista2=ComprasListaA.values('idComprador__Cedula').annotate(head_count=Count('idComprador__Cedula'), totalNumeros=Sum('NumeroBoletos'), last_order=Max('FechaCompra'), orders_last_week=Sum(Case( When(FechaCompra__gte=one_month_ago, then=1),default=0,output_field=IntegerField()))).values('idComprador__Cedula','head_count','totalNumeros', 'orders_last_week')
  print(ComprasLista2.count())
  m1=ComprasLista2.filter(head_count__lte=1, orders_last_week__gte=1)
  print(m1.count())
  m2=ComprasLista2.filter(head_count__gte=2, orders_last_week__gte=1)
  print(m2.count())

  

  one_day_ago = timezone.now() - timezone.timedelta(days=1)
  print(one_day_ago)
  ComprasLista3=ComprasListaA.values('idComprador__Cedula').annotate(head_count=Count('idComprador__Cedula'), totalNumeros=Sum('NumeroBoletos'), last_order=Max('FechaCompra'), orders_last_week=Sum(Case( When(FechaCompra__gte=one_day_ago, then=1),default=0,output_field=IntegerField()))).values('idComprador__Cedula','head_count','totalNumeros', 'orders_last_week')
  print(ComprasLista3.count())
  d1=ComprasLista3.filter(head_count__lte=1, orders_last_week__gte=1)
  print(d1.count())
  d2=ComprasLista3.filter(head_count__gte=2, orders_last_week__gte=1)
  print(d2.count())


  UsuarioStats.objects.create(date=country_time, sNuevo=s1.count(), sRecurrente=s2.count(), dNuevo=d1.count(), dRecurrente=d2.count(), mNuevo=m1.count(), mRecurrente=m2.count())
  


def avisos():
    Rifas=RifaModel.objects.filter(Estado=True).filter(Eliminada=False)
    Rifa=Rifas.last()

    # raw query
    # SELECT  COUNT("Numero"), "Numero" FROM public."Rifa_numeroscompra" join "Rifa_compra" on "idCompra_id"="Id"  where "idRifa_id"=100 and "Estado"=3  group by "Numero" having COUNT("Numero")>1;
    compras= Compra.objects.raw(f'SELECT  COUNT("Numero"), "Numero" FROM public."Rifa_numeroscompra" join "Rifa_compra" on "idCompra_id"="Id"  where "idRifa_id"={Rifa.id} and "Estado" in (1,3)  group by "Numero" having COUNT("Numero")>1;')

    # if there is data send email to manuelrrk22@gmail.com

    if compras:
      # send email
      subject = f'Alerta de numeros multiples en la Rifa {Rifa.Nombre}'
      message = f'Alerta de numeros multiples en la Rifa {Rifa.Nombre}'
      with get_connection(
                    host=settings.EMAIL_HOST,
                    port=settings.EMAIL_PORT,
                    username=settings.EMAIL_HOST_USER,
                    password=settings.EMAIL_HOST_PASSWORD,
                    use_tls=settings.EMAIL_USE_TLS
                ) as connection:
                    subject = subject
                    email_from = settings.EMAIL_HOST_USER
                    recipient_list = ['manuelrrk22@gmail.com','jmmartineztuarez@gmail.com' ]
                    message = 'Alerta de numeros multiples en la Rifa {Rifa.Nombre} ID: {Rifa.id}'
                    email = EmailMessage(
                        subject, message, email_from, recipient_list, connection=connection)
                    email.content_subtype = 'html'
                    email.send()
      Logger.objects.create(date=datetime.now(), description=f"Ejecutando Cron {compras} numeros multiples", evento="Aviso")

 
 
 




    return