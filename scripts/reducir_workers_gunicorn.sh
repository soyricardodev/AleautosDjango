#!/bin/bash

# Script para reducir workers de Gunicorn y evitar "can't start new thread"

set -e

GUNICORN_SERVICE="/etc/systemd/system/gunicorn.service"
BACKUP_FILE="${GUNICORN_SERVICE}.backup.$(date +%Y%m%d_%H%M%S)"

echo "========================================="
echo "  REDUCIR WORKERS DE GUNICORN"
echo "========================================="
echo ""

if [ ! -f "$GUNICORN_SERVICE" ]; then
    echo "❌ Error: No se encontró $GUNICORN_SERVICE"
    exit 1
fi

# Hacer backup
echo "1. Creando backup..."
sudo cp "$GUNICORN_SERVICE" "$BACKUP_FILE"
echo "   ✓ Backup creado: $BACKUP_FILE"
echo ""

# Leer configuración actual
echo "2. Configuración actual:"
grep -E "(workers|threads|UvicornWorker|wsgi|asgi)" "$GUNICORN_SERVICE" || echo "   (no encontrado)"
echo ""

# Preguntar si usar WSGI o ASGI
echo "3. ¿Qué quieres hacer?"
echo "   a) Cambiar a WSGI (recomendado si no necesitas async)"
echo "   b) Mantener ASGI pero reducir workers"
read -p "   Opción (a/b): " opcion

if [ "$opcion" = "a" ]; then
    echo ""
    echo "4. Cambiando a WSGI..."
    
    # Crear override temporal
    sudo mkdir -p /etc/systemd/system/gunicorn.service.d/
    sudo tee /etc/systemd/system/gunicorn.service.d/override.conf > /dev/null <<EOF
[Service]
ExecStart=
ExecStart=/opt/AleautosDjango/.venv/bin/gunicorn \\
  --access-logfile - \\
  --workers 2 \\
  --threads 4 \\
  --max-requests 1000 \\
  --max-requests-jitter 50 \\
  --timeout 120 \\
  --bind unix:/run/gunicorn.sock \\
  proyectoBallena.wsgi:application
LimitNPROC=4096
LimitNOFILE=65536
TasksMax=4096
EOF
    
    echo "   ✓ Configuración WSGI creada"
    echo "   - Workers: 2"
    echo "   - Threads: 4 por worker"
    echo "   - Max requests: 1000"
    
elif [ "$opcion" = "b" ]; then
    echo ""
    echo "4. Reduciendo workers de ASGI..."
    
    # Crear override temporal
    sudo mkdir -p /etc/systemd/system/gunicorn.service.d/
    sudo tee /etc/systemd/system/gunicorn.service.d/override.conf > /dev/null <<EOF
[Service]
ExecStart=
ExecStart=/opt/AleautosDjango/.venv/bin/gunicorn \\
  --access-logfile - \\
  -k uvicorn.workers.UvicornWorker \\
  --workers 1 \\
  --threads 8 \\
  --limit-concurrency 100 \\
  --timeout 120 \\
  --bind unix:/run/gunicorn.sock \\
  proyectoBallena.asgi:application
LimitNPROC=4096
LimitNOFILE=65536
TasksMax=4096
EOF
    
    echo "   ✓ Configuración ASGI optimizada"
    echo "   - Workers: 1"
    echo "   - Threads: 8"
    echo "   - Limit concurrency: 100"
    
else
    echo "❌ Opción inválida"
    exit 1
fi

echo ""

# Recargar systemd
echo "5. Recargando systemd..."
sudo systemctl daemon-reload
echo "   ✓ Systemd recargado"
echo ""

# Reiniciar Gunicorn
echo "6. ¿Reiniciar Gunicorn ahora? (s/n)"
read -p "   Respuesta: " reiniciar

if [ "$reiniciar" = "s" ]; then
    echo ""
    echo "   Reiniciando Gunicorn..."
    sudo systemctl restart gunicorn
    sleep 2
    sudo systemctl status gunicorn --no-pager -l || true
    echo ""
    echo "   ✓ Gunicorn reiniciado"
else
    echo ""
    echo "   ⚠ No se reinició. Ejecuta manualmente:"
    echo "   sudo systemctl restart gunicorn"
fi

echo ""
echo "========================================="
echo "  COMPLETADO"
echo "========================================="
echo ""
echo "Para verificar:"
echo "  sudo systemctl status gunicorn"
echo "  ps -eLf | grep gunicorn | wc -l  # Threads de Gunicorn"
echo ""

