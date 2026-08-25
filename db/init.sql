-- ==============================================
--  ESQUEMA INICIAL
-- ==============================================
-- Este script solo CREA. Los DROP TABLE que estaban aca se movieron a
-- db/dev_reset.sql: al vivir en el mismo archivo que el CREATE DATABASE,
-- init.sql parecia un script de setup seguro para correr a mano, y correrlo
-- contra la base de produccion borraba toda la historia clinica.
--
-- Docker solo lo ejecuta cuando el datadir esta vacio (esta montado en
-- /docker-entrypoint-initdb.d). Sobre una base existente, los cambios de
-- esquema van por db/migrations/.

CREATE DATABASE IF NOT EXISTS hc_bfa
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE hc_bfa;

-- Solo la sesion: SET GLOBAL requiere privilegio SUPER y afecta al servidor
-- entero, no a esta base. La zona horaria del servidor se fija por
-- --default-time-zone en docker-compose.yml.
SET time_zone = '-3:00';

-- ==============================================
-- TABLA DE USUARIOS
-- ==============================================
CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) DEFAULT NULL,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    rol ENUM('director', 'profesional', 'administrativo','area') NOT NULL,
    especialidad VARCHAR(100) NULL,
    duracion_turno INT NOT NULL DEFAULT 20,
    foto VARCHAR(255) DEFAULT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    dni VARCHAR(20) DEFAULT NULL,
    sexo ENUM('M', 'F', 'X', 'O') DEFAULT NULL,
    profesion VARCHAR(100) DEFAULT NULL,
    -- 'OP' (otro profesional) viene del fork. Ver
    -- db/migrations/20260824_reconciliacion_esquema.sql
    matricula_tipo ENUM('MN', 'MP', 'OP') DEFAULT NULL,
    matricula_numero VARCHAR(50) DEFAULT NULL,
    matricula_provincia VARCHAR(100) DEFAULT NULL
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- TABLA DE PACIENTES
-- ==============================================
CREATE TABLE pacientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nro_hc VARCHAR(20) NOT NULL UNIQUE,
    dni VARCHAR(20) NOT NULL UNIQUE,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    fecha_nacimiento DATE,
    sexo ENUM('Masculino', 'Femenino', 'Otro') DEFAULT NULL,
    nacionalidad VARCHAR(50),
    ocupacion VARCHAR(100),
    direccion VARCHAR(255),
    codigo_postal VARCHAR(20),
    telefono VARCHAR(50),
    celular VARCHAR(50),
    email VARCHAR(100),
    contacto VARCHAR(100),
    cobertura VARCHAR(100),
    cert_discapacidad ENUM('Sí', 'No') DEFAULT NULL,
    nro_certificado VARCHAR(50),
    derivado_por VARCHAR(100),
    diagnostico TEXT,
    motivo_derivacion TEXT,
    medico_cabecera VARCHAR(100),
    comentarios TEXT,
    motivo_ingreso TEXT,
    enfermedad_actual TEXT,
    antecedentes_enfermedad_actual TEXT,
    antecedentes_personales TEXT,
    antecedentes_heredofamiliares TEXT,
    registrado_por INT DEFAULT NULL,
    modificado_por INT DEFAULT NULL,
    FOREIGN KEY (registrado_por) REFERENCES usuarios(id),
    FOREIGN KEY (modificado_por) REFERENCES usuarios(id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- TABLA DE HISTORIAS CLÍNICAS (actualizada para blockchain)
-- ==============================================
CREATE TABLE historias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL UNIQUE,
    usuario_id INT NOT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    resumen LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    hash_local CHAR(64) DEFAULT NULL,        -- Hash SHA-256 del contenido
    tx_hash VARCHAR(512) DEFAULT NULL,       -- Recibo TSA de BFA (rd base64)
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- TABLA DE EVOLUCIONES
-- ==============================================
CREATE TABLE evoluciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    fecha DATE NOT NULL,
    contenido TEXT NOT NULL,
    indicaciones TEXT,
    usuario_id INT NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- ARCHIVOS ASOCIADOS A EVOLUCIONES
-- ==============================================
CREATE TABLE evolucion_archivos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    evolucion_id INT NOT NULL,
    filename VARCHAR(255),
    filepath TEXT,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evolucion_id) REFERENCES evoluciones(id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- TABLA DE TURNOS
-- ==============================================
CREATE TABLE turnos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    usuario_id INT NOT NULL,
    fecha_inicio DATETIME NOT NULL,
    fecha_fin DATETIME NOT NULL,
    motivo VARCHAR(255),
    notificado BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- AUSENCIAS PROFESIONALES
-- ==============================================
CREATE TABLE ausencias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    fecha_inicio DATETIME NOT NULL,
    fecha_fin DATETIME NOT NULL,
    motivo VARCHAR(255),
    creado_por INT NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- DISPONIBILIDADES DE PROFESIONALES
-- ==============================================
CREATE TABLE disponibilidades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    dia_semana ENUM('Lunes','Martes','Miercoles','Jueves','Viernes','Sabado','Domingo') NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    activo BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- GRUPOS PROFESIONALES
-- ==============================================
CREATE TABLE grupos_profesionales (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    color VARCHAR(20) DEFAULT '#00936B',
    -- Los grupos de rehabilitación se muestran en su propio módulo de agenda.
    es_rehabilitacion TINYINT(1) NOT NULL DEFAULT 0,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE grupo_miembros (
    id INT AUTO_INCREMENT PRIMARY KEY,
    grupo_id INT NOT NULL,
    usuario_id INT NOT NULL,
    UNIQUE KEY idx_grupo_usuario (grupo_id, usuario_id),
    FOREIGN KEY (grupo_id) REFERENCES grupos_profesionales(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- AUDITORÍAS BLOCKCHAIN
-- ==============================================
CREATE TABLE auditorias_blockchain (
    id INT AUTO_INCREMENT PRIMARY KEY,
    historia_id INT NOT NULL,
    hash_local VARCHAR(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    hash_bfa   VARCHAR(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    valido TINYINT(1) NOT NULL,
    usuario VARCHAR(100) NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (historia_id) REFERENCES historias(id) ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ==============================================
-- ÍNDICES
-- ==============================================
CREATE INDEX idx_pacientes_dni ON pacientes (dni);
CREATE INDEX idx_pacientes_nombre ON pacientes (nombre);
CREATE INDEX idx_pacientes_apellido ON pacientes (apellido);

-- ==============================================
-- USUARIO ADMINISTRADOR INICIAL
-- ==============================================
INSERT INTO usuarios (nombre, apellido, username, email, password_hash, rol, dni, sexo, profesion, matricula_tipo, matricula_numero, matricula_provincia)
SELECT 'Admin', 'Castro', 'admin', 'admin@ejemplo.com',
'scrypt:32768:8:1$bdt4huruWlbjvNqs$4a236ac9509c5ee61ab5ce7103a686d272d512c2cf5f11d30b5afcb91f98832cba6ba1118114c6c4df2e4e9387f452514b05c6f9b6fc7d35a3a2e042f07fc0af',
'director', '67887891', 'M', 'Médico', 'MN', '43243', 'Nacional'
WHERE NOT EXISTS (
    SELECT 1 FROM usuarios WHERE username = 'admin'
);

-- ==============================================
-- USUARIO DE APLICACIÓN (no root)
-- ==============================================
DROP USER IF EXISTS 'hc_app'@'%';
CREATE USER IF NOT EXISTS 'hc_app'@'%' IDENTIFIED BY 'HC_App_2025!';
GRANT SELECT, INSERT, UPDATE, DELETE ON hc_bfa.* TO 'hc_app'@'%';

-- Crear usuario para backups
DROP USER IF EXISTS 'backup_user'@'%';
CREATE USER IF NOT EXISTS 'backup_user'@'%' IDENTIFIED BY 'Backup_2025!';

-- Permisos necesarios para mysqldump seguro
GRANT SELECT, LOCK TABLES ON hc_bfa.* TO 'backup_user'@'%';
FLUSH PRIVILEGES;
