-- Los turnos que el paciente reservo, para poder verlos y cancelarlos.
--
-- Hasta ahora reservar dejaba un texto en el buzon ("Turno con X el dia Y") y
-- nada mas. Al paciente le servia para enterarse, pero no habia forma de saber
-- **cual** turno era: sin el id y el consultorio, cancelar era imposible.
--
-- Esto es un PUNTERO, no la verdad. El turno de verdad vive en la tabla `turnos`
-- de la base del consultorio, que es quien manda: si ahi se cancela o se
-- reprograma, esta fila queda vieja. Por eso al listar se verifica contra el
-- consultorio en lugar de confiar en la copia — es una consulta por consultorio
-- con el que el paciente tiene turnos, tipicamente uno o dos.
--
-- Se guarda igual el detalle (profesional, lugar) porque hace falta para mostrar
-- la lista sin ir a buscarlo, y porque si ese consultorio cancela su cuenta y se
-- borra su base, el paciente tiene que seguir viendo que tuvo un turno ahi.
--
-- Una clausula por sentencia: ver la nota en 20260522_bfa_evoluciones_auditoria.sql

CREATE TABLE IF NOT EXISTS turnos_reservados (
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- De quien es. Por documento, igual que el buzon: es la llave del plano.
    tipo_documento VARCHAR(20) NOT NULL,
    numero_documento VARCHAR(30) NOT NULL,

    -- Donde vive el turno de verdad.
    cliente_id INT NOT NULL,
    consultorio_slug VARCHAR(63) NOT NULL,
    consultorio_nombre VARCHAR(180) NOT NULL,
    turno_id INT NOT NULL,
    usuario_id INT NOT NULL,

    profesional_nombre VARCHAR(180) NULL,
    lugar VARCHAR(255) NULL,
    motivo VARCHAR(255) NULL,

    fecha_inicio DATETIME NOT NULL,

    -- reservado | cancelado
    --
    -- Cancelar en el consultorio BORRA la fila de `turnos`; aca en cambio se
    -- marca. El paciente tiene que poder ver que cancelo un turno, y cuando: si
    -- desapareciera, no habria como distinguir "lo cancele" de "nunca existio".
    estado VARCHAR(20) NOT NULL DEFAULT 'reservado',
    cancelado_en DATETIME NULL,
    cancelado_por VARCHAR(20) NULL,

    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    KEY idx_turno_paciente (tipo_documento, numero_documento, fecha_inicio),
    KEY idx_turno_origen (cliente_id, turno_id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
