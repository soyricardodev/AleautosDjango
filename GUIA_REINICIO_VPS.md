# 🔄 Guía: Reiniciar VPS para Solucionar Problemas

## ✅ SÍ, Reiniciar el VPS Ayuda Inmediatamente

Reiniciar el VPS:
- ✅ Mata todos los procesos con fuga masiva
- ✅ Libera todas las conexiones de PostgreSQL
- ✅ Libera todos los archivos abiertos
- ✅ Reinicia todos los servicios con configuraciones limpias

**PERO**: Es una solución **temporal**. Los problemas volverán si no aplicas las correcciones permanentes.

---

## 📋 QUÉ HACER ANTES DEL REINICIO

### 1. Asegurar que los cambios estén guardados

```bash
# Verificar que docker-compose.yaml tiene max_connections=200
cat docker-compose.yaml | grep max_connections
```

### 2. (Opcional) Hacer backup de la base de datos

```bash
# Si quieres estar seguro
docker exec <nombre_contenedor_postgres> pg_dump -U postgres proyectoballena > backup_$(date +%Y%m%d_%H%M%S).sql
```

---

## 🔄 REINICIAR EL VPS

```bash
sudo reboot
```

O desde el panel de control de tu proveedor de VPS.

---

## 📋 QUÉ HACER DESPUÉS DEL REINICIO

### 1. Esperar a que todos los servicios inicien (2-3 minutos)

```bash
# Verificar que Docker está corriendo
docker ps

# Verificar que Gunicorn está corriendo
sudo systemctl status gunicorn
```

### 2. Aplicar configuración de PostgreSQL (CRÍTICO)

```bash
cd /opt/AleautosDjango  # O donde esté tu proyecto
docker-compose down
docker-compose up -d db
```

Esto aplica `max_connections=200` en PostgreSQL.

### 3. Configurar Gunicorn permanentemente

```bash
cd /opt/AleautosDjango
sudo bash scripts/fix_gunicorn_systemd.sh
```

### 4. Aumentar límite de archivos permanentemente

```bash
sudo bash scripts/aumentar_ulimit.sh
```

**IMPORTANTE**: Después de este paso, es recomendable hacer **logout y login** para que el límite se aplique completamente.

### 5. Verificar que todo funciona

```bash
# Verificar límite de archivos
ulimit -n
# Debe mostrar 65536

# Verificar estado de Gunicorn
sudo systemctl status gunicorn

# Verificar conexiones de PostgreSQL
bash scripts/liberar_conexiones_postgres_docker.sh

# Diagnóstico completo
bash scripts/diagnostico_completo.sh
```

---

## ⚠️ IMPORTANTE: Correcciones Permanentes

Después del reinicio, **DEBES** aplicar estas correcciones para que los problemas no vuelvan:

1. ✅ **docker-compose.yaml** - Ya tiene `max_connections=200` (aplicar con `docker-compose up -d db`)
2. ✅ **Código corregido** - Las conexiones HTTP ya se cierran correctamente (ya está en el código)
3. ✅ **Gunicorn configurado** - Con `LimitNOFILE=65536` y `--max-requests 1000` (aplicar con el script)
4. ✅ **ulimit aumentado** - Límite de archivos a 65536 (aplicar con el script)

---

## 🎯 ORDEN RECOMENDADO DESPUÉS DEL REINICIO

```bash
# 1. Esperar 2-3 minutos a que todo inicie
sleep 180

# 2. Aplicar configuración de PostgreSQL
cd /opt/AleautosDjango
docker-compose down
docker-compose up -d db

# 3. Configurar Gunicorn
sudo bash scripts/fix_gunicorn_systemd.sh

# 4. Aumentar ulimit
sudo bash scripts/aumentar_ulimit.sh

# 5. Logout y login (o simplemente ejecutar)
ulimit -n 65536

# 6. Verificar
bash scripts/diagnostico_completo.sh
```

---

## ✅ VENTAJAS DEL REINICIO

- Solución inmediata a todos los problemas actuales
- Todos los servicios inician limpios
- No necesitas matar procesos manualmente
- Base limpia para aplicar correcciones permanentes

---

## ⚠️ DESVENTAJAS DEL REINICIO

- **Temporal**: Los problemas volverán si no aplicas las correcciones permanentes
- **Downtime**: El sitio estará caído durante el reinicio (1-2 minutos)
- **Pérdida de sesiones**: Los usuarios activos perderán sus sesiones

---

## 💡 RECOMENDACIÓN

**SÍ, reinicia el VPS** si:
- ✅ Tienes múltiples procesos con fuga masiva
- ✅ El sistema está muy lento
- ✅ Necesitas una solución inmediata

**PERO** después del reinicio, **aplica todas las correcciones permanentes** para que los problemas no vuelvan.

Si prefieres no reiniciar, puedes seguir los pasos de `LEEME_PRIMERO.md` para solucionar sin reinicio.

