# Solución para "too many clients already" con PostgreSQL en Docker

## Problema

```
django.db.utils.OperationalError: connection to server at "127.0.0.1", port 5432 failed: FATAL: sorry, too many clients already
```

PostgreSQL tiene un límite predeterminado de **100 conexiones simultáneas**. Cuando Django/Gunicorn abre más conexiones de las permitidas, aparece este error.

## Solución 1: Aumentar max_connections en Docker (PERMANENTE)

### Opción A: Modificar docker-compose.yaml (RECOMENDADO)

Ya está actualizado en `docker-compose.yaml`:

```yaml
db:
  command: postgres -c max_connections=200 -c shared_buffers=256MB
```

**Aplicar cambios:**
```bash
docker-compose down
docker-compose up -d db
```

### Opción B: Configurar desde dentro del contenedor

```bash
# 1. Entrar al contenedor
docker exec -it <nombre_contenedor_postgres> bash

# 2. Editar postgresql.conf
echo "max_connections = 200" >> /var/lib/postgresql/data/postgresql.conf

# 3. Reiniciar contenedor
docker restart <nombre_contenedor_postgres>
```

## Solución 2: Liberar conexiones inactivas (INMEDIATA)

```bash
# Usar el script automático
bash scripts/liberar_conexiones_postgres_docker.sh

# O manualmente:
docker exec <nombre_contenedor> psql -U postgres -d proyectoballena -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = current_database()
AND pid <> pg_backend_pid()
AND state = 'idle'
AND state_change < now() - interval '2 minutes';
"
```

## Solución 3: Reducir CONN_MAX_AGE en Django

Si sigues teniendo problemas, reduce el tiempo de vida de las conexiones:

En `proyectoBallena/settings.py` o `.env`:
```python
"CONN_MAX_AGE": 30  # Reducir de 60 a 30 segundos
```

O en `.env`:
```bash
DB_CONN_MAX_AGE=30
```

## Verificar conexiones actuales

```bash
# Ver todas las conexiones
docker exec <nombre_contenedor> psql -U postgres -d proyectoballena -c "
SELECT 
    pid,
    usename,
    application_name,
    state,
    now() - state_change AS idle_duration
FROM pg_stat_activity
WHERE datname = current_database()
ORDER BY state_change;
"

# Contar conexiones por estado
docker exec <nombre_contenedor> psql -U postgres -d proyectoballena -c "
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE state = 'active') as active,
    COUNT(*) FILTER (WHERE state = 'idle') as idle,
    COUNT(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
FROM pg_stat_activity
WHERE datname = current_database();
"
```

## Nota sobre el diagnóstico

Si el diagnóstico muestra "0 conexiones" pero el error persiste, puede ser porque:
1. Las conexiones se están abriendo y cerrando muy rápido
2. El diagnóstico se ejecuta en un momento diferente
3. Hay conexiones "zombie" que no aparecen en `pg_stat_activity`

**Solución**: Aumentar `max_connections` en PostgreSQL es la solución más efectiva.

