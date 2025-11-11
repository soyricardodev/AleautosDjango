from datetime import datetime
import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator 
from django.contrib.postgres.fields import ArrayField
from .utils import get_file_path
import pytz
from django.utils import timezone

# Create your models here.
def getDatetime():
    country_time_zone = pytz.timezone('America/Caracas')
    country_time = datetime.now(country_time_zone)
    return country_time

# ekkipagos

class Ordenes(models.Model):
    class currencyType(models.TextChoices):
        Bs = "VES"
        Usd = "USD"
        
    class paymentTypeEnum(models.TextChoices):
        P2C = "P2C"
        C2P = "C2P"
        P2Pc = "P2Pc"
        P2Pp = "P2Pp"
        P2P = "P2P"
        RTIc = "RTIc"
        RTIp = "RTIp"
    class channelType(models.TextChoices):
        MERCHANT = "MERCHANT"
        POS = "POS"
        VPOS = "VPOS"
        PAYMENT_BUTTON = "PAYMENT_BUTTON"
        WALLET = "WALLET"
        WEB  = "WEB "


    

    Id = models.BigAutoField(primary_key=True)
    reference=models.TextField(null=False,)
    currency = models.TextField(null=False, blank=False, default=currencyType.Usd, choices=[(tag, tag.value) for tag in currencyType] )
    amount= models.DecimalField(null=False, blank=False, decimal_places=2, max_digits=20)
    paymentType = models.TextField(null=False, blank=False, default=paymentTypeEnum.P2C, choices=[(tag, tag.value) for tag in paymentTypeEnum] )
    customer_name = models.TextField(null=False, blank=False)
    customer_email = models.TextField(null=True, blank=True)
    customer_phone = models.TextField(null=False, blank=False)
    customer_identification= models.TextField(null=False, blank=False)
    customer_bank= models.TextField(null=True, blank=True)
    customer_account= models.TextField(null=True, blank=True)
    description= models.TextField(null=False, blank=False)
    branchOffice= models.TextField(null=True, blank=True)
    cashRegister= models.TextField(null=True, blank=True)
    seller= models.TextField(null=True, blank=True)
    channel= models.TextField(null=False, blank=False, default=channelType.PAYMENT_BUTTON, choices=[(tag, tag.value) for tag in channelType] )
    def __str__(self):
        return self





class Rifa(models.Model):
    Id = models.SmallAutoField(primary_key=True)
    Nombre = models.TextField(null=False, blank=False)
    NombreEnlace = models.TextField(unique=True, null=True)
    Intervalo = models.IntegerField(null=False,)
    FechaSorteo = models.DateTimeField(null=True,)
    fechaCreacion = models.DateTimeField(null=False, default=timezone.now)
    MinCompra= models.IntegerField(null=False,)
    MaxCompra= models.IntegerField(null=False,)
    RangoInicial = models.IntegerField(null=False, validators=[MinValueValidator(0)])
    RangoFinal = models.IntegerField(null=False )
    Precio = models.FloatField(null=False,default=10, validators=[MinValueValidator(0.1)] )
    PrecioAlt = models.FloatField(null=False,default=1, validators=[MinValueValidator(0.1)] )
    Banner = models.ImageField(null=True, default=None, upload_to=get_file_path)
    Descripcion = models.TextField(null=True) 
    Resumen = models.TextField(null=True) 
    Estado = models.BooleanField(default=False)
    Extension = models.BooleanField(default=True)
    Eliminada = models.BooleanField(default=False)
    TotalNumeros = models.IntegerField(default=0)
    TotalComprados = models.IntegerField(default=0)
    DiasFecha = models.IntegerField(default=0)
    PorcentajeActivacion = models.FloatField(default=0)
    ModoPorcentaje = models.BooleanField(default=False)
    Video = models.TextField(null=True)




 
    def __str__(self):
        return self.Nombre
    
class ImagenesRifa(models.Model):
    DetallesRiFA = models.ForeignKey(Rifa, on_delete=models.CASCADE, default=None, null=True, related_name='ImagenesRifa')
    imagePath = models.URLField()
    imageName = models.TextField()
    imagePosition = models.IntegerField()

    def __str__(self):
        return self.imagePath
    
class Comprador(models.Model):
    Id = models.BigAutoField(primary_key=True)
    Nombre = models.TextField()
    Cedula = models.TextField()
    Correo = models.EmailField(null=True)
    Direccion = models.TextField()
    NumeroTlf = models.TextField()

    def __str__(self):
        return self.Nombre
    
class Tasas(models.Model):
    date = models.DateTimeField(null=True)
    tasa  = models.FloatField(null=True)
    def __str__(self):
        return self.tasa
    
class Compra(models.Model):
    class EstadoCompra(models.TextChoices):
        Pendiente = 1
        Cancelado = 2
        Pagado = 3
        Rechazado=4
        Caducado=5

    class MetodoPagoOpciones (models.TextChoices):
        EkiiPagos = 1
        Binance = 2
        Tranferencia = 3
        Zelle = 4
        Efectivo = 5

        
    Id = models.BigAutoField(primary_key=True)
    Referencia = models.TextField(null=True)
    FechaCompra= models.DateTimeField(null=True)
    FechaEstado= models.DateTimeField(null=True)
    Comprobante=models.FileField(null=True, default=None, upload_to=get_file_path)
    NumeroBoletos= models.IntegerField(null=True)
    TotalPagado= models.FloatField(null=True)
    TotalPagadoAlt= models.FloatField(null=True)
    TasaBS= models.FloatField(null=True)
    MetodoPago= models.IntegerField( choices=[(tag, tag.value) for tag in MetodoPagoOpciones], default=MetodoPagoOpciones.Tranferencia )
    Estado= models.IntegerField( choices=[(tag, tag.value) for tag in EstadoCompra], default=EstadoCompra.Pendiente )
    idComprador = models.ForeignKey(Comprador, on_delete=models.CASCADE, default=None, null=True, related_name='Comprador')
    idOrden = models.ForeignKey(Ordenes, on_delete=models.CASCADE, default=None, null=True, related_name='OrdenCompra')
    idRifa = models.ForeignKey(Rifa, on_delete=models.CASCADE, default=None, null=True, related_name='RifaCompra')
    hash = models.UUIDField( default=uuid.uuid4, unique=True)
    recuperado = models.BooleanField(default=False)
    CorreoEnviado = models.BooleanField(default=False)
    qr=models.FileField(null=True, default=None, upload_to=get_file_path)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
    )


    def __str__(self):
        return self.Referencia
    
class NumerosCompra(models.Model):
    idCompra = models.ForeignKey(Compra, on_delete=models.CASCADE, default=None, null=True, related_name='NumerosCompra')
    Numero = models.TextField()
   
    def __str__(self):
        return self.Numero

class NumerosCompraArray(models.Model):
    idCompra = models.ForeignKey(Compra, on_delete=models.CASCADE, default=None, null=True, related_name='NumerosCompraArray')
    Numeros = ArrayField( models.TextField( blank=True, null=True))

    def __str__(self):
        return self.Numeros
    
class NumeroRifaComprados(models.Model):
    idRifa = models.ForeignKey(Rifa, on_delete=models.CASCADE, default=None, null=True, related_name='NumeroRifaComprados')
    Numero = models.TextField()
   
    def __str__(self):
        return self.Numero
    
class NumeroRifaCompradosArray(models.Model):
    idRifa = models.ForeignKey(Rifa, on_delete=models.CASCADE, default=None, null=True, related_name='NumeroRifaCompradosArray')
    Numeros = ArrayField( models.TextField( blank=True, null=True))
    def __str__(self):
        return self.Numeros
    
class NumeroRifaDisponibles(models.Model):
    idRifa = models.ForeignKey(Rifa, on_delete=models.CASCADE, default=None, null=True, related_name='NumeroRifaDisponibles')
    Numero = models.TextField()
    def __str__(self):
        return self.Numero
    def __json__(self):
        return {
            "numero_rifa": str(self.Numero),
            "rifa": self.idRifa,
        }
    
class NumeroRifaDisponiblesArray(models.Model):
    idRifa = models.ForeignKey(Rifa, on_delete=models.CASCADE, default=None, null=True, related_name='NumeroRifaDisponblesArray')
    Numeros = ArrayField( models.TextField( blank=True, null=True))
    def __str__(self):
        return self.Numeros

class PremiosRifa(models.Model):
    idRifa = models.ForeignKey(Rifa, on_delete=models.CASCADE, default=None, null=True, related_name='PremiosRifa')
    Nombre=models.TextField(null=False)
    Descripcion=models.TextField(null=True, default=None)
    Orden=models.SmallIntegerField(null=False)
    FotoPremio = models.ImageField(null=True, default=None, upload_to=get_file_path)
    FotoGanador = models.ImageField(null=True, default=None, upload_to=get_file_path)

    def __str__(self):
        return self.Nombre


class NumeroRifaReservados(models.Model):
    idRifa = models.ForeignKey(Rifa, on_delete=models.CASCADE, default=None, null=True, related_name='numReserva')
    idOrden= models.ForeignKey(Ordenes, on_delete=models.CASCADE, default=None, null=True, related_name='OrdenNumero')
    Numero = models.TextField()
    date = models.DateTimeField(null=True)
    def __str__(self):
        return self.Numero


class Logger(models.Model):
    date = models.DateTimeField(null=True)
    description  = models.TextField(null=True)
    evento = models.TextField(null=True)

    def __str__(self):
        return self.description
    
class Settings(models.Model):
    code = models.TextField(null=True, unique=True)
    descripcion  = models.TextField(null=True)
    valor = models.TextField(null=True)

    def __str__(self):
        return self.code

class LoggerAprobadoRechazo(models.Model):
    date = models.DateTimeField(null=True)
    description  = models.TextField(null=True)
    evento = models.TextField(null=True)
    idCompra = models.ForeignKey(Compra, on_delete=models.CASCADE, default=None, null=True, related_name='NumerosCompraLogger')


    def __str__(self):
        return self.description

class UsuarioStats(models.Model):
    date = models.DateTimeField(null=True)
    dNuevo = models.IntegerField(null=True, default=0)
    dRecurrente = models.IntegerField(null=True, default=0)
    mNuevo = models.IntegerField(null=True, default=0)
    mRecurrente = models.IntegerField(null=True, default=0)
    sNuevo = models.IntegerField(null=True, default=0)
    sRecurrente = models.IntegerField(null=True, default=0)
    

    def __str__(self):
        return self.date

class ReenviosMasivos(models.Model):
    ultimo = models.IntegerField(null=True, default=0)
    total = models.IntegerField(null=True, default=0)
    estado = models.SmallIntegerField(null=True, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    idRifa = models.ForeignKey(
        Rifa, on_delete=models.CASCADE, default=None, null=True, related_name='RifaReenvio')


    def __str__(self):
        return self.idRifa.Nombre + " " + str(self.created_at)


class OrdenesReservas(models.Model):

    Id = models.BigAutoField(primary_key=True)
    amount= models.DecimalField(null=False, blank=False, decimal_places=2, max_digits=20)
    date = models.DateTimeField(null=True)
    customer_name = models.TextField(null=False, blank=False)
    customer_email = models.TextField(null=True, blank=True)
    customer_phone = models.TextField(null=False, blank=False)
    customer_identification= models.TextField(null=False, blank=False)
    description= models.TextField(null=False, blank=False)
    idRifa = models.ForeignKey(Rifa, on_delete=models.CASCADE, default=None, null=True, related_name='RifaOrden')
    completada = models.BooleanField(default=False)

    def __str__(self):
        return self


class NumeroRifaReservadosOrdenes(models.Model):
    idRifa = models.ForeignKey(Rifa, on_delete=models.CASCADE, default=None, null=True, related_name='RifaReserva')
    idOrden= models.ForeignKey(OrdenesReservas, on_delete=models.CASCADE, default=None, null=True, related_name='OrdenReserva')
    Numero = models.TextField()
    date = models.DateTimeField(null=True)
    def __str__(self):
        return self.Numero
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['idRifa', 'Numero'], name='unique_Compra'),
        ]