from django.urls import path

from .import apis

from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView
urlpatterns = [
  #region vistas    
    path("", views.index, name="index"),
      path('Detalles/<str:name>/', views.DetallesRifa, name="Detalles"),
      path('Preview/<str:name>/', views.PreviewRifa, name="Preview"),
      path('Verificador/<str:name>/', views.VerificadorRifa, name="Verificador"),
     # path('Compra/<str:name>/', views.CompraRifa, name="Compra"),
      path('Rifa/', views.Rifa, name="Rifa"),
      path('Rifa/<int:id>', views.RifaEdit, name="RifaEdit"),
      path('PremiosDelete/<int:id>', views.PremiosDelete, name="PremiosDelete"),
      path('ListaRifas/', views.ListaRifas, name="ListaRifas"),
      path('Dashboard/', views.Dashboard, name="Dashboard"),
      path('Historial/', views.Historial, name="Historial"),
      path('Historial/<int:id>', views.Historial, name="Historial"),
      path('tableDialog/', views.tableDialog, name="tableDialog"),
      path('tableDialog/<int:id>', views.tableDialog, name="tableDialog"),
       path('tableDialogBuscaNumero/', views.tableDialogBuscaNumero, name="tableDialogBuscaNumero"),
      path('tableDialogBuscaNumero/<int:id>', views.tableDialogBuscaNumero, name="tableDialogBuscaNumero"),
       path('tableNumList/', views.tableNumList, name="tableNumList"),
       path('privacy/', views.privacidad, name="privacy"),
       path('terminos/', views.terminos, name="terminos"),


      path('dialogCompra/', views.dialogCompra, name="dialogCompra"),
      path('compradorDialog/', views.compradorDialog, name="compradorDialog"),
      path('dialogSettings/', views.dialogSettings, name="dialogSettings"),
    path('dialogReenvioCorreo/', views.dialogReenvioCorreo,
         name="dialogReenvioCorreo"),

      path('Login/', views.Login, name="Login"),
      path('Logout/', LogoutView.as_view(next_page=settings.LOGOUT_REDIRECT_URL), name='Logout'),
      path('registrate/', views.registro_cliente, name='registro_cliente'),
      path('inicia-sesion/', views.inicio_sesion_cliente, name='inicio_sesion_cliente'),
      path('cerrar-sesion-cliente/', views.cerrar_sesion_cliente, name='cerrar_sesion_cliente'),
      path('PDF/', views.export_pdf, name="PDF"),
      path('tableDialogPDF/', views.tableDialogPDF, name="tableDialogPDF"),
      path('tableDialogPDF/<int:id>', views.tableDialogPDF, name="tableDialogPDF"),
      path('tableDialogExcel/', views.tableDialogExcel, name="tableDialogExcel"),
      path('tableDialogExcel/<int:id>', views.tableDialogExcel, name="tableDialogExcel"),
      path('deleteRifa', views.deleteRifa, name="deleteRifa"),
      path('insertVideoRifa', views.insertVideoRifa, name="insertVideoRifa"),
      path('copyRifa', views.copyRifa, name="copyRifa"),
      path('Comprobante/<str:name>', views.vistaCompra, name="Comprobante"),








    #endregion


    #region apis    
    path("api/changeState", apis.changeState, name="changeState"),
    path("api/changeExtension", apis.changeExtension, name="changeExtension"),
    path("api/aprobarCompra", apis.aprobarCompra, name="aprobarCompra"),
    path("api/ReenviarComprobante", apis.ReenviarComprobante, name="ReenviarComprobante"),
    path("api/rechazarCompra", apis.rechazarCompra, name="rechazarCompra"),
    path("api/recuperaNumeros", apis.sss, name="sss"),
    path("api/reenvioMasivo", views.reenvioMasivo, name="reenvioCorreo"),
    path("api/reenvioMasivoWS", views.reenvioMasivoWS, name="reenvioMasivoWS"),
    path("api/deleteComprobantes", apis.deleteComprobantes, name="deleteComprobantes"),

    path("api/registerlog", apis.registerlog, name="registerlog"),

    path("api/testWhatsapp", apis.testWhatsapp, name="testWhatsapp"),
    path("api/settings", apis.SaveSettings, name="settings"),
    path("api/comprador", apis.SaveComprador, name="comprador"),
    path("api/verificadorBoletos", apis.VerificaBoletos, name="VerificaBoletos"),



    #Retorno de Numeros
    path("api/RifaNumbersV1", apis.RifabyArray, name="RifaNumbersV1"),
    path("api/RifaNumbersV2", apis.RifabyDisponibles, name="RifaNumbersV2"),
    path("api/RifaNumbersV3", apis.RifabyComprados, name="RifaNumbersV3"),
    path("api/RifaNumbersV4", apis.RifabyCompradosArray, name="RifaNumbersV4"),
    #Compras
    path("api/CompraV1", apis.CompraRifabyArrayDisponibles, name="CompraV1"),
    path("api/CompraV2", apis.CompraRifabyDisponibles, name="CompraV2"),
    path("api/CompraV3", apis.CompraRifabyComprados, name="CompraV3"),
    path("api/CompraV4", apis.CompraRifabyCompradosArray, name="CompraV4"),

    #path("api/CompraNumerosV2", apis.CompraNumerosByDisponibles, name="CompraNumerosV2"),
    path("api/CompraNumerosV2", apis.CompraNumerosByDisponiblesV2, name="CompraNumerosV2"),






    #Consulta de Numeros
    path("api/ConsultaV2", apis.ConsultaRifabyDisponiples, name="ConsultaV2"),
    path("api/ConsultaListaV2", apis.ConsultaRifabyDisponiplesLista, name="ConsultaListaV2"),
    path("api/ConsultaListaV3", apis.ConsultaRifabyDisponiplesListaV3, name="ConsultaListaV3"),
    path("api/ConsultaTodosV2", apis.ConsultaRifabyDisponiplesTodos, name="ConsultaTodosV2"),
    path("api/ConsultaNumero", apis.ConsultaRifabyDisponiple, name="ConsultaNumero"),


    path("api/sendEmail", apis.sendEmail, name="sendEmail"),
    path("api/EmailBody", apis.EmailBody, name="EmailBody"),




    #endregion

  #region ekiipago
  path("api/createOrder", apis.createOrder, name="createOrder"),
  path("api/updateOrder", apis.updateOrder, name="updateOrder"),
  path("api/reserveNumbers", apis.reserveNumbers, name="reserveNumbers"),
  path("api/CheckPay", apis.CheckPay, name="CheckPay"),
  # Pago móvil R4
  path("api/createOrderPagoMovilR4", apis.createOrderPagoMovilR4, name="createOrderPagoMovilR4"),
  path("api/verificarPagoR4", apis.verificarPagoR4, name="verificarPagoR4"),
  




  #endregion

    
  path("api/ComprarRifa", apis.ComprarRifa, name="ComprarRifa"),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)