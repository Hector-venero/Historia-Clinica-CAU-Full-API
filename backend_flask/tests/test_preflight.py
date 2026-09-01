"""Que un despliegue mal configurado no arranque.

CLAUDE.md tiene una decena de avisos con la forma "si te olvidas de esto en
produccion, pasa algo malo en silencio". Un aviso en un archivo de texto no
detiene un despliegue.

Lo que estos tests fijan:

1. **En desarrollo no molesta.** Un chequeo que grita siempre deja de leerse, y
   ademas bloquearia el trabajo diario.
2. Lo que impide arrancar es lo que significa **servir de forma insegura sin que
   nadie se entere**. Servir con la clave de sesion del repositorio es que
   cualquiera se firme una cookie de director.
3. Que un aviso no tumbe el arranque. Hay cosas que conviene revisar y pueden
   ser una decision deliberada.
"""

import pytest

from app import preflight


def _produccion(**extra):
    """Un entorno de produccion bien configurado, para ir rompiendolo de a uno."""
    base = {
        "FLASK_ENV": "production",
        "SECRET_KEY": "a" * 64,
        "FRONTEND_URL": "https://fichasalud.com.ar",
        "MULTI_TENANT": "true",
        "DOMINIO_BASE": "fichasalud.com.ar",
        "PLATAFORMA_SECRET_KEY": "x" * 44,
        "MAIL_DEFAULT_SENDER": "hola@fichasalud.com.ar",
        "QBI_BASE_URL": "https://apirecipe.qbitos.com",
        "DB_PASSWORD": "algo-que-no-es-el-ejemplo",
    }
    base.update(extra)
    return base


def _claves(problemas, nivel=None):
    return {c for n, c, _t in problemas if nivel is None or n == nivel}


# ------------------------------------------------------ en desarrollo, silencio


def test_en_desarrollo_no_dice_nada():
    """Todo esto es normal trabajando, y bloquearlo haria imposible trabajar."""
    assert preflight.revisar({"FLASK_ENV": "development"}) == []


def test_sin_flask_env_tampoco():
    """Sin definir, config.py asume development."""
    assert preflight.revisar({"SECRET_KEY": preflight.CLAVE_DE_EJEMPLO}) == []


def test_una_produccion_bien_configurada_pasa_limpia():
    assert preflight.revisar(_produccion()) == []


# --------------------------------------------------- lo que impide arrancar


def test_la_clave_de_ejemplo_impide_arrancar():
    """Esta publicada en el repositorio: con ella cualquiera se firma una cookie
    de sesion valida y entra como director de cualquier consultorio."""
    problemas = preflight.revisar(_produccion(SECRET_KEY=preflight.CLAVE_DE_EJEMPLO))

    assert "SECRET_KEY" in _claves(problemas, preflight.FATAL)


def test_sin_clave_de_sesion_tampoco_arranca():
    entorno = _produccion()
    del entorno["SECRET_KEY"]

    assert "SECRET_KEY" in _claves(preflight.revisar(entorno), preflight.FATAL)


def test_el_depurador_encendido_impide_arrancar():
    """El depurador de Werkzeug expone una consola de Python en el navegador
    ante cualquier excepcion."""
    problemas = preflight.revisar(_produccion(FLASK_DEBUG="true"))

    assert "FLASK_DEBUG" in _claves(problemas, preflight.FATAL)


def test_sin_dominio_base_cualquier_host_es_un_consultorio():
    entorno = _produccion()
    del entorno["DOMINIO_BASE"]

    assert "DOMINIO_BASE" in _claves(preflight.revisar(entorno), preflight.FATAL)


def test_sin_multi_tenant_no_se_exige_dominio_base():
    """La instalacion de un solo centro no tiene subdominios que resolver."""
    entorno = _produccion(MULTI_TENANT="false")
    del entorno["DOMINIO_BASE"]
    del entorno["PLATAFORMA_SECRET_KEY"]

    assert preflight.revisar(entorno) == []


def test_la_cookie_con_dominio_comodin_impide_arrancar():
    """Con un dominio comodin la sesion de un consultorio viaja a todos los
    demas. Es la regla que CLAUDE.md repite tres veces."""
    problemas = preflight.revisar(_produccion(SESSION_COOKIE_DOMAIN=".fichasalud.com.ar"))

    assert "SESSION_COOKIE_DOMAIN" in _claves(problemas, preflight.FATAL)


def test_frontend_sin_https_impide_arrancar():
    problemas = preflight.revisar(_produccion(FRONTEND_URL="http://fichasalud.com.ar"))

    assert "FRONTEND_URL" in _claves(problemas, preflight.FATAL)


def test_apagar_la_cookie_segura_a_mano_impide_arrancar():
    problemas = preflight.revisar(_produccion(SESSION_COOKIE_SECURE="false"))

    assert "SESSION_COOKIE_SECURE" in _claves(problemas, preflight.FATAL)


def test_no_definirla_esta_bien():
    """config.py la deriva del entorno y en produccion da True. Lo que se busca
    es que alguien la haya apagado a mano, no que falte."""
    entorno = _produccion()
    entorno.pop("SESSION_COOKIE_SECURE", None)

    assert "SESSION_COOKIE_SECURE" not in _claves(preflight.revisar(entorno))


# ------------------------------------------------------------- lo que avisa


@pytest.mark.parametrize(
    "clave,entorno",
    [
        ("QBI_BASE_URL", {"QBI_BASE_URL": ""}),
        ("MAIL_DEFAULT_SENDER", {"MAIL_DEFAULT_SENDER": ""}),
        ("DB_PASSWORD", {"DB_PASSWORD": "hc_password"}),
        ("ENABLE_BLOCKCHAIN_TEST_ENDPOINTS", {"ENABLE_BLOCKCHAIN_TEST_ENDPOINTS": "true"}),
    ],
)
def test_avisa_sin_impedir_el_arranque(clave, entorno):
    problemas = preflight.revisar(_produccion(**entorno))

    assert clave in _claves(problemas, preflight.AVISO)
    assert not _claves(problemas, preflight.FATAL)


def test_una_clave_corta_solo_avisa():
    """Es peor que una larga, pero no es la clave publicada del repositorio."""
    problemas = preflight.revisar(_produccion(SECRET_KEY="corta"))

    assert "SECRET_KEY" in _claves(problemas, preflight.AVISO)
    assert not _claves(problemas, preflight.FATAL)


# ---------------------------------------------------------------- exigir()


def test_exigir_levanta_con_lo_fatal():
    with pytest.raises(preflight.ConfiguracionInsegura) as error:
        preflight.exigir(_produccion(SECRET_KEY=preflight.CLAVE_DE_EJEMPLO))

    # El mensaje tiene que decir QUE hacer, no solo que algo esta mal.
    assert "SECRET_KEY" in str(error.value)
    assert "token_hex" in str(error.value)


def test_exigir_devuelve_los_avisos_para_que_se_impriman():
    """Un aviso que nadie ve es lo mismo que no tenerlo."""
    avisos = preflight.exigir(_produccion(QBI_BASE_URL=""))

    assert [c for _n, c, _t in avisos] == ["QBI_BASE_URL"]


def test_exigir_en_desarrollo_no_levanta_nunca():
    assert preflight.exigir({"FLASK_ENV": "development"}) == []
