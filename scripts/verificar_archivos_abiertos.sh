#!/bin/bash
# Script para verificar archivos abiertos y diagnosticar problemas
# Uso: ./scripts/verificar_archivos_abiertos.sh

echo "=== Diagnóstico de Archivos Abiertos ==="
echo ""

echo "1. Límite actual del sistema:"
ulimit -n
echo ""

echo "2. Límite máximo del sistema:"
cat /proc/sys/fs/file-max
echo ""

echo "3. Archivos abiertos actualmente:"
cat /proc/sys/fs/file-nr
echo ""

echo "4. Procesos de Gunicorn:"
ps aux | grep gunicorn | grep -v grep
echo ""

echo "5. Archivos abiertos por cada proceso de Gunicorn:"
for pid in $(pgrep -f gunicorn); do
    # Filtrar warnings de lsof
    count=$(lsof -p $pid 2>/dev/null | grep -v "WARNING" | grep -v "can't stat" | grep -v "no pwd entry" | wc -l)
    limits=$(cat /proc/$pid/limits 2>/dev/null | grep "open files" || echo "N/A")
    echo "  PID $pid: $count archivos abiertos"
    echo "            Límite: $limits"
done
echo ""

echo "6. Archivos abiertos por PostgreSQL:"
total_postgres=0
for pid in $(pgrep -f postgres); do
    count=$(lsof -p $pid 2>/dev/null | grep -v "WARNING" | grep -v "can't stat" | grep -v "no pwd entry" | wc -l)
    total_postgres=$((total_postgres + count))
done
echo "  Total: $total_postgres archivos abiertos"
echo ""

echo "7. Top 10 procesos con más archivos abiertos (sin warnings):"
lsof 2>/dev/null | grep -v "WARNING" | grep -v "can't stat" | grep -v "no pwd entry" | \
    awk '{print $2}' | sort | uniq -c | sort -rn | head -10 | while read count pid; do
    if [ -f "/proc/$pid/comm" ]; then
        name=$(cat /proc/$pid/comm 2>/dev/null)
        cmd=$(ps -p $pid -o cmd= 2>/dev/null | cut -c1-50)
        echo "  $name (PID $pid): $count archivos"
        echo "      $cmd"
    fi
done
echo ""

echo "8. Conexiones de red abiertas:"
ESTABLISHED=$(netstat -an 2>/dev/null | grep ESTABLISHED | wc -l || ss -an 2>/dev/null | grep ESTAB | wc -l)
LISTEN=$(netstat -an 2>/dev/null | grep LISTEN | wc -l || ss -an 2>/dev/null | grep LISTEN | wc -l)
echo "  ESTABLISHED: $ESTABLISHED"
echo "  LISTEN: $LISTEN"
echo ""

echo "9. Total de archivos abiertos (sin warnings):"
TOTAL=$(lsof 2>/dev/null | grep -v "WARNING" | grep -v "can't stat" | grep -v "no pwd entry" | wc -l)
echo "  Total: $TOTAL archivos"
echo ""

echo "=== Recomendaciones ==="
CURRENT=$(ulimit -n)
MAX=$(cat /proc/sys/fs/file-max)
if [ "$CURRENT" -lt 4096 ]; then
    echo "⚠ Límite actual ($CURRENT) es muy bajo. Recomendado: 65536"
    echo "  Ejecuta: sudo bash scripts/aumentar_ulimit.sh"
fi

GUNICORN_COUNT=$(pgrep -f gunicorn | wc -l)
if [ "$GUNICORN_COUNT" -gt 5 ]; then
    echo "⚠ Hay $GUNICORN_COUNT procesos de Gunicorn. Considera reducir workers."
fi

