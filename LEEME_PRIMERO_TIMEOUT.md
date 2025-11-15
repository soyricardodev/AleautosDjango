# 🚨 SOLUCIÓN URGENTE - Timeout Expired

## ⚠️ ERROR ACTUAL

```
connection to server at "127.0.0.1", port 5432 failed: timeout expired
```

PostgreSQL **no está respondiendo** dentro del tiempo límite.

---

## ⚡ SOLUCIÓN INMEDIATA (Ejecutar AHORA)

### 1. Verificar estado de PostgreSQL
```bash
bash scripts/verificar_postgres_docker.sh
```

### 2. Si PostgreSQL está caído, iniciarlo
```bash
docker-compose up -d db
```

### 3. Si PostgreSQL está activo pero no responde, reiniciarlo
```bash
docker-compose restart db
```

### 4. Esperar 10 segundos y verificar nuevamente
```bash
sleep 10
bash scripts/verificar_postgres_docker.sh
```

### 5. Reiniciar Gunicorn para aplicar el nuevo timeout
```bash
sudo systemctl restart gunicorn
```

---

## ✅ CAMBIOS APLICADOS

1. **Timeout aumentado**: De 10 a 30 segundos en `settings.py`
2. **Script de verificación**: `scripts/verificar_postgres_docker.sh` creado
3. **Documentación**: `SOLUCION_TIMEOUT_POSTGRES.md` creada

---

## 🔍 DIAGNÓSTICO

Si el problema persiste después de reiniciar:

```bash
# Ver logs de PostgreSQL
docker logs <nombre_contenedor_postgres> --tail 100

# Verificar conexiones bloqueadas
docker exec <nombre_contenedor> psql -U postgres -d proyectoballena -c "
SELECT 
    pid,
    state,
    wait_event_type,
    wait_event,
    now() - state_change AS idle_duration,
    LEFT(query, 50) as query_preview
FROM pg_stat_activity
WHERE datname = current_database()
AND state != 'idle'
ORDER BY state_change;
"
```

---

## 📚 DOCUMENTACIÓN COMPLETA

Ver `SOLUCION_TIMEOUT_POSTGRES.md` para:
- Diagnóstico completo
- Soluciones adicionales
- Prevención de futuros problemas

