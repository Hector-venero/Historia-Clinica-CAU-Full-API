# Migraciones del plano del paciente

Cambios al esquema de la base `portal` (cuentas de pacientes y el buzón de
documentos). Separadas de las de los consultorios y de las del plano de control:
son tres esquemas distintos y no tienen por qué avanzar al mismo ritmo.

`db/portal/init.sql` solo corre al crear el plano. Todo cambio posterior va acá,
con el mismo formato: `AAAAMMDD_descripcion.sql`, una cláusula por sentencia.
