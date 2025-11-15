"""
Middleware para cerrar conexiones de base de datos inactivas después de cada request.
Esto previene la acumulación de conexiones que causa "too many clients already"
"""
from django.db import connections
from django.db.utils import OperationalError
import logging

logger = logging.getLogger('ballena')


class CloseDBConnectionsMiddleware:
    """
    Middleware que cierra conexiones de base de datos inactivas después de cada request.
    Solo cierra conexiones que están realmente inactivas para evitar problemas de reconexión.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Procesar el request
        response = self.get_response(request)
        
        # Cerrar conexiones inactivas después de la respuesta
        # IMPORTANTE: Solo cerrar si CONN_MAX_AGE está en 0, de lo contrario Django las gestiona
        try:
            from django.conf import settings
            conn_max_age = settings.DATABASES.get('default', {}).get('CONN_MAX_AGE', None)
            
            # Solo cerrar conexiones si CONN_MAX_AGE es 0
            if conn_max_age == 0:
                for alias in connections:
                    try:
                        connection = connections[alias]
                        # Solo cerrar si la conexión existe y no está en uso
                        if connection.connection is not None:
                            # Verificar si la conexión está realmente inactiva
                            try:
                                # Intentar una consulta simple para ver si está activa
                                with connection.cursor() as cursor:
                                    cursor.execute("SELECT 1")
                                # Si llegamos aquí, la conexión está activa, no la cerramos
                                # Django la gestionará automáticamente
                            except (OperationalError, AttributeError):
                                # La conexión está muerta o inactiva, cerrarla
                                connection.close()
                    except Exception as e:
                        # No queremos que un error al cerrar una conexión afecte otras
                        logger.debug(f"Error al verificar/cerrar conexión {alias}: {str(e)}")
        except Exception as e:
            # No queremos que un error al cerrar conexiones afecte la respuesta
            logger.warning(f"Error en middleware de cierre de conexiones: {str(e)}")
        
        return response

