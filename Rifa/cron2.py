from datetime import datetime, timedelta
import requests
from lxml import html
from bs4 import BeautifulSoup


response = requests.get('https://www.bcv.org.ve/')
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

