-- Consentimiento del paciente: cuándo aceptó y **qué versión**.
--
-- Sin la versión, el dato no sirve para lo que existe: el día que los términos
-- cambien no hay forma de saber qué aceptó cada uno, y volver a pedir el
-- consentimiento a todos es la única salida.
--
-- Un ALTER por cláusula: MySQL evalúa un ALTER compuesto de forma atómica, así
-- que un choque de "ya existe" pierde el statement entero.

ALTER TABLE pacientes_cuenta ADD COLUMN terminos_version VARCHAR(20) NULL;
ALTER TABLE pacientes_cuenta ADD COLUMN terminos_aceptados_en DATETIME NULL;
