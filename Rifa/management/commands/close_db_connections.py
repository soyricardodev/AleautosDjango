"""
Comando de gestión para cerrar conexiones de base de datos inactivas.
Uso: python manage.py close_db_connections
"""
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError
import logging

logger = logging.getLogger('ballena')


class Command(BaseCommand):
    help = 'Cierra todas las conexiones de base de datos inactivas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Fuerza el cierre de todas las conexiones (incluso activas)',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        self.stdout.write(self.style.WARNING('Cerrando conexiones de base de datos...'))
        
        closed_count = 0
        for alias in connections:
            connection = connections[alias]
            
            try:
                if connection.connection is not None:
                    if force:
                        # Cerrar forzadamente
                        connection.close()
                        closed_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ Conexión {alias} cerrada forzadamente')
                        )
                    else:
                        # Solo cerrar si está inactiva
                        try:
                            # Intentar una consulta simple para ver si está activa
                            with connection.cursor() as cursor:
                                cursor.execute("SELECT 1")
                            # Si llegamos aquí, la conexión está activa, no la cerramos
                            self.stdout.write(
                                self.style.WARNING(f'⚠ Conexión {alias} está activa, no se cerró')
                            )
                        except OperationalError:
                            # La conexión está muerta, cerrarla
                            connection.close()
                            closed_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'✓ Conexión {alias} cerrada (estaba inactiva)')
                            )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Conexión {alias} ya estaba cerrada')
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Error al cerrar conexión {alias}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✓ Total de conexiones cerradas: {closed_count}')
        )
        
        # También ejecutar comando SQL para terminar conexiones en PostgreSQL
        self.stdout.write(self.style.WARNING('\nEjecutando limpieza en PostgreSQL...'))
        try:
            with connections['default'].cursor() as cursor:
                # Terminar conexiones inactivas (idle) de más de 5 minutos
                cursor.execute("""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                    AND pid <> pg_backend_pid()
                    AND state = 'idle'
                    AND state_change < now() - interval '5 minutes'
                """)
                terminated = cursor.rowcount
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {terminated} conexiones inactivas terminadas en PostgreSQL')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error al terminar conexiones en PostgreSQL: {str(e)}')
            )

