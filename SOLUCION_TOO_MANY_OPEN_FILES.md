# Solución para Error "Too many open files"

## Problema
```
OSError: [Errno 24] Too many open files
django.db.utils.OperationalError: connection to server at "127.0.0.1", port 5432 failed: could not create socket: Too many open files
```

Este error indica que el sistema ha alcanzado el límite de archivos abiertos (file descriptors).

## Soluciones Inmediatas

### Solución 1: Aumentar el límite de archivos abiertos (TEMPORAL)

```bash
# Ver el límite actual
ulimit -n

# Aumentar temporalmente (solo para la sesión actual)
ulimit -n 65536

# Verificar que se aplicó
ulimit -n
```

### Solución 2: Aumentar el límite permanentemente

#### Para el usuario actual:
```bash
# Editar ~/.bashrc o ~/.profile
echo "ulimit -n 65536" >> ~/.bashrc
source ~/.bashrc
```

#### Para todo el sistema (requiere root):
```bash
# Editar /etc/security/limits.conf
sudo nano /etc/security/limits.conf

# Agregar estas líneas:
* soft nofile 65536
* hard nofile 65536
root soft nofile 65536
root hard nofile 65536

# Reiniciar o hacer logout/login
```

#### Para systemd (si Gunicorn corre como servicio):
```bash
# Crear o editar /etc/systemd/system/gunicorn.service
sudo nano /etc/systemd/system/gunicorn.service

# Agregar en la sección [Service]:
LimitNOFILE=65536

# Recargar y reiniciar
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
```

### Solución 3: Reducir Workers de Gunicorn

Si no puedes aumentar el límite, reduce el número de workers:

En `docker/supervisord.conf` o donde esté configurado Gunicorn:
```ini
[program:gunicorn]
command=gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 2 proyectoBallena.wsgi
# Reducir de 3 a 2 workers (o incluso 1 si es necesario)
```

### Solución 4: Verificar y cerrar archivos abiertos

```bash
# Ver cuántos archivos tiene abiertos cada proceso
lsof | wc -l

# Ver archivos abiertos por Gunicorn
lsof -p $(pgrep -f gunicorn) | wc -l

# Ver archivos abiertos por PostgreSQL
lsof -p $(pgrep -f postgres) | wc -l

# Ver el proceso con más archivos abiertos
lsof | awk '{print $2}' | sort | uniq -c | sort -rn | head -10
```

## Cambios en el Código

### 1. Reducir Workers en supervisord.conf

Ya se ha actualizado para usar menos workers.

### 2. Configurar ulimit en supervisord

Agregar configuración de ulimit en supervisord.conf.

## Comandos de Diagnóstico

```bash
# Ver límite actual
ulimit -n

# Ver límite de todos los usuarios
cat /proc/sys/fs/file-max

# Ver archivos abiertos actualmente
cat /proc/sys/fs/file-nr

# Ver archivos abiertos por proceso específico
lsof -p <PID> | wc -l

# Ver todos los límites del sistema
cat /proc/sys/fs/file-max
```

## Prevención

1. **Reducir workers de Gunicorn**: Menos workers = menos conexiones simultáneas
2. **Aumentar ulimit permanentemente**: Configurar en `/etc/security/limits.conf`
3. **Monitorear archivos abiertos**: Usar `lsof` regularmente
4. **Optimizar código**: Cerrar archivos y conexiones explícitamente

