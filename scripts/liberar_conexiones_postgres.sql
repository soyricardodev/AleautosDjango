-- Script SQL para liberar conexiones en PostgreSQL
-- Ejecutar como superusuario o usuario con permisos

-- 1. Ver todas las conexiones actuales
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    state,
    state_change,
    query_start,
    now() - state_change AS idle_duration,
    query
FROM pg_stat_activity
WHERE datname = current_database()
ORDER BY state_change;

-- 2. Ver solo conexiones inactivas (idle) de más de 5 minutos
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
AND pid <> pg_backend_pid()
AND state = 'idle'
AND state_change < now() - interval '5 minutes'
ORDER BY state_change;

-- 3. TERMINAR conexiones inactivas de más de 5 minutos (SEGURO)
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = current_database()
AND pid <> pg_backend_pid()
AND state = 'idle'
AND state_change < now() - interval '5 minutes';

-- 4. TERMINAR TODAS las conexiones excepto la actual (CUIDADO - solo en emergencias)
-- SELECT pg_terminate_backend(pid)
-- FROM pg_stat_activity
-- WHERE datname = current_database()
-- AND pid <> pg_backend_pid();

-- 5. Ver el límite máximo de conexiones
SHOW max_connections;

-- 6. Ver cuántas conexiones están en uso
SELECT count(*) as conexiones_activas
FROM pg_stat_activity
WHERE datname = current_database();

-- 7. Ver conexiones por aplicación
SELECT 
    application_name,
    count(*) as cantidad,
    count(*) FILTER (WHERE state = 'active') as activas,
    count(*) FILTER (WHERE state = 'idle') as inactivas
FROM pg_stat_activity
WHERE datname = current_database()
GROUP BY application_name
ORDER BY cantidad DESC;

