"""
Middleware para cerrar conexiones de base de datos después de cada request.
Esto previene la acumulación de conexiones que causa "too many clients already"
"""
from django.db import connections
import logging

logger = logging.getLogger('ballena')


class CloseDBConnectionsMiddleware:
    """
    Middleware que cierra todas las conexiones de base de datos después de cada request.
    Esto es necesario cuando CONN_MAX_AGE está en 0 pero las conexiones no se cierran automáticamente.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Procesar el request
        response = self.get_response(request)
        
        # Cerrar todas las conexiones después de la respuesta
        try:
            for alias in connections:
                connection = connections[alias]
                if connection.connection is not None:
                    connection.close()
        except Exception as e:
            # No queremos que un error al cerrar conexiones afecte la respuesta
            logger.warning(f"Error al cerrar conexiones en middleware: {str(e)}")
        
        return response

