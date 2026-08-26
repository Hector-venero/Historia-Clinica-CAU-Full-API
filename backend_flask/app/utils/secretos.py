"""Cifrado de los secretos que la plataforma guarda por cliente.

La contrasena de la base de cada consultorio y su token de recetas se guardan en
el plano de control, y la aplicacion necesita **recuperarlos**, no solo
compararlos: con ellos se conecta a la base y se habla con el proveedor. Por eso
van cifrados y no hasheados —un hash no se puede deshacer, que es justamente su
gracia para las contrasenas de usuario, y lo contrario de lo que hace falta aca.

La clave sale de PLATAFORMA_SECRET_KEY. Si falta, se falla ruidosamente: la
alternativa —guardar en claro y seguir— deja credenciales de bases con historias
clinicas legibles para cualquiera que abra el plano de control.

Generar una clave nueva:

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

**Rotarla invalida todo lo cifrado.** Si alguna vez hay que cambiarla, primero
descifrar con la vieja y volver a cifrar con la nueva.
"""

import os

from cryptography.fernet import Fernet, InvalidToken


class SecretoNoConfigurado(RuntimeError):
    """Falta PLATAFORMA_SECRET_KEY o no es una clave valida."""


class SecretoIlegible(RuntimeError):
    """El dato no se puede descifrar con la clave actual."""


def _fernet():
    clave = os.getenv("PLATAFORMA_SECRET_KEY")
    if not clave:
        raise SecretoNoConfigurado(
            "Falta PLATAFORMA_SECRET_KEY. Sin ella no se pueden leer las "
            "credenciales de los clientes. Generar una con: "
            "python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(clave.encode() if isinstance(clave, str) else clave)
    except (ValueError, TypeError) as exc:
        raise SecretoNoConfigurado(
            "PLATAFORMA_SECRET_KEY no es una clave Fernet valida (32 bytes en "
            "base64 url-safe)."
        ) from exc


def cifrar(valor):
    """Devuelve el valor cifrado, listo para guardar en una columna VARBINARY."""
    if valor is None:
        return None
    if isinstance(valor, str):
        valor = valor.encode("utf-8")
    return _fernet().encrypt(valor)


def descifrar(dato):
    """Recupera el valor original. None entra y sale como None."""
    if dato is None:
        return None
    if isinstance(dato, str):
        dato = dato.encode("utf-8")
    try:
        return _fernet().decrypt(dato).decode("utf-8")
    except InvalidToken as exc:
        # Casi siempre significa que la clave cambio. Conviene decirlo, porque
        # el sintoma —"no puedo conectarme a la base del cliente"— no lleva solo
        # hasta la causa.
        raise SecretoIlegible(
            "No se pudo descifrar el secreto. Suele indicar que "
            "PLATAFORMA_SECRET_KEY cambio desde que se guardo."
        ) from exc
