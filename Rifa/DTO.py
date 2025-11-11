from pydantic import BaseModel
from typing import Optional


class AuthReqDTO(BaseModel):
    username: str
    platformId: int
    password: str

class AuthResDTO(BaseModel):
    errorCode:	str
    clientMessage:	str
    systemMessage:	str
    codigoHttp:	int
    access_token:	str

class CreateOrderDTO(BaseModel):
        reference: int
        currency: str
        amount: float
        paymentType: str
        customer_name: str
        customer_email: str
        customer_phone: str
        customer_identification: str
        customer_bank: str
        customer_account: str
        description: str
        branchOffice: str
        cashRegister: str
        seller: str
        channel: str


class CreateOrderResDTO(BaseModel):
    errorCode:	str
    clientMessage:	str
    systemMessage:	str
    codigoHttp:	int
    reference:	str
    amount:	int
    date:	str

class AuthReqDTO(BaseModel):
    title: str
    description: str | None = None

class AuthReqDTO(BaseModel):
    title: str
    description: str | None = None