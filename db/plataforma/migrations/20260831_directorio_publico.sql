-- Directorio de profesionales que aceptan turnos online.
--
-- Es una **proyeccion**: los datos verdaderos viven en la tabla `usuarios` de
-- cada consultorio, y aca hay una copia de los pocos campos que hacen falta para
-- buscar y elegir.
--
-- Duplicar datos es algo que normalmente se evita, asi que el motivo tiene que
-- quedar escrito: buscar un profesional recorriendo la base de cada consultorio
-- serian N consultas por busqueda, con N creciendo con cada cliente nuevo. Es la
-- consulta mas usada del sitio publico y la haria alguien sin sesion, o sea el
-- peor lugar posible para poner algo que escala mal.
--
-- La copia se actualiza cuando el profesional guarda su perfil publico. Si
-- alguna vez quedan desincronizadas, la verdad esta en la base del consultorio:
-- esta tabla se puede reconstruir entera desde ahi.
--
-- **Solo entran los que se dieron de alta explicitamente** (agenda_publica = 1).
-- Un profesional que no lo activo no figura, y por lo tanto no se lo puede
-- encontrar ni reservarle.
--
-- Una clausula por sentencia: ver la nota en 20260522_bfa_evoluciones_auditoria.sql

CREATE TABLE IF NOT EXISTS profesionales_publicos (
    -- Un profesional se identifica por el par consultorio + usuario: el id 1
    -- existe en la base de cada consultorio.
    cliente_id INT NOT NULL,
    usuario_id INT NOT NULL,

    -- Copiado de la base del consultorio.
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NULL,
    especialidad VARCHAR(120) NULL,
    presentacion VARCHAR(300) NULL,
    matricula VARCHAR(60) NULL,

    -- Donde atiende. Es lo primero que mira un paciente despues de la
    -- especialidad.
    lugar_nombre VARCHAR(180) NULL,
    lugar_direccion VARCHAR(255) NULL,

    -- Denormalizados para poder listar sin tocar la tabla `clientes`.
    consultorio_slug VARCHAR(63) NOT NULL,
    consultorio_nombre VARCHAR(180) NOT NULL,

    duracion_turno INT NOT NULL DEFAULT 20,

    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (cliente_id, usuario_id),
    KEY idx_directorio_especialidad (especialidad),
    KEY idx_directorio_slug (consultorio_slug),
    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
