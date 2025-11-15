-- SCRIPT DE EMERGENCIA: Liberar TODAS las conexiones excepto la actual
-- ⚠️ ADVERTENCIA: Esto terminará TODAS las conexiones activas
-- Solo usar en caso de emergencia cuando el servidor está completamente bloqueado

-- 1. Ver todas las conexiones antes de terminar
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    state,
    now() - state_change AS idle_duration,
    query
FROM pg_stat_activity
WHERE datname = current_database()
ORDER BY state_change;

-- 2. TERMINAR TODAS las conexiones excepto la actual (EMERGENCIA)
-- ⚠️ Esto desconectará a todos los usuarios y aplicaciones
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = current_database()
AND pid <> pg_backend_pid();

-- 3. Verificar que se terminaron
SELECT count(*) as conexiones_restantes
FROM pg_stat_activity
WHERE datname = current_database();

-- 4. Ver el límite máximo de conexiones
SHOW max_connections;

-- 5. Si es necesario, aumentar el límite temporalmente (requiere reinicio)
-- ALTER SYSTEM SET max_connections = 200;
-- SELECT pg_reload_conf();

