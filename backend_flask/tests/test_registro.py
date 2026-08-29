"""Alta autoservicio: lo que se puede probar sin MySQL.

Las reglas de validacion y el orden del recorrido. Que la base se cree de verdad
se verifica contra el stack, porque ahi lo que importa es el CREATE real.
"""

import pytest

from app import registro


class PlataformaFalsa:
    """Doble del plano de control. Registra lo que se le pidio."""

    def __init__(self, ocupados=()):
        self.ocupados = set(ocupados)
        self.insertados = []
        self.borrados = []

    def slug_disponible(self, slug):
        return slug not in self.ocupados


@pytest.fixture
def plataforma_falsa(monkeypatch):
    doble = PlataformaFalsa(ocupados={"drlopez", "www"})
    monkeypatch.setattr(registro.plataforma, "slug_disponible", doble.slug_disponible)
    return doble


# ------------------------------------------------------------ la direccion


@pytest.mark.parametrize("slug", ["dentalsur", "abc", "con-guion", "clinica2024"])
def test_direcciones_validas(slug, plataforma_falsa):
    assert registro.validar_slug(slug) == slug


def test_la_direccion_se_normaliza_a_minusculas(plataforma_falsa):
    """El formulario acepta mayusculas pero la direccion es una etiqueta DNS.

    Se devuelve normalizada para que la pantalla muestre la que va a quedar y no
    la que se escribio.
    """
    assert registro.validar_slug("  DentalSur  ") == "dentalsur"


@pytest.mark.parametrize("slug", ["ab", "a", ""])
def test_las_direcciones_muy_cortas_se_rechazan(slug, plataforma_falsa):
    """Minimo 3: los subdominios de una o dos letras son los mas cotizados y no
    se reparten por orden de llegada."""
    with pytest.raises(registro.ErrorRegistro):
        registro.validar_slug(slug)


@pytest.mark.parametrize(
    "slug", ["-empieza", "termina-", "con espacio", "con.punto", "con_guion", "x" * 64]
)
def test_las_direcciones_mal_formadas_se_rechazan(slug, plataforma_falsa):
    with pytest.raises(registro.ErrorRegistro):
        registro.validar_slug(slug)


def test_una_direccion_tomada_se_rechaza(plataforma_falsa):
    with pytest.raises(registro.ErrorRegistro) as exc:
        registro.validar_slug("drlopez")
    assert "no esta disponible" in str(exc.value)


def test_una_direccion_reservada_da_el_mismo_mensaje_que_una_tomada(plataforma_falsa):
    """Distinguirlas permitiria averiguar que consultorios existen probando."""
    with pytest.raises(registro.ErrorRegistro) as tomada:
        registro.validar_slug("drlopez")
    with pytest.raises(registro.ErrorRegistro) as reservada:
        registro.validar_slug("www")

    assert str(tomada.value) == str(reservada.value)


# ------------------------------------------------------------- los datos


def test_el_nombre_es_obligatorio(plataforma_falsa):
    with pytest.raises(registro.ErrorRegistro):
        registro._validar_datos({"nombre": "ab", "email": "a@b.com", "password": "Prueba123!"})


def test_el_correo_se_valida(plataforma_falsa):
    with pytest.raises(registro.ErrorRegistro) as exc:
        registro._validar_datos(
            {"nombre": "Consultorio", "email": "no-es-un-correo", "password": "Prueba123!"}
        )
    assert "correo" in str(exc.value).lower()


def test_la_contrasena_debe_ser_fuerte(plataforma_falsa):
    """Es la del director del consultorio: la cuenta con mas privilegios."""
    with pytest.raises(registro.ErrorRegistro):
        registro._validar_datos(
            {"nombre": "Consultorio", "email": "a@b.com", "password": "corta"}
        )


def test_el_correo_se_normaliza_a_minusculas(plataforma_falsa):
    _nombre, email, _pw = registro._validar_datos(
        {"nombre": "Consultorio", "email": "  Dental@Ejemplo.COM ", "password": "Prueba123!"}
    )
    assert email == "dental@ejemplo.com"


# --------------------------------------------------------- el recorrido


def test_registrar_no_crea_ninguna_base(monkeypatch, plataforma_falsa):
    """El formulario es publico. Crear la base antes de verificar el correo
    permitiria llenar el servidor de bases vacias con un script."""
    llamadas = []

    class CursorFalso:
        def execute(self, *a, **k):
            llamadas.append(a[0].split()[0].upper())

    class ContextoFalso:
        def __enter__(self):
            return (None, CursorFalso())

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(
        registro.plataforma, "cursor_plataforma", lambda commit=False: ContextoFalso()
    )

    def no_llamar(*a, **k):
        raise AssertionError("no se debe crear la base al registrarse")

    monkeypatch.setattr("app.alta_cliente.dar_de_alta", no_llamar, raising=False)

    token = registro.registrar(
        {
            "slug": "dentalsur",
            "nombre": "Consultorio Dental Sur",
            "email": "dental@ejemplo.com",
            "password": "Prueba123!",
        }
    )

    assert len(token) == 64
    assert "INSERT" in llamadas


def test_la_contrasena_no_se_guarda_en_claro(monkeypatch, plataforma_falsa):
    """Entre el registro y la verificacion puede pasar un dia."""
    guardados = []

    class CursorFalso:
        def execute(self, sql, params=None):
            if params:
                guardados.append(params)

    class ContextoFalso:
        def __enter__(self):
            return (None, CursorFalso())

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(
        registro.plataforma, "cursor_plataforma", lambda commit=False: ContextoFalso()
    )

    registro.registrar(
        {
            "slug": "dentalsur",
            "nombre": "Consultorio Dental Sur",
            "email": "dental@ejemplo.com",
            "password": "Prueba123!",
        }
    )

    # Se busca el hash entre los parametros en lugar de contarlos por posicion:
    # el INSERT gano una columna al agregar el tipo de alta, y un test que cuenta
    # parametros se rompe con cada campo nuevo sin que nada este mal.
    valores = [str(v) for params in guardados for v in params]

    assert not any("Prueba123!" == v for v in valores), "la contrasena viaja en claro"
    assert any(v.startswith("scrypt:") for v in valores), "no se guardo el hash"


def test_un_enlace_invalido_no_revela_nada(monkeypatch):
    monkeypatch.setattr(registro, "buscar_por_token", lambda t: None)
    with pytest.raises(registro.ErrorRegistro) as exc:
        registro.verificar_y_crear("token-que-no-existe")
    assert "no es valido" in str(exc.value)


def test_reabrir_un_enlace_ya_usado_no_crea_un_segundo_consultorio(monkeypatch):
    fila = {"estado": "listo", "slug": "dentalsur", "email": "a@b.com"}
    monkeypatch.setattr(registro, "buscar_por_token", lambda t: fila)

    def no_llamar(*a, **k):
        raise AssertionError("no se debe volver a crear el consultorio")

    monkeypatch.setattr("app.alta_cliente.dar_de_alta", no_llamar, raising=False)

    assert registro.verificar_y_crear("token")["estado"] == "listo"


def test_un_enlace_vencido_se_rechaza(monkeypatch):
    from datetime import datetime, timedelta

    fila = {
        "estado": "pendiente",
        "slug": "dentalsur",
        "expira_en": datetime.now() - timedelta(hours=1),
    }
    monkeypatch.setattr(registro, "buscar_por_token", lambda t: fila)

    with pytest.raises(registro.ErrorRegistro) as exc:
        registro.verificar_y_crear("token")
    assert "vencio" in str(exc.value)


def test_si_alguien_tomo_la_direccion_mientras_tanto_se_avisa(monkeypatch):
    """Entre el registro y la verificacion pueden pasar 48 horas."""
    from datetime import datetime, timedelta

    fila = {
        "estado": "pendiente",
        "slug": "dentalsur",
        "expira_en": datetime.now() + timedelta(hours=1),
    }
    monkeypatch.setattr(registro, "buscar_por_token", lambda t: fila)
    monkeypatch.setattr(registro.plataforma, "slug_disponible", lambda s: False)

    with pytest.raises(registro.ErrorRegistro) as exc:
        registro.verificar_y_crear("token")
    assert "otra" in str(exc.value)


# --------------------------------------------------- alta de instituciones


def test_el_tipo_de_alta_se_valida(plataforma_falsa):
    with pytest.raises(registro.ErrorRegistro):
        registro.registrar({
            "tipo": "inventado", "slug": "clinicanorte", "nombre": "Clinica Norte",
            "email": "a@b.com", "password": "Prueba123!",
        })


def test_una_institucion_necesita_un_contacto(plataforma_falsa):
    """Es una conversacion comercial: hay que saber con quien hablar."""
    with pytest.raises(registro.ErrorRegistro) as exc:
        registro._validar_institucion({"contacto_telefono": "11 5555-1234"})
    assert "con quien hablar" in str(exc.value)


def test_una_institucion_necesita_un_telefono(plataforma_falsa):
    with pytest.raises(registro.ErrorRegistro) as exc:
        registro._validar_institucion({"contacto_nombre": "Laura Diaz"})
    assert "telefono" in str(exc.value)


def test_la_cantidad_de_profesionales_tiene_que_ser_un_numero(plataforma_falsa):
    with pytest.raises(registro.ErrorRegistro):
        registro._validar_institucion({
            "contacto_nombre": "Laura", "contacto_telefono": "11 5555-1234",
            "cantidad_profesionales": "muchos",
        })


def test_verificar_una_institucion_no_crea_la_base(monkeypatch):
    """El punto entero del circuito de aprobacion.

    Crear la base al verificar el correo significaria que cualquiera con una
    casilla puede llenar el servidor, que es justo lo que la verificacion evita
    en el alta de un medico. Aca la verificacion demuestra la casilla; la
    aprobacion decide si el consultorio existe.
    """
    from datetime import datetime, timedelta

    fila = {
        "estado": "pendiente",
        "tipo": "institucion",
        "slug": "clinicanorte",
        "token": "t",
        "expira_en": datetime.now() + timedelta(hours=1),
    }
    monkeypatch.setattr(registro, "buscar_por_token", lambda t: fila)
    monkeypatch.setattr(registro, "_marcar", lambda *a, **k: None)
    monkeypatch.setattr(registro.plataforma, "slug_disponible", lambda s: True)

    def no_llamar(*a, **k):
        raise AssertionError("una institucion no obtiene su base al verificar")

    monkeypatch.setattr("app.alta_cliente.dar_de_alta", no_llamar, raising=False)

    registro.verificar_y_crear("t")


def test_verificar_un_medico_si_crea_la_base(monkeypatch):
    """El camino de un profesional independiente no cambia: no hay nada que
    evaluar, asi que verificar el correo alcanza."""
    from datetime import datetime, timedelta

    fila = {
        "estado": "pendiente",
        "tipo": "medico",
        "slug": "drasosa",
        "nombre": "Dra. Sosa",
        "email": "sosa@ejemplo.com",
        "password_hash": "scrypt:x",
        "token": "t",
        "expira_en": datetime.now() + timedelta(hours=1),
    }
    llamadas = []

    monkeypatch.setattr(registro, "buscar_por_token", lambda t: fila)
    monkeypatch.setattr(registro, "_marcar", lambda *a, **k: None)
    monkeypatch.setattr(registro.plataforma, "slug_disponible", lambda s: True)
    monkeypatch.setattr(
        registro.plataforma, "cursor_plataforma",
        lambda commit=False: _ContextoNulo(),
    )
    monkeypatch.setattr(
        "app.alta_cliente.dar_de_alta",
        lambda **k: llamadas.append(k) or {"cliente_id": 1},
        raising=False,
    )

    registro.verificar_y_crear("t")
    assert llamadas, "el alta de un medico tiene que crear la base"


class _ContextoNulo:
    def __enter__(self):
        class _Cur:
            def execute(self, *a, **k):
                pass
        return (None, _Cur())

    def __exit__(self, *a):
        return False


def test_reabrir_el_enlace_de_una_institucion_aprobada_no_la_duplica(monkeypatch):
    fila = {"estado": "pendiente_aprobacion", "tipo": "institucion", "slug": "x"}
    monkeypatch.setattr(registro, "buscar_por_token", lambda t: fila)

    def no_llamar(*a, **k):
        raise AssertionError("no se debe crear nada")

    monkeypatch.setattr("app.alta_cliente.dar_de_alta", no_llamar, raising=False)

    assert registro.verificar_y_crear("t")["estado"] == "pendiente_aprobacion"
