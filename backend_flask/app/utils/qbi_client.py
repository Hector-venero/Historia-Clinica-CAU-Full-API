"""Cliente HTTP de la API de recetas electronicas (Qbitos / QBI2).

Toda la comunicacion con el proveedor vive aca y no en las rutas: eso permite
mockear una sola cosa en los tests, y evita que cada endpoint arme headers y
maneje errores a su manera.

La configuracion se lee de la config de Flask, no de os.getenv a nivel de
modulo: leerla al importar congelaba los valores del arranque y hacia imposible
cambiarlos en tests.
"""

from urllib.parse import quote

import requests
from flask import current_app

RECETA_ENDPOINT = "/apirecipe/Receta"
PRACTICA_ENDPOINT = "/apirecipe/prescribirPractica"


class QbiNoConfigurado(RuntimeError):
    """Faltan credenciales o URL: el modulo de recetas no puede operar."""


class QbiError(RuntimeError):
    """El proveedor respondio con error. `status` y `detalle` traen el contexto."""

    def __init__(self, mensaje, status=502, detalle=None):
        super().__init__(mensaje)
        self.status = status
        self.detalle = detalle


def get_config():
    """Config vigente. Lanza QbiNoConfigurado si falta algo esencial.

    Las credenciales salen del consultorio que hace el pedido, no del entorno del
    proceso: cada uno factura con su propia cuenta ante el proveedor, asi que un
    token compartido emitiria recetas de un consultorio a nombre de otro. Sin
    consultorio resuelto —instalacion de un solo centro— se leen del entorno,
    como siempre.
    """
    from app import marca

    cfg = current_app.config
    credenciales = marca.qbi()
    base_url = credenciales["base_url"]
    token = credenciales["token"]
    client_id = credenciales["client_id"]

    faltantes = [
        nombre
        for nombre, valor in (
            ("QBI_BASE_URL", base_url),
            ("QBI_TOKEN", token),
            ("QBI_CLIENT_ID", client_id),
        )
        if not valor
    ]
    if faltantes:
        raise QbiNoConfigurado(
            "Integración de recetas no configurada. Faltan: " + ", ".join(faltantes)
        )

    return {
        "base_url": base_url,
        "token": token,
        "client_id": client_id,
        "timeout": cfg.get("QBI_TIMEOUT", 30),
    }


def esta_configurado():
    try:
        get_config()
        return True
    except QbiNoConfigurado:
        return False


def _headers(config):
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {config['token']}",
        "Content-Type": "application/json",
    }


def _request(method, path, *, params=None, json_body=None):
    """Hace la llamada y normaliza los errores a QbiError."""
    config = get_config()
    try:
        resp = requests.request(
            method,
            f"{config['base_url']}{path}",
            headers=_headers(config),
            params=params,
            json=json_body,
            timeout=config["timeout"],
        )
    except requests.RequestException as exc:
        current_app.logger.exception("Error conectando con la API de recetas")
        raise QbiError(
            "No se pudo conectar con el servicio de recetas", status=502, detalle=str(exc)
        ) from exc

    try:
        payload = resp.json()
    except ValueError:
        payload = {"raw": resp.text}

    if resp.status_code >= 400:
        # Se conserva el status del proveedor: un 400 suyo es un dato del
        # pedido, no una falla nuestra, y colapsarlo a 502 lo ocultaria.
        raise QbiError(
            "El servicio de recetas rechazó la solicitud",
            status=resp.status_code,
            detalle=payload,
        )

    return payload


# --------------------------------------------------------------- catalogos


def buscar_medicamento(search: str, **filtros):
    config = get_config()
    params = {"clienteAppId": config["client_id"]}
    params.update({k: v for k, v in filtros.items() if v})
    return _request("GET", f"/apirecipe/GetMedicamento/{quote(search)}", params=params)


def buscar_diagnostico(search: str = ""):
    config = get_config()
    params = {"clienteAppId": config["client_id"]}
    if search:
        params["text"] = search
    return _request("GET", "/apirecipe/GetDiagnostico", params=params)


def get_financiadores():
    config = get_config()
    # Antes el clienteAppId iba fijo en la URL (554), ignorando la config.
    return _request(
        "GET", "/apirecipe/GetFinanciadores", params={"clienteAppId": config["client_id"]}
    )


# --------------------------------------------------------------- emision


def emitir_receta(payload: dict):
    return _request("POST", RECETA_ENDPOINT, json_body=payload)


def emitir_practica(payload: dict):
    """Prescripcion de estudios: texto libre en vez de medicamento."""
    return _request("POST", PRACTICA_ENDPOINT, json_body=payload)


def anular_receta(hash_receta: str):
    config = get_config()
    return _request(
        "DELETE",
        f"{RECETA_ENDPOINT}/{quote(str(hash_receta))}",
        json_body={"clienteAppId": config["client_id"]},
    )
