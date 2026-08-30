-- Videoconsulta: modalidad del turno y enlace de la videollamada.
--
-- Un ALTER por clausula. MySQL evalua un ALTER compuesto de forma atomica: si
-- una clausula choca con "ya existe", se pierde el statement entero y la
-- migracion quedaria marcada como aplicada con columnas faltantes.
--
-- VARCHAR y no ENUM, igual que comunicados.prioridad: se valida en la
-- aplicacion, y sumar una modalidad no vuelve a ser una migracion de esquema.
--
-- El enlace lo pone el profesional (Meet, Zoom, lo que use). No se genera ni se
-- aloja la videollamada: ver docs/VIDEOCONSULTA.md.

ALTER TABLE turnos ADD COLUMN modalidad VARCHAR(20) NOT NULL DEFAULT 'presencial';
ALTER TABLE turnos ADD COLUMN enlace_video VARCHAR(500) NULL;
