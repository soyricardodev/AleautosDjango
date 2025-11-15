# Instrucciones para Liberar Conexiones de PostgreSQL

## Problema
Error: `django.db.utils.OperationalError: connection to server at "localhost" (127.0.0.1), port 5432 failed: FATAL: sorry, too many clients already`

## Soluciones Inmediatas

### Opción 1: Usar el comando de Django (RECOMENDADO)

```bash
# Cerrar conexiones inactivas
python manage.py close_db_connections

# Forzar cierre de todas las conexiones (solo en emergencias)
python manage.py close_db_connections --force
```

### Opción 2: Ejecutar SQL directamente en PostgreSQL

1. Conectarse a PostgreSQL:
```bash
psql -U postgres -d proyectoballena
# O si usas Docker:
docker exec -it <nombre_contenedor_postgres> psql -U postgres -d proyectoballena
```

2. Ejecutar el script SQL:
```sql
-- Ver conexiones actuales
SELECT 
    pid,
    usename,
    application_name,
    state,
    now() - state_change AS idle_duration
FROM pg_stat_activity
WHERE datname = current_database()
ORDER BY state_change;

-- Terminar conexiones inactivas de más de 5 minutos
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = current_database()
AND pid <> pg_backend_pid()
AND state = 'idle'
AND state_change < now() - interval '5 minutes';
```

3. Ver el archivo completo: `scripts/liberar_conexiones_postgres.sql`

### Opción 3: Reiniciar Gunicorn (si es posible)

```bash
# Reiniciar el servidor Gunicorn
sudo systemctl restart gunicorn
# O si usas supervisor:
sudo supervisorctl restart gunicorn
```

## Cambios Realizados en el Código

### 1. Configuración de Base de Datos (`settings.py`)
- `CONN_MAX_AGE` reducido de 500 a 60 segundos
- Timeout de conexión configurado a 10 segundos
- Timeout de statements configurado a 30 segundos

### 2. Optimizaciones en el Código
- QuerySets evaluados una sola vez (convertidos a listas)
- Uso de `select_related()` para evitar consultas N+1
- Límites en consultas para evitar cargar demasiados registros
- Eliminada llamada a `marcarComprasExpiradas()` en cada request de polling

## Prevención Futura

### 1. Monitorear Conexiones
```sql
-- Ver conexiones activas
SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();

-- Ver límite máximo
SHOW max_connections;
```

### 2. Aumentar Límite de Conexiones en PostgreSQL (si es necesario)
Editar `postgresql.conf`:
```
max_connections = 200  # Aumentar según necesidad
```

Luego reiniciar PostgreSQL.

### 3. Usar Connection Pooling (Recomendado para producción)
Considerar usar `pgbouncer` o `pgpool` para manejar mejor las conexiones.

## Comandos Útiles

```bash
# Ver conexiones desde Django shell
python manage.py shell
>>> from django.db import connections
>>> for alias in connections:
...     print(f"{alias}: {connections[alias].connection}")
```

```sql
-- Ver todas las conexiones con detalles
SELECT * FROM pg_stat_activity WHERE datname = current_database();

-- Ver conexiones por aplicación
SELECT application_name, count(*) 
FROM pg_stat_activity 
WHERE datname = current_database()
GROUP BY application_name;
```

