from datetime import datetime, timedelta
import requests
from lxml import html
from bs4 import BeautifulSoup

# CRÍTICO: Usar sesión con context manager para cerrar conexión HTTP correctamente
with requests.Session() as session:
    try:
        response = session.get('https://www.bcv.org.ve/', timeout=30)
        response.raise_for_status()  # Lanzar excepción si hay error HTTP
        soup = BeautifulSoup(response.text, 'html.parser')
        dolar=soup.find(id="dolar").text
        #spli lines and remove white empty lines
        dolar=dolar.splitlines()
        dolar=list(filter(None, dolar))
        dolar=dolar[1]
        print(dolar)

        #tasa to float
        dolar=float(dolar.replace(",","."))
        print(dolar)
    except Exception as e:
        print(f"Error al obtener tasa BCV: {str(e)}")
        raise

