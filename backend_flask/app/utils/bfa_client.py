# app/utils/bfa_client.py
"""Cliente de la API oficial TSA de Blockchain Federal Argentina.

El sellado es asincrono: la TSA agrupa hashes en lotes y los ancla en
blockchain cada varios minutos. Entre el sellado y su confirmacion, verificar
devuelve `pending`, que NO significa que el documento este adulterado.

Por eso este cliente no interpreta ni reintenta: devuelve la respuesta cruda y
deja que la ruta decida. Reintentar aca con sleep bloqueaba un worker de Flask
durante segundos y, peor, terminaba reportando como adulterada una historia
cuyo unico problema era que el lote todavia no habia cerrado.
"""

import base64
import os

import requests

TSA_BASE_URL = os.getenv("BFA_TSA_URL", "https://tsaapi.bfa.ar/api/tsa").rstrip("/")
TIMEOUT = 30

# Estados que devuelve la TSA al verificar.
ESTADO_OK = "success"
ESTADO_PENDIENTE = "pending"
ESTADO_ERROR = "failure"


def _normalize_hash(hash_hex: str) -> str:
    if not isinstance(hash_hex, str):
        raise ValueError("hash_hex debe ser str")
    return hash_hex[2:] if hash_hex.startswith("0x") else hash_hex


def parse_permanent_rd(permanent_rd: str) -> dict:
    """Decodifica el `permanent_rd` que devuelve la TSA al verificar con exito.

    Formato tras base64-decode: `1x-{file_hash}-{nonce}-{0xleaf}-{block_number}`.
    Devuelve {} si no parsea, para no romper la ruta por un formato inesperado.
    """
    if not permanent_rd:
        return {}
    try:
        raw = base64.b64decode(permanent_rd).decode("utf-8")
        parts = raw.split("-")
        if len(parts) < 5:
            return {}
        return {
            "file_hash": parts[1],
            "block_number": int(parts[-1]),
            "raw": raw,
        }
    except Exception:
        return {}


def registrar_hash_en_bfa(hash_hex: str) -> str:
    """Sella un hash SHA-256 en BFA. Devuelve el `temporary_rd` (recibo).

    Ese recibo hay que persistirlo: es lo unico que despues permite verificar.
    """
    file_hash = _normalize_hash(hash_hex)
    resp = requests.post(
        f"{TSA_BASE_URL}/stamp/",
        json={"file_hash": file_hash},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != ESTADO_OK:
        raise RuntimeError(f"TSA stamp rechazado: {data.get('messages')}")
    return data["temporary_rd"]


def verificar_hash_en_bfa(hash_hex: str, rd: str) -> dict:
    """Verifica un par (hash, recibo) contra la TSA.

    Devuelve la respuesta cruda, sin interpretarla. `status` puede ser:
      success  el hash esta anclado en blockchain y coincide
      pending  el sellado existe pero el lote todavia no se confirmo
      failure  el par no coincide: el contenido cambio

    No reintenta: distinguir `pending` de `failure` es responsabilidad de quien
    llama, y esperar aca bloquearia el worker sin necesidad.

    Los errores de red se propagan como requests.RequestException, para que la
    ruta no los confunda con una verificacion fallida.
    """
    if not rd:
        raise ValueError("rd requerido para verificar")
    resp = requests.post(
        f"{TSA_BASE_URL}/verify/",
        json={"file_hash": _normalize_hash(hash_hex), "rd": rd},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def get_bfa_status() -> dict:
    """Disponibilidad de la TSA, para el health check.

    Reemplaza al chequeo del nodo Geth local (http://bfa-node:8545), que dejo
    de existir al migrar a la API oficial.
    """
    estado = {"tsa_url": TSA_BASE_URL, "connected": False, "status_code": None}
    try:
        resp = requests.get(TSA_BASE_URL, timeout=5)
        estado["connected"] = True
        estado["status_code"] = resp.status_code
    except requests.RequestException as exc:
        estado["error"] = str(exc)
    return estado
