#!/bin/bash
# Script para liberar conexiones de PostgreSQL
# Uso: ./scripts/liberar_conexiones.sh

echo "=== Liberando conexiones de PostgreSQL ==="
echo ""

# Opción 1: Usar el comando de Django
echo "1. Cerrando conexiones desde Django..."
python manage.py close_db_connections --force

echo ""
echo "2. Ejecutando limpieza directa en PostgreSQL..."
echo "   (Necesitas tener acceso a psql)"

# Opción 2: Ejecutar SQL directamente (ajusta las credenciales)
# psql -U postgres -d proyectoballena -c "
# SELECT pg_terminate_backend(pid)
# FROM pg_stat_activity
# WHERE datname = current_database()
# AND pid <> pg_backend_pid()
# AND state = 'idle'
# AND state_change < now() - interval '5 minutes';
# "

echo ""
echo "=== Para ejecutar manualmente en psql, usa el archivo: scripts/liberar_conexiones_postgres.sql ==="

