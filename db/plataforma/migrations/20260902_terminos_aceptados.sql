-- Consentimiento en el alta de un consultorio: cuándo y **qué versión**.
--
-- Mismo motivo que en el plano del portal: sin la versión, cuando los términos
-- cambien no se puede saber qué aceptó cada uno.
--
-- Va en `registros_pendientes`, que es donde vive la intención de alta antes de
-- que exista el consultorio: el consentimiento se da al registrarse, no al
-- verificar el correo.

ALTER TABLE registros_pendientes ADD COLUMN terminos_version VARCHAR(20) NULL;
ALTER TABLE registros_pendientes ADD COLUMN terminos_aceptados_en DATETIME NULL;
