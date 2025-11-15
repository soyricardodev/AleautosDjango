# 🚨 SOLUCIÓN URGENTE - Too Many Open Files

## Problema Actual
```
OSError: [Errno 24] Too many open files
could not create socket: Too many open files
```

## ⚡ SOLUCIÓN INMEDIATA (Ejecutar AHORA)

### Paso 1: Aumentar límite temporalmente
```bash
ulimit -n 65536
```

### Paso 2: Liberar conexiones de PostgreSQL
```bash
# Opción A: Comando Django
python manage.py close_db_connections --force

# Opción B: SQL directo (más rápido)
psql -U postgres -d proyectoballena -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = current_database()
AND pid <> pg_backend_pid()
AND state = 'idle'
AND state_change < now() - interval '2 minutes';
"
```

### Paso 3: Reiniciar Gunicorn
```bash
sudo systemctl restart gunicorn
# O
sudo supervisorctl restart gunicorn
```

## 🔧 SOLUCIÓN PERMANENTE

### 1. Aumentar ulimit permanentemente
```bash
sudo bash scripts/aumentar_ulimit.sh
```

### 2. Configurar systemd (si aplica)
```bash
sudo bash scripts/fix_ulimit_systemd.sh
```

### 3. Verificar configuración
```bash
bash scripts/verificar_archivos_abiertos.sh
```

## 📋 Cambios Aplicados en el Código

✅ **Workers de Gunicorn reducidos**: De 3 a 2  
✅ **CONN_MAX_AGE**: Configurado en 60 segundos  
✅ **Middleware inteligente**: Cierra solo conexiones inactivas  
✅ **Optimizaciones de código**: Menos consultas = menos conexiones  
✅ **Max-requests en Gunicorn**: Recicla workers cada 1000 requests  

## 🎯 Verificación

Después de aplicar las soluciones, verifica:

```bash
# Diagnóstico completo (recomendado)
bash scripts/diagnostico_completo.sh

# O verificación manual:
# 1. Límite de archivos
ulimit -n
# Debe mostrar 65536 o más

# 2. Archivos abiertos por Gunicorn (sin warnings)
lsof -p $(pgrep -f gunicorn | head -1) 2>/dev/null | grep -v WARNING | wc -l
# Debe ser razonable (< 1000 por worker)

# 3. Total de archivos abiertos (sin warnings)
lsof 2>/dev/null | grep -v WARNING | grep -v "can't stat" | grep -v "no pwd entry" | wc -l

# 4. Conexiones de PostgreSQL
psql -U postgres -d proyectoballena -c "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();"
# Debe ser < 50 normalmente
```

## 📚 Documentación Completa

- `SOLUCION_TOO_MANY_OPEN_FILES.md` - Guía detallada
- `INSTRUCCIONES_LIBERAR_CONEXIONES.md` - Todas las soluciones
- `scripts/verificar_archivos_abiertos.sh` - Diagnóstico
- `scripts/aumentar_ulimit.sh` - Aumentar límite
- `scripts/fix_ulimit_systemd.sh` - Configurar systemd

## ⚠️ Si el Problema Persiste

1. **Reducir workers a 1 temporalmente**:
   ```bash
   # Editar supervisord.conf o systemd service
   # Cambiar --workers 2 a --workers 1
   ```

2. **Aumentar ulimit aún más**:
   ```bash
   ulimit -n 131072
   ```

3. **Revisar otros procesos**:
   ```bash
   lsof | awk '{print $2}' | sort | uniq -c | sort -rn | head -20
   ```

