-- Crear la base de datos si no existe
CREATE DATABASE IF NOT EXISTS hc_bfa;
USE hc_bfa;

SET GLOBAL time_zone = '-3:00';
SET time_zone = '-3:00';

-- Eliminar tablas si existen (para desarrollo)
DROP TABLE IF EXISTS historias;
DROP TABLE IF EXISTS turnos;
DROP TABLE IF EXISTS evolucion_archivos;
DROP TABLE IF EXISTS evoluciones;
DROP TABLE IF EXISTS pacientes;
DROP TABLE IF EXISTS usuarios;

-- Tabla de usuarios
CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    rol ENUM('director', 'profesional', 'administrativo') NOT NULL,
    especialidad VARCHAR(100) NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1   -- ✅ soft delete
);

-- Tabla de pacientes (extendida)
CREATE TABLE pacientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nro_hc VARCHAR(20),
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
    registrado_por INT DEFAULT NULL,
    modificado_por INT DEFAULT NULL,
    FOREIGN KEY (registrado_por) REFERENCES usuarios(id),
    FOREIGN KEY (modificado_por) REFERENCES usuarios(id)
);

-- Tabla de historias clínicas
CREATE TABLE historias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    usuario_id INT NOT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    motivo_consulta TEXT,
    antecedentes TEXT,
    examen_fisico TEXT,
    diagnostico TEXT,
    tratamiento TEXT,
    observaciones TEXT,
    hash CHAR(64) NOT NULL,
    tx_hash VARCHAR(100),
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- Tabla de evoluciones
CREATE TABLE evoluciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    fecha DATE NOT NULL,
    contenido TEXT NOT NULL,
    usuario_id INT NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- Archivos asociados a evoluciones
CREATE TABLE evolucion_archivos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    evolucion_id INT NOT NULL,
    filename VARCHAR(255),
    filepath TEXT,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evolucion_id) REFERENCES evoluciones(id)
);

-- Tabla de turnos
CREATE TABLE turnos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NOT NULL,
    usuario_id INT NOT NULL,
    fecha DATETIME NOT NULL,
    motivo VARCHAR(255),
    notificado BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE ausencias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,           -- médico al que aplica
    fecha_inicio DATETIME NOT NULL,
    fecha_fin DATETIME NOT NULL,
    motivo VARCHAR(255),
    creado_por INT NOT NULL,           -- usuario que lo cargó
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE disponibilidades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,  -- médico o profesional
    dia_semana ENUM('Lunes','Martes','Miercoles','Jueves','Viernes','Sabado') NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    activo BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- Índices útiles
CREATE INDEX idx_pacientes_dni ON pacientes (dni);
CREATE INDEX idx_pacientes_nombre ON pacientes (nombre);
CREATE INDEX idx_pacientes_apellido ON pacientes (apellido);

-- Usuario administrador inicial
INSERT INTO usuarios (nombre, username, email, password_hash, rol)
SELECT 'Admin', 'admin', 'admin@ejemplo.com',
'scrypt:32768:8:1$bdt4huruWlbjvNqs$4a236ac9509c5ee61ab5ce7103a686d272d512c2cf5f11d30b5afcb91f98832cba6ba1118114c6c4df2e4e9387f452514b05c6f9b6fc7d35a3a2e042f07fc0af',
'director'
WHERE NOT EXISTS (
    SELECT 1 FROM usuarios WHERE username = 'admin'
);
