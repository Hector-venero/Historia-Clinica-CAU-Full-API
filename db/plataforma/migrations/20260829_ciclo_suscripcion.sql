-- Ciclo de vida de la suscripcion.
--
-- Un consultorio pasa por prueba -> activo -> suspendido -> cancelado, y hay que
-- poder responder tres preguntas en cada punto: cuando avisamos que vencia,
-- cuando se corto el acceso, y hasta cuando guardamos los datos.
--
-- `cancelado_en` existe para eso ultimo. Cancelar no borra: se retiene un tiempo
-- y recien despues se elimina la base. Sin la fecha no hay forma de saber cuando
-- se cumple ese plazo, y borrar historias clinicas antes de tiempo no tiene
-- vuelta atras.
--
-- Una clausula por sentencia: ver la nota en 20260522_bfa_evoluciones_auditoria.sql

-- Para el panel: distinguir un consultorio que trabaja de uno que se dio de alta
-- y nunca volvio. Son conversaciones comerciales distintas.
ALTER TABLE clientes ADD COLUMN ultimo_acceso DATETIME NULL;

-- Cuando se mando el aviso de que la prueba estaba por terminar. Es una marca y
-- no un booleano para poder saber si el aviso llego a tiempo.
ALTER TABLE clientes ADD COLUMN aviso_vencimiento_en DATETIME NULL;

-- Cuando se corto el acceso.
ALTER TABLE clientes ADD COLUMN suspendido_en DATETIME NULL;

-- Cuando se cancelo. Desde aca corre el plazo de retencion.
ALTER TABLE clientes ADD COLUMN cancelado_en DATETIME NULL;

-- Motivo del ultimo cambio de estado, para el panel y para el soporte.
ALTER TABLE clientes ADD COLUMN motivo_estado VARCHAR(255) NULL;

CREATE INDEX idx_clientes_estado_prueba ON clientes (estado, prueba_hasta);
