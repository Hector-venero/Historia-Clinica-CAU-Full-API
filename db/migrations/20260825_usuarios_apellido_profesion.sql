-- Columnas de identidad profesional que quedaron sin migracion.
--
-- `apellido` y `profesion` se agregaron a init.sql en el commit del modulo de
-- recetas (bffc6de2) pero nunca tuvieron migracion. En cualquier base creada
-- antes de ese commit no existen, y el modulo de recetas las lee: emitir
-- terminaba en 1054 "Unknown column 'apellido'".
--
-- `apellido` ademas es obligatoria para el proveedor: _validar_payload() la
-- exige y solo se deduce del nombre completo como fallback, asi que con un
-- nombre de una sola palabra no hay de donde sacarla.
--
-- Es el tercer caso del mismo patron, despues del valor 'Domingo' en
-- disponibilidades y de grupos_profesionales.es_rehabilitacion. Los tres los
-- detecta ahora scripts/comparar_esquemas.sh.
--
-- Una clausula por sentencia: ver la nota en 20260522_bfa_evoluciones_auditoria.sql

ALTER TABLE usuarios ADD COLUMN apellido VARCHAR(100) DEFAULT NULL;
ALTER TABLE usuarios ADD COLUMN profesion VARCHAR(100) DEFAULT NULL;
