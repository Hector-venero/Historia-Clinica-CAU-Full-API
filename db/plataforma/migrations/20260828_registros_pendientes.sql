-- Altas que todavia no son consultorios.
--
-- El registro es autoservicio y publico, asi que crear la base en cuanto alguien
-- completa el formulario significa que cualquiera puede llenar el servidor de
-- bases vacias con un script. Primero se guarda la intencion y se manda un
-- correo; la base se crea recien cuando alguien demuestra tener esa casilla.
--
-- La contrasena del futuro admin se guarda ya hasheada: entre el registro y la
-- verificacion puede pasar un dia, y no hay motivo para que exista en claro ni
-- un minuto.
--
-- El slug NO se reserva al registrarse, a proposito. Si se reservara, bastaria
-- con registrar sin verificar nunca para bloquear un nombre para siempre. Se
-- vuelve a comprobar que este libre al momento de crear la base.
--
-- Una clausula por sentencia: ver la nota en 20260522_bfa_evoluciones_auditoria.sql

CREATE TABLE IF NOT EXISTS registros_pendientes (
    id INT AUTO_INCREMENT PRIMARY KEY,

    slug VARCHAR(63) NOT NULL,
    nombre VARCHAR(180) NOT NULL,
    email VARCHAR(180) NOT NULL,

    -- Hash de la contrasena con la que va a entrar el admin del consultorio.
    password_hash VARCHAR(255) NOT NULL,

    -- Token del enlace de verificacion. Unico e impredecible.
    token CHAR(64) NOT NULL,

    -- pendiente  -> se mando el correo, falta que lo abran
    -- creando    -> se esta creando la base
    -- listo      -> el consultorio existe
    -- fallido    -> la creacion fallo; el detalle queda en `error`
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    error VARCHAR(500) NULL,

    -- Queda apuntado a que consultorio dio origen, para poder rastrearlo.
    cliente_id INT NULL,

    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Un registro sin verificar caduca: si no, la tabla acumula intentos
    -- abandonados y direcciones de correo de gente que nunca uso el servicio.
    expira_en DATETIME NOT NULL,
    verificado_en DATETIME NULL,

    UNIQUE KEY idx_registro_token (token),
    KEY idx_registro_slug (slug),
    KEY idx_registro_email (email),
    KEY idx_registro_estado (estado)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
