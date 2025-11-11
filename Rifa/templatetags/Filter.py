from datetime import datetime, timedelta
from django import template
import pytz
import json
from json import JSONDecodeError

register = template.Library()

@register.filter(name='RifaActiva')
def RifaActiva(fecha):
    country_time_zone = pytz.timezone('America/Caracas')
    country_time = datetime.now(country_time_zone)
    print(fecha)
    print(country_time)

    if country_time < fecha:
        return True
    else:
        return False

@register.filter(name='EstadosRifa')
def EstadosRifa(e):
    print(e)
    if e == '0':
        return "En curso"
    if e=='1':
        return "Finalizada"
    if e=='2':
        return "Todas"

@register.filter(name='TotalNumeros')
def TotalNumeros(t,d):
    return t-d

@register.filter(name='totalPorcentaje')
def totalPorcentaje(total,noDisponibles):
    return round((noDisponibles)*100/total, 2)

@register.filter(name='totalPorcentaje2')
def totalPorcentaje2(total,noDisponibles):
    return round((total-noDisponibles)*100/total, 2)

@register.filter(name='isSoldOut')
def isSoldOut(Rifa):
    return Rifa.TotalNumeros <= Rifa.TotalComprados
    
@register.filter(name='reversoMetodoPago')
def reversoMetodoPago(metodo):
    if metodo == 1:
        return "EkiiPagos"
    if metodo == 2:
        return "Binance"    
    if metodo == 3:
        return "Pago Movil"   
    if metodo == 4:
        return "Zelle"   
    if metodo == 5:
        return "Zinli"   

@register.filter(name='reversoEstado')
def reversoEstado(estado):
    if estado == 1:
        return "Pendiente"
    if estado == 2:
        return "Cancelado"
    if estado == 3:
        return "Pagado"
    if estado == 4:
        return "Rechazado"
    if estado == 5:
        return "Caducado"


@register.filter(name='totalpago')
def totalpago(a, b ):
    return a*b

@register.filter(name='stringify')
def stringify(texto):
    try:
        object = json.loads(texto)
        return json.dumps(object)
    except JSONDecodeError:
        return f"'{texto}'"
    
@register.filter(name='is_html')
def is_html(texto):
    try:
        object = json.loads(texto)
        return False
    except JSONDecodeError:
        return True
    
@register.filter(name='wordcap')
def wordcap(word:str, size:int):
    if len(word) > size:
        return f"{word[0:size]}..."
    else:
        return word

@register.filter(name='add_days')
def add_days(days):
   new_date = datetime.today() + timedelta(days=days)
   return new_date

@register.filter(name='float_str')
def float_str(price:float):
   new_price = str(price).replace(',','.')
   return new_price

@register.filter(name='limit_str')
def limit_str(title:str = '', limit:int = 20):
   limit = title[0:limit] if len(title) > limit else title
   return limit + '...'

@register.filter(name='format_price')
def format_price(price:float|None):
    if price is None:
        return '0.00'
    return f'{price:,.2f}'

@register.filter(name='readable_phone')
def readable_phone(phone:str|None):
    if phone is None:
        return ''
    if len(phone) < 12:
        return ''
    return f'+{phone[0:2]} {phone[2:5]} - {phone[5:8]}.{phone[8:10]}.{phone[10:]}'

@register.filter(name='number_len')
def number_len(number:int|None):
    if number is None:
        return 0
    return len(str(number))

@register.filter(name='description_as_list')
def description_as_list(description:str):
    return description.split('\n')