"""Reglas de las migraciones que se pueden verificar sin levantar MySQL.

La comparacion real entre init.sql y las migraciones NO se hace acá: leer el SQL
como texto es demasiado fragil (no distingue una columna base de una agregada,
ni entiende MODIFY). Para eso está scripts/comparar_esquemas.sh, que construye
las dos bases y diffea el esquema resultante.

Acá quedan los chequeos baratos, que igual atrapan errores reales.

Hay dos caminos para llegar al esquema: una base nueva lo crea desde init.sql, y
una existente lo alcanza aplicando migraciones. Nada garantizaba que
coincidieran, y ya pasó dos veces que una columna llegara solo a init.sql:

  - disponibilidades: el valor 'Domingo' del ENUM. En bases migradas, guardar
    una disponibilidad de domingo fallaba con 1265 "Data truncated".
  - grupos_profesionales.es_rehabilitacion. El listado de turnos grupales
    fallaba con 1054 "Unknown column".

Los dos aparecieron en runtime, con la app andando. Estos tests comparan las dos
definiciones leyendo el SQL, sin necesidad de levantar MySQL.
"""

import pathlib
import re

import pytest


def _buscar_hacia_arriba(relativo):
    for base in pathlib.Path(__file__).resolve().parents:
        candidato = base / relativo
        if candidato.exists():
            return candidato
    return None


INIT_SQL = _buscar_hacia_arriba("db/init.sql")
MIGRACIONES = _buscar_hacia_arriba("db/migrations")

pytestmark = pytest.mark.skipif(
    INIT_SQL is None or MIGRACIONES is None,
    reason="no se encontraron db/init.sql o db/migrations",
)

# Palabras con las que empieza una línea que no declara una columna.
NO_SON_COLUMNAS = (
    "--", "#", "FOREIGN KEY", "UNIQUE", "INDEX", "PRIMARY KEY",
    "CONSTRAINT", "KEY ", "ENGINE", ")",
)


def test_las_migraciones_no_usan_alter_compuesto():
    """MySQL evalúa un ALTER de varias cláusulas de forma atómica.

    Si una choca con "ya existe", se pierde el statement entero y el runner no
    puede distinguirlo de "ya estaba aplicado".
    """
    import sys

    app_dir = _buscar_hacia_arriba("app/migrate.py")
    if app_dir:
        sys.path.insert(0, str(app_dir.parent))
    migrate = pytest.importorskip("migrate")

    ofensores = []
    for archivo in sorted(MIGRACIONES.glob("*.sql")):
        for sentencia in migrate.split_statements(archivo.read_text(encoding="utf-8")):
            if migrate.es_alter_compuesto(sentencia):
                ofensores.append(f"{archivo.name}: {sentencia[:70]}")

    assert not ofensores, "ALTER compuestos:\n  " + "\n  ".join(ofensores)


def test_las_migraciones_se_ordenan_por_fecha():
    """El runner las aplica con sorted() sobre el nombre.

    Sin el prefijo YYYYMMDD el orden alfabético no coincide con el cronológico y
    una migración podría correr antes que aquella de la que depende.
    """
    sin_prefijo = [
        a.name for a in MIGRACIONES.glob("*.sql")
        if not re.match(r"^\d{8}_", a.name)
    ]

    assert not sin_prefijo, (
        "Migraciones sin prefijo de fecha:\n  " + "\n  ".join(sin_prefijo)
    )


def test_no_hay_migraciones_fuera_del_directorio():
    """Un .sql suelto en db/ parece una migración pero el runner no lo mira."""
    db = MIGRACIONES.parent
    sueltos = [
        a.name for a in db.glob("*.sql")
        if a.name not in ("init.sql", "dev_reset.sql")
    ]

    assert not sueltos, (
        "Archivos .sql en db/ que el runner nunca ejecuta. Si son migraciones, "
        "van en db/migrations/:\n  " + "\n  ".join(sueltos)
    )
