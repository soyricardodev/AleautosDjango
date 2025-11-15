# Comandos Rápidos para Diagnóstico

## Conteo de Archivos Abiertos (Sin Warnings)

```bash
# Conteo total sin warnings
lsof 2>/dev/null | grep -v "WARNING" | grep -v "can't stat" | grep -v "no pwd entry" | wc -l

# O usar el script de diagnóstico completo
bash scripts/diagnostico_completo.sh
```

## Ver Archivos por Proceso Específico

```bash
# Por PID de Gunicorn
PID=$(pgrep -f gunicorn | head -1)
lsof -p $PID 2>/dev/null | grep -v "WARNING" | grep -v "can't stat" | wc -l

# Por nombre de proceso
lsof -c gunicorn 2>/dev/null | grep -v "WARNING" | grep -v "can't stat" | wc -l
```

## Ver Límites Actuales

```bash
# Límite del usuario actual
ulimit -n

# Límite de un proceso específico
cat /proc/$(pgrep -f gunicorn | head -1)/limits | grep "open files"

# Límite máximo del sistema
cat /proc/sys/fs/file-max
```

## Top Procesos con Más Archivos

```bash
# Top 10 procesos (sin warnings)
lsof 2>/dev/null | grep -v "WARNING" | grep -v "can't stat" | grep -v "no pwd entry" | \
    awk '{print $2}' | sort | uniq -c | sort -rn | head -10
```

## Conexiones de PostgreSQL

```bash
# Contar conexiones activas
psql -U postgres -d proyectoballena -t -c \
  "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();"

# Ver todas las conexiones
psql -U postgres -d proyectoballena -c \
  "SELECT pid, usename, application_name, state, query_start FROM pg_stat_activity WHERE datname = current_database();"
```

## Aumentar Límite Rápidamente

```bash
# Temporal (solo esta sesión)
ulimit -n 65536

# Verificar
ulimit -n

# Permanente (requiere logout/login o reiniciar)
sudo bash scripts/aumentar_ulimit.sh
```

