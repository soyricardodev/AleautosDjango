# 🚨 SOLUCIÓN URGENTE - EJECUTAR EN ESTE ORDEN

## 🔴 ERROR CRÍTICO ACTUAL: CAN'T START NEW THREAD

```
RuntimeError: can't start new thread
```

**El sistema no puede crear más threads.** Esto ocurre porque ASGI (UvicornWorker) crea demasiados threads.

### ⚡ SOLUCIÓN INMEDIATA (EJECUTAR PRIMERO):

```bash
# 1. Aumentar límite de threads (temporal)
echo 32768 | sudo tee /proc/sys/kernel/threads-max

# 2. Reducir workers de Gunicorn (URGENTE)
sudo systemctl edit gunicorn
```

**Pega esto en el editor:**
```ini
[Service]
ExecStart=
ExecStart=/opt/AleautosDjango/.venv/bin/gunicorn \
  --access-logfile - \
  -k uvicorn.workers.UvicornWorker \
  --workers 1 \
  --threads 8 \
  --limit-concurrency 100 \
  --timeout 120 \
  --bind unix:/run/gunicorn.sock \
  proyectoBallena.asgi:application
LimitNPROC=4096
LimitNOFILE=65536
TasksMax=4096
```

**Luego:**
```bash
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
```

**O usar el script automático:**
```bash
bash scripts/fix_thread_limit.sh
bash scripts/reducir_workers_gunicorn.sh
```

**💡 RECOMENDACIÓN: Si no necesitas async, cambia a WSGI** (ver `LEEME_PRIMERO_THREADS.md`)

Ver `SOLUCION_CANT_START_NEW_THREAD.md` o `LEEME_PRIMERO_THREADS.md` para más detalles.

---

## ⚠️ ERROR ANTERIOR: TIMEOUT EXPIRED

```
connection to server at "127.0.0.1", port 5432 failed: timeout expired
```

**PostgreSQL no está respondiendo** dentro del tiempo límite.

### ⚡ SOLUCIÓN INMEDIATA PARA TIMEOUT:

```bash
# 1. Verificar estado de PostgreSQL
bash scripts/verificar_postgres_docker.sh

# 2. Si está caído, iniciarlo
docker-compose up -d db

# 3. Si está activo pero no responde, reiniciarlo
docker-compose restart db

# 4. Reiniciar Gunicorn (para aplicar nuevo timeout de 30 segundos)
sudo systemctl restart gunicorn
```

**✅ Ya actualicé el timeout de 10 a 30 segundos en `settings.py`**

Ver `LEEME_PRIMERO_TIMEOUT.md` o `SOLUCION_TIMEOUT_POSTGRES.md` para más detalles.

---

## ⚠️ PROBLEMA CRÍTICO: OTRO PROCESO CON FUGA MASIVA

**PID 2167175 tiene 599,786 archivos abiertos** - ¡OTRA FUGA MASIVA!

Además, PostgreSQL en Docker tiene límite de 100 conexiones y está lleno.

---

## 🔄 OPCIÓN RÁPIDA: REINICIAR EL VPS

**Si tienes múltiples procesos problemáticos y quieres una solución inmediata:**

```bash
sudo reboot
```

**Después del reinicio**, ejecuta los pasos 5-8 de abajo para aplicar las correcciones permanentes.

Ver `GUIA_REINICIO_VPS.md` para detalles completos.

---

## ⚡ COMANDOS A EJECUTAR (Copiar y pegar en orden)

### 1. Matar el proceso problemático (INMEDIATO)
```bash
sudo kill -9 2167175
```

O usar el script automático:
```bash
sudo bash scripts/matar_proceso_fuga.sh 2167175
```

### 2. Aumentar límite temporalmente
```bash
ulimit -n 65536
```

### 3. Liberar conexiones de PostgreSQL (Docker)
```bash
bash scripts/liberar_conexiones_postgres_docker.sh
```

### 4. Reiniciar Gunicorn (para aplicar el código corregido)
```bash
sudo systemctl restart gunicorn
```

### 5. Aumentar límite de conexiones en PostgreSQL (PERMANENTE)

**Opción A: Usar docker-compose.yaml actualizado** (ya está modificado)
```bash
docker-compose down
docker-compose up -d db
```

**Opción B: Configurar manualmente**
```bash
sudo bash scripts/configurar_postgres_docker.sh
```

### 6. Configurar Gunicorn permanentemente
```bash
cd /opt/AleautosDjango
sudo bash scripts/fix_gunicorn_systemd.sh
```

### 7. Aumentar límite de archivos permanentemente
```bash
sudo bash scripts/aumentar_ulimit.sh
```

### 8. Verificar que se solucionó
```bash
bash scripts/diagnostico_completo.sh
```

---

## 📋 QUÉ HACE CADA PASO

**Paso 1**: Mata el worker con 599,786 archivos abiertos (fuga masiva)

**Paso 2**: Aumenta el límite de archivos abiertos temporalmente (efecto inmediato)

**Paso 3**: Libera conexiones inactivas de PostgreSQL en Docker

**Paso 4**: Reinicia Gunicorn para que cargue el código corregido (conexiones HTTP ahora se cierran)

**Paso 5**: Aumenta `max_connections` de PostgreSQL de 100 a 200 (evita "too many clients already")

**Paso 6**: 
- Actualiza tu servicio systemd de Gunicorn
- Reduce workers de 3 a 2
- Agrega `LimitNOFILE=65536`
- Agrega `--max-requests 1000` para reciclar workers
- Reinicia Gunicorn automáticamente

**Paso 7**: Configura el límite permanentemente en `/etc/security/limits.conf`

**Paso 8**: Verifica que todo esté funcionando correctamente

---

## ⚠️ IMPORTANTE

- **El código ya está corregido** - las conexiones HTTP ahora se cierran correctamente
- **docker-compose.yaml ya está actualizado** - `max_connections=200` configurado
- Después del **Paso 4**, Gunicorn cargará el código corregido
- Después del **Paso 5**, PostgreSQL aceptará hasta 200 conexiones simultáneas
- El script del **Paso 6** hace backup automático de tu configuración
- Si algo sale mal, puedes restaurar desde el backup

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

# Ver conexiones de PostgreSQL
bash scripts/liberar_conexiones_postgres_docker.sh
```

---

## 📚 DOCUMENTACIÓN COMPLETA

- `SOLUCION_POSTGRES_DOCKER.md` - Solución específica para PostgreSQL en Docker
- `SOLUCION_URGENTE_FUGA_MASIVA.md` - Detalles del problema de fuga de archivos
- `EJECUTAR_ESTOS_COMANDOS.md` - Guía detallada paso a paso
- `SOLUCION_PASO_A_PASO.md` - Explicación completa
- `SOLUCION_TOO_MANY_OPEN_FILES.md` - Solución técnica detallada

---

## 🎯 CAMBIOS APLICADOS EN EL CÓDIGO

✅ **Rifa/views.py** - `enviarWhatsapp()` ahora cierra conexiones HTTP  
✅ **Rifa/apis.py** - `testWhatsapp()` ahora cierra conexiones HTTP  
✅ **docker-compose.yaml** - `max_connections=200` configurado  
✅ **Scripts creados** - Para matar procesos problemáticos y liberar conexiones
