-- Plantillas de texto clinico.
--
-- Buena parte de lo que se escribe en una evolucion se repite: el control de
-- una misma patologia, las indicaciones post quirurgicas, la pauta de alarma
-- que hay que dejar por escrito siempre. Hoy se vuelve a tipear cada vez, y lo
-- que se tipea de nuevo sale distinto cada vez.
--
-- `campo` separa las de evolucion de las de indicaciones: son textos de
-- naturaleza distinta y mezclarlas obliga a leer veinte opciones para encontrar
-- una. Es VARCHAR y no ENUM, como `turnos.modalidad`: sumar un campo no tiene
-- por que ser una migracion de esquema.
--
-- `usuario_id` NULL significa "del consultorio", igual que en `servicios`. Una
-- pauta de alarma la escribe la direccion una vez y la usa todo el equipo; el
-- texto con el que un profesional describe su propio control es suyo.
--
-- El cuerpo es TEXT y no VARCHAR: una evolucion completa no entra en 255.

CREATE TABLE IF NOT EXISTS plantillas_texto (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NULL,
    campo VARCHAR(30) NOT NULL DEFAULT 'evolucion',
    nombre VARCHAR(120) NOT NULL,
    cuerpo TEXT NOT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    INDEX idx_plantillas_uso (campo, activo, usuario_id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
