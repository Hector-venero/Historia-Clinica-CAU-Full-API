import re

# ---------------------------------------------------
# VALIDACIÓN DE CONTRASEÑAS SEGURAS
# ---------------------------------------------------
def password_valida(password: str) -> bool:
    """
    Regla unificada:
    - mínimo 8 caracteres
    - al menos 1 minúscula
    - al menos 1 mayúscula
    - al menos 1 número
    - al menos 1 símbolo
    - longitud máxima opcional (64)
    """
    if not password or len(password) < 8 or len(password) > 64:
        return False

    patron = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).+$"
    return bool(re.match(patron, password))


# ---------------------------------------------------
# VALIDACIÓN DE EMAIL
# ---------------------------------------------------
def validar_email(email: str) -> bool:
    """
    Valida que tenga estructura correcta.
    """
    if not email or len(email) > 120:
        return False

    patron = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    return bool(re.match(patron, email.strip()))
