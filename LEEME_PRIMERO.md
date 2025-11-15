# 🚨 SOLUCIÓN URGENTE - EJECUTAR EN ESTE ORDEN

## ⚠️ PROBLEMA CRÍTICO ENCONTRADO Y CORREGIDO

**CAUSA RAÍZ IDENTIFICADA**: Conexiones HTTP (`http.client.HTTPConnection`) que **NO SE CERRABAN** en:
- `Rifa/views.py` - función `enviarWhatsapp()` (línea 2059)
- `Rifa/apis.py` - función `testWhatsapp()` (línea 1178)

Esto causaba que cada vez que se enviaba un WhatsApp, se abriera una conexión que nunca se cerraba, acumulándose hasta **488,868 archivos abiertos** en un solo worker.

**✅ CORRECCIÓN APLICADA**: Se agregó `try/finally` para cerrar las conexiones HTTP siempre.

---

## ⚡ COMANDOS A EJECUTAR (Copiar y pegar en orden)

### 1. Matar el proceso problemático (INMEDIATO)
```bash
sudo kill -9 2117153
```

### 2. Aumentar límite temporalmente
```bash
ulimit -n 65536
```

### 3. Liberar conexiones de PostgreSQL
```bash
sudo -u postgres psql -d proyectoballena -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid() AND state = 'idle' AND state_change < now() - interval '2 minutes';"
```

### 4. Reiniciar Gunicorn (para aplicar el código corregido)
```bash
sudo systemctl restart gunicorn
```

### 5. Configurar Gunicorn permanentemente
```bash
cd /opt/AleautosDjango
sudo bash scripts/fix_gunicorn_systemd.sh
```

### 6. Aumentar límite permanentemente
```bash
sudo bash scripts/aumentar_ulimit.sh
```

### 7. Verificar que se solucionó
```bash
bash scripts/diagnostico_completo.sh
```

---

## 📋 QUÉ HACE CADA PASO

**Paso 1**: Mata el worker con 488,868 archivos abiertos (fuga masiva)

**Paso 2**: Aumenta el límite de archivos abiertos temporalmente (efecto inmediato)

**Paso 3**: Libera conexiones inactivas de PostgreSQL que están consumiendo recursos

**Paso 4**: Reinicia Gunicorn para que cargue el código corregido (conexiones HTTP ahora se cierran)

**Paso 5**: 
- Actualiza tu servicio systemd de Gunicorn
- Reduce workers de 3 a 2
- Agrega `LimitNOFILE=65536`
- Agrega `--max-requests 1000` para reciclar workers
- Reinicia Gunicorn automáticamente

**Paso 6**: Configura el límite permanentemente en `/etc/security/limits.conf`

**Paso 7**: Verifica que todo esté funcionando correctamente

---

## ⚠️ IMPORTANTE

- El código ya está corregido en el repositorio
- Después del **Paso 4**, Gunicorn cargará el código corregido y las conexiones HTTP se cerrarán correctamente
- El script del **Paso 5** hace backup automático de tu configuración en `/opt/AleautosDjango/backups/`
- Si algo sale mal, puedes restaurar desde el backup
- Después del **Paso 6**, es recomendable hacer logout/login para que el límite se aplique completamente

---

## 🔍 VERIFICACIÓN RÁPIDA

```bash
# Ver límite actual
ulimit -n
# Debe mostrar 65536

# Ver estado de Gunicorn
sudo systemctl status gunicorn

# Ver archivos abiertos por cada worker (debe ser < 1000)
for pid in $(pgrep -f gunicorn); do
    echo "PID $pid: $(lsof -p $pid 2>/dev/null | grep -v WARNING | grep -v 'can't stat' | wc -l) archivos"
done
```

---

## 📚 DOCUMENTACIÓN COMPLETA

- `SOLUCION_URGENTE_FUGA_MASIVA.md` - Detalles del problema y solución
- `EJECUTAR_ESTOS_COMANDOS.md` - Guía detallada paso a paso
- `SOLUCION_PASO_A_PASO.md` - Explicación completa
- `SOLUCION_TOO_MANY_OPEN_FILES.md` - Solución técnica detallada
