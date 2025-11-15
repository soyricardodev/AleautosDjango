# 🚨 URGENTE: RuntimeError: can't start new thread

## ⚡ ACCIÓN INMEDIATA

El sistema no puede crear más threads. Ejecuta estos comandos AHORA:

```bash
# 1. Aumentar límite de threads (temporal)
echo 32768 | sudo tee /proc/sys/kernel/threads-max

# 2. Reducir workers de Gunicorn (URGENTE)
sudo systemctl edit gunicorn
```

Pega esto en el editor:
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

Luego:
```bash
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
```

## 🔧 SOLUCIÓN PERMANENTE

### Opción 1: Usar scripts automáticos
```bash
./scripts/fix_thread_limit.sh
./scripts/reducir_workers_gunicorn.sh
```

### Opción 2: Cambiar a WSGI (MEJOR si no necesitas async)

Si no usas características async, cambia a WSGI:

```bash
sudo systemctl edit gunicorn
```

Pega esto:
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
LimitNPROC=4096
LimitNOFILE=65536
TasksMax=4096
```

Luego:
```bash
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
```

## 📊 VERIFICAR

```bash
# Ver threads actuales
ps -eLf | grep gunicorn | wc -l

# Ver límites
ulimit -u
cat /proc/sys/kernel/threads-max

# Estado de Gunicorn
sudo systemctl status gunicorn
```

## ⚠️ IMPORTANTE

- **ASGI crea más threads** que WSGI
- Si no necesitas async, **usa WSGI**
- Reduce workers si el problema persiste
- Aumenta límites del sistema permanentemente

Ver `SOLUCION_CANT_START_NEW_THREAD.md` para más detalles.

