-- ==============================================================
--  PLANO DE CONTROL DE LA PLATAFORMA
-- ==============================================================
--
-- Esta base NO contiene datos clinicos. Solo sabe que consultorios existen, en
-- que estado estan y donde vive la base de cada uno. Las historias clinicas
-- viven en la base propia de cada cliente, a la que esta no accede nunca.
--
-- La separacion es el punto entero de la arquitectura: un error de programacion
-- aca no puede exponer un paciente, porque aca no hay pacientes.
--
-- Se aplica una sola vez al crear la plataforma. Los cambios posteriores van en
-- db/plataforma/migrations/.

CREATE DATABASE IF NOT EXISTS plataforma
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE plataforma;

-- ==============================================================
--  CLIENTES
-- ==============================================================
CREATE TABLE IF NOT EXISTS clientes (
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- El subdominio: drjperez.<dominio>. Es lo que resuelve a que base ir.
    -- 63 caracteres es el maximo de una etiqueta DNS; no tiene sentido permitir
    -- un slug que despues no pueda existir como subdominio.
    slug VARCHAR(63) NOT NULL,

    nombre VARCHAR(180) NOT NULL,
    email_contacto VARCHAR(180) NOT NULL,

    -- prueba | activo | suspendido | cancelado
    --
    -- VARCHAR y no ENUM, igual que comunicados.prioridad: ampliar un ENUM en uso
    -- obliga a reescribir la tabla, y un valor invalido daria un 1265 en vez de
    -- un error legible. La validacion vive en la aplicacion.
    estado VARCHAR(20) NOT NULL DEFAULT 'prueba',
    plan VARCHAR(30) NOT NULL DEFAULT 'basico',

    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    prueba_hasta DATE NULL,

    -- Donde vive su base y con que credenciales se entra.
    --
    -- Cada cliente tiene su PROPIO usuario de MySQL, con permisos solo sobre su
    -- base. Asi una inyeccion SQL en cualquier endpoint queda encerrada en ese
    -- consultorio en lugar de exponer a todos.
    --
    -- El usuario de MySQL admite 32 caracteres como maximo (verificado contra
    -- information_schema en MySQL 8), de ahi el limite de la columna.
    db_nombre VARCHAR(64) NOT NULL,
    db_usuario VARCHAR(32) NOT NULL,

    -- Cifrada con la clave de la plataforma, no en claro. Ver utils/secretos.py.
    db_password VARBINARY(512) NOT NULL,

    UNIQUE KEY idx_clientes_slug (slug),
    UNIQUE KEY idx_clientes_db (db_nombre),
    INDEX idx_clientes_estado (estado)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================================
--  CONFIGURACION POR CLIENTE
-- ==============================================================
-- Separada de `clientes` porque se lee en cada pedido (marca, modulos) mientras
-- que los datos de conexion se leen una vez y se cachean.
CREATE TABLE IF NOT EXISTS clientes_config (
    cliente_id INT PRIMARY KEY,

    -- Marca. Hoy "CAU UNSAM" y el logo estan escritos en el codigo; cada
    -- consultorio necesita el suyo en la app, las recetas y los mails.
    nombre_visible VARCHAR(180) NULL,
    logo VARCHAR(255) NULL,

    -- Modulos habilitados, separados por coma (turnos,recetas,grupos,...).
    -- El backend valida contra esto: ocultar una opcion del menu no es un
    -- permiso.
    modulos VARCHAR(255) NOT NULL DEFAULT 'turnos,pacientes,historias,recetas',

    -- Diferencial opcional, apagado por defecto: no todo consultorio tiene por
    -- que entender que es el sellado en blockchain.
    blockchain TINYINT(1) NOT NULL DEFAULT 0,

    -- Recetas electronicas. Hoy el token de QBI es global del sistema; cada
    -- consultorio tiene que usar el suyo.
    qbi_base_url VARCHAR(255) NULL,
    qbi_client_id VARCHAR(120) NULL,
    qbi_token VARBINARY(512) NULL,

    -- Datos del lugar de atencion que se imprimen por defecto en las recetas.
    lugar_nombre VARCHAR(180) NULL,
    lugar_direccion VARCHAR(255) NULL,
    lugar_telefono VARCHAR(50) NULL,
    lugar_email VARCHAR(180) NULL,

    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================================
--  SLUGS RESERVADOS
-- ==============================================================
-- Nombres que no puede tomar un cliente porque colisionan con el propio
-- servicio. Van en una tabla y no en una constante del codigo para poder sumar
-- uno sin desplegar.
CREATE TABLE IF NOT EXISTS slugs_reservados (
    slug VARCHAR(63) PRIMARY KEY,
    motivo VARCHAR(180) NULL
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO slugs_reservados (slug, motivo) VALUES
    ('www',      'sitio publico'),
    ('api',      'reservado tecnico'),
    ('app',      'reservado tecnico'),
    ('admin',    'panel de la plataforma'),
    ('panel',    'panel de la plataforma'),
    ('mail',     'correo'),
    ('smtp',     'correo'),
    ('ftp',      'reservado tecnico'),
    ('cdn',      'reservado tecnico'),
    ('static',   'reservado tecnico'),
    ('soporte',  'atencion al cliente'),
    ('ayuda',    'atencion al cliente'),
    ('blog',     'sitio publico'),
    ('status',   'estado del servicio'),
    ('test',     'reservado tecnico'),
    ('demo',     'demostraciones');
