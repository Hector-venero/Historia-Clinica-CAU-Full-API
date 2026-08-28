-- Quien acepta que los pacientes le reserven turnos online.
--
-- **Apagado por defecto, y eso es lo importante.** Sin este valor por defecto,
-- activar la reserva online publicaria de golpe la agenda de todos los
-- profesionales de todos los consultorios: nadie contrato eso, y varios no
-- quieren que un desconocido les ocupe un horario sin hablar antes.
--
-- Se enciende por profesional y no por consultorio porque dentro de un mismo
-- centro conviven criterios distintos: el kinesiologo puede querer agenda
-- abierta y el que hace primeras consultas, no.
--
-- Una clausula por sentencia: ver la nota en 20260522_bfa_evoluciones_auditoria.sql

ALTER TABLE usuarios ADD COLUMN agenda_publica TINYINT(1) NOT NULL DEFAULT 0;

-- Lo que el paciente ve al elegir con quien atenderse. Es distinto de
-- `especialidad`, que es el dato administrativo: aca va como el profesional
-- quiere presentarse.
ALTER TABLE usuarios ADD COLUMN presentacion_publica VARCHAR(300) NULL;
