-- Qué avisos quiere recibir el paciente, y su foto.
--
-- Hasta ahora se le mandaba todo siempre, sin forma de apagarlo. Con datos de
-- salud de por medio, que alguien pueda decidir qué le llega al correo no es un
-- lujo: puede compartir la casilla, o simplemente no querer que un asunto diga
-- de qué consultorio le escriben.
--
-- Vienen en 1: quien ya tiene cuenta no puede quedar sin avisos por un cambio
-- que no pidió.
--
-- Un ALTER por cláusula: MySQL evalúa un ALTER compuesto de forma atómica.

ALTER TABLE pacientes_cuenta ADD COLUMN avisar_documentos BOOLEAN NOT NULL DEFAULT 1;
ALTER TABLE pacientes_cuenta ADD COLUMN avisar_turnos BOOLEAN NOT NULL DEFAULT 1;
ALTER TABLE pacientes_cuenta ADD COLUMN foto VARCHAR(120) NULL;
