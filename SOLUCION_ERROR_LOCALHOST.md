# Solución para Error "could not translate host name localhost"

## Problema
```
django.db.utils.OperationalError: could not translate host name "localhost" to address: System error
```

Este error puede ocurrir cuando:
1. El middleware está cerrando conexiones demasiado agresivamente
2. Hay problemas de resolución DNS
3. La configuración de `DB_HOST` no es correcta

## Soluciones

### Solución 1: Cambiar CONN_MAX_AGE a 60 segundos (RECOMENDADO)

Si el error persiste con `CONN_MAX_AGE = 0`, cambia a un valor intermedio:

En `proyectoBallena/settings.py`:
```python
"CONN_MAX_AGE": int(os.environ.get('DB_CONN_MAX_AGE') or "60"),  # Cambiar de 0 a 60
```

O establecer la variable de entorno:
```bash
export DB_CONN_MAX_AGE=60
```

### Solución 2: Usar IP en lugar de localhost

Si `DB_HOST` está configurado como `localhost`, cambiar a `127.0.0.1`:

En tu archivo `.env` o variables de entorno:
```bash
DB_HOST=127.0.0.1  # En lugar de localhost
```

### Solución 3: Desactivar temporalmente el middleware

Si el problema persiste, puedes comentar temporalmente el middleware:

En `proyectoBallena/settings.py`:
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
     'django_session_timeout.middleware.SessionTimeoutMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'Rifa.middleware.CloseDBConnectionsMiddleware',  # COMENTAR TEMPORALMENTE
]
```

Y usar `CONN_MAX_AGE = 60` en su lugar.

### Solución 4: Verificar configuración de red

```bash
# Verificar que localhost resuelve correctamente
ping localhost
nslookup localhost

# Verificar que PostgreSQL está escuchando
netstat -tlnp | grep 5432
# O
ss -tlnp | grep 5432
```

## Recomendación Final

**Para producción**: Usar `CONN_MAX_AGE = 60` en lugar de `0`. Esto:
- Cierra conexiones después de 60 segundos de inactividad
- Evita problemas de reconexión
- Sigue previniendo la acumulación de conexiones
- Es más estable que cerrar después de cada request

