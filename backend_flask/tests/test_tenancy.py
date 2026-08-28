"""Resolucion del consultorio a partir del subdominio.

Es la pieza de la que depende el aislamiento: si `slug_desde_host` devuelve el
slug equivocado, un consultorio termina conectado a la base de otro. Por eso se
prueba con mas casos de borde que el resto.
"""

import pytest

from app import tenancy


@pytest.fixture(autouse=True)
def _cache_limpio():
    """El cache es de modulo: sin limpiarlo, un test contamina al siguiente."""
    tenancy.olvidar()
    yield
    tenancy.olvidar()


# ------------------------------------------------- el slug sale del Host


@pytest.mark.parametrize(
    "host, esperado",
    [
        ("drlopez.miproducto.com", "drlopez"),
        ("DRLOPEZ.MiProducto.com", "drlopez"),      # se normaliza a minusculas
        ("drlopez.miproducto.com:5000", "drlopez"),  # con puerto (desarrollo)
        ("drlopez.miproducto.com.", "drlopez"),      # con punto final (FQDN)
        ("clinica-sur.miproducto.com", "clinica-sur"),
    ],
)
def test_slug_desde_el_host(monkeypatch, host, esperado):
    monkeypatch.setenv("DOMINIO_BASE", "miproducto.com")

    assert tenancy.slug_desde_host(host) == esperado


@pytest.mark.parametrize(
    "host",
    [
        "miproducto.com",            # el dominio raiz es el sitio publico
        "www.miproducto.com",
        "api.miproducto.com",
        "app.miproducto.com",
        "a.b.miproducto.com",        # varios niveles no son un cliente
        "otrodominio.com",           # no cuelga del dominio base
        "drlopez.otrodominio.com",
        "",
        None,
    ],
)
def test_hosts_que_no_son_un_consultorio(monkeypatch, host):
    monkeypatch.setenv("DOMINIO_BASE", "miproducto.com")

    assert tenancy.slug_desde_host(host) is None


def test_sin_dominio_base_se_toma_la_primera_etiqueta(monkeypatch):
    """Modo desarrollo: drlopez.localhost. En produccion conviene declarar
    DOMINIO_BASE, o cualquier host que apunte al servidor resolveria."""
    monkeypatch.delenv("DOMINIO_BASE", raising=False)

    assert tenancy.slug_desde_host("drlopez.localhost") == "drlopez"
    assert tenancy.slug_desde_host("localhost") is None


def test_un_host_de_otro_dominio_no_resuelve(monkeypatch):
    """Sin esto, apuntar cualquier dominio propio al servidor daria acceso al
    consultorio que coincida con su primera etiqueta."""
    monkeypatch.setenv("DOMINIO_BASE", "miproducto.com")

    assert tenancy.slug_desde_host("drlopez.sitio-de-un-atacante.com") is None


# ------------------------------------------------------------- el cache


def test_el_cliente_se_cachea(monkeypatch):
    llamadas = []

    def falso_buscar(slug):
        llamadas.append(slug)
        return object()

    monkeypatch.setattr(tenancy.plataforma, "buscar_por_slug", falso_buscar)

    tenancy.resolver("drlopez")
    tenancy.resolver("drlopez")
    tenancy.resolver("drlopez")

    assert llamadas == ["drlopez"], "El plano de control se consulto de mas"


def test_un_cliente_inexistente_no_se_cachea(monkeypatch):
    """Cachear el None dejaria a un consultorio recien dado de alta sin entrar
    hasta que venciera el TTL."""
    llamadas = []

    def falso_buscar(slug):
        llamadas.append(slug)
        return None

    monkeypatch.setattr(tenancy.plataforma, "buscar_por_slug", falso_buscar)

    tenancy.resolver("nuevo")
    tenancy.resolver("nuevo")

    assert len(llamadas) == 2


def test_el_cache_vence(monkeypatch):
    monkeypatch.setattr(tenancy, "TTL_CACHE_SEGUNDOS", 0)
    llamadas = []
    monkeypatch.setattr(
        tenancy.plataforma, "buscar_por_slug", lambda s: llamadas.append(s) or object()
    )

    tenancy.resolver("drlopez")
    tenancy.resolver("drlopez")

    assert len(llamadas) == 2


def test_olvidar_invalida_un_slug(monkeypatch):
    """Suspender a un cliente tiene que surtir efecto sin esperar el TTL."""
    llamadas = []
    monkeypatch.setattr(
        tenancy.plataforma, "buscar_por_slug", lambda s: llamadas.append(s) or object()
    )

    tenancy.resolver("drlopez")
    tenancy.olvidar("drlopez")
    tenancy.resolver("drlopez")

    assert len(llamadas) == 2


# ------------------------------------------------------- el interruptor


def test_multi_tenant_esta_apagado_por_defecto(monkeypatch):
    """La instalacion del CAU corre este mismo codigo: sin el interruptor, todo
    tiene que comportarse como un solo consultorio."""
    monkeypatch.delenv("MULTI_TENANT", raising=False)

    assert tenancy.multi_tenant_activo() is False


@pytest.mark.parametrize("valor, esperado", [("true", True), ("TRUE", True), ("false", False), ("1", False), ("", False)])
def test_el_interruptor_solo_acepta_true(monkeypatch, valor, esperado):
    monkeypatch.setenv("MULTI_TENANT", valor)

    assert tenancy.multi_tenant_activo() is esperado


# ------------------------------------------- la sesion queda atada al cliente


class _ClienteFalso:
    """Doble del Cliente del plano de control.

    Expone lo mismo que la clase real: si le falta algo que el codigo consulta
    —`config` y `nombre` los lee app/marca.py— el test falla por AttributeError
    y no por lo que pretendia comprobar.
    """

    def __init__(self, slug, estado="activo", nombre=None, config=None):
        self.slug = slug
        self.estado = estado
        self.activo = estado in ("prueba", "activo")
        self.nombre = nombre or f"Consultorio {slug}"
        self.plan = "basico"
        self.prueba_hasta = None
        self.config = config or {}


def _modo_multi(monkeypatch, clientes):
    """Enciende la multi-tenencia y resuelve contra un catalogo de mentira."""
    monkeypatch.setattr(tenancy, "multi_tenant_activo", lambda: True)
    monkeypatch.setattr(tenancy, "slug_desde_host", lambda host: (host or "").split(".")[0] or None)
    monkeypatch.setattr(tenancy, "resolver", lambda slug: clientes.get(slug))


def test_una_sesion_de_otro_consultorio_se_rechaza(client, monkeypatch):
    """La cookie va firmada con SECRET_KEY, que es la misma para todos los
    clientes, y adentro solo lleva el id del usuario. Como cada base tiene su
    propio usuario 1, sin esta comprobacion una sesion de un consultorio
    autenticaba en otro: comprobado reenviando la cookie a mano, respondia 200.
    """
    _modo_multi(monkeypatch, {"a": _ClienteFalso("a"), "b": _ClienteFalso("b")})

    with client.session_transaction() as sesion:
        sesion[tenancy.CLAVE_SESION] = "a"

    respuesta = client.get("/api/usuarios/me", headers={"Host": "b.localhost"})

    assert respuesta.status_code == 401


def test_la_sesion_vale_en_su_propio_consultorio(client, monkeypatch):
    _modo_multi(monkeypatch, {"a": _ClienteFalso("a")})

    with client.session_transaction() as sesion:
        sesion[tenancy.CLAVE_SESION] = "a"

    respuesta = client.get("/api/health/public", headers={"Host": "a.localhost"})

    assert respuesta.status_code == 200


def test_un_consultorio_suspendido_no_puede_operar(client, monkeypatch):
    """Se corta el uso del sistema para trabajar."""
    _modo_multi(monkeypatch, {"a": _ClienteFalso("a", estado="suspendido")})

    respuesta = client.get("/api/pacientes", headers={"Host": "a.localhost"})

    assert respuesta.status_code == 402
    assert respuesta.get_json()["estado"] == "suspendido"


def test_un_consultorio_suspendido_igual_puede_llevarse_sus_datos(client, monkeypatch):
    """Suspender por falta de pago no puede significar secuestrar historias
    clinicas: son datos del paciente, no del proveedor.

    Estas rutas siguen atendiendo con la cuenta suspendida. Que devuelvan 401 sin
    sesion y no 402 es justamente lo que se comprueba: llegaron al control de
    autenticacion en vez de rebotar antes por el estado de la cuenta."""
    _modo_multi(monkeypatch, {"a": _ClienteFalso("a", estado="suspendido")})

    for ruta in ("/api/cuenta/estado", "/api/cuenta/exportar", "/api/usuarios/me"):
        respuesta = client.get(ruta, headers={"Host": "a.localhost"})
        assert respuesta.status_code != 402, f"{ruta} quedo bloqueada por el estado"


def test_la_marca_se_ve_aunque_la_cuenta_este_suspendida(client, monkeypatch):
    """La pantalla que explica la suspension tiene que poder mostrar de quien
    es el consultorio."""
    _modo_multi(monkeypatch, {"a": _ClienteFalso("a", estado="suspendido")})

    respuesta = client.get("/api/publico/marca", headers={"Host": "a.localhost"})

    assert respuesta.status_code == 200


def test_un_consultorio_inexistente_da_404(client, monkeypatch):
    _modo_multi(monkeypatch, {})

    respuesta = client.get("/api/usuarios/me", headers={"Host": "fantasma.localhost"})

    assert respuesta.status_code == 404


def test_el_chequeo_de_salud_responde_sin_consultorio(client, monkeypatch):
    """Lo mira el monitoreo de la plataforma, no el de un cliente."""
    _modo_multi(monkeypatch, {})

    respuesta = client.get("/api/health/public", headers={"Host": "fantasma.localhost"})

    assert respuesta.status_code == 200
