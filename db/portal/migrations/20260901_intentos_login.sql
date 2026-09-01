-- Freno a los intentos de adivinar una contrasena.
--
-- El login no tenia ningun limite: una pagina de entrada publica por cada
-- subdominio, y del otro lado historias clinicas.
--
-- Va en la base y no en memoria porque en produccion corren tres workers de
-- Gunicorn: un contador en memoria vive en cada uno por separado, con lo que el
-- limite real seria el triple y dependeria de a que worker cae cada pedido.
--
-- `clave` es `u:<usuario>|<ip>` o `ip:<ip>`. Se cuenta por las dos: solo por
-- usuario, la proteccion se vuelve el ataque —cualquiera deja afuera al
-- director escribiendo mal su contrasena diez veces— y solo por IP no frena a
-- quien sale por muchas.
--
-- 190 y no 255: es el tope de una PRIMARY KEY de texto en utf8mb4.
--
-- Las filas se pisan solas al volver a fallar y se borran al entrar bien. No
-- hace falta limpieza programada: lo que quede viejo se reinicia en el mismo
-- INSERT ... ON DUPLICATE KEY, y son unos pocos bytes por combinacion.

CREATE TABLE IF NOT EXISTS intentos_login (
    clave VARCHAR(190) NOT NULL PRIMARY KEY,
    fallos INT NOT NULL DEFAULT 0,
    ultimo_en DATETIME NOT NULL
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
