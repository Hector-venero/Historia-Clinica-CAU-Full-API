# Revisiones del frontend

Dos chequeos mecánicos sobre defectos que **ninguna prueba automática encuentra**
y que solo aparecen usando la app — o revisándola a mano, que es peor porque hay
que acordarse.

```bash
node scripts/revisiones/enlaces_rotos.mjs frontend/src
node scripts/revisiones/modo_oscuro.mjs   frontend/src
```

## `enlaces_rotos.mjs`

Compara los `to="…"` estáticos de las vistas contra las rutas declaradas en el
router. Nació porque el avatar del portal enlazaba a `/portal/perfil`, una ruta
que no existía: el clic caía en el 404 y nadie lo notó hasta abrir la pantalla.

Al 31/08/2026 pasa limpio.

## `modo_oscuro.mjs`

Busca clases claras (`bg-white`, `text-gray-800`, …) sin su variante `dark:` en
el mismo elemento. Un color sin pareja deja esa parte de la pantalla en claro
sobre una app oscura, y es deuda que no ve nadie hasta que un cliente usa el
sistema de noche.

Al 31/08/2026 quedan **26**, todas `text-gray-400`: un gris medio que se lee
sobre los dos fondos. Se dejaron a propósito.

⚠️ Si se automatiza la corrección, **la pareja se busca por prefijo**
(`dark:text-`) y no por familia exacta (`dark:text-gray`): `text-gray-800
dark:text-white` ya está resuelto a mano, y buscar la familia no lo ve y termina
dejando dos `dark:text-*` en la misma clase. Pasó, y hubo que descartar el
cambio entero y rehacerlo.

Los dos **solo informan**: no reescriben nada.
