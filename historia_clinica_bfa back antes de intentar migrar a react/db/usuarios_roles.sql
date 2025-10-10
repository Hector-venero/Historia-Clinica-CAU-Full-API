-- Crea los usuarios con sus respectivos roles y claves hasheadas

-- Usuario Admin
INSERT INTO usuarios (nombre, username, password_hash, rol)
VALUES ('Administrador', 'admin', 'pbkdf2:sha256:600000$admin$58fa227b460ec63e59b22db76368b98db1c57031a48ec55e48e50849a82c5ab3', 'Admin');

-- Usuario Doctor
INSERT INTO usuarios (nombre, username, password_hash, rol)
VALUES ('Dra. Juarez', 'drajuarez', 'pbkdf2:sha256:600000$drajuarez$2df843eb089fe69e108973c893f0b4a7788f59156a6ccecbda5b52a26977cbeb', 'Doctor');

-- Usuario Enfermero
INSERT INTO usuarios (nombre, username, password_hash, rol)
VALUES ('Lic. Díaz', 'enfermerodiaz', 'pbkdf2:sha256:600000$enfermerodiaz$9c28fbcf0b2267cb697fb4a8b16f8c182bb08c372faeb986c86a3004e3078e50', 'Enfermero');

-- Usuario Técnico
INSERT INTO usuarios (nombre, username, password_hash, rol)
VALUES ('Tec. Gómez', 'tecgomez', 'pbkdf2:sha256:600000$tecgomez$746a217016fd8e6315b25e0e5a4e826624b174fd78edc66f8b405e91f1096a2b', 'Tecnico');
