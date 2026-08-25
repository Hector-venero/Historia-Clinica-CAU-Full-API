-- Anclaje de evoluciones individuales en blockchain.
--
-- Hasta ahora solo se anclaba la historia consolidada. La ruta de verificacion
-- por evolucion existia pero comparaba el hash de la evolucion contra el recibo
-- de la historia: dos hashes distintos, asi que la TSA respondia failure siempre
-- y la pantalla mostraba "evolucion modificada" sobre evoluciones intactas. Se
-- habia dejado en 501 hasta poder hacerlo bien.
--
-- Una evolucion se sella por separado y guarda su propio recibo. Eso permite
-- probar la integridad de un acto medico puntual sin depender del estado de la
-- historia completa, que cambia cada vez que se carga una evolucion nueva.
--
-- Una clausula por sentencia: ver la nota en 20260522_bfa_evoluciones_auditoria.sql

-- La tabla pasa a alojar los dos tipos de anclaje, asi que el nombre con
-- "historia" quedaba enganhoso.
RENAME TABLE anclajes_historia TO anclajes_blockchain;

-- 'historia' | 'evolucion'. Las filas existentes son todas de historia.
ALTER TABLE anclajes_blockchain
    ADD COLUMN entidad_tipo VARCHAR(20) NOT NULL DEFAULT 'historia';

ALTER TABLE anclajes_blockchain ADD COLUMN evolucion_id INT NULL;

-- RESTRICT y no CASCADE, igual que el resto de la auditoria: borrar una
-- evolucion no puede llevarse la prueba de lo que se anclo.
ALTER TABLE anclajes_blockchain
    ADD CONSTRAINT fk_anclajes_evolucion
        FOREIGN KEY (evolucion_id) REFERENCES evoluciones(id) ON DELETE RESTRICT;

ALTER TABLE anclajes_blockchain
    ADD INDEX idx_anclajes_entidad (entidad_tipo, evolucion_id);
