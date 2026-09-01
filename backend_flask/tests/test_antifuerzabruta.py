"""Freno a los intentos de adivinar una contrasena.

El login no tenia ningun limite: una pagina de entrada publica por cada
subdominio, y del otro lado historias clinicas.

Lo que estos tests fijan, en orden de importancia:

1. **Que no bloquee a quien no ataca.** Una persona real se equivoca varias
   veces con el bloqueo de mayusculas puesto, y dejarla afuera del sistema con
   el que trabaja es peor que el ataque que se esta evitando.
2. **Que la proteccion no se vuelva el ataque.** Contando solo por usuario,
   cualquiera deja afuera al director de un consultorio un lunes a la manana
   escribiendo mal su contrasena diez veces. Por eso la clave principal incluye
   la IP.
3. **Que un fallo de base no deje a nadie afuera.** Este contador es una ayuda;
   romper el login porque no se pudo escribir una fila es mucho peor que el
   problema que resuelve.
4. Que entrar bien limpie el contador propio **pero no el de la IP**.
"""

from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest

from app import antifuerzabruta as afb
from conftest import FakeConnection, FakeCursor

AHORA = datetime(2026, 9, 1, 10, 0, 0)


def _cursor_de(cursor):
    """Un `cursor_de` como el que reciben las funciones del modulo."""

    @contextmanager
    def _cm(commit=False):
        conexion = FakeConnection(cursor)
        yield conexion, cursor

    return _cm


def _con_fila(fallos, hace_minutos=0):
    """Una base falsa donde la primera clave ya tiene fallos anotados."""
    fila = {"fallos": fallos, "ultimo_en": AHORA - timedelta(minutes=hace_minutos)}
    return FakeCursor(fetchone_results=[fila, None])


# ------------------------------------------------------ no molestar al inocente


def test_sin_fallos_previos_deja_pasar():
    cur = FakeCursor(fetchone_results=[None, None])

    afb.revisar(_cursor_de(cur), "alice", "1.2.3.4", ahora=AHORA)


@pytest.mark.parametrize("fallos", range(1, afb.FALLOS_LIBRES + 1))
def test_los_primeros_fallos_no_frenan(fallos):
    """Se equivoca cualquiera. Frenar al segundo intento molesta a todo el mundo
    y no detiene a nadie."""
    afb.revisar(_cursor_de(_con_fila(fallos)), "alice", "1.2.3.4", ahora=AHORA)


def test_los_fallos_viejos_no_cuentan():
    """Sin esto, alguien que se equivoco cinco veces a lo largo de un ano
    arrancaria bloqueado."""
    viejo = _con_fila(50, hace_minutos=afb.VENTANA_MINUTOS + 1)

    afb.revisar(_cursor_de(viejo), "alice", "1.2.3.4", ahora=AHORA)


def test_cuando_la_espera_ya_paso_deja_pasar():
    # 6 fallos = 1 minuto de espera; pasaron 5.
    cur = _con_fila(afb.FALLOS_LIBRES + 1, hace_minutos=5)

    afb.revisar(_cursor_de(cur), "alice", "1.2.3.4", ahora=AHORA)


# --------------------------------------------------------------- si frena, frena


def test_pasado_el_limite_hay_que_esperar():
    cur = _con_fila(afb.FALLOS_LIBRES + 1)

    with pytest.raises(afb.DemasiadosIntentos):
        afb.revisar(_cursor_de(cur), "alice", "1.2.3.4", ahora=AHORA)


def test_la_espera_crece_con_los_intentos():
    """Mil intentos pasan a ser dias, que es lo unico que hace falta: nadie deja
    corriendo un ataque que rinde dos intentos por hora."""
    poco = afb._espera(afb.FALLOS_LIBRES + 1, afb.FALLOS_LIBRES)
    mucho = afb._espera(afb.FALLOS_LIBRES + 5, afb.FALLOS_LIBRES)

    assert mucho > poco


def test_la_espera_tiene_tope():
    """Sin tope, treinta fallos serian anios de bloqueo: eso ya no es un freno,
    es perder la cuenta."""
    enorme = afb._espera(afb.FALLOS_LIBRES + 100, afb.FALLOS_LIBRES)

    assert enorme == timedelta(minutes=afb.ESPERA_MAXIMA_MINUTOS)


# ---------------------------------------------- que la proteccion no sea el ataque


def test_la_clave_principal_incluye_la_ip():
    """Contando solo por usuario, cualquiera deja afuera al director de un
    consultorio escribiendo mal su contrasena diez veces."""
    (clave_usuario, _), (clave_ip, _) = afb._claves("alice", "1.2.3.4")

    assert clave_usuario == "u:alice|1.2.3.4"
    assert clave_ip == "ip:1.2.3.4"


def test_la_ip_sola_tolera_mas_fallos():
    """En un consultorio todo el equipo sale por la misma IP: cuatro personas
    equivocandose no son un ataque."""
    assert afb.FALLOS_LIBRES_POR_IP > afb.FALLOS_LIBRES


def test_el_usuario_se_normaliza():
    """`Alice` y `alice` son la misma cuenta; si no, cambiar una mayuscula
    reiniciaria el contador."""
    (clave, _), _ = afb._claves("  ALICE  ", "1.2.3.4")

    assert clave == "u:alice|1.2.3.4"


def test_la_clave_entra_en_la_columna():
    """La PRIMARY KEY es VARCHAR(190): el usuario llega del pedido y puede venir
    de cualquier largo."""
    (clave, _), _ = afb._claves("a" * 500, "b" * 500)

    assert len(clave) <= 190


# --------------------------------------------------------- ante la duda, pasar


def test_si_la_base_falla_no_bloquea():
    """Dejar a todo el mundo afuera porque fallo una consulta de este contador
    es peor que el problema que resuelve."""

    @contextmanager
    def _rota(commit=False):
        raise RuntimeError("base caida")
        yield  # pragma: no cover

    afb.revisar(_rota, "alice", "1.2.3.4", ahora=AHORA)


def test_si_no_se_puede_anotar_el_fallo_no_revienta():
    """Que no se pueda escribir el contador no puede impedir responder al
    login."""

    @contextmanager
    def _rota(commit=False):
        raise RuntimeError("base caida")
        yield  # pragma: no cover

    afb.registrar_fallo(_rota, "alice", "1.2.3.4", ahora=AHORA)


# --------------------------------------------------------------- entrar y salir


def test_registrar_fallo_anota_las_dos_claves():
    cur = FakeCursor()

    afb.registrar_fallo(_cursor_de(cur), "alice", "1.2.3.4", ahora=AHORA)

    claves = [params[0] for _q, params in cur.executed]
    assert claves == ["u:alice|1.2.3.4", "ip:1.2.3.4"]


def test_registrar_fallo_reinicia_lo_viejo_en_la_misma_sentencia():
    """Leer y despues escribir deja una ventana entre las dos donde dos pedidos
    simultaneos pisan el conteo."""
    cur = FakeCursor()

    afb.registrar_fallo(_cursor_de(cur), "alice", "1.2.3.4", ahora=AHORA)

    consulta = " ".join(cur.queries[0].split())
    assert "ON DUPLICATE KEY UPDATE" in consulta
    assert "IF(ultimo_en < %s, 1, fallos + 1)" in consulta


def test_entrar_bien_limpia_solo_el_contador_propio():
    """Si limpiara tambien el de la IP, un atacante que conoce una cuenta propia
    entra con ella cada cinco intentos y sigue probando con las demas."""
    cur = FakeCursor()

    afb.limpiar(_cursor_de(cur), "alice", "1.2.3.4")

    assert len(cur.executed) == 1
    assert cur.executed[0][1] == ("u:alice|1.2.3.4",)


# ------------------------------------------------------------------- el mensaje


def test_el_mensaje_dice_cuanto_falta():
    """"Demasiados intentos" a secas hace recargar cada dos segundos, que es
    exactamente lo que se esta tratando de evitar."""
    assert "30 segundos" in afb.mensaje(afb.DemasiadosIntentos(30))
    assert "1 minuto" in afb.mensaje(afb.DemasiadosIntentos(60))
    assert "5 minutos" in afb.mensaje(afb.DemasiadosIntentos(300))


def test_el_instante_se_guarda_al_segundo():
    """MySQL REDONDEA al guardar en un DATETIME sin fraccion: 13:08:46.7 queda
    como 13:08:47, medio segundo en el futuro. Al releerlo, el ultimo fallo
    quedaba despues de "ahora" y el pedido siguiente se rechazaba aunque el
    contador estuviera en cero.

    Se veia contra el stack real como un bloqueo de un segundo despues de CADA
    fallo, incluido el primero.
    """
    cur = FakeCursor()
    con_fraccion = AHORA.replace(microsecond=700000)

    afb.registrar_fallo(_cursor_de(cur), "alice", "1.2.3.4", ahora=con_fraccion)

    guardado = cur.executed[0][1][1]
    assert guardado.microsecond == 0
    assert guardado == AHORA


def test_un_fallo_recien_anotado_no_bloquea_el_intento_siguiente():
    """El caso exacto del bug: un solo fallo, muy por debajo del limite."""
    cur = _con_fila(1, hace_minutos=0)

    afb.revisar(_cursor_de(cur), "alice", "1.2.3.4", ahora=AHORA.replace(microsecond=1))
