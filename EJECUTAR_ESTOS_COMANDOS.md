# 🚨 EJECUTAR ESTOS COMANDOS EN ORDEN

## ⚡ ORDEN EXACTO DE EJECUCIÓN

### 1️⃣ Aumentar límite temporalmente (PRIMERO)
```bash
ulimit -n 65536
ulimit -n  # Verificar: debe mostrar 65536
```

### 2️⃣ Liberar conexiones de PostgreSQL
```bash
sudo -u postgres psql -d proyectoballena -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid() AND state = 'idle' AND state_change < now() - interval '2 minutes';"
```

### 3️⃣ Configurar Gunicorn (ACTUALIZA TU SERVICIO SYSTEMD)
```bash
cd /opt/AleautosDjango
sudo bash scripts/fix_gunicorn_systemd.sh
```

Este script:
- ✅ Hace backup de tu configuración actual
- ✅ Reduce workers de 3 a 2
- ✅ Agrega `LimitNOFILE=65536` al servicio
- ✅ Agrega `--max-requests 1000` para reciclar workers
- ✅ Reinicia Gunicorn automáticamente

### 4️⃣ Aumentar límite permanentemente en el sistema
```bash
sudo bash scripts/aumentar_ulimit.sh
```

O manualmente:
```bash
sudo nano /etc/security/limits.conf
# Agregar al final:
* soft nofile 65536
* hard nofile 65536
root soft nofile 65536
root hard nofile 65536
admin soft nofile 65536
admin hard nofile 65536
```

### 5️⃣ Verificar que todo funciona
```bash
# Ver estado de Gunicorn
sudo systemctl status gunicorn

# Ver límite configurado
PID=$(systemctl show -p MainPID --value gunicorn)
cat /proc/$PID/limits | grep "open files"

# Diagnóstico completo
bash scripts/diagnostico_completo.sh
```

## 📋 COMANDOS EN UNA SOLA LÍNEA (Copiar y pegar)

```bash
# Ejecutar todos en secuencia
ulimit -n 65536 && \
sudo -u postgres psql -d proyectoballena -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid() AND state = 'idle' AND state_change < now() - interval '2 minutes';" && \
cd /opt/AleautosDjango && \
sudo bash scripts/fix_gunicorn_systemd.sh && \
sudo bash scripts/aumentar_ulimit.sh && \
echo "✅ Configuración completada. Verificando..." && \
sudo systemctl status gunicorn --no-pager -l | head -20
```

## 🔍 VERIFICACIÓN POST-CONFIGURACIÓN

```bash
# 1. Verificar límite del proceso Gunicorn
PID=$(systemctl show -p MainPID --value gunicorn)
echo "Límite de archivos:"
cat /proc/$PID/limits | grep "open files"

# 2. Ver archivos abiertos por Gunicorn
echo "Archivos abiertos:"
lsof -p $PID 2>/dev/null | grep -v WARNING | grep -v "can't stat" | wc -l

# 3. Ver conexiones de PostgreSQL
echo "Conexiones PostgreSQL:"
sudo -u postgres psql -d proyectoballena -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();"

# 4. Ver logs de Gunicorn
sudo journalctl -u gunicorn --since "5 minutes ago" --no-pager
```

## ⚠️ SI GUNICORN NO INICIA

```bash
# Ver logs detallados
sudo journalctl -u gunicorn -n 50 --no-pager

# Verificar configuración
sudo systemctl cat gunicorn

# Reiniciar manualmente
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
```

## 📝 QUÉ HACE CADA SCRIPT

### `fix_gunicorn_systemd.sh`
- Actualiza `/etc/systemd/system/gunicorn.service`
- Reduce workers: 3 → 2
- Agrega `LimitNOFILE=65536`
- Agrega `--max-requests 1000`
- Reinicia Gunicorn

### `aumentar_ulimit.sh`
- Actualiza `/etc/security/limits.conf`
- Aumenta límite para todos los usuarios
- Requiere logout/login para aplicar completamente

### `diagnostico_completo.sh`
- Muestra diagnóstico completo del sistema
- Filtra warnings de lsof
- Muestra top procesos con más archivos

