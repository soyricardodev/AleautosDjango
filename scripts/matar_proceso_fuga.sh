#!/bin/bash
# Script para matar procesos de Gunicorn con fuga masiva de archivos
# Uso: sudo bash scripts/matar_proceso_fuga.sh [PID]

echo "=========================================="
echo "  MATAR PROCESO CON FUGA MASIVA"
echo "=========================================="
echo ""

if [ -n "$1" ]; then
    # Si se proporciona un PID, matarlo directamente
    PROBLEM_PID=$1
    echo "Matando PID específico: $PROBLEM_PID"
else
    # Buscar automáticamente el proceso con más archivos
    echo "Buscando proceso de Gunicorn con más archivos abiertos..."
    PROBLEM_PID=""
    MAX_FILES=0

    for pid in $(pgrep -f gunicorn); do
        if [ -d "/proc/$pid" ]; then
            count=$(lsof -p $pid 2>/dev/null | grep -v "WARNING" | grep -v "can't stat" | grep -v "no pwd entry" | wc -l)
            if [ "$count" -gt "$MAX_FILES" ]; then
                MAX_FILES=$count
                PROBLEM_PID=$pid
            fi
            echo "  PID $pid: $count archivos"
        fi
    done

    if [ -z "$PROBLEM_PID" ] || [ "$MAX_FILES" -lt 10000 ]; then
        echo "⚠ No se encontró un proceso con fuga masiva (>10,000 archivos)"
        if [ -n "$PROBLEM_PID" ]; then
            echo "El proceso más problemático tiene $MAX_FILES archivos"
        fi
        exit 0
    fi

    echo ""
    echo "⚠⚠⚠ PROCESO PROBLEMÁTICO ENCONTRADO ⚠⚠⚠"
    echo "  PID: $PROBLEM_PID"
    echo "  Archivos abiertos: $MAX_FILES"
fi

echo ""
echo "Información del proceso:"
ps -p $PROBLEM_PID -o pid,ppid,cmd,etime 2>/dev/null || echo "Proceso no encontrado"
echo ""

# Matar el proceso
echo "Matando proceso $PROBLEM_PID..."
kill -9 $PROBLEM_PID 2>/dev/null

sleep 2

# Verificar que se mató
if [ -d "/proc/$PROBLEM_PID" ]; then
    echo "❌ El proceso aún existe, intentando forzar..."
    kill -9 $PROBLEM_PID 2>/dev/null
    sleep 1
    if [ -d "/proc/$PROBLEM_PID" ]; then
        echo "❌ No se pudo matar el proceso. Puede requerir permisos root."
        exit 1
    fi
fi

echo "✓ Proceso eliminado"
echo ""
echo "Gunicorn debería reiniciar automáticamente el worker"
echo "Verificar con: sudo systemctl status gunicorn"

