-- Ajustes operativos del consultorio, como clave/valor.
--
-- Empieza con los avisos por correo. Hasta ahora el correo se mandaba SIEMPRE y
-- no habia forma de apagarlo: un consultorio que avisa por WhatsApp le manda al
-- paciente dos confirmaciones del mismo turno, y no hay pantalla que lo evite.
--
-- Va en la base de CADA consultorio y no en `clientes_config` del plano de
-- control, a proposito:
--
--   * `clientes_config` solo existe con MULTI_TENANT. Aca la instalacion de un
--     solo centro tambien puede apagar sus avisos, con el mismo codigo.
--   * Son ajustes de como trabaja el consultorio, no de que contrato. El plan
--     dice que modulos tiene; esto, como los usa.
--
-- Clave/valor y no una columna por ajuste: cada ajuste nuevo seria una
-- migracion sobre las bases de todos los consultorios. Los valores se
-- interpretan en `app/ajustes.py`, que es donde estan los tipos y los valores
-- por defecto.
--
-- Sin fila = el valor por defecto. No se siembran filas al crear la base: una
-- fila ausente y una fila con el valor por defecto significan lo mismo, y
-- sembrarlas obliga a mantener la semilla sincronizada con el codigo.

CREATE TABLE IF NOT EXISTS configuracion (
    clave VARCHAR(60) NOT NULL PRIMARY KEY,
    valor VARCHAR(255) NOT NULL,
    actualizado_en DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
