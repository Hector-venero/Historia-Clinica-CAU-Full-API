-- Marca de grupo de rehabilitacion.
--
-- La columna estaba en el init.sql del fork pero nunca tuvo migracion, igual
-- que habia pasado con 'Domingo' en disponibilidades. En una base migrada (no
-- recreada desde cero) el listado de turnos grupales fallaba con
-- 1054 "Unknown column 'gp.es_rehabilitacion' in 'field list'".
--
-- Distingue los grupos de rehabilitacion, que en la agenda se muestran en su
-- propio modulo y con reglas de cupo distintas a las de un grupo comun.

ALTER TABLE grupos_profesionales ADD COLUMN es_rehabilitacion TINYINT(1) NOT NULL DEFAULT 0;
