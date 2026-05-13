import os
import requests

_BASE_URL  = os.getenv("QBI_BASE_URL", "https://apirecipe.hml.qbitos.com").rstrip("/")
_TOKEN     = os.getenv("QBI_TOKEN", "")
_CLIENT_ID = os.getenv("QBI_CLIENT_ID", "")


def _headers():
    return {
        "Authorization": f"Bearer {_TOKEN}",
        "clienteAppId": _CLIENT_ID,
        "Content-Type": "application/json",
    }


def buscar_medicamento(search: str) -> list:
    url = f"{_BASE_URL}/apirecipe/GetMedicamento/{search}"
    resp = requests.get(url, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def buscar_diagnostico(search: str = "") -> list:
    url = f"{_BASE_URL}/apirecipe/GetDiagnostico"
    params = {"text": search} if search else {}
    resp = requests.get(url, headers=_headers(), params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def emitir_receta(payload: dict) -> dict:
    url = f"{_BASE_URL}/apirecipe/Receta"
    resp = requests.post(url, headers=_headers(), json=payload, timeout=15)
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError:
        print(f"ERROR DE QBI2: {resp.text}")
        raise Exception(f"Qbi2 Error: {resp.text}")
    return resp.json()


def get_financiadores() -> list:
    url = f"{_BASE_URL}/apirecipe/GetFinanciadores?clienteAppId=554"
    resp = requests.get(url, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def anular_receta(hash_receta: str) -> dict:
    url = f"{_BASE_URL}/apirecipe/Receta/{hash_receta}"
    resp = requests.delete(url, headers=_headers(), json={"clienteAppId": 554}, timeout=10)
    resp.raise_for_status()
    return resp.json()
