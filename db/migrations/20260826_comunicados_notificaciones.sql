-- Notificaciones de comunicados: prioridad y estado de leido por usuario.
--
-- Los comunicados existian como una pantalla a la que habia que entrar: no
-- avisaban nada. Se agregan dos canales, y la prioridad decide cuales se usan:
--
--   normal      -> solo la campana en la barra superior
--   importante  -> campana + mail a todos los usuarios activos
--
-- La distincion es deliberada. Mandar un mail por cada aviso convierte la
-- casilla en ruido y la gente deja de leerlos, que es justo lo contrario de lo
-- que se busca con un aviso importante.
--
-- `prioridad` es VARCHAR y no ENUM a proposito: agregar un valor a un ENUM en
-- uso obliga a un ALTER que reescribe la tabla, y quitar una etiqueta que
-- todavia tiene filas falla con 1265 o, peor, las deja en cadena vacia. La
-- validacion vive en la aplicacion, que es donde se puede dar un error legible.
--
-- Una clausula por sentencia: ver la nota en 20260522_bfa_evoluciones_auditoria.sql

ALTER TABLE comunicados
    ADD COLUMN prioridad VARCHAR(20) NOT NULL DEFAULT 'normal';

-- El estado de leido es por usuario, asi que no puede vivir en `comunicados`.
-- La ausencia de fila significa no leido: no hace falta escribir una fila por
-- cada usuario cada vez que se publica un aviso.
--
-- CREATE TABLE sin IF NOT EXISTS a proposito: si ya existe, MySQL devuelve el
-- error 1050 que migrate.py tolera. IF NOT EXISTS devolveria un warning que el
-- conector C deja sin consumir y rompe el siguiente execute con un 2014.
CREATE TABLE comunicado_lecturas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    comunicado_id INT NOT NULL,
    usuario_id INT NOT NULL,
    leido_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Evita duplicados si el frontend marca lo mismo dos veces (doble click,
    -- reintento de red) y permite usar INSERT IGNORE en vez de consultar antes.
    UNIQUE KEY idx_comunicado_usuario (comunicado_id, usuario_id),
    -- CASCADE en los dos lados: la lectura no es evidencia de nada, a diferencia
    -- de la auditoria de blockchain. Si se borra el comunicado o el usuario, sus
    -- marcas de leido dejan de tener sentido.
    FOREIGN KEY (comunicado_id) REFERENCES comunicados(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    -- El contador de no leidos filtra por usuario en cada carga de la barra.
    INDEX idx_lecturas_usuario (usuario_id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
