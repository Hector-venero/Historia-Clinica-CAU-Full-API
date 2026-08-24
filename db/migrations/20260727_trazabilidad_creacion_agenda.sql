-- Trazabilidad de creacion en los eventos de agenda: QUIEN lo cargo y CUANDO.
-- Ver TODO.md: "Ver en la agenda quien creo cada evento y cuando".
--
-- Estado previo (inconsistente entre tablas):
--   turnos_grupales -> ya tenia creado_por + creado_en
--   ausencias       -> tenia creado_por, le faltaba creado_en
--   turnos          -> no tenia ninguno de los dos
--
-- OJO: turnos.usuario_id NO es quien cargo el turno, es el profesional al que
-- pertenece. Por eso hace falta una columna nueva y no alcanza con la existente.
--
-- Las columnas van NULL DEFAULT NULL a proposito. Con DEFAULT CURRENT_TIMESTAMP,
-- MySQL le estampa a TODAS las filas preexistentes la fecha en que corre la
-- migracion (verificado), lo que dejaria un dato falso con apariencia de valido.
-- Preferimos el campo vacio: los eventos historicos no tienen este dato y no es
-- recuperable, asi que se muestran como "sin registro".

-- Una clausula por sentencia: ver nota en 20260522_bfa_evoluciones_auditoria.sql

ALTER TABLE turnos ADD COLUMN creado_por INT NULL;
ALTER TABLE turnos ADD COLUMN creado_en TIMESTAMP NULL DEFAULT NULL;
ALTER TABLE turnos
    ADD CONSTRAINT fk_turnos_creado_por
        FOREIGN KEY (creado_por) REFERENCES usuarios(id);

ALTER TABLE ausencias ADD COLUMN creado_en TIMESTAMP NULL DEFAULT NULL;
