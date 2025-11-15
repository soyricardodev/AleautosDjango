# 📊 Resumen: max_connections en PostgreSQL Docker

## ✅ SÍ, puedes aumentar max_connections

Actualmente está en **200**, pero puedes aumentarlo según tu RAM.

## 🎯 Valores Recomendados por RAM

| RAM del VPS | max_connections | shared_buffers | work_mem |
|-------------|----------------|----------------|----------|
| 1GB         | 100            | 256MB          | 4MB      |
| 2GB         | 200-300        | 512MB          | 4MB      |
| 4GB         | 300-500        | 1GB            | 8MB      |
| 8GB         | 500-1000       | 2GB            | 8MB      |
| 16GB+       | 1000+          | 4GB            | 16MB     |

## 📝 Configuración Actualizada

Ya actualicé `docker-compose.yaml` a **300 conexiones** (óptimo para 2-4GB RAM):

```yaml
command: postgres -c max_connections=300 -c shared_buffers=512MB -c work_mem=4MB
```

## 🚀 Aplicar Cambios

```bash
docker-compose down
docker-compose up -d db
```

## ⚠️ Consideraciones

1. **No todas las conexiones están activas simultáneamente**
   - Django con `CONN_MAX_AGE=60` recicla conexiones
   - Solo necesitas suficientes para picos de tráfico

2. **Monitoreo**
   - Si nunca alcanzas el límite, no necesitas más
   - Si sigues teniendo "too many clients", el problema puede ser:
     - Conexiones no cerradas (ya corregido en el código)
     - `CONN_MAX_AGE` muy alto
     - Muchos workers de Gunicorn

3. **Límite máximo teórico**: 2,147,483,647 conexiones
   - **Límite práctico**: Depende de RAM y CPU
   - **Recomendado**: 100-500 para la mayoría de aplicaciones

## 📚 Documentación Completa

Ver `CONFIGURACION_POSTGRES_AVANZADA.md` para:
- Fórmulas de cálculo de memoria
- Configuraciones avanzadas
- Uso de PgBouncer para alto tráfico
- Monitoreo y verificación

