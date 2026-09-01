-- Plano del paciente.
--
-- El tercer plano de Ficha Salud, junto al de control (`plataforma`) y al de
-- cada consultorio (`hc_<slug>`).
--
-- Aca vive la cuenta del paciente y lo que los profesionales le enviaron. **No**
-- vive la historia clinica: esa sigue siendo del consultorio que la escribio. El
-- paciente ve un buzon de lo que le mandaron, no el cuaderno interno de nadie.
--
-- A diferencia de las bases clinicas, esta es **una sola y compartida** entre
-- todos los pacientes. Es deliberado y es lo que hace posible lo que se busca:
-- que Ana atendida en dos consultorios distintos vea las dos cosas juntas. Con
-- una base por paciente eso seria imposible, y con una por consultorio volveria
-- a estar partido.
--
-- Se aplica una sola vez al crear el plano. Los cambios posteriores van en
-- db/portal/migrations/.

CREATE DATABASE IF NOT EXISTS portal
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE portal;


-- ---------------------------------------------------------------- la cuenta

CREATE TABLE IF NOT EXISTS pacientes_cuenta (
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- La identidad es el documento, no el correo.
    --
    -- Es la llave que permite que dos consultorios le envien algo a la MISMA
    -- persona sin conocerse entre si: cada uno tiene su propia fila de paciente
    -- en su propia base, pero el documento es el mismo numero en los dos lados.
    --
    -- Se guarda el tipo ademas del numero porque no todos son DNI: hay cedulas
    -- y pasaportes, y dos personas de paises distintos pueden compartir numero.
    tipo_documento VARCHAR(20) NOT NULL DEFAULT 'DNI',
    numero_documento VARCHAR(30) NOT NULL,

    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    email VARCHAR(180) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,

    telefono VARCHAR(40) NULL,
    fecha_nacimiento DATE NULL,
    sexo VARCHAR(1) NULL,

    -- Cobertura. La carga el paciente y la puede ver el profesional al que le
    -- pide turno, para no tener que preguntarsela por telefono.
    cobertura VARCHAR(120) NULL,
    plan_cobertura VARCHAR(120) NULL,
    nro_afiliado VARCHAR(60) NULL,

    -- Baja logica, igual que en `usuarios`: nunca se borra a alguien que tiene
    -- documentos clinicos asociados.
    activo TINYINT(1) NOT NULL DEFAULT 1,

    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso DATETIME NULL,

    UNIQUE KEY idx_cuenta_documento (tipo_documento, numero_documento),
    UNIQUE KEY idx_cuenta_email (email)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;


-- ------------------------------------------------------------- el buzon

CREATE TABLE IF NOT EXISTS documentos (
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- A quien va dirigido, POR DOCUMENTO y no por cuenta_id.
    --
    -- Un profesional le manda un estudio a un paciente que quizas no se
    -- registro todavia. Si esto apuntara a una cuenta, no habria a que apuntar y
    -- el envio fallaria o se perderia. Asi el documento espera, y aparece solo
    -- cuando esa persona se registra con ese numero.
    tipo_documento VARCHAR(20) NOT NULL,
    numero_documento VARCHAR(30) NOT NULL,

    -- De donde vino. El nombre del consultorio y del profesional se COPIAN, no
    -- se referencian: si ese consultorio cancela y su base se borra, el paciente
    -- tiene que seguir sabiendo quien le mando su estudio.
    consultorio_slug VARCHAR(63) NOT NULL,
    consultorio_nombre VARCHAR(180) NOT NULL,
    profesional_nombre VARCHAR(180) NULL,

    -- estudio | receta | informe | indicacion
    tipo VARCHAR(30) NOT NULL DEFAULT 'informe',
    titulo VARCHAR(200) NOT NULL,
    descripcion TEXT NULL,

    -- El archivo tambien se copia, a uploads/_portal/<token>/.
    --
    -- El token es aleatorio y no deriva del documento del paciente: la ruta de
    -- un archivo no puede dejar averiguar de quien es. `_portal` no colisiona
    -- con la carpeta de ningun consultorio porque un slug no puede empezar con
    -- guion bajo.
    archivo_token CHAR(32) NULL,
    archivo_nombre VARCHAR(255) NULL,

    enviado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    leido_en DATETIME NULL,

    KEY idx_doc_destinatario (tipo_documento, numero_documento, enviado_en),
    KEY idx_doc_consultorio (consultorio_slug)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;


-- ------------------------------------------------- altas sin verificar

-- Mismo criterio que el registro de consultorios: se guarda la intencion y la
-- cuenta se crea recien cuando alguien demuestra tener esa casilla. El
-- formulario es publico.
CREATE TABLE IF NOT EXISTS registros_paciente (
    id INT AUTO_INCREMENT PRIMARY KEY,

    tipo_documento VARCHAR(20) NOT NULL DEFAULT 'DNI',
    numero_documento VARCHAR(30) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    email VARCHAR(180) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    telefono VARCHAR(40) NULL,
    fecha_nacimiento DATE NULL,

    token CHAR(64) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',

    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expira_en DATETIME NOT NULL,
    verificado_en DATETIME NULL,

    UNIQUE KEY idx_reg_paciente_token (token),
    KEY idx_reg_paciente_documento (tipo_documento, numero_documento),
    KEY idx_reg_paciente_email (email)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- INTENTOS DE ENTRADA FALLIDOS
-- ==============================================
-- Igual que en la base de cada consultorio: el portal también tiene una página
-- de entrada pública. `clave` es `u:<usuario>|<ip>` o `ip:<ip>`.
--
-- Es una tabla propia y no compartida con los consultorios a propósito: son dos
-- poblaciones distintas, y un paciente equivocándose no tiene por qué contar
-- contra el personal de ninguna clínica.
CREATE TABLE IF NOT EXISTS intentos_login (
    clave VARCHAR(190) NOT NULL PRIMARY KEY,
    fallos INT NOT NULL DEFAULT 0,
    ultimo_en DATETIME NOT NULL
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
