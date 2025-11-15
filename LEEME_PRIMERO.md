# 🚨 SOLUCIÓN URGENTE - EJECUTAR EN ESTE ORDEN

## ⚡ COMANDOS A EJECUTAR (Copiar y pegar en orden)

### 1. Aumentar límite temporalmente
```bash
ulimit -n 65536
```

### 2. Liberar conexiones de PostgreSQL
```bash
sudo -u postgres psql -d proyectoballena -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid() AND state = 'idle' AND state_change < now() - interval '2 minutes';"
```

### 3. Configurar Gunicorn (ACTUALIZA TU SYSTEMD)
```bash
cd /opt/AleautosDjango
sudo bash scripts/fix_gunicorn_systemd.sh
```

### 4. Aumentar límite permanentemente
```bash
sudo bash scripts/aumentar_ulimit.sh
```

### 5. Verificar
```bash
sudo systemctl status gunicorn
bash scripts/diagnostico_completo.sh
```

---

## 📋 QUÉ HACE CADA PASO

**Paso 1**: Aumenta el límite de archivos abiertos temporalmente (efecto inmediato)

**Paso 2**: Libera conexiones inactivas de PostgreSQL que están consumiendo recursos

**Paso 3**: 
- Actualiza tu servicio systemd de Gunicorn
- Reduce workers de 3 a 2
- Agrega `LimitNOFILE=65536`
- Agrega `--max-requests 1000` para reciclar workers
- Reinicia Gunicorn automáticamente

**Paso 4**: Configura el límite permanentemente en `/etc/security/limits.conf`

**Paso 5**: Verifica que todo esté funcionando correctamente

---

## ⚠️ IMPORTANTE

- El script del **Paso 3** hace backup automático de tu configuración en `/opt/AleautosDjango/backups/`
- Si algo sale mal, puedes restaurar desde el backup
- Después del **Paso 4**, es recomendable hacer logout/login para que el límite se aplique completamente

---

## 🔍 VERIFICACIÓN RÁPIDA

```bash
# Ver límite actual
ulimit -n
# Debe mostrar 65536

# Ver estado de Gunicorn
sudo systemctl status gunicorn

# Ver límite del proceso Gunicorn
PID=$(systemctl show -p MainPID --value gunicorn)
cat /proc/$PID/limits | grep "open files"
# Debe mostrar 65536
```

---

## 📚 DOCUMENTACIÓN COMPLETA

- `EJECUTAR_ESTOS_COMANDOS.md` - Guía detallada paso a paso
- `SOLUCION_PASO_A_PASO.md` - Explicación completa
- `SOLUCION_TOO_MANY_OPEN_FILES.md` - Solución técnica detallada

