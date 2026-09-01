"""Ajustes operativos del consultorio.

Empieza con los avisos por correo. Hasta ahora el correo se mandaba **siempre**
y no habia forma de apagarlo: un consultorio que ya avisa por WhatsApp le manda
al paciente dos confirmaciones del mismo turno, y nada en el sistema lo evita.

Viven en la tabla `configuracion` de la base de **cada consultorio**, no en
`clientes_config` del plano de control:

  * `clientes_config` solo existe con MULTI_TENANT. Aca la instalacion de un
    solo centro tambien puede apagar sus avisos, con el mismo codigo.
  * Son ajustes de **como trabaja** el consultorio, no de **que contrato**. El
    plan dice que modulos tiene; esto, como los usa.

Clave/valor y no una columna por ajuste: cada ajuste nuevo seria una migracion
sobre las bases de todos los consultorios.

⚠️ **Sin fila rige el valor por defecto.** No se siembran filas al crear la
base: una fila ausente y una fila con el valor por defecto significan lo mismo,
y sembrarlas obligaria a mantener la semilla sincronizada con este archivo.

⚠️ **Los valores por defecto dicen que SI.** Un consultorio que actualiza el
sistema no puede dejar de avisarle a sus pacientes porque aparecio un
interruptor que nunca toco.
"""

from app.database import db_cursor

# Cada ajuste, con su tipo y su valor por defecto.
#
# `bool` es el unico tipo por ahora. Cuando haga falta otro, el lugar de
# convertirlo es `_convertir()`, no cada uno de los que llaman.
AJUSTES = {
    "avisar_turno_nuevo": {
        "tipo": bool,
        "defecto": True,
        "titulo": "Confirmación de turno",
        "detalle": "Al paciente, cuando se le agenda un turno. Incluye la invitación para su calendario.",
    },
    "avisar_turno_cancelado": {
        "tipo": bool,
        "defecto": True,
        "titulo": "Aviso de cancelación",
        "detalle": "Al paciente, cuando se cancela su turno.",
    },
    "resumen_diario": {
        "tipo": bool,
        "defecto": True,
        "titulo": "Resumen de la agenda",
        "detalle": "A cada profesional, con los turnos que tiene al día siguiente.",
    },
}

# Lo que se guarda en la base para un booleano. Se escribe como texto y no como
# 0/1 para que la fila se entienda leyendola.
_VERDADERO = "si"
_FALSO = "no"


def _convertir(definicion, crudo):
    if definicion["tipo"] is bool:
        return str(crudo).strip().lower() in (_VERDADERO, "1", "true", "sí")
    return crudo


def _serializar(definicion, valor):
    if definicion["tipo"] is bool:
        return _VERDADERO if valor else _FALSO
    return str(valor)


def todos():
    """Todos los ajustes, con lo guardado o su valor por defecto.

    Una sola consulta: son pocos y se leen juntos en la pantalla que los edita.
    """
    guardados = {}
    try:
        with db_cursor() as (_conn, cur):
            cur.execute("SELECT clave, valor FROM configuracion")
            guardados = {f["clave"]: f["valor"] for f in cur.fetchall()}
    except Exception:
        # Una base sin la tabla todavia migrada no puede dejar sin avisos a
        # nadie: se cae a los valores por defecto, que son los de siempre.
        guardados = {}

    return {
        clave: _convertir(definicion, guardados[clave])
        if clave in guardados
        else definicion["defecto"]
        for clave, definicion in AJUSTES.items()
    }


def activo(clave):
    """Si un aviso esta encendido. Es lo que consultan los envios.

    Ante cualquier duda —clave desconocida, tabla sin migrar, base caida—
    devuelve True: dejar de avisarle a un paciente por un problema del sistema
    es peor que mandar un correo de mas.
    """
    definicion = AJUSTES.get(clave)
    if definicion is None:
        return True
    try:
        with db_cursor() as (_conn, cur):
            cur.execute("SELECT valor FROM configuracion WHERE clave = %s", (clave,))
            fila = cur.fetchone()
    except Exception:
        return bool(definicion["defecto"])

    if not fila:
        return bool(definicion["defecto"])
    return bool(_convertir(definicion, fila["valor"]))


def guardar(valores):
    """Guarda los ajustes que vengan. Ignora las claves que no conoce.

    Devuelve el estado completo despues de guardar, para que quien llama no
    tenga que volver a leer.
    """
    conocidos = {c: v for c, v in (valores or {}).items() if c in AJUSTES}
    if conocidos:
        with db_cursor(commit=True) as (_conn, cur):
            for clave, valor in conocidos.items():
                cur.execute(
                    """
                    INSERT INTO configuracion (clave, valor) VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE valor = VALUES(valor)
                    """,
                    (clave, _serializar(AJUSTES[clave], valor)),
                )
    return todos()


def descripcion():
    """Los ajustes con su titulo y su explicacion, para dibujar la pantalla.

    El texto vive aca y no en el `.vue` para que agregar un ajuste sea un solo
    lugar: la pantalla se dibuja sola con lo que reciba.
    """
    estado = todos()
    return [
        {
            "clave": clave,
            "titulo": definicion["titulo"],
            "detalle": definicion["detalle"],
            "valor": estado[clave],
        }
        for clave, definicion in AJUSTES.items()
    ]
