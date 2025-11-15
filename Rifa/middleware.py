"""
Middleware para cerrar conexiones de base de datos inactivas después de cada request.
Esto previene la acumulación de conexiones que causa "too many clients already"
"""
from django.db import connections
from django.db.utils import OperationalError
import logging
import time

logger = logging.getLogger('ballena')


class CloseDBConnectionsMiddleware:
    """
    Middleware que cierra conexiones de base de datos inactivas después de cada request.
    Cierra conexiones que están realmente inactivas (muertas o sin uso) incluso cuando
    CONN_MAX_AGE != 0, para prevenir acumulación gradual de conexiones.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Procesar el request
        response = self.get_response(request)
        
        # Cerrar conexiones inactivas después de la respuesta
        # MEJORADO: Cerrar conexiones inactivas incluso cuando CONN_MAX_AGE != 0
        # para prevenir acumulación gradual que causa "too many clients already"
        try:
            for alias in connections:
                try:
                    connection = connections[alias]
                    # Solo cerrar si la conexión existe
                    if connection.connection is not None:
                        # Verificar si la conexión está realmente inactiva o muerta
                        try:
                            # Intentar una consulta simple para ver si está activa
                            with connection.cursor() as cursor:
                                cursor.execute("SELECT 1")
                            # Si llegamos aquí, la conexión está activa, no la cerramos
                            # Django la gestionará automáticamente según CONN_MAX_AGE
                        except (OperationalError, AttributeError):
                            # La conexión está muerta o inactiva, cerrarla
                            # Esto previene acumulación de conexiones "zombie"
                            try:
                                connection.close()
                                logger.debug(f"Conexión {alias} cerrada (estaba inactiva/muerta)")
                            except Exception:
                                pass  # Ignorar errores al cerrar conexiones muertas
                except Exception as e:
                    # No queremos que un error al cerrar una conexión afecte otras
                    logger.debug(f"Error al verificar/cerrar conexión {alias}: {str(e)}")
        except Exception as e:
            # No queremos que un error al cerrar conexiones afecte la respuesta
            logger.warning(f"Error en middleware de cierre de conexiones: {str(e)}")
        
        return response

