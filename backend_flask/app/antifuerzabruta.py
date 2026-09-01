"""Freno a los intentos de adivinar una contrasena.

El login no tenia ningun limite: una pagina de entrada publica por cada
subdominio, y del otro lado historias clinicas. Probar `admin` contra las mil
contrasenas mas usadas era cuestion de dejarlo corriendo.

**Por que en la base y no en memoria.** En produccion corren tres workers de
Gunicorn. Un contador en memoria vive en cada worker por separado, asi que el
limite real seria el triple del configurado y dependeria de a que worker cae
cada pedido. Una tabla no tiene ese problema y ademas sobrevive a un reinicio,
que es justo cuando conviene que no se olvide.

**Por que se cuenta por usuario Y por IP, y no solo por usuario.** Contar solo
por usuario convierte la proteccion en el ataque: cualquiera puede dejar afuera
al director de un consultorio un lunes a la manana escribiendo mal su
contrasena diez veces. La clave principal es `usuario|ip` —que es lo que
identifica a quien esta probando— y hay un segundo contador por IP sola, para
que no alcance con ir cambiando de usuario.

**El bloqueo siempre vence.** No hay bloqueo permanente ni desbloqueo manual:
una cuenta que hay que ir a destrabar a mano es soporte todos los lunes. La
espera crece con los intentos y llega a un tope.

⚠️ **La IP tiene que ser la real.** Detras de nginx, `remote_addr` es la del
proxy y todos los intentos del mundo compartirian contador. `ProxyFix` ya esta
aplicado en `app/__init__.py`, que es lo que hace que `request.remote_addr`
valga; sin el, el contador por IP no distingue a nadie.
"""

from datetime import datetime, timedelta

# Cuantos fallos se toleran antes de empezar a frenar.
#
# Cinco es lo que se equivoca una persona real con el bloqueo de mayusculas
# puesto. Menos que eso molesta a quien no esta atacando nada.
FALLOS_LIBRES = 5

# Cuanto dura el primer bloqueo, y cuanto se puede llegar a esperar.
#
# Crece al doble con cada fallo posterior: 1, 2, 4, 8, 16, 30, 30... Con el tope
# en media hora, mil intentos pasan a ser dias — que es lo unico que hace falta,
# porque nadie deja corriendo un ataque que rinde dos intentos por hora.
ESPERA_INICIAL_MINUTOS = 1
ESPERA_MAXIMA_MINUTOS = 30

# Los fallos viejos no cuentan. Sin esto, alguien que se equivoco cinco veces a
# lo largo de un ano arrancaria bloqueado.
VENTANA_MINUTOS = 60

# El contador por IP sola tolera mas: en un consultorio todo el equipo sale por
# la misma IP, y cuatro personas equivocandose no son un ataque.
FALLOS_LIBRES_POR_IP = 20


class DemasiadosIntentos(Exception):
    """Hay que esperar antes de volver a probar."""

    def __init__(self, segundos):
        self.segundos = max(1, int(segundos))
        super().__init__(f"Esperar {self.segundos} segundos.")


def _espera(fallos, libres):
    """Cuanto hay que esperar despues de `fallos` fallidos."""
    if fallos <= libres:
        return timedelta(0)
    minutos = ESPERA_INICIAL_MINUTOS * (2 ** (fallos - libres - 1))
    return timedelta(minutes=min(minutos, ESPERA_MAXIMA_MINUTOS))


def _al_segundo(momento):
    """Sin microsegundos.

    ⚠️ MySQL **redondea** al guardar en un DATETIME sin fraccion: 13:08:46.7 se
    guarda como 13:08:47, o sea MEDIO SEGUNDO EN EL FUTURO. Al releerlo, el
    ultimo fallo quedaba despues de "ahora" y el pedido siguiente se rechazaba
    aunque el contador estuviera en cero.

    Se veia como un bloqueo de un segundo despues de CADA fallo, incluido el
    primero: probando contra el stack, el segundo intento daba 429 diciendo
    "probá de nuevo en 1 segundos". Con truncar antes de escribir, lo que se
    guarda es lo mismo que se comparo.
    """
    return momento.replace(microsecond=0)


def _claves(usuario, ip):
    """Las dos claves con las que se cuenta.

    El usuario se normaliza y se recorta: es texto que llega del pedido y la
    columna tiene 190 (el tope de un indice utf8mb4).
    """
    usuario = (usuario or "").strip().lower()[:100]
    ip = (ip or "sin-ip")[:60]
    return [
        (f"u:{usuario}|{ip}", FALLOS_LIBRES),
        (f"ip:{ip}", FALLOS_LIBRES_POR_IP),
    ]


def _leer(cur, clave):
    cur.execute(
        "SELECT fallos, ultimo_en FROM intentos_login WHERE clave = %s", (clave,)
    )
    return cur.fetchone()


def revisar(cursor_de, usuario, ip, ahora=None):
    """Levanta DemasiadosIntentos si todavia hay que esperar.

    `cursor_de` es el context manager de la base donde vive la cuenta:
    `database.db_cursor` para el personal, `portal.cursor_portal` para un
    paciente. Se recibe en vez de importarse para que este modulo sirva en los
    dos planos sin saber cual es cual.

    Ante un error de base **no bloquea**: dejar a todo el mundo afuera porque
    fallo una consulta de este contador es peor que el problema que resuelve.
    """
    ahora = _al_segundo(ahora or datetime.now())
    try:
        with cursor_de() as (_conn, cur):
            for clave, libres in _claves(usuario, ip):
                fila = _leer(cur, clave)
                if not fila:
                    continue
                ultimo = fila["ultimo_en"]
                if ultimo is None or ahora - ultimo > timedelta(minutes=VENTANA_MINUTOS):
                    continue  # los fallos viejos no cuentan
                espera = _espera(int(fila["fallos"]), libres)
                libre_en = ultimo + espera
                if libre_en > ahora:
                    raise DemasiadosIntentos((libre_en - ahora).total_seconds())
    except DemasiadosIntentos:
        raise
    except Exception:
        return


def registrar_fallo(cursor_de, usuario, ip, ahora=None):
    """Suma uno a los dos contadores.

    El INSERT ... ON DUPLICATE KEY reinicia el contador si el ultimo fallo quedo
    fuera de la ventana, en la misma sentencia: leer y despues escribir dejaria
    una ventana entre las dos donde dos pedidos simultaneos pisan el conteo.
    """
    ahora = _al_segundo(ahora or datetime.now())
    corte = ahora - timedelta(minutes=VENTANA_MINUTOS)
    try:
        with cursor_de(commit=True) as (_conn, cur):
            for clave, _libres in _claves(usuario, ip):
                cur.execute(
                    """
                    INSERT INTO intentos_login (clave, fallos, ultimo_en)
                    VALUES (%s, 1, %s)
                    ON DUPLICATE KEY UPDATE
                        fallos = IF(ultimo_en < %s, 1, fallos + 1),
                        ultimo_en = VALUES(ultimo_en)
                    """,
                    (clave, ahora, corte),
                )
    except Exception:
        # Que no se pueda anotar el fallo no puede impedir responder al login.
        return


def limpiar(cursor_de, usuario, ip):
    """Borra los contadores despues de entrar bien.

    Solo el de `usuario|ip`: el de la IP sola se deja. Si no, un atacante que
    conoce una cuenta propia entra con ella cada cinco intentos y se limpia el
    contador de la IP para seguir probando con las demas.
    """
    try:
        clave, _libres = _claves(usuario, ip)[0]
        with cursor_de(commit=True) as (_conn, cur):
            cur.execute("DELETE FROM intentos_login WHERE clave = %s", (clave,))
    except Exception:
        return


def mensaje(error):
    """El texto que se le muestra a quien espera.

    Dice cuanto falta. "Demasiados intentos" a secas hace recargar cada dos
    segundos, que es exactamente lo que se esta tratando de evitar.
    """
    segundos = error.segundos
    if segundos < 60:
        cuanto = f"{segundos} segundos"
    else:
        minutos = round(segundos / 60)
        cuanto = "1 minuto" if minutos == 1 else f"{minutos} minutos"
    return f"Demasiados intentos fallidos. Probá de nuevo en {cuanto}."
