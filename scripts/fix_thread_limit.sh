#!/bin/bash

# Script para solucionar el error "can't start new thread"
# Aumenta límites de threads y procesos del sistema

set -e

echo "========================================="
echo "  SOLUCIÓN: can't start new thread"
echo "========================================="
echo ""

# 1. Verificar límites actuales
echo "1. Límites actuales:"
echo "   Threads máximos del sistema: $(cat /proc/sys/kernel/threads-max)"
echo "   Threads actuales: $(ps -eLf | wc -l)"
echo "   Límite de procesos (ulimit -u): $(ulimit -u)"
echo ""

# 2. Aumentar límite de threads del sistema
echo "2. Aumentando límite de threads del sistema..."
echo "32768" | sudo tee /proc/sys/kernel/threads-max > /dev/null
echo "   ✓ Límite temporal aumentado a 32768"
echo ""

# 3. Hacer permanente
echo "3. Configurando límite permanente..."
if ! grep -q "kernel.threads-max" /etc/sysctl.conf; then
    echo "kernel.threads-max = 32768" | sudo tee -a /etc/sysctl.conf > /dev/null
    echo "   ✓ Agregado a /etc/sysctl.conf"
else
    echo "   ⚠ Ya existe en /etc/sysctl.conf"
fi
echo ""

# 4. Aumentar límite de procesos en limits.conf
echo "4. Configurando límites de procesos en /etc/security/limits.conf..."
if ! grep -q "^admin.*nproc" /etc/security/limits.conf; then
    echo "" | sudo tee -a /etc/security/limits.conf > /dev/null
    echo "# Límites para Gunicorn - can't start new thread fix" | sudo tee -a /etc/security/limits.conf > /dev/null
    echo "admin soft nproc 4096" | sudo tee -a /etc/security/limits.conf > /dev/null
    echo "admin hard nproc 8192" | sudo tee -a /etc/security/limits.conf > /dev/null
    echo "www-data soft nproc 4096" | sudo tee -a /etc/security/limits.conf > /dev/null
    echo "www-data hard nproc 8192" | sudo tee -a /etc/security/limits.conf > /dev/null
    echo "   ✓ Límites agregados"
else
    echo "   ⚠ Ya existen límites configurados"
fi
echo ""

# 5. Aplicar sysctl
echo "5. Aplicando cambios de sysctl..."
sudo sysctl -p > /dev/null 2>&1 || true
echo "   ✓ Cambios aplicados"
echo ""

# 6. Verificar Gunicorn
echo "6. Verificando configuración de Gunicorn..."
GUNICORN_SERVICE="/etc/systemd/system/gunicorn.service"
if [ -f "$GUNICORN_SERVICE" ]; then
    echo "   Archivo encontrado: $GUNICORN_SERVICE"
    
    # Verificar si tiene LimitNPROC
    if ! grep -q "LimitNPROC" "$GUNICORN_SERVICE"; then
        echo "   ⚠ No tiene LimitNPROC configurado"
        echo "   Recomendación: Agregar LimitNPROC=4096 al [Service]"
    else
        echo "   ✓ Tiene LimitNPROC configurado"
    fi
else
    echo "   ⚠ Archivo no encontrado"
fi
echo ""

# 7. Resumen
echo "========================================="
echo "  RESUMEN"
echo "========================================="
echo "✓ Límite de threads aumentado (temporal y permanente)"
echo "✓ Límites de procesos configurados"
echo ""
echo "⚠ IMPORTANTE:"
echo "  1. Reinicia Gunicorn: sudo systemctl restart gunicorn"
echo "  2. Considera reducir workers si el problema persiste"
echo "  3. Si usas ASGI, considera cambiar a WSGI si no necesitas async"
echo ""
echo "Para verificar threads actuales:"
echo "  ps -eLf | wc -l"
echo "  ps -eLf | grep gunicorn | wc -l"
echo ""

