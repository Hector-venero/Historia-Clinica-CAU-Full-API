-- El ENUM cert_discapacidad quedo con su propia definicion doble-codificada.
--
-- En las bases creadas por el cliente latin1 (ver 20260901_reparar_doble_utf8),
-- la columna no quedo como ENUM('Sí','No') sino como ENUM('SÃ­','No'). No es un
-- dato mal guardado: es la **definicion de la columna**. La consecuencia es peor
-- que un acento feo — guardar 'Sí' desde la aplicacion no coincide con ningun
-- valor del ENUM y MySQL lo rechaza o lo guarda vacio.
--
-- Lo detecto scripts/comparar_esquemas.sh al comparar una base nueva contra una
-- migrada, que es exactamente para lo que existe.
--
-- MySQL guarda el ENUM por indice, no por texto: al renombrar el primer valor,
-- las filas que ya lo tenian siguen apuntando al indice 1 y pasan a leerse
-- 'Sí'. Por eso alcanza con MODIFY y no hace falta tocar los datos.

ALTER TABLE pacientes MODIFY cert_discapacidad ENUM('Sí', 'No') DEFAULT NULL;
