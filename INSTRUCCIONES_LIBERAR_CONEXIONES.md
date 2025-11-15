# Instrucciones para Liberar Conexiones de PostgreSQL

## Problemas Relacionados

### Error 1: "too many clients already"
`django.db.utils.OperationalError: connection to server at "localhost" (127.0.0.1), port 5432 failed: FATAL: sorry, too many clients already`

### Error 2: "could not translate host name localhost"
`django.db.utils.OperationalError: could not translate host name "localhost" to address: System error`

**Solución para Error 2**: Si ves este error después de aplicar los cambios, el middleware puede estar siendo demasiado agresivo. Considera:
1. Cambiar `CONN_MAX_AGE` de `0` a `60` en `settings.py`
2. O verificar que `DB_HOST` esté configurado correctamente (usar `127.0.0.1` en lugar de `localhost` si es necesario)

### Error 3: "Too many open files" ⚠️ CRÍTICO
`OSError: [Errno 24] Too many open files` o `could not create socket: Too many open files`

**Este es el error más grave** - el sistema ha alcanzado el límite de archivos abiertos.

**Solución inmediata**:
```bash
# 1. Aumentar límite temporalmente
ulimit -n 65536

# 2. Verificar archivos abiertos
bash scripts/verificar_archivos_abiertos.sh

# 3. Aumentar permanentemente
sudo bash scripts/aumentar_ulimit.sh

# 4. Si usas systemd
sudo bash scripts/fix_ulimit_systemd.sh

# 5. Reiniciar Gunicorn
sudo systemctl restart gunicorn
```

Ver `SOLUCION_TOO_MANY_OPEN_FILES.md` para detalles completos.

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
- `CONN_MAX_AGE` configurado en **0** (cerrar después de cada request)
- Timeout de conexión configurado a 10 segundos
- **NUEVO**: Middleware `CloseDBConnectionsMiddleware` agregado para forzar cierre de conexiones

### 2. Middleware de Cierre de Conexiones (`Rifa/middleware.py`)
- **NUEVO**: Middleware que cierra todas las conexiones después de cada request
- Previene acumulación de conexiones incluso si CONN_MAX_AGE falla

### 3. Optimizaciones en el Código
- QuerySets evaluados una sola vez (convertidos a listas)
- Uso de `select_related()` para evitar consultas N+1
- Límites en consultas para evitar cargar demasiados registros
- Eliminada llamada a `marcarComprasExpiradas()` en cada request de polling
- **NUEVO**: Manejo de errores que cierra conexiones en caso de excepción
- **NUEVO**: Optimización de la vista `index` para reducir consultas

### 4. Reducción de Workers de Gunicorn (`docker/supervisord.conf`)
- **NUEVO**: Workers reducidos de 3 a 2 para reducir archivos abiertos
- **NUEVO**: Agregado `--max-requests` para reciclar workers periódicamente
- **NUEVO**: Configuración de `ULIMIT_NOFILE` en supervisord

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

