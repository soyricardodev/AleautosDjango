#!/bin/bash
# Script para aumentar el límite de archivos abiertos (ulimit)
# Uso: sudo ./scripts/aumentar_ulimit.sh

echo "=== Aumentando límite de archivos abiertos ==="

# Ver límite actual
echo "Límite actual:"
ulimit -n

# Aumentar temporalmente
echo "Aumentando a 65536..."
ulimit -n 65536

echo "Nuevo límite:"
ulimit -n

# Configurar permanentemente para el usuario actual
if [ -f ~/.bashrc ]; then
    if ! grep -q "ulimit -n 65536" ~/.bashrc; then
        echo "ulimit -n 65536" >> ~/.bashrc
        echo "✓ Agregado a ~/.bashrc"
    else
        echo "⚠ Ya existe en ~/.bashrc"
    fi
fi

# Configurar para todo el sistema (requiere root)
if [ "$EUID" -eq 0 ]; then
    LIMITS_FILE="/etc/security/limits.conf"
    if [ -f "$LIMITS_FILE" ]; then
        if ! grep -q "nofile 65536" "$LIMITS_FILE"; then
            echo "" >> "$LIMITS_FILE"
            echo "# Límite de archivos abiertos para prevenir 'too many open files'" >> "$LIMITS_FILE"
            echo "* soft nofile 65536" >> "$LIMITS_FILE"
            echo "* hard nofile 65536" >> "$LIMITS_FILE"
            echo "root soft nofile 65536" >> "$LIMITS_FILE"
            echo "root hard nofile 65536" >> "$LIMITS_FILE"
            echo "✓ Configurado en $LIMITS_FILE"
            echo "⚠ Necesitas hacer logout/login o reiniciar para que tome efecto"
        else
            echo "⚠ Ya está configurado en $LIMITS_FILE"
        fi
    fi
else
    echo "⚠ Para configurar permanentemente para todo el sistema, ejecuta como root:"
    echo "  sudo bash $0"
fi

echo ""
echo "=== Para aplicar cambios inmediatamente ==="
echo "Ejecuta: ulimit -n 65536"
echo "O reinicia la sesión"

