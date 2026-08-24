-- Reconcilia la DB con init.sql para la edicion auditada de evoluciones
-- (arbol padre_id/version/activo), y para ausencias/observaciones en turnos
-- (individuales y grupales). Ver TODO.md: "Permitir ediciones de Historia
-- auditadas", "Poder marcar turnos como ausente", "Agregar campo
-- Observaciones en turnos (ademas de motivo)".
--
-- Sin esta migracion, cualquier DB migrada (no creada desde cero con init.sql)
-- rompe con 1054 Unknown column al consultar evoluciones/turnos/turnos_grupales.

-- Una clausula por sentencia: ver nota en 20260522_bfa_evoluciones_auditoria.sql

ALTER TABLE evoluciones ADD COLUMN padre_id INT NULL;
ALTER TABLE evoluciones ADD COLUMN version INT NOT NULL DEFAULT 1;
ALTER TABLE evoluciones ADD COLUMN activo TINYINT(1) NOT NULL DEFAULT 1;

-- ON DELETE RESTRICT, no CASCADE: padre_id es un arbol de versiones de una
-- evolucion clinica. Con CASCADE, borrar la version original se llevaba en
-- silencio todo el historial de ediciones, que es justamente la evidencia que
-- la edicion auditada tiene que preservar.
ALTER TABLE evoluciones
    ADD CONSTRAINT fk_evoluciones_padre_id
        FOREIGN KEY (padre_id) REFERENCES evoluciones(id) ON DELETE RESTRICT;

ALTER TABLE evoluciones ADD INDEX idx_evoluciones_padre_activo (padre_id, activo);

ALTER TABLE turnos ADD COLUMN observaciones TEXT DEFAULT NULL;
ALTER TABLE turnos ADD COLUMN ausencia ENUM('con_aviso', 'sin_aviso') DEFAULT NULL;

ALTER TABLE turnos_grupales ADD COLUMN observaciones TEXT DEFAULT NULL;
ALTER TABLE turnos_grupales ADD COLUMN ausencia ENUM('con_aviso', 'sin_aviso') DEFAULT NULL;
