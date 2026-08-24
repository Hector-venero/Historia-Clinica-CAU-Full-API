-- ==============================================
--  RESET DE DESARROLLO — DESTRUCTIVO
-- ==============================================
--
--   ⚠️  ESTE SCRIPT BORRA TODAS LAS TABLAS, INCLUIDAS LAS HISTORIAS CLINICAS
--   ⚠️  Y SU RASTRO DE AUDITORIA EN BLOCKCHAIN. NO TIENE VUELTA ATRAS.
--
-- Estaba dentro de init.sql, que ademas hace CREATE DATABASE IF NOT EXISTS y
-- por eso parecia un script de setup inofensivo. Se separo justamente para que
-- borrar la base sea siempre un acto deliberado.
--
-- Uso (solo desarrollo, nunca produccion):
--
--   docker compose exec -T db mysql -uroot -p"$MYSQL_ROOT_PASSWORD" < db/dev_reset.sql
--   docker compose exec -T db mysql -uroot -p"$MYSQL_ROOT_PASSWORD" < db/init.sql
--
-- Alternativa mas limpia en desarrollo: docker compose down -v, que descarta el
-- volumen db_data y hace que Docker vuelva a correr init.sql desde cero.

USE hc_bfa;

-- Se desactivan las FK para poder borrar sin importar el orden. Las FKs de
-- auditoria son RESTRICT a proposito (ver db/migrations/), asi que sin esto
-- el DROP fallaria.
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS auditorias_blockchain;
DROP TABLE IF EXISTS historias;
DROP TABLE IF EXISTS turnos;
DROP TABLE IF EXISTS evolucion_archivos;
DROP TABLE IF EXISTS evoluciones;
DROP TABLE IF EXISTS pacientes;
DROP TABLE IF EXISTS usuarios;
DROP TABLE IF EXISTS ausencias;
DROP TABLE IF EXISTS disponibilidades;
DROP TABLE IF EXISTS grupos_profesionales;
DROP TABLE IF EXISTS grupo_miembros;

-- Tablas incorporadas desde el fork
DROP TABLE IF EXISTS turnos_grupales;
DROP TABLE IF EXISTS comunicados;
DROP TABLE IF EXISTS grupo_posteos;
DROP TABLE IF EXISTS recetas_electronicas;

-- Tracking de migraciones: si se borra el esquema hay que borrarlo tambien,
-- si no migrate.py cree que ya aplico todo sobre una base vacia.
DROP TABLE IF EXISTS schema_migrations;

SET FOREIGN_KEY_CHECKS = 1;
