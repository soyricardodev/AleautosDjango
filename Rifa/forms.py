from django import forms 
from django.views.generic.edit import FormView
from dynamic_preferences.forms import global_preference_form_builder
from .models import *
from django.forms import ModelForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


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
    id = forms.IntegerField(required=False)
    nombre = forms.CharField(required=True)
    correo=forms.EmailField(required=True)
    cedula=forms.CharField(required=True)
    telefono=forms.CharField(required=True)
    password = forms.CharField(required=False, widget=forms.PasswordInput())


class RegistroClienteForm(forms.Form):
    nombre = forms.CharField(
        max_length=150,
        required=True,
        label='Nombre completo',
        widget=forms.TextInput(attrs={
            'class': 'input w-full text-color-primary',
            'placeholder': 'Ingresa tu nombre completo'
        })
    )
    cedula = forms.CharField(
        max_length=20,
        required=True,
        label='Cédula',
        widget=forms.TextInput(attrs={
            'class': 'input w-full text-color-primary',
            'placeholder': 'Ingresa tu cédula'
        })
    )
    correo = forms.EmailField(
        required=True,
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'class': 'input w-full text-color-primary',
            'placeholder': 'correo@ejemplo.com'
        })
    )
    telefono = forms.CharField(
        max_length=15,
        required=True,
        label='Teléfono',
        widget=forms.TextInput(attrs={
            'class': 'input w-full text-color-primary',
            'placeholder': '0412-1234567'
        })
    )
    password = forms.CharField(
        required=True,
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'input w-full text-color-primary',
            'placeholder': 'Mínimo 8 caracteres'
        })
    )

    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula')
        if Cliente.objects.filter(cedula=cedula).exists():
            raise forms.ValidationError('Esta cédula ya está registrada.')
        return cedula

    def clean_correo(self):
        correo = self.cleaned_data.get('correo')
        if User.objects.filter(email=correo).exists():
            raise forms.ValidationError('Este correo electrónico ya está registrado.')
        return correo

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password and len(password) < 8:
            raise forms.ValidationError('La contraseña debe tener al menos 8 caracteres.')
        return password


class LoginClienteForm(forms.Form):
    usuario = forms.CharField(
        required=True,
        label='Cédula o Correo',
        widget=forms.TextInput(attrs={
            'class': 'input w-full text-color-primary',
            'placeholder': 'Cédula o correo electrónico'
        })
    )
    password = forms.CharField(
        required=True,
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'input w-full text-color-primary',
            'placeholder': 'Tu contraseña'
        })
    )