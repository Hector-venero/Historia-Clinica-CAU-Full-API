-- Anclaje BFA de evoluciones individuales y auditoria por entidad.
--
-- Una clausula por sentencia a proposito: MySQL evalua un ALTER compuesto de
-- forma atomica, asi que si una sola clausula choca con "ya existe", se pierde
-- el statement entero. Con ALTERs compuestos, el runner no puede distinguir
-- "ya estaba" de "no se aplico nada" y la migracion queda marcada como
-- completa con columnas faltantes.

ALTER TABLE historias ADD COLUMN fecha_anclaje_bfa DATETIME DEFAULT NULL;
ALTER TABLE historias ADD COLUMN estado_bfa VARCHAR(20) NOT NULL DEFAULT 'pendiente';

ALTER TABLE evoluciones ADD COLUMN hash_local CHAR(64) DEFAULT NULL;
ALTER TABLE evoluciones ADD COLUMN tx_hash VARCHAR(100) DEFAULT NULL;
ALTER TABLE evoluciones ADD COLUMN fecha_anclaje_bfa DATETIME DEFAULT NULL;
ALTER TABLE evoluciones ADD COLUMN estado_bfa VARCHAR(20) NOT NULL DEFAULT 'pendiente';

-- historia_id pasa a NULL para poder auditar una evolucion suelta.
ALTER TABLE auditorias_blockchain MODIFY historia_id INT NULL;
ALTER TABLE auditorias_blockchain ADD COLUMN evolucion_id INT NULL;
ALTER TABLE auditorias_blockchain ADD COLUMN entidad_tipo VARCHAR(20) NOT NULL DEFAULT 'historia';
ALTER TABLE auditorias_blockchain ADD COLUMN entidad_id INT NULL;
ALTER TABLE auditorias_blockchain ADD COLUMN tx_hash VARCHAR(100) DEFAULT NULL;

-- ON DELETE RESTRICT, no CASCADE: esta tabla es el rastro de auditoria de lo
-- que se anclo en blockchain. Con CASCADE, borrar una evolucion borraba su
-- propia prueba de integridad, que es justamente lo que el sistema existe para
-- conservar.
ALTER TABLE auditorias_blockchain
    ADD CONSTRAINT fk_auditorias_blockchain_evolucion
        FOREIGN KEY (evolucion_id) REFERENCES evoluciones(id) ON DELETE RESTRICT;
