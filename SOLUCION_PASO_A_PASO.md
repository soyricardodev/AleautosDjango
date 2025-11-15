# 🚨 SOLUCIÓN PASO A PASO - Too Many Open Files

## ⚡ ORDEN DE EJECUCIÓN (Seguir en este orden)

### PASO 1: Aumentar límite temporalmente (INMEDIATO)
```bash
ulimit -n 65536
ulimit -n  # Verificar que se aplicó (debe mostrar 65536)
```

### PASO 2: Liberar conexiones de PostgreSQL
```bash
# Opción A: SQL directo (más rápido)
sudo -u postgres psql -d proyectoballena -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = current_database()
AND pid <> pg_backend_pid()
AND state = 'idle'
AND state_change < now() - interval '2 minutes';
"

# Opción B: Comando Django
cd /opt/AleautosDjango
source .venv/bin/activate
python manage.py close_db_connections --force
```

### PASO 3: Configurar Gunicorn con systemd
```bash
# Ejecutar el script que actualiza tu servicio systemd
sudo bash scripts/fix_gunicorn_systemd.sh
```

Este script:
- ✅ Reduce workers de 3 a 2
- ✅ Agrega `LimitNOFILE=65536` al servicio
- ✅ Agrega `--max-requests 1000` para reciclar workers
- ✅ Agrega `--timeout 120`
- ✅ Reinicia Gunicorn automáticamente

### PASO 4: Aumentar límite permanentemente en el sistema
```bash
# Editar /etc/security/limits.conf
sudo nano /etc/security/limits.conf

# Agregar estas líneas al final:
* soft nofile 65536
* hard nofile 65536
root soft nofile 65536
root hard nofile 65536
admin soft nofile 65536
admin hard nofile 65536

# Guardar y salir (Ctrl+X, Y, Enter)

# O usar el script automático:
sudo bash scripts/aumentar_ulimit.sh
```

### PASO 5: Reiniciar sesión o aplicar cambios
```bash
# Opción A: Logout y login (recomendado)
# O simplemente ejecutar:
ulimit -n 65536

# Opción B: Reiniciar Gunicorn (ya se hace en PASO 3, pero por si acaso)
sudo systemctl restart gunicorn
```

### PASO 6: Verificar que todo funciona
```bash
# 1. Verificar límite
ulimit -n
# Debe mostrar 65536

# 2. Verificar Gunicorn
sudo systemctl status gunicorn

# 3. Verificar archivos abiertos
bash scripts/diagnostico_completo.sh

# 4. Verificar conexiones de PostgreSQL
sudo -u postgres psql -d proyectoballena -c "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();"
```

## 📋 RESUMEN DE COMANDOS (Copiar y pegar)

```bash
# 1. Aumentar límite temporal
ulimit -n 65536

# 2. Liberar conexiones PostgreSQL
sudo -u postgres psql -d proyectoballena -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid() AND state = 'idle' AND state_change < now() - interval '2 minutes';"

# 3. Configurar Gunicorn
sudo bash /opt/AleautosDjango/scripts/fix_gunicorn_systemd.sh

# 4. Aumentar límite permanentemente
sudo bash /opt/AleautosDjango/scripts/aumentar_ulimit.sh

# 5. Verificar
bash /opt/AleautosDjango/scripts/diagnostico_completo.sh
```

## 🔍 Verificación Post-Configuración

```bash
# Ver configuración del servicio
sudo systemctl show gunicorn | grep LimitNOFILE

# Ver límite del proceso
PID=$(systemctl show -p MainPID --value gunicorn)
cat /proc/$PID/limits | grep "open files"

# Ver archivos abiertos por Gunicorn
lsof -p $(systemctl show -p MainPID --value gunicorn) 2>/dev/null | grep -v WARNING | grep -v "can't stat" | wc -l
```

## ⚠️ Si Algo Sale Mal

### Restaurar configuración anterior:
```bash
# Los backups están en:
ls -la /opt/AleautosDjango/backups/systemd_*/

# Restaurar:
sudo cp /opt/AleautosDjango/backups/systemd_*/gunicorn.service.backup /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
```

### Ver logs de Gunicorn:
```bash
sudo journalctl -u gunicorn -f
sudo journalctl -u gunicorn --since "10 minutes ago"
```

## 📝 Cambios que se Aplicarán

### En `/etc/systemd/system/gunicorn.service`:
- Workers: `3` → `2`
- Agregado: `LimitNOFILE=65536`
- Agregado: `--max-requests 1000`
- Agregado: `--max-requests-jitter 50`
- Agregado: `--timeout 120`
- Agregado: `Restart=always`

### En el sistema:
- `/etc/security/limits.conf`: Límites aumentados a 65536

