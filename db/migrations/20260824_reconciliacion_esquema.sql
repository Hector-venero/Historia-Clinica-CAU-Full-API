-- Reconciliacion del esquema entre las dos lineas de trabajo paralelas.
--
-- Las dos ramas agregaron columnas de matricula profesional a `usuarios` de
-- forma independiente, con ENUMs distintos, y cada una tiene columnas que la
-- otra no. Esta migracion deja un esquema unico que sirve a las dos.
--
-- Sobre los ENUM: MySQL convierte por ETIQUETA, no por posicion, asi que
-- reordenar valores es inofensivo ('M' sigue siendo 'M' aunque cambie de
-- indice). Lo que si es destructivo es QUITAR una etiqueta que este en uso:
-- con sql_mode estricto el ALTER falla con 1265, y sin modo estricto la fila
-- queda en cadena vacia sin aviso. Por eso cada ENUM de abajo es la UNION de
-- los valores de ambas ramas: no se quita ninguno, y el resultado es seguro
-- sin importar el sql_mode del servidor.


-- ============================================================
-- usuarios.sexo
-- ============================================================
-- Rama principal: ENUM('M','F','X','O')   Fork: ENUM('F','M','X')
-- Union: se conservan los cuatro. 'O' (otro) solo existia en la rama
-- principal y se perderia al adoptar el ENUM del fork tal cual.
ALTER TABLE usuarios MODIFY sexo ENUM('M','F','X','O') DEFAULT NULL;


-- ============================================================
-- usuarios.matricula_tipo
-- ============================================================
-- Rama principal: ENUM('MN','MP')   Fork: ENUM('MN','MP','OP')
-- Union: 'OP' viene del fork (matricula de otro profesional).
ALTER TABLE usuarios MODIFY matricula_tipo ENUM('MN','MP','OP') DEFAULT NULL;


-- ============================================================
-- disponibilidades.dia_semana
-- ============================================================
-- El fork agrego 'Domingo' solo en init.sql y nunca escribio la migracion:
-- en cualquier base migrada (no recreada desde cero) guardar una
-- disponibilidad de domingo falla con 1265 "Data truncated".
-- Se agrega al final para no mover los valores existentes.
ALTER TABLE disponibilidades
    MODIFY dia_semana ENUM('Lunes','Martes','Miercoles','Jueves','Viernes','Sabado','Domingo') NOT NULL;


-- ============================================================
-- FKs de auditoria: ON DELETE CASCADE -> RESTRICT
-- ============================================================
-- Las versiones originales de 20260522 y 20260727 creaban estas FKs con
-- CASCADE. Una base nueva ya las crea con RESTRICT (esos archivos fueron
-- corregidos), pero una base que ya las aplico conserva el CASCADE, y como el
-- tracking la da por aplicada nunca se reintenta. Este bloque las corrige.
--
-- Con CASCADE, borrar una evolucion borraba tambien su rastro de auditoria
-- blockchain y todo su arbol de versiones: exactamente la evidencia que el
-- sistema existe para conservar.
--
-- Se usa information_schema para que sea idempotente: si la FK ya es RESTRICT
-- o no existe, no se hace nada (DROP FOREIGN KEY sobre una inexistente daria
-- 1091, que el runner no tolera a proposito).

-- --- auditorias_blockchain.evolucion_id ---
SET @tiene_cascade := (
    SELECT COUNT(*) FROM information_schema.REFERENTIAL_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = DATABASE()
      AND TABLE_NAME = 'auditorias_blockchain'
      AND CONSTRAINT_NAME = 'fk_auditorias_blockchain_evolucion'
      AND DELETE_RULE = 'CASCADE'
);
SET @sql := IF(@tiene_cascade > 0,
    'ALTER TABLE auditorias_blockchain DROP FOREIGN KEY fk_auditorias_blockchain_evolucion',
    'DO 0');
PREPARE st FROM @sql;
EXECUTE st;
DEALLOCATE PREPARE st;

SET @existe := (
    SELECT COUNT(*) FROM information_schema.REFERENTIAL_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = DATABASE()
      AND TABLE_NAME = 'auditorias_blockchain'
      AND CONSTRAINT_NAME = 'fk_auditorias_blockchain_evolucion'
);
SET @sql := IF(@existe = 0,
    'ALTER TABLE auditorias_blockchain ADD CONSTRAINT fk_auditorias_blockchain_evolucion FOREIGN KEY (evolucion_id) REFERENCES evoluciones(id) ON DELETE RESTRICT',
    'DO 0');
PREPARE st FROM @sql;
EXECUTE st;
DEALLOCATE PREPARE st;

-- --- evoluciones.padre_id (arbol de versiones) ---
SET @tiene_cascade := (
    SELECT COUNT(*) FROM information_schema.REFERENTIAL_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = DATABASE()
      AND TABLE_NAME = 'evoluciones'
      AND CONSTRAINT_NAME = 'fk_evoluciones_padre_id'
      AND DELETE_RULE = 'CASCADE'
);
SET @sql := IF(@tiene_cascade > 0,
    'ALTER TABLE evoluciones DROP FOREIGN KEY fk_evoluciones_padre_id',
    'DO 0');
PREPARE st FROM @sql;
EXECUTE st;
DEALLOCATE PREPARE st;

SET @existe := (
    SELECT COUNT(*) FROM information_schema.REFERENTIAL_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = DATABASE()
      AND TABLE_NAME = 'evoluciones'
      AND CONSTRAINT_NAME = 'fk_evoluciones_padre_id'
);
SET @sql := IF(@existe = 0,
    'ALTER TABLE evoluciones ADD CONSTRAINT fk_evoluciones_padre_id FOREIGN KEY (padre_id) REFERENCES evoluciones(id) ON DELETE RESTRICT',
    'DO 0');
PREPARE st FROM @sql;
EXECUTE st;
DEALLOCATE PREPARE st;
