#!/bin/bash
# Script de diagnóstico completo para problemas de archivos abiertos
# Uso: bash scripts/diagnostico_completo.sh

echo "=========================================="
echo "  DIAGNÓSTICO COMPLETO - Archivos Abiertos"
echo "=========================================="
echo ""

# 1. Límites del sistema
echo "1. LÍMITES DEL SISTEMA:"
echo "   Límite actual (ulimit -n): $(ulimit -n)"
echo "   Límite máximo del sistema: $(cat /proc/sys/fs/file-max 2>/dev/null || echo 'N/A')"
echo "   Archivos abiertos actualmente: $(cat /proc/sys/fs/file-nr 2>/dev/null | awk '{print $1}' || echo 'N/A')"
echo ""

# 2. Procesos de Gunicorn
echo "2. PROCESOS DE GUNICORN:"
GUNICORN_PIDS=$(pgrep -f gunicorn 2>/dev/null)
if [ -z "$GUNICORN_PIDS" ]; then
    echo "   ⚠ No se encontraron procesos de Gunicorn"
else
    echo "   PIDs encontrados: $GUNICORN_PIDS"
    for pid in $GUNICORN_PIDS; do
        if [ -d "/proc/$pid" ]; then
            count=$(lsof -p $pid 2>/dev/null | grep -v "WARNING" | wc -l)
            limits=$(cat /proc/$pid/limits 2>/dev/null | grep "open files" || echo "N/A")
            echo "   PID $pid: $count archivos abiertos"
            echo "            Límite: $limits"
        fi
    done
fi
echo ""

# 3. Procesos de PostgreSQL
echo "3. PROCESOS DE POSTGRESQL:"
POSTGRES_PIDS=$(pgrep -f postgres 2>/dev/null)
if [ -z "$POSTGRES_PIDS" ]; then
    echo "   ⚠ No se encontraron procesos de PostgreSQL"
else
    echo "   PIDs encontrados: $(echo $POSTGRES_PIDS | wc -w) procesos"
    total_postgres=0
    for pid in $POSTGRES_PIDS; do
        if [ -d "/proc/$pid" ]; then
            count=$(lsof -p $pid 2>/dev/null | grep -v "WARNING" | wc -l)
            total_postgres=$((total_postgres + count))
        fi
    done
    echo "   Total archivos abiertos por PostgreSQL: $total_postgres"
fi
echo ""

# 4. Top procesos con más archivos abiertos (sin warnings)
echo "4. TOP 10 PROCESOS CON MÁS ARCHIVOS ABIERTOS:"
lsof 2>/dev/null | grep -v "WARNING" | grep -v "can't stat" | grep -v "no pwd entry" | \
    awk '{print $2}' | sort | uniq -c | sort -rn | head -10 | \
    while read count pid; do
        if [ -f "/proc/$pid/comm" ]; then
            name=$(cat /proc/$pid/comm 2>/dev/null)
            cmd=$(ps -p $pid -o cmd= 2>/dev/null | cut -c1-60)
            echo "   $name (PID $pid): $count archivos"
            echo "      CMD: $cmd"
        fi
    done
echo ""

# 5. Conexiones de red
echo "5. CONEXIONES DE RED:"
ESTABLISHED=$(netstat -an 2>/dev/null | grep ESTABLISHED | wc -l || ss -an 2>/dev/null | grep ESTAB | wc -l)
LISTEN=$(netstat -an 2>/dev/null | grep LISTEN | wc -l || ss -an 2>/dev/null | grep LISTEN | wc -l)
echo "   Conexiones ESTABLISHED: $ESTABLISHED"
echo "   Conexiones LISTEN: $LISTEN"
echo ""

# 6. Conexiones de PostgreSQL
echo "6. CONEXIONES DE POSTGRESQL:"
if command -v psql &> /dev/null; then
    PG_CONN=$(psql -U postgres -d proyectoballena -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();" 2>/dev/null || echo "N/A")
    echo "   Conexiones activas a la BD: $PG_CONN"
else
    echo "   ⚠ psql no disponible"
fi
echo ""

# 7. Recomendaciones
echo "7. RECOMENDACIONES:"
CURRENT_ULIMIT=$(ulimit -n)
if [ "$CURRENT_ULIMIT" -lt 4096 ]; then
    echo "   ⚠ Límite actual ($CURRENT_ULIMIT) es muy bajo"
    echo "   → Ejecutar: ulimit -n 65536"
    echo "   → Permanente: sudo bash scripts/aumentar_ulimit.sh"
fi

GUNICORN_COUNT=$(echo $GUNICORN_PIDS | wc -w)
if [ "$GUNICORN_COUNT" -gt 5 ]; then
    echo "   ⚠ Hay $GUNICORN_COUNT procesos de Gunicorn (muchos)"
    echo "   → Considerar reducir workers en supervisord.conf"
fi

TOTAL_FILES=$(lsof 2>/dev/null | grep -v "WARNING" | grep -v "can't stat" | grep -v "no pwd entry" | wc -l)
MAX_FILES=$(cat /proc/sys/fs/file-max 2>/dev/null)
if [ -n "$MAX_FILES" ] && [ "$TOTAL_FILES" -gt $((MAX_FILES * 80 / 100)) ]; then
    echo "   ⚠ Archivos abiertos ($TOTAL_FILES) cerca del máximo ($MAX_FILES)"
    echo "   → Aumentar límite del sistema"
fi

echo ""
echo "=========================================="
echo "  Para ver solo el conteo sin warnings:"
echo "  lsof 2>/dev/null | grep -v WARNING | grep -v 'can't stat' | wc -l"
echo "=========================================="

