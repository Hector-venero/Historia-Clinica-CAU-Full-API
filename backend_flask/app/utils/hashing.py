import hashlib

def generar_hash(contenido: str) -> str:
    """
    Genera un hash SHA-256 a partir de un string (UTF-8).
    Ignora valores None y limpia espacios.
    """
    if not contenido:
        contenido = ""
    return hashlib.sha256(contenido.strip().encode('utf-8')).hexdigest()


def validar_integridad(contenido: str, hash_guardado: str) -> bool:
    """
    Verifica si el contenido actual coincide con el hash almacenado.
    Retorna True si ambos hashes coinciden, False si difieren.
    """
    hash_actual = generar_hash(contenido)
    return hash_actual == hash_guardado
