#!/bin/bash
# Script para configurar max_connections en PostgreSQL Docker
# Uso: sudo bash scripts/configurar_postgres_docker.sh

echo "=========================================="
echo "  CONFIGURAR POSTGRESQL EN DOCKER"
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

# Ver configuración actual
echo "=== Configuración actual ==="
docker exec $CONTAINER_NAME psql -U postgres -c "SHOW max_connections;" 2>/dev/null
docker exec $CONTAINER_NAME psql -U postgres -c "SHOW shared_buffers;" 2>/dev/null

echo ""
echo "=== Aumentando max_connections a 200 ==="
docker exec $CONTAINER_NAME psql -U postgres -c "ALTER SYSTEM SET max_connections = 200;" 2>/dev/null

echo ""
echo "⚠️ IMPORTANTE: Para aplicar los cambios, necesitas:"
echo "  1. Reiniciar el contenedor de PostgreSQL:"
echo "     docker restart $CONTAINER_NAME"
echo ""
echo "  2. O modificar docker-compose.yaml y agregar:"
echo "     command: postgres -c max_connections=200"
echo ""
echo "  3. Luego reiniciar:"
echo "     docker-compose restart db"
echo ""

read -p "¿Reiniciar el contenedor ahora? (s/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo "Reiniciando contenedor..."
    docker restart $CONTAINER_NAME
    sleep 5
    echo "✓ Contenedor reiniciado"
    echo ""
    echo "Verificando nueva configuración:"
    docker exec $CONTAINER_NAME psql -U postgres -c "SHOW max_connections;" 2>/dev/null
fi

