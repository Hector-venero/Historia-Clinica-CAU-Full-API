"""Tests del runner de migraciones.

El caso central es el que rompio en produccion: un apostrofe dentro de un
comentario SQL ("doesn't") hacia que el parser creyera estar dentro de un
literal y se tragara todos los punto y coma siguientes, colapsando el archivo
entero en una sola sentencia.
"""

import pathlib
import sys

import pytest

def _buscar_hacia_arriba(relativo):
    """Busca un path relativo subiendo desde este archivo.

    Se evita indexar parents[] con numeros fijos: los tests corren tanto desde
    backend_flask/ como montados en otra ruta dentro del contenedor, y un indice
    fijo revienta con IndexError segun donde esten.
    """
    for base in pathlib.Path(__file__).resolve().parents:
        candidato = base / relativo
        if candidato.exists():
            return candidato
    return None


APP_DIR = _buscar_hacia_arriba("app/migrate.py")
if APP_DIR is not None:
    sys.path.insert(0, str(APP_DIR.parent))

migrate = pytest.importorskip("migrate", reason="no se encontro app/migrate.py")

split_statements = migrate.split_statements
es_alter_compuesto = migrate.es_alter_compuesto
_contar_clausulas_alter = migrate._contar_clausulas_alter

MIGRATIONS_DIR = _buscar_hacia_arriba("db/migrations")


# ---------------------------------------------------------------- split


def test_apostrofe_en_comentario_no_traga_las_sentencias():
    sql = """
    -- El dashboard rompe (Table 'comunicados' doesn't exist).
    CREATE TABLE a (id INT);
    CREATE TABLE b (id INT);
    CREATE TABLE c (id INT);
    """
    assert len(split_statements(sql)) == 3


def test_comentario_de_bloque_y_numeral():
    sql = """
    /* comentario ; con punto y coma
       y varias lineas */
    CREATE TABLE a (id INT);
    # otro comentario ; con punto y coma
    CREATE TABLE b (id INT);
    """
    assert len(split_statements(sql)) == 2


def test_punto_y_coma_dentro_de_literal_no_separa():
    sql = "INSERT INTO t (c) VALUES ('a;b'); INSERT INTO t (c) VALUES ('c;d');"
    sentencias = split_statements(sql)
    assert len(sentencias) == 2
    assert "'a;b'" in sentencias[0]


def test_comilla_duplicada_dentro_de_literal():
    sql = "INSERT INTO t (c) VALUES ('no''existe'); CREATE TABLE b (id INT);"
    assert len(split_statements(sql)) == 2


def test_backticks_con_punto_y_coma():
    sql = "CREATE TABLE `raro;nombre` (id INT); CREATE TABLE b (id INT);"
    assert len(split_statements(sql)) == 2


def test_sentencia_final_sin_punto_y_coma():
    assert len(split_statements("CREATE TABLE a (id INT)")) == 1


def test_script_vacio_o_solo_comentarios():
    assert split_statements("") == []
    assert split_statements("-- nada\n# tampoco\n") == []


# ---------------------------------------------------------------- ALTER


def test_detecta_alter_compuesto():
    assert es_alter_compuesto("ALTER TABLE t ADD COLUMN a INT, ADD COLUMN b INT")


def test_alter_de_una_clausula_no_es_compuesto():
    assert not es_alter_compuesto("ALTER TABLE t ADD COLUMN a INT")


def test_comas_dentro_de_parentesis_no_cuentan_como_clausulas():
    # El ENUM y el indice compuesto traen comas que no separan clausulas.
    sentencia = "ALTER TABLE t ADD COLUMN a ENUM('x', 'y', 'z') DEFAULT NULL"
    assert _contar_clausulas_alter(sentencia) == 1
    assert not es_alter_compuesto(sentencia)

    indice = "ALTER TABLE t ADD INDEX idx (col_a, col_b)"
    assert not es_alter_compuesto(indice)


def test_create_table_nunca_es_alter_compuesto():
    assert not es_alter_compuesto("CREATE TABLE t (a INT, b INT, c INT)")


# ---------------------------------------------- las migraciones reales


@pytest.mark.skipif(MIGRATIONS_DIR is None, reason="sin db/migrations")
def test_ninguna_migracion_tiene_alter_compuesto():
    """Un ALTER compuesto no se puede aplicar de forma idempotente.

    MySQL lo evalua atomicamente: si una clausula choca con "ya existe", se
    pierde el statement entero, y el runner no puede distinguir eso de "ya
    estaba aplicado".
    """
    ofensores = []
    for archivo in sorted(MIGRATIONS_DIR.glob("*.sql")):
        for sentencia in split_statements(archivo.read_text(encoding="utf-8")):
            if es_alter_compuesto(sentencia):
                ofensores.append(f"{archivo.name}: {sentencia[:80]}")
    assert not ofensores, "ALTERs compuestos encontrados:\n" + "\n".join(ofensores)


@pytest.mark.skipif(MIGRATIONS_DIR is None, reason="sin db/migrations")
def test_grupos_comunicados_parsea_cinco_sentencias():
    """Regresion del bug del apostrofe: este archivo colapsaba a 1 sentencia."""
    archivo = MIGRATIONS_DIR / "20260624_grupos_comunicados.sql"
    if not archivo.exists():
        pytest.skip("migracion no presente")
    assert len(split_statements(archivo.read_text(encoding="utf-8"))) == 5
