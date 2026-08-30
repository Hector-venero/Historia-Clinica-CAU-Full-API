-- Repara el texto con doble codificacion UTF-8 del usuario sembrado.
--
-- Diagnostico (30/08/2026): en hc_bfa, `SELECT HEX(profesion)` del usuario
-- admin devolvia 4D C383 C2A9 6469636F. Esos son los bytes UTF-8 de "MÃ©dico",
-- es decir "Médico" codificado dos veces. La conexion de la aplicacion ya era
-- utf8mb4 y las tablas tambien: lo que estaba en latin1 era el cliente de MySQL
-- que ejecuta db/init.sql al crear el datadir. La causa se corrigio ahi con un
-- SET NAMES; esta migracion arregla las filas que ya quedaron mal.
--
-- Solo alcanza a las bases creadas por ese camino. Los consultorios que se dan
-- de alta con alta_cliente.py escriben con mysql-connector, que negocia
-- utf8mb4, y ya estaban bien: ahi estas sentencias no encuentran nada.
--
-- El filtro por 'Ã' es lo que la hace segura de aplicar en cualquier base: un
-- texto en castellano bien guardado no contiene ese caracter, asi que una fila
-- correcta no se toca. La condicion IS NOT NULL descarta lo que no se pueda
-- reinterpretar, en vez de reemplazarlo por basura.

UPDATE usuarios
   SET nombre = CONVERT(BINARY(CONVERT(nombre USING latin1)) USING utf8mb4)
 WHERE nombre LIKE '%Ã%'
   AND CONVERT(BINARY(CONVERT(nombre USING latin1)) USING utf8mb4) IS NOT NULL;

UPDATE usuarios
   SET apellido = CONVERT(BINARY(CONVERT(apellido USING latin1)) USING utf8mb4)
 WHERE apellido LIKE '%Ã%'
   AND CONVERT(BINARY(CONVERT(apellido USING latin1)) USING utf8mb4) IS NOT NULL;

UPDATE usuarios
   SET profesion = CONVERT(BINARY(CONVERT(profesion USING latin1)) USING utf8mb4)
 WHERE profesion LIKE '%Ã%'
   AND CONVERT(BINARY(CONVERT(profesion USING latin1)) USING utf8mb4) IS NOT NULL;

UPDATE usuarios
   SET matricula_provincia = CONVERT(BINARY(CONVERT(matricula_provincia USING latin1)) USING utf8mb4)
 WHERE matricula_provincia LIKE '%Ã%'
   AND CONVERT(BINARY(CONVERT(matricula_provincia USING latin1)) USING utf8mb4) IS NOT NULL;

UPDATE usuarios
   SET lugar_atencion_nombre = CONVERT(BINARY(CONVERT(lugar_atencion_nombre USING latin1)) USING utf8mb4)
 WHERE lugar_atencion_nombre LIKE '%Ã%'
   AND CONVERT(BINARY(CONVERT(lugar_atencion_nombre USING latin1)) USING utf8mb4) IS NOT NULL;

UPDATE usuarios
   SET lugar_atencion_direccion = CONVERT(BINARY(CONVERT(lugar_atencion_direccion USING latin1)) USING utf8mb4)
 WHERE lugar_atencion_direccion LIKE '%Ã%'
   AND CONVERT(BINARY(CONVERT(lugar_atencion_direccion USING latin1)) USING utf8mb4) IS NOT NULL;
