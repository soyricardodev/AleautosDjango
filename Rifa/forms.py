from django import forms 
from django.views.generic.edit import FormView
from dynamic_preferences.forms import global_preference_form_builder
from .models import *
from django.forms import ModelForm


class DateInput(forms.DateInput):
    input_type = 'date'


class DateTimeInput(forms.DateTimeInput):
    input_type = 'datetime'


class RifaForm(ModelForm):
    Cantidad=forms.IntegerField(required=True)
    PorcentajeActivacion = forms.IntegerField(required=False, initial=0)
    DiasFecha = forms.IntegerField(required=False, initial=0)
    FechaSorteo = forms.DateTimeField(required=False)
    class Meta:
        model = Rifa
        fields = ["Nombre", "FechaSorteo","Resumen", "MinCompra","MaxCompra","Precio", "Banner", "PorcentajeActivacion", "ModoPorcentaje", "DiasFecha", "PrecioAlt"]
        labels={
            "FechaSorteo": "Fecha del sorteo",
            "Resumen": "Descripcion breve",
            "MinCompra": "Mínimo de compra",
            "MaxCompra": "Máximo de compra",
            "Banner": "Portada de la rifa",
            "Precio": "Precio de boleto",
            "PorcentajeActivacion": "Porcentaje de activación",
            "ModoPorcentaje": "Modo de porcentaje",
            "DiasFecha": "Días de porcentaje",
            "PrecioAlt": "Precio en Zelle",
        }
        widgets = {
            'FechaSorteo': DateTimeInput(),
            'NombreEnlace': forms.TextInput(),
            'ModoPorcentaje': forms.CheckboxInput(),
        }



class UploadFileForm(forms.Form):
    nombre = forms.CharField(required=True)
    file = forms.FileField(required=True)
    correo=forms.EmailField(required=True)
    cedula=forms.CharField(required=True)
    # direccion=forms.CharField(required=True)
    numeroTlf=forms.CharField(required=True)
    referencia=forms.CharField(required=True)
    fechaPago=forms.DateTimeField(required=True)
    idRifa=forms.IntegerField(required=True)
    numeros=forms.IntegerField(required=True)



class ReserveForm(forms.Form):
    idRifa=forms.IntegerField(required=True)
    numeros=forms.IntegerField(required=True)
    boletos = forms.CharField(required=False)

class UpdateOrderForm(forms.Form):
    nombre = forms.CharField(required=True)
    correo=forms.EmailField(required=True)
    cedula=forms.CharField(required=True)
    numeroTlf=forms.CharField(required=True)
    idRifa=forms.IntegerField(required=True)
    idOrden=forms.IntegerField(required=True)

class FirstFileForm(forms.Form):
    nombre = forms.CharField(required=True)
    correo=forms.EmailField(required=True)
    cedula=forms.CharField(required=True)
    # direccion=forms.CharField(required=True)
    numeroTlf=forms.CharField(required=True)
    idRifa=forms.IntegerField(required=True)
    numeros=forms.IntegerField(required=True)


class SecondFileForm(forms.Form):
    file = forms.FileField(required=True)
    referencia=forms.CharField(required=True)
    idOrden=forms.IntegerField(required=True)
    Cantidad=forms.IntegerField(required=True)
    tipoPago=forms.IntegerField(required=True)

class VerificaForm(forms.Form):
    correo=forms.EmailField(required=True)

class CompradorForm(forms.Form):
    id = forms.IntegerField(required=True)
    nombre = forms.CharField(required=True)
    correo=forms.EmailField(required=True)
    cedula=forms.CharField(required=True)
    telefono=forms.CharField(required=True)