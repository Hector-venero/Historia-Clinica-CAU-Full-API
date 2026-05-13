# app/utils/bfa_client.py
import os
import time
import base64
import requests

TSA_BASE_URL = os.getenv("BFA_TSA_URL", "https://tsaapi.bfa.ar/api/tsa")
TIMEOUT = 30
# La TSA es asíncrona: el batch puede tardar segundos en confirmarse en blockchain.
# Reintentamos cortos para tolerar la verificación justo después de sellar.
VERIFY_RETRIES = 3
VERIFY_BACKOFF_SECONDS = 4


def _normalize_hash(hash_hex: str) -> str:
    if not isinstance(hash_hex, str):
        raise ValueError("hash_hex debe ser str")
    return hash_hex[2:] if hash_hex.startswith("0x") else hash_hex


def parse_permanent_rd(permanent_rd: str) -> dict:
    """
    Decodifica el `permanent_rd` que devuelve la TSA tras verificar exitosamente.
    Formato (tras base64-decode): `1x-{file_hash}-{nonce}-{0xleaf}-{block_number}`.
    Devuelve dict con los campos útiles para auditoría legal. Devuelve {} si no parsea.
    """
    if not permanent_rd:
        return {}
    try:
        raw = base64.b64decode(permanent_rd).decode("utf-8")
        parts = raw.split("-")
        if len(parts) < 5:
            return {}
        block_number = int(parts[-1])
        file_hash = parts[1]
        return {"file_hash": file_hash, "block_number": block_number, "raw": raw}
    except Exception:
        return {}


def registrar_hash_en_bfa(hash_hex: str) -> str:
    """
    Sella un hash SHA-256 en BFA usando la API oficial TSA.
    Devuelve el `temporary_rd` (recibo) que identifica el sellado.
    Ese recibo se persiste y luego se usa para verificar.
    """
    file_hash = _normalize_hash(hash_hex)
    resp = requests.post(
        f"{TSA_BASE_URL}/stamp/",
        json={"file_hash": file_hash},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "success":
        raise RuntimeError(f"TSA stamp rechazado: {data.get('messages')}")
    return data["temporary_rd"]


def verificar_hash_en_bfa(hash_hex: str, rd: str) -> dict:
    """
    Verifica un hash sellado contra la TSA de BFA.
    Devuelve el cuerpo completo de la respuesta cuando el sellado existe:
      {status, attestation_time, permanent_rd, messages}
    Lanza RuntimeError si la TSA reporta `failure` tras los reintentos.

    Reintenta varias veces con backoff para tolerar la latencia del batch
    (un stamp recién emitido puede no estar verificable durante unos segundos).
    """
    if not rd:
        raise ValueError("rd requerido para verificar")
    file_hash = _normalize_hash(hash_hex)
    last_msg = None
    for intento in range(VERIFY_RETRIES):
        resp = requests.post(
            f"{TSA_BASE_URL}/verify/",
            json={"file_hash": file_hash, "rd": rd},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "success":
            return data
        last_msg = data.get("messages")
        if intento < VERIFY_RETRIES - 1:
            time.sleep(VERIFY_BACKOFF_SECONDS)
    raise RuntimeError(f"TSA verify rechazado: {last_msg}")
