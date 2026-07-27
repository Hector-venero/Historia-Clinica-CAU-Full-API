-- Reconcilia la DB con init.sql para la edicion auditada de evoluciones
-- (arbol padre_id/version/activo). Ver TODO.md: "Permitir ediciones de
-- Historia auditadas".
--
-- Sin esta migracion, cualquier DB migrada (no creada desde cero con init.sql)
-- rompe con 1054 Unknown column al consultar evoluciones.

ALTER TABLE evoluciones
    ADD COLUMN padre_id INT NULL,
    ADD COLUMN version INT NOT NULL DEFAULT 1,
    ADD COLUMN activo TINYINT(1) NOT NULL DEFAULT 1,
    ADD CONSTRAINT fk_evoluciones_padre_id
        FOREIGN KEY (padre_id) REFERENCES evoluciones(id) ON DELETE CASCADE,
    ADD INDEX idx_evoluciones_padre_activo (padre_id, activo);
