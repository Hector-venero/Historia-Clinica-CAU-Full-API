-- Quien abrio la historia de quien.
--
-- No habia ningun registro. En un consultorio con direccion, varios
-- profesionales, secretaria y coordinacion de area —todos con acceso a datos de
-- pacientes— nadie podia responder "¿quien miro esta historia?". Para datos de
-- salud de terceros (Ley 25.326) esa pregunta se contesta, y ademas es la
-- primera que hace un cliente cuando sospecha algo.
--
-- APPEND-ONLY, como `anclajes_blockchain`. La aplicacion no actualiza ni borra
-- estas filas: un registro de accesos que el propio sistema puede reescribir no
-- prueba nada.
--
-- ⚠️ Guarda QUIEN, QUE y CUANDO, nunca el contenido. Copiar aca lo que se leyo
-- seria duplicar la historia clinica en una segunda tabla, con las mismas
-- obligaciones y menos cuidado.
--
-- BIGINT porque es la tabla que mas crece del esquema: una fila por cada
-- apertura de historia, todos los dias, sin borrado.
--
-- Sin FK a `pacientes`: si algun dia se borra un paciente, el rastro de quien
-- lo miro es justamente lo que no se puede perder. Por eso tampoco hay CASCADE.

CREATE TABLE IF NOT EXISTS accesos_historia (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NULL,
    paciente_id INT NOT NULL,
    accion VARCHAR(30) NOT NULL,
    detalle VARCHAR(255) NULL,
    ip VARCHAR(60) NULL,
    creado_en DATETIME NOT NULL,
    INDEX idx_accesos_paciente (paciente_id, creado_en),
    INDEX idx_accesos_usuario (usuario_id, creado_en)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
