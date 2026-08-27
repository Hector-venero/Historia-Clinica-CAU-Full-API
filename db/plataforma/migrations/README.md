# Migraciones del plano de control

Cambios al esquema de la base `plataforma` (clientes, su configuración, slugs
reservados). Están separadas de `db/migrations/` a propósito: son esquemas
distintos y no tienen por qué avanzar al mismo ritmo.

`db/plataforma/init.sql` solo corre al crear la plataforma. Todo cambio
posterior va acá, con el mismo formato que las de los inquilinos:
`AAAAMMDD_descripcion.sql`, una cláusula por sentencia.

Las aplica `migrate.py --plataforma`, y `--todos` las corre antes que las de los
consultorios: la lista de clientes sale de esta base, así que su esquema tiene
que estar al día antes de recorrerla.
