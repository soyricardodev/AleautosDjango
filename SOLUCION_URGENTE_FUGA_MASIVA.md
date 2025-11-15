# 🚨 EMERGENCIA: Fuga Masiva de Archivos Abiertos

## ⚠️ PROBLEMA CRÍTICO DETECTADO

**Un worker de Gunicorn (PID 2117153) tiene 488,868 archivos abiertos**

Esto es extremadamente anormal y indica una **fuga masiva** de descriptores de archivo.

## ⚡ ACCIÓN INMEDIATA (EJECUTAR AHORA)

### Paso 1: Matar el proceso problemático
```bash
# Opción A: Usar el script automático
sudo bash scripts/matar_worker_problematico.sh

# Opción B: Matar manualmente
sudo kill -9 2117153
```

### Paso 2: Reiniciar Gunicorn completamente
```bash
sudo systemctl restart gunicorn
```

### Paso 3: Aumentar límite temporalmente
```bash
ulimit -n 65536
```

### Paso 4: Verificar que se solucionó
```bash
bash scripts/diagnostico_completo.sh
```

## 🔍 POSIBLES CAUSAS

1. **Conexiones HTTP no cerradas** (`http.client.HTTPConnection` en `Rifa/views.py` y `Rifa/apis.py`)
2. **Conexiones de base de datos no cerradas** (aunque ya se implementó middleware)
3. **Loop infinito abriendo archivos/conexiones**
4. **Sockets no cerrados**

## 🔧 SOLUCIÓN PERMANENTE

### 1. Verificar y corregir conexiones HTTP

Revisar que todas las conexiones HTTP se cierren correctamente:

**En `Rifa/views.py` y `Rifa/apis.py`:**
- Asegurar que `conn.close()` se llame siempre, incluso en caso de error
- Usar `try/finally` o context managers

### 2. Configurar Gunicorn correctamente

```bash
sudo bash scripts/fix_gunicorn_systemd.sh
```

### 3. Aumentar límite permanentemente

```bash
sudo bash scripts/aumentar_ulimit.sh
```

### 4. Agregar monitoreo

Crear un script de monitoreo que alerte cuando un proceso tenga más de 10,000 archivos abiertos.

## 📊 MONITOREO CONTINUO

```bash
# Verificar archivos abiertos por Gunicorn cada minuto
watch -n 60 'lsof -p $(pgrep -f gunicorn | head -1) 2>/dev/null | grep -v WARNING | wc -l'
```

## 🎯 OBJETIVO

- Cada worker de Gunicorn debe tener **< 1,000 archivos abiertos** normalmente
- Si un worker supera **10,000 archivos**, hay una fuga y debe reiniciarse

