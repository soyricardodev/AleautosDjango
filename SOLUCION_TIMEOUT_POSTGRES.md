# Solución para "timeout expired" en PostgreSQL

## Problema

```
django.db.utils.OperationalError: connection to server at "127.0.0.1", port 5432 failed: timeout expired
```

Este error indica que PostgreSQL **no está respondiendo** dentro del tiempo límite (10 segundos por defecto).

## Causas Posibles

1. **PostgreSQL está caído o no inició correctamente**
2. **PostgreSQL está sobrecargado** (demasiadas conexiones o consultas lentas)
3. **Timeout de conexión muy corto** (10 segundos puede ser insuficiente)
4. **Problemas de red** entre Gunicorn y el contenedor Docker

## Solución 1: Verificar Estado de PostgreSQL (INMEDIATO)

```bash
# Verificar estado del contenedor
bash scripts/verificar_postgres_docker.sh

# O manualmente:
docker ps | grep postgres
docker logs <nombre_contenedor_postgres> --tail 50
```

Si el contenedor está caído:
```bash
docker-compose up -d db
```

## Solución 2: Aumentar Timeout de Conexión

El timeout actual es de 10 segundos. Aumentarlo a 30 segundos:

En `proyectoBallena/settings.py`:
```python
"OPTIONS": {
    "connect_timeout": 30,  # Aumentar de 10 a 30 segundos
    "keepalives": 1,
    "keepalives_idle": 30,
    "keepalives_interval": 10,
    "keepalives_count": 5,
},
```

## Solución 3: Reiniciar PostgreSQL

```bash
# Reiniciar solo el contenedor de PostgreSQL
docker-compose restart db

# O reiniciar todo
docker-compose down
docker-compose up -d db
```

## Solución 4: Liberar Conexiones Bloqueadas

Si PostgreSQL está sobrecargado:

```bash
# Liberar conexiones inactivas
bash scripts/liberar_conexiones_postgres_docker.sh

# O forzar cierre de todas las conexiones (solo en emergencias)
docker exec <nombre_contenedor> psql -U postgres -d proyectoballena -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = current_database()
AND pid <> pg_backend_pid();
"
```

## Solución 5: Verificar Recursos del Sistema

```bash
# Ver uso de CPU y memoria
docker stats

# Ver procesos de PostgreSQL
docker exec <nombre_contenedor> ps aux | grep postgres

# Ver logs de PostgreSQL
docker logs <nombre_contenedor> --tail 100
```

## Solución 6: Reducir CONN_MAX_AGE Temporalmente

Si el problema persiste, reducir el tiempo de vida de las conexiones:

En `proyectoBallena/settings.py` o `.env`:
```python
"CONN_MAX_AGE": 30  # Reducir de 60 a 30 segundos
```

## Diagnóstico Completo

```bash
# 1. Verificar estado
bash scripts/verificar_postgres_docker.sh

# 2. Ver logs
docker logs <nombre_contenedor_postgres> --tail 100

# 3. Verificar conexiones
docker exec <nombre_contenedor> psql -U postgres -d proyectoballena -c "
SELECT 
    pid,
    usename,
    state,
    wait_event_type,
    wait_event,
    query_start,
    state_change,
    now() - state_change AS idle_duration,
    LEFT(query, 50) as query_preview
FROM pg_stat_activity
WHERE datname = current_database()
ORDER BY state_change;
"

# 4. Verificar bloqueos
docker exec <nombre_contenedor> psql -U postgres -d proyectoballena -c "
SELECT 
    blocked_locks.pid AS blocked_pid,
    blocking_locks.pid AS blocking_pid,
    blocked_activity.usename AS blocked_user,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_statement,
    blocking_activity.query AS blocking_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted
AND blocking_locks.granted;
"
```

## Acción Inmediata Recomendada

```bash
# 1. Verificar estado
bash scripts/verificar_postgres_docker.sh

# 2. Si está caído, iniciar
docker-compose up -d db

# 3. Esperar 10 segundos
sleep 10

# 4. Verificar nuevamente
bash scripts/verificar_postgres_docker.sh

# 5. Si sigue fallando, reiniciar
docker-compose restart db
```

## Prevención

1. **Aumentar timeout** a 30 segundos (ya configurado en settings.py)
2. **Monitorear conexiones** regularmente
3. **Configurar max_connections** apropiadamente (ya configurado en docker-compose.yaml)
4. **Usar connection pooling** si es necesario (PgBouncer)

