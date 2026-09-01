-- Servicios (prestaciones): que un turno sea *de algo*.
--
-- Hasta ahora un turno tenia `motivo` —texto libre— y la duracion era una sola
-- por profesional (`usuarios.duracion_turno`). Con esto cada turno puede ser de
-- un servicio con su propia duracion y su precio: una consulta de 30 y un
-- control de 15 dejan de tener que durar lo mismo.
--
-- `usuario_id` NULL significa "de todo el consultorio". Se resolvio asi y no con
-- una tabla de union `servicio_profesionales` porque el caso real es que casi
-- todos los servicios los ofrece todo el mundo, y el que no, lo ofrece uno solo.
-- Una tabla de union para eso son dos consultas y una pantalla mas, todos los
-- dias, para cubrir el caso raro.
--
-- `turnos.servicio_id` es OPCIONAL y se queda en NULL para siempre en un
-- consultorio que no use servicios. Es lo que permite soltar esto sin migrar a
-- nadie: sin servicio, la duracion sigue saliendo de `usuarios.duracion_turno`
-- exactamente como hoy.
--
-- ON DELETE SET NULL y no CASCADE: borrar un servicio del catalogo no puede
-- borrar los turnos que se dieron con el. El turno sucedio.

CREATE TABLE IF NOT EXISTS servicios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NULL,
    nombre VARCHAR(120) NOT NULL,
    descripcion VARCHAR(255) NULL,
    duracion_minutos INT NOT NULL,
    precio DECIMAL(10,2) NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    INDEX idx_servicios_usuario (usuario_id, activo)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- Un ALTER por clausula: MySQL evalua un ALTER compuesto de forma atomica y si
-- una clausula choca con "ya existe" se pierde el statement entero.
ALTER TABLE turnos ADD COLUMN servicio_id INT NULL;
ALTER TABLE turnos ADD CONSTRAINT fk_turnos_servicio FOREIGN KEY (servicio_id) REFERENCES servicios(id) ON DELETE SET NULL;
