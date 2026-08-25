"""Hashing de historias clinicas para el anclaje en blockchain.

El hash de la historia consolidada es SHA-256 sobre el JSON de sus evoluciones.
Ese JSON es el "payload", y su forma exacta es parte del algoritmo: agregar un
campo o filtrar filas cambia el hash de TODAS las historias, y las que ya
estaban ancladas dejarian de verificar contra su recibo de la TSA.

Por eso el payload esta versionado. Una historia guarda con que version se
calculo su hash, y una verificacion vuelve a usar esa misma version. Cuando
haga falta cambiar el payload, se agrega una version nueva y las anteriores
siguen siendo reproducibles.

  v1  Payload original: id, fecha, contenido, usuario_id. Sin filtrar por
      `activo` (la columna todavia no existia).
  v2  Agrega `indicaciones` y descarta las evoluciones dadas de baja
      (activo = 0), que no deben formar parte de la historia vigente.
"""

import hashlib
import json

# Version con la que se calculan los hashes nuevos.
PAYLOAD_VERSION_ACTUAL = 2

# Campos de cada evolucion que entran al payload, por version.
CAMPOS_POR_VERSION = {
    1: ("id", "fecha", "contenido", "usuario_id"),
    2: ("id", "fecha", "contenido", "indicaciones", "usuario_id"),
}

# Si el payload filtra por evoluciones activas.
FILTRA_ACTIVAS = {
    1: False,
    2: True,
}


def versiones_soportadas():
    return sorted(CAMPOS_POR_VERSION)


def _serializar_fecha(valor):
    return valor.isoformat() if hasattr(valor, "isoformat") else str(valor)


def campos_payload(version=PAYLOAD_VERSION_ACTUAL):
    """Columnas que hay que traer de la DB para armar el payload de esa version."""
    try:
        return CAMPOS_POR_VERSION[version]
    except KeyError:
        raise ValueError(f"Version de payload desconocida: {version}") from None


def filtra_activas(version=PAYLOAD_VERSION_ACTUAL):
    try:
        return FILTRA_ACTIVAS[version]
    except KeyError:
        raise ValueError(f"Version de payload desconocida: {version}") from None


def payload_historia(evoluciones, version=PAYLOAD_VERSION_ACTUAL):
    """Arma el payload canonico de una historia consolidada.

    Toma solo los campos de la version pedida y en orden estable, para que el
    hash no dependa del orden en que la query devolvio las columnas.
    """
    campos = campos_payload(version)
    payload = []
    for evo in evoluciones:
        fila = {}
        for campo in campos:
            valor = evo.get(campo)
            fila[campo] = _serializar_fecha(valor) if campo == "fecha" else valor
        payload.append(fila)
    return payload


def serializar_payload(payload):
    """JSON canonico: claves ordenadas y sin escapar el unicode."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)


def generar_hash_historia(evoluciones, version=PAYLOAD_VERSION_ACTUAL):
    """Devuelve (hash_local, resumen_json) de una historia consolidada."""
    resumen = serializar_payload(payload_historia(evoluciones, version))
    return hashlib.sha256(resumen.encode("utf-8")).hexdigest(), resumen


def generar_hash(contenido: str) -> str:
    """Hash SHA-256 de un string suelto.

    Se conserva sin cambios: cualquier modificacion aca invalidaria los hashes
    ya anclados en blockchain.
    """
    if not contenido:
        contenido = ""
    return hashlib.sha256(contenido.strip().encode("utf-8")).hexdigest()


def validar_integridad(contenido: str, hash_guardado: str) -> bool:
    """True si el contenido actual sigue produciendo el hash almacenado."""
    return generar_hash(contenido) == hash_guardado
