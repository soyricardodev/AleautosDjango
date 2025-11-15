# SOLUCIÓN URGENTE: RuntimeError: can't start new thread

## 🔴 PROBLEMA CRÍTICO

El sistema ha alcanzado el límite de threads que puede crear. Esto ocurre cuando:
- Gunicorn con UvicornWorker (ASGI) crea demasiados threads
- Cada request que ejecuta código síncrono crea un thread
- El sistema no puede crear más threads

## ⚡ SOLUCIÓN INMEDIATA (EJECUTAR AHORA)

### 1. Verificar límite actual de threads
```bash
ulimit -u
cat /proc/sys/kernel/threads-max
ps -eLf | wc -l  # Threads actuales en uso
```

### 2. Reducir workers de Gunicorn (URGENTE)
```bash
sudo systemctl edit gunicorn
```

Agregar/modificar:
```ini
[Service]
ExecStart=
ExecStart=/opt/AleautosDjango/.venv/bin/gunicorn \
  --access-logfile - \
  -k uvicorn.workers.UvicornWorker \
  --workers 1 \
  --threads 4 \
  --bind unix:/run/gunicorn.sock \
  proyectoBallena.asgi:application
```

Luego:
```bash
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
```

### 3. Aumentar límite de threads del sistema
```bash
# Temporal (hasta reinicio)
echo 32768 | sudo tee /proc/sys/kernel/threads-max

# Permanente
echo "kernel.threads-max = 32768" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 4. Aumentar límite de procesos del usuario
```bash
# Ver límite actual
ulimit -u

# Temporal
ulimit -u 4096

# Permanente - agregar a /etc/security/limits.conf
sudo nano /etc/security/limits.conf
```

Agregar:
```
admin soft nproc 4096
admin hard nproc 8192
www-data soft nproc 4096
www-data hard nproc 8192
```

## 🔧 SOLUCIÓN PERMANENTE

### Opción 1: Cambiar a WSGI (RECOMENDADO si no necesitas async)

Si no estás usando características async de Django, cambia a WSGI:

```bash
sudo systemctl edit gunicorn
```

Cambiar a:
```ini
[Service]
ExecStart=
ExecStart=/opt/AleautosDjango/.venv/bin/gunicorn \
  --access-logfile - \
  --workers 2 \
  --threads 4 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --timeout 120 \
  --bind unix:/run/gunicorn.sock \
  proyectoBallena.wsgi:application
```

### Opción 2: Optimizar configuración ASGI

Si necesitas ASGI, limita threads:

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
```

### Opción 3: Configurar límites en systemd

```bash
sudo systemctl edit gunicorn
```

Agregar:
```ini
[Service]
LimitNPROC=4096
LimitNOFILE=65536
TasksMax=4096
```

## 📊 DIAGNÓSTICO

### Ver threads actuales
```bash
# Threads por proceso
ps -eLf | grep gunicorn | wc -l

# Threads del sistema
cat /proc/sys/kernel/threads-max
ps -eLf | wc -l

# Threads por PID específico
ps -T -p <PID> | wc -l
```

### Ver límites del proceso
```bash
# Límites del proceso Gunicorn
cat /proc/$(pgrep -f gunicorn | head -1)/limits | grep processes
```

## 🎯 RECOMENDACIÓN FINAL

**Para producción con alta carga:**
1. Cambiar a WSGI si no necesitas async
2. Usar 2 workers con 4 threads cada uno
3. Configurar `max-requests` para reciclar workers
4. Aumentar límites del sistema permanentemente

**Si necesitas ASGI:**
1. Usar solo 1 worker con más threads
2. Limitar concurrencia con `--limit-concurrency`
3. Optimizar código para evitar `sync_to_async` innecesario

