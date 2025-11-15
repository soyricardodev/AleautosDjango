# Configuración Avanzada de PostgreSQL en Docker

## Aumentar max_connections

Sí, puedes aumentar `max_connections` más allá de 200, pero hay consideraciones importantes.

## Fórmula para Calcular Recursos

### Memoria Requerida

Cada conexión consume memoria. La fórmula aproximada es:

```
Memoria Total = shared_buffers + (max_connections × work_mem) + otros
```

**Valores típicos:**
- `shared_buffers`: 25% de RAM total (máximo recomendado)
- `work_mem`: 4-16 MB por conexión activa
- `maintenance_work_mem`: 64-256 MB
- `effective_cache_size`: 50-75% de RAM total

### Ejemplo de Cálculo

Para un VPS con **2GB de RAM**:

```
shared_buffers = 512MB (25% de 2GB)
work_mem = 4MB por conexión
max_connections = 200

Memoria base = 512MB (shared_buffers)
Memoria conexiones = 200 × 4MB = 800MB (si todas están activas)
Total aproximado = ~1.3GB
```

**Conclusión**: Con 2GB de RAM, 200-300 conexiones es razonable.

## Configuraciones Recomendadas por Tamaño de RAM

### VPS con 1GB RAM
```yaml
command: postgres -c max_connections=100 -c shared_buffers=256MB -c work_mem=4MB
```

### VPS con 2GB RAM
```yaml
command: postgres -c max_connections=200 -c shared_buffers=512MB -c work_mem=4MB
```

### VPS con 4GB RAM
```yaml
command: postgres -c max_connections=300 -c shared_buffers=1GB -c work_mem=8MB
```

### VPS con 8GB RAM
```yaml
command: postgres -c max_connections=500 -c shared_buffers=2GB -c work_mem=8MB
```

### VPS con 16GB+ RAM
```yaml
command: postgres -c max_connections=1000 -c shared_buffers=4GB -c work_mem=16MB
```

## Configuración Completa Recomendada

Para un VPS típico de 2-4GB, esta configuración es óptima:

```yaml
db:
  image: postgres:16.4-alpine3.19
  restart: always
  environment:
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: TazaAzul123+++
    POSTGRES_DB: proyectoballena
  ports:
    - "5432:5432"
  volumes:
    - ./docker/init_db:/docker-entrypoint-initdb.d
    - proyectoballena_data:/var/lib/postgresql/data
  command: >
    postgres
    -c max_connections=300
    -c shared_buffers=512MB
    -c work_mem=4MB
    -c maintenance_work_mem=128MB
    -c effective_cache_size=1GB
    -c checkpoint_completion_target=0.9
    -c wal_buffers=16MB
    -c default_statistics_target=100
    -c random_page_cost=1.1
    -c effective_io_concurrency=200
    -c max_worker_processes=4
    -c max_parallel_workers_per_gather=2
    -c max_parallel_workers=4
```

## Límites Prácticos

### Límite Absoluto de PostgreSQL
- **Máximo teórico**: 2,147,483,647 conexiones
- **Límite práctico**: Depende de RAM y CPU
- **Recomendado**: 100-500 para la mayoría de aplicaciones

### Consideraciones

1. **No todas las conexiones están activas simultáneamente**
   - Django con `CONN_MAX_AGE=60` recicla conexiones
   - Solo necesitas suficientes para picos de tráfico

2. **Connection Pooling**
   - Considera usar PgBouncer para reducir conexiones reales
   - Django puede usar 50 conexiones, pero PgBouncer las comparte con PostgreSQL

3. **Monitoreo**
   - Monitorea conexiones activas vs. máximas
   - Si nunca alcanzas el límite, no necesitas más

## Verificar Uso Actual

```bash
# Ver conexiones actuales
docker exec <nombre_contenedor> psql -U postgres -d proyectoballena -c "
SELECT 
    COUNT(*) as total_connections,
    COUNT(*) FILTER (WHERE state = 'active') as active,
    COUNT(*) FILTER (WHERE state = 'idle') as idle,
    (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_allowed
FROM pg_stat_activity
WHERE datname = current_database();
"

# Ver memoria usada
docker exec <nombre_contenedor> psql -U postgres -c "
SELECT 
    name,
    setting,
    unit,
    source
FROM pg_settings
WHERE name IN ('max_connections', 'shared_buffers', 'work_mem', 'effective_cache_size')
ORDER BY name;
"
```

## Aumentar max_connections en docker-compose.yaml

### Paso 1: Editar docker-compose.yaml

```yaml
db:
  command: postgres -c max_connections=300 -c shared_buffers=512MB
```

### Paso 2: Aplicar cambios

```bash
docker-compose down
docker-compose up -d db
```

### Paso 3: Verificar

```bash
docker exec <nombre_contenedor> psql -U postgres -c "SHOW max_connections;"
```

## Usar PgBouncer (Recomendado para Alto Tráfico)

Si necesitas más de 500 conexiones, considera usar PgBouncer como intermediario:

```yaml
pgbouncer:
  image: pgbouncer/pgbouncer:latest
  environment:
    DATABASES_HOST: db
    DATABASES_PORT: 5432
    DATABASES_USER: postgres
    DATABASES_PASSWORD: TazaAzul123+++
    DATABASES_DBNAME: proyectoballena
    PGBOUNCER_POOL_MODE: transaction
    PGBOUNCER_MAX_CLIENT_CONN: 1000
    PGBOUNCER_DEFAULT_POOL_SIZE: 25
  ports:
    - "6432:6432"
```

Luego Django se conecta a PgBouncer (puerto 6432) en lugar de PostgreSQL directamente.

## Recomendación Final

Para tu caso actual:
- **200-300 conexiones** debería ser suficiente
- Si sigues teniendo problemas, el problema probablemente es:
  1. Conexiones no cerradas (ya corregido en el código)
  2. `CONN_MAX_AGE` muy alto
  3. Muchos workers de Gunicorn

**Aumentar a 300-500** es razonable si tienes 2GB+ de RAM.

