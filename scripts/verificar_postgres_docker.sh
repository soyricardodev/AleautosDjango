#!/bin/bash
# Script para verificar el estado de PostgreSQL en Docker
# Uso: bash scripts/verificar_postgres_docker.sh

echo "=========================================="
echo "  VERIFICAR POSTGRESQL EN DOCKER"
echo "=========================================="
echo ""

# Buscar el contenedor de PostgreSQL
CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep -i postgres | head -1)

if [ -z "$CONTAINER_NAME" ]; then
    echo "❌ No se encontró contenedor de PostgreSQL activo"
    echo ""
    echo "Contenedores Docker:"
    docker ps -a --format "{{.Names}}\t{{.Status}}"
    echo ""
    echo "⚠️ PostgreSQL puede estar caído. Intentar iniciar:"
    echo "   docker-compose up -d db"
    exit 1
fi

echo "✓ Contenedor encontrado: $CONTAINER_NAME"
echo ""

# Verificar estado del contenedor
echo "=== Estado del contenedor ==="
docker ps --filter "name=$CONTAINER_NAME" --format "{{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Verificar si PostgreSQL está respondiendo
echo "=== Verificando conexión a PostgreSQL ==="
if docker exec $CONTAINER_NAME pg_isready -U postgres > /dev/null 2>&1; then
    echo "✓ PostgreSQL está respondiendo"
else
    echo "❌ PostgreSQL NO está respondiendo"
    echo ""
    echo "Verificando logs del contenedor:"
    docker logs --tail 20 $CONTAINER_NAME
    exit 1
fi
echo ""

# Verificar conexiones actuales
echo "=== Conexiones actuales ==="
docker exec $CONTAINER_NAME psql -U postgres -d proyectoballena -c "
SELECT 
    COUNT(*) as total_connections,
    COUNT(*) FILTER (WHERE state = 'active') as active,
    COUNT(*) FILTER (WHERE state = 'idle') as idle,
    COUNT(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction,
    (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_allowed
FROM pg_stat_activity
WHERE datname = current_database();
" 2>/dev/null || echo "Error al obtener conexiones"

echo ""

# Verificar configuración
echo "=== Configuración de PostgreSQL ==="
docker exec $CONTAINER_NAME psql -U postgres -c "
SELECT 
    name,
    setting,
    unit,
    source
FROM pg_settings
WHERE name IN ('max_connections', 'shared_buffers', 'work_mem', 'connect_timeout')
ORDER BY name;
" 2>/dev/null || echo "Error al obtener configuración"

echo ""

# Verificar recursos del contenedor
echo "=== Recursos del contenedor ==="
docker stats $CONTAINER_NAME --no-stream --format "CPU: {{.CPUPerc}}\tMemoria: {{.MemUsage}}"

echo ""
echo "=========================================="

