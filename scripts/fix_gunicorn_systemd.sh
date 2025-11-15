#!/bin/bash
# Script específico para configurar Gunicorn con systemd
# Uso: sudo bash scripts/fix_gunicorn_systemd.sh

echo "=========================================="
echo "  CONFIGURACIÓN DE GUNICORN CON SYSTEMD"
echo "=========================================="
echo ""

# Verificar que estamos como root
if [ "$EUID" -ne 0 ]; then 
    echo "⚠ Este script debe ejecutarse como root (sudo)"
    exit 1
fi

# Rutas de los archivos de servicio
SERVICE_FILE="/etc/systemd/system/gunicorn.service"
SOCKET_FILE="/etc/systemd/system/gunicorn.socket"

# Verificar que existen
if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ No se encontró $SERVICE_FILE"
    exit 1
fi

echo "✓ Archivos encontrados:"
echo "  - $SERVICE_FILE"
if [ -f "$SOCKET_FILE" ]; then
    echo "  - $SOCKET_FILE"
fi
echo ""

# Hacer backup
BACKUP_DIR="/opt/AleautosDjango/backups/systemd_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp "$SERVICE_FILE" "$BACKUP_DIR/gunicorn.service.backup"
if [ -f "$SOCKET_FILE" ]; then
    cp "$SOCKET_FILE" "$BACKUP_DIR/gunicorn.socket.backup"
fi
echo "✓ Backups creados en: $BACKUP_DIR"
echo ""

# Leer el archivo actual
echo "=== Configuración actual ==="
cat "$SERVICE_FILE"
echo ""

# Crear nuevo archivo de servicio con LimitNOFILE
echo "=== Creando nueva configuración ==="
cat > "$SERVICE_FILE" << 'EOF'
[Unit]
Description=gunicorn daemon
Requires=gunicorn.socket
After=network.target

[Service]
User=admin
Group=www-data
WorkingDirectory=/opt/AleautosDjango/
ExecStart=/opt/AleautosDjango/.venv/bin/gunicorn \
          --access-logfile - \
          -k uvicorn.workers.UvicornWorker \
          --workers 2 \
          --max-requests 1000 \
          --max-requests-jitter 50 \
          --timeout 120 \
          --bind unix:/run/gunicorn.sock \
          proyectoBallena.asgi:application
EnvironmentFile=/opt/AleautosDjango/.env

# CRÍTICO: Límite de archivos abiertos
LimitNOFILE=65536

# Reiniciar automáticamente
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Archivo de servicio actualizado"
echo ""

# Mostrar cambios
echo "=== Cambios aplicados ==="
echo "  ✓ Workers reducidos: 3 → 2"
echo "  ✓ Agregado --max-requests 1000 (recicla workers)"
echo "  ✓ Agregado --max-requests-jitter 50"
echo "  ✓ Agregado --timeout 120"
echo "  ✓ Agregado LimitNOFILE=65536"
echo "  ✓ Agregado Restart=always"
echo ""

# Recargar systemd
echo "=== Recargando systemd ==="
systemctl daemon-reload
echo "✓ systemd recargado"
echo ""

# Reiniciar Gunicorn
echo "=== Reiniciando Gunicorn ==="
systemctl restart gunicorn
sleep 2

# Verificar estado
if systemctl is-active --quiet gunicorn; then
    echo "✓ Gunicorn está corriendo"
    systemctl status gunicorn --no-pager -l | head -15
else
    echo "❌ Error al iniciar Gunicorn"
    systemctl status gunicorn --no-pager -l
    exit 1
fi

echo ""
echo "=== Verificando límite de archivos ==="
PID=$(systemctl show -p MainPID --value gunicorn)
if [ -n "$PID" ] && [ "$PID" != "0" ]; then
    echo "PID de Gunicorn: $PID"
    LIMITS=$(cat /proc/$PID/limits 2>/dev/null | grep "open files")
    echo "Límite configurado: $LIMITS"
    
    # Contar archivos abiertos
    FILES=$(lsof -p $PID 2>/dev/null | grep -v "WARNING" | grep -v "can't stat" | grep -v "no pwd entry" | wc -l)
    echo "Archivos abiertos actualmente: $FILES"
else
    echo "⚠ No se pudo obtener PID de Gunicorn"
fi

echo ""
echo "=========================================="
echo "  CONFIGURACIÓN COMPLETADA"
echo "=========================================="
echo ""
echo "Para ver logs:"
echo "  sudo journalctl -u gunicorn -f"
echo ""
echo "Para verificar estado:"
echo "  sudo systemctl status gunicorn"
echo ""

