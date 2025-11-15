#!/bin/bash
# Script para configurar ulimit en systemd para Gunicorn
# Uso: sudo ./scripts/fix_ulimit_systemd.sh

echo "=== Configurando ulimit para Gunicorn en systemd ==="

# Buscar archivo de servicio de Gunicorn
SERVICE_FILE=""
if [ -f "/etc/systemd/system/gunicorn.service" ]; then
    SERVICE_FILE="/etc/systemd/system/gunicorn.service"
elif [ -f "/etc/systemd/system/gunicorn.socket" ]; then
    SERVICE_FILE="/etc/systemd/system/gunicorn.socket"
elif [ -f "/lib/systemd/system/gunicorn.service" ]; then
    SERVICE_FILE="/lib/systemd/system/gunicorn.service"
fi

if [ -z "$SERVICE_FILE" ]; then
    echo "⚠ No se encontró archivo de servicio de Gunicorn"
    echo "Buscando procesos de Gunicorn..."
    ps aux | grep gunicorn | grep -v grep
    echo ""
    echo "Por favor, crea manualmente el archivo de servicio o especifica la ruta"
    exit 1
fi

echo "Archivo encontrado: $SERVICE_FILE"

# Hacer backup
cp "$SERVICE_FILE" "${SERVICE_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
echo "✓ Backup creado"

# Verificar si ya tiene LimitNOFILE
if grep -q "LimitNOFILE" "$SERVICE_FILE"; then
    echo "⚠ Ya existe LimitNOFILE en el archivo"
    echo "Actualizando valor..."
    sed -i 's/LimitNOFILE=.*/LimitNOFILE=65536/' "$SERVICE_FILE"
else
    echo "Agregando LimitNOFILE..."
    # Agregar después de [Service]
    if grep -q "\[Service\]" "$SERVICE_FILE"; then
        sed -i '/\[Service\]/a LimitNOFILE=65536' "$SERVICE_FILE"
    else
        # Si no hay sección [Service], agregarla
        echo "" >> "$SERVICE_FILE"
        echo "[Service]" >> "$SERVICE_FILE"
        echo "LimitNOFILE=65536" >> "$SERVICE_FILE"
    fi
fi

echo "✓ Archivo actualizado"
echo ""
echo "Contenido relevante:"
grep -A 5 "\[Service\]" "$SERVICE_FILE" | head -10

echo ""
echo "=== Recargando systemd ==="
systemctl daemon-reload
echo "✓ systemd recargado"

echo ""
echo "=== Reiniciando Gunicorn ==="
if systemctl is-active --quiet gunicorn; then
    systemctl restart gunicorn
    echo "✓ Gunicorn reiniciado"
else
    echo "⚠ Gunicorn no está corriendo como servicio systemd"
    echo "Reinicia manualmente con: sudo systemctl restart gunicorn"
fi

echo ""
echo "=== Verificando límite ==="
if systemctl is-active --quiet gunicorn; then
    PID=$(systemctl show -p MainPID --value gunicorn)
    if [ -n "$PID" ] && [ "$PID" != "0" ]; then
        echo "PID de Gunicorn: $PID"
        echo "Límite de archivos: $(cat /proc/$PID/limits | grep "open files")"
    fi
fi

echo ""
echo "=== Para verificar manualmente ==="
echo "ulimit -n"
echo "lsof -p \$(pgrep -f gunicorn | head -1) | wc -l"

