#!/bin/bash
# Script para liberar conexiones de PostgreSQL en Docker
# Uso: bash scripts/liberar_conexiones_postgres_docker.sh

echo "=========================================="
echo "  LIBERAR CONEXIONES POSTGRESQL (DOCKER)"
echo "=========================================="
echo ""

# Buscar el contenedor de PostgreSQL
CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep -i postgres | head -1)

if [ -z "$CONTAINER_NAME" ]; then
    echo "❌ No se encontró contenedor de PostgreSQL"
    echo "Contenedores Docker activos:"
    docker ps --format "{{.Names}}"
    exit 1
fi

echo "✓ Contenedor encontrado: $CONTAINER_NAME"
echo ""

# Ver conexiones actuales
echo "=== Conexiones actuales ==="
docker exec $CONTAINER_NAME psql -U postgres -d proyectoballena -c "
SELECT 
    pid,
    usename,
    application_name,
    state,
    now() - state_change AS idle_duration,
    query
FROM pg_stat_activity
WHERE datname = current_database()
ORDER BY state_change;
" 2>/dev/null || echo "Error al obtener conexiones"

echo ""
echo "=== Terminando conexiones inactivas (>2 minutos) ==="
docker exec $CONTAINER_NAME psql -U postgres -d proyectoballena -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = current_database()
AND pid <> pg_backend_pid()
AND state = 'idle'
AND state_change < now() - interval '2 minutes';
" 2>/dev/null

echo ""
echo "=== Conexiones después de limpiar ==="
docker exec $CONTAINER_NAME psql -U postgres -d proyectoballena -c "
SELECT 
    COUNT(*) as total_connections,
    COUNT(*) FILTER (WHERE state = 'active') as active,
    COUNT(*) FILTER (WHERE state = 'idle') as idle,
    COUNT(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
FROM pg_stat_activity
WHERE datname = current_database();
" 2>/dev/null

echo ""
echo "✓ Proceso completado"

