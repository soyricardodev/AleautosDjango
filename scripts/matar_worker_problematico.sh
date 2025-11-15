#!/bin/bash
# Script de EMERGENCIA para matar el worker de Gunicorn con demasiados archivos abiertos
# Uso: sudo bash scripts/matar_worker_problematico.sh

echo "=========================================="
echo "  EMERGENCIA: Matar Worker Problemático"
echo "=========================================="
echo ""

# Encontrar el proceso con más archivos abiertos
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
    echo "El proceso más problemático tiene $MAX_FILES archivos"
    exit 0
fi

echo ""
echo "⚠⚠⚠ PROCESO PROBLEMÁTICO ENCONTRADO ⚠⚠⚠"
echo "  PID: $PROBLEM_PID"
echo "  Archivos abiertos: $MAX_FILES"
echo ""

# Mostrar información del proceso
echo "Información del proceso:"
ps -p $PROBLEM_PID -o pid,ppid,cmd,etime
echo ""

# Preguntar confirmación
read -p "¿Matar este proceso? (s/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "Operación cancelada"
    exit 0
fi

# Matar el proceso
echo "Matando proceso $PROBLEM_PID..."
kill -9 $PROBLEM_PID

sleep 2

# Verificar que se mató
if [ -d "/proc/$PROBLEM_PID" ]; then
    echo "❌ El proceso aún existe, intentando forzar..."
    kill -9 $PROBLEM_PID
    sleep 1
else
    echo "✓ Proceso eliminado"
fi

echo ""
echo "Gunicorn debería reiniciar automáticamente el worker"
echo "Verificar con: sudo systemctl status gunicorn"

