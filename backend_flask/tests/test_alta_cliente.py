"""Validacion del alta de un consultorio.

Se prueba lo que se puede sin MySQL: las reglas del subdominio y el filtrado del
esquema base. Crear una base y un usuario de MySQL se verifica a mano contra el
stack, porque ahi lo que importa es el GRANT real.
"""

import pytest

from app import alta_cliente
from app.alta_cliente import PATRON_SLUG, AltaInvalida, _es_administrativa, _nombres_mysql


# ------------------------------------------------------------ el subdominio


@pytest.mark.parametrize("slug", ["drlopez", "abc", "con-guion", "clinica2024", "a1b"])
def test_slugs_validos(slug):
    assert PATRON_SLUG.match(slug)


@pytest.mark.parametrize(
    "slug",
    [
        "-empieza-con-guion",
        "termina-con-guion-",
        "MAYUSCULAS",
        "con espacio",
        "con.punto",
        "con_guion_bajo",
        "",
        "x" * 64,  # DNS admite 63 por etiqueta
    ],
)
def test_slugs_invalidos(slug):
    assert not PATRON_SLUG.match(slug)


def test_dos_caracteres_pasan_el_patron():
    """El cuantificador estaba en {1,61}, y eso hacia que el grupo opcional
    exigiera dos caracteres despues del primero: 'a' se aceptaba y 'ab' no."""
    assert PATRON_SLUG.match("ab")


@pytest.mark.parametrize("slug", ["a", "ab"])
def test_los_slugs_muy_cortos_se_rechazan(slug, monkeypatch):
    """Son validos para DNS, pero no sirven como nombre de un consultorio."""
    monkeypatch.setattr(alta_cliente.plataforma, "slug_disponible", lambda s: True)

    with pytest.raises(AltaInvalida, match="demasiado corto"):
        alta_cliente._validar(slug)


def test_un_slug_reservado_se_rechaza(monkeypatch):
    monkeypatch.setattr(alta_cliente.plataforma, "slug_disponible", lambda s: False)

    with pytest.raises(AltaInvalida, match="tomado o es reservado"):
        alta_cliente._validar("admin")


# ------------------------------------------------------------ nombres MySQL


def test_el_usuario_mysql_respeta_el_limite_de_32():
    """MySQL 8 corta los nombres de usuario en 32 caracteres (verificado contra
    information_schema). Un slug largo tiene que recortarse, no fallar."""
    _db, usuario = _nombres_mysql("x" * 63)

    assert len(usuario) <= 32


def test_los_guiones_pasan_a_guion_bajo():
    """El guion es valido en DNS pero incomodo como identificador de MySQL."""
    db, usuario = _nombres_mysql("dr-lopez")

    assert db == "hc_dr_lopez"
    assert usuario == "c_dr_lopez"


# ------------------------------------------------- filtrado del esquema base


@pytest.mark.parametrize(
    "sentencia",
    [
        "CREATE DATABASE IF NOT EXISTS hc_bfa",
        "USE hc_bfa",
        "CREATE USER IF NOT EXISTS 'hc_app'@'%' IDENTIFIED BY 'x'",
        "DROP USER IF EXISTS 'hc_app'@'%'",
        "GRANT SELECT ON hc_bfa.* TO 'hc_app'@'%'",
        "FLUSH PRIVILEGES",
        "SET time_zone = '-3:00'",
        "  set  time_zone = '-3:00'",
    ],
)
def test_las_sentencias_administrativas_no_van_al_inquilino(sentencia):
    """Crean la base del CAU o usuarios con permisos fijos sobre ella: nada de
    eso corresponde a la base de un consultorio."""
    assert _es_administrativa(sentencia)


def test_el_admin_sembrado_no_va_al_inquilino():
    """init.sql siembra un admin con la contrasena 'admin123', publicada en el
    README. Un consultorio nuevo no puede nacer con credenciales conocidas."""
    assert _es_administrativa(
        "INSERT INTO usuarios (nombre, username, password_hash, rol) VALUES ('Admin', 'admin', 'x', 'director')"
    )


@pytest.mark.parametrize(
    "sentencia",
    [
        "CREATE TABLE pacientes (id INT)",
        "ALTER TABLE usuarios ADD COLUMN dni VARCHAR(20)",
        "CREATE INDEX idx_x ON turnos (fecha)",
        "INSERT INTO slugs_reservados (slug) VALUES ('www')",
    ],
)
def test_las_sentencias_de_esquema_si_van(sentencia):
    assert not _es_administrativa(sentencia)
