-- Alta de instituciones: la misma solicitud, con aprobacion manual.
--
-- Un medico independiente se da de alta solo: verifica el correo y ya tiene su
-- sistema. Una institucion no, porque detras hay una conversacion comercial —
-- cuantos profesionales, que plan, si factura— y porque conviene mirar quien
-- pide una cuenta para varias personas antes de darsela.
--
-- El sistema de referencia resuelve esto con un formulario de Google y un correo
-- aparte. Aca no hace falta: la solicitud es una fila mas en el plano de control
-- y se aprueba con `flask cliente-estado`, que ya existe. Un formulario externo
-- obligaria a copiar los datos a mano de un lado al otro.
--
-- **La base NO se crea hasta que se aprueba.** Crearla antes significaria que
-- cualquiera puede llenar el servidor de bases con solo verificar un correo, que
-- es justamente lo que la verificacion evita en el alta de medicos. Aca la
-- verificacion demuestra la casilla; la aprobacion decide si existe el
-- consultorio.
--
-- Una clausula por sentencia: ver la nota en 20260522_bfa_evoluciones_auditoria.sql

-- 'medico' | 'institucion'. Las altas anteriores son todas de medico.
ALTER TABLE registros_pendientes ADD COLUMN tipo VARCHAR(20) NOT NULL DEFAULT 'medico';

-- Datos que solo tienen sentido para una institucion. Se guardan en la solicitud
-- y no en `clientes` porque son de la conversacion previa: sirven para decidir
-- si se aprueba y con que plan, no para operar el sistema despues.
ALTER TABLE registros_pendientes ADD COLUMN contacto_nombre VARCHAR(180) NULL;

ALTER TABLE registros_pendientes ADD COLUMN contacto_telefono VARCHAR(40) NULL;

ALTER TABLE registros_pendientes ADD COLUMN direccion VARCHAR(255) NULL;

ALTER TABLE registros_pendientes ADD COLUMN localidad VARCHAR(180) NULL;

ALTER TABLE registros_pendientes ADD COLUMN cantidad_profesionales INT NULL;

ALTER TABLE registros_pendientes ADD COLUMN cantidad_consultorios INT NULL;

ALTER TABLE registros_pendientes ADD COLUMN atencion_online TINYINT(1) NULL;

ALTER TABLE registros_pendientes ADD COLUMN sitio_web VARCHAR(255) NULL;

ALTER TABLE registros_pendientes ADD COLUMN comentarios TEXT NULL;

-- Como nos conocio. Sirve para saber que canal trae clientes antes de gastar en
-- ninguno.
ALTER TABLE registros_pendientes ADD COLUMN como_nos_conocio VARCHAR(120) NULL;

-- Quien y cuando resolvio la solicitud, y por que si se rechazo.
ALTER TABLE registros_pendientes ADD COLUMN resuelto_en DATETIME NULL;

ALTER TABLE registros_pendientes ADD COLUMN motivo_rechazo VARCHAR(500) NULL;

CREATE INDEX idx_registro_tipo_estado ON registros_pendientes (tipo, estado);
