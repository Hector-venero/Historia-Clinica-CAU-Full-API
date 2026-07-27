-- Reconcilia la DB con init.sql para la edicion auditada de evoluciones
-- (arbol padre_id/version/activo), y para ausencias/observaciones en turnos
-- (individuales y grupales). Ver TODO.md: "Permitir ediciones de Historia
-- auditadas", "Poder marcar turnos como ausente", "Agregar campo
-- Observaciones en turnos (ademas de motivo)".
--
-- Sin esta migracion, cualquier DB migrada (no creada desde cero con init.sql)
-- rompe con 1054 Unknown column al consultar evoluciones/turnos/turnos_grupales.

ALTER TABLE evoluciones
    ADD COLUMN padre_id INT NULL,
    ADD COLUMN version INT NOT NULL DEFAULT 1,
    ADD COLUMN activo TINYINT(1) NOT NULL DEFAULT 1,
    ADD CONSTRAINT fk_evoluciones_padre_id
        FOREIGN KEY (padre_id) REFERENCES evoluciones(id) ON DELETE CASCADE,
    ADD INDEX idx_evoluciones_padre_activo (padre_id, activo);

ALTER TABLE turnos
    ADD COLUMN observaciones TEXT DEFAULT NULL,
    ADD COLUMN ausencia ENUM('con_aviso', 'sin_aviso') DEFAULT NULL;

ALTER TABLE turnos_grupales
    ADD COLUMN observaciones TEXT DEFAULT NULL,
    ADD COLUMN ausencia ENUM('con_aviso', 'sin_aviso') DEFAULT NULL;
