-- Registro append-only de anclajes en blockchain.
--
-- Problema que resuelve: `historias` guarda un solo par (hash_local, tx_hash).
-- Cada vez que se recalcula la historia consolidada (o sea, cada vez que se
-- carga o edita una evolucion) el hash cambia y pisa al anterior, dejando el
-- recibo de la TSA apuntando a un hash que ya no existe en ningun lado. La
-- prueba de que en tal fecha se sello tal contenido se pierde.
--
-- Ademas el payload del hash esta versionado (ver utils/hashing.py): sin
-- guardar con que version se calculo cada anclaje, un cambio de payload haria
-- irreproducibles todos los hashes anteriores.
--
-- Esta tabla nunca se actualiza ni se borra: cada sellado agrega una fila. La
-- verificacion usa el hash y el recibo de la fila, no el estado actual de
-- `historias`, asi que un anclaje viejo sigue verificando aunque la historia
-- haya seguido creciendo.

CREATE TABLE IF NOT EXISTS anclajes_historia (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    historia_id INT NULL,

    -- Hash sellado y version del payload con que se calculo.
    hash_local CHAR(64) NOT NULL,
    hash_version INT NOT NULL DEFAULT 2,

    -- Recibos de la TSA: temporary_rd al sellar, permanent_rd al verificar.
    recibo_tsa VARCHAR(512) NOT NULL,
    permanent_rd VARCHAR(512) NULL,

    -- pendiente: sellado pero todavia sin confirmar en blockchain
    -- confirmado: la TSA devolvio success
    -- error: la TSA rechazo el par (hash, recibo)
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    block_number BIGINT NULL,
    attestation_time VARCHAR(64) NULL,

    usuario VARCHAR(100) NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    verificado_en TIMESTAMP NULL DEFAULT NULL,

    -- RESTRICT, igual que el resto de la auditoria: borrar un paciente no
    -- puede llevarse la prueba de lo que se anclo.
    CONSTRAINT fk_anclajes_paciente FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_anclajes_paciente ON anclajes_historia (paciente_id, creado_en);
CREATE INDEX idx_anclajes_hash ON anclajes_historia (hash_local);


-- Version del payload con que se calculo el hash vigente de cada historia.
-- Las historias que ya existen se marcan como v1: se calcularon antes de que
-- el payload incorporara `indicaciones` y el filtro por activo.
ALTER TABLE historias ADD COLUMN hash_version INT NOT NULL DEFAULT 1;


-- Backfill: las historias ya ancladas pasan a tener su fila de anclaje, para
-- que la verificacion pueda dejar de leer de `historias` sin perder nada.
-- Se marcan como v1 y estado 'pendiente' (no sabemos si llegaron a
-- confirmarse; la proxima verificacion lo resuelve).
INSERT INTO anclajes_historia
    (paciente_id, historia_id, hash_local, hash_version, recibo_tsa, estado, creado_en)
SELECT h.paciente_id, h.id, h.hash_local, 1, h.tx_hash, 'pendiente', COALESCE(h.fecha, NOW())
FROM historias h
WHERE h.tx_hash IS NOT NULL
  AND h.hash_local IS NOT NULL;
