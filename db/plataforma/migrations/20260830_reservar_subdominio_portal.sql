-- `mi` queda reservado: es el subdominio del portal del paciente.
--
-- tenancy.py ya lo excluye de resolver como consultorio, pero eso solo evita que
-- un pedido a mi.<dominio> busque un cliente inexistente. Sin reservarlo aca,
-- alguien podria **dar de alta un consultorio llamado `mi`** desde el registro
-- autoservicio: el alta funcionaria, se crearia su base, y despues nunca podria
-- entrar porque su subdominio lo atiende el portal.
--
-- Se suman tambien los del sitio publico y los que suelen usarse para
-- infraestructura, por el mismo motivo.
--
-- Una clausula por sentencia: ver la nota en 20260522_bfa_evoluciones_auditoria.sql

INSERT IGNORE INTO slugs_reservados (slug, motivo) VALUES
    ('mi',        'Portal del paciente'),
    ('portal',    'Portal del paciente'),
    ('cuenta',    'Portal del paciente'),
    ('pacientes', 'Portal del paciente'),
    ('turnos',    'Reserva de turnos online'),
    ('ayuda',     'Sitio publico'),
    ('precios',   'Sitio publico'),
    ('registro',  'Sitio publico'),
    ('soporte',   'Sitio publico'),
    ('legal',     'Sitio publico'),
    ('ns1',       'Infraestructura'),
    ('ns2',       'Infraestructura'),
    ('vpn',       'Infraestructura');
