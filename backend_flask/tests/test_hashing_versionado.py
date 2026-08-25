"""El payload del hash esta versionado y las versiones viejas siguen siendo reproducibles.

El fork cambio el payload de la historia consolidada (agrego `indicaciones` y
filtro por activo = 1) sin versionarlo. Como el hash es SHA-256 sobre ese
payload, el cambio altera el hash de TODAS las historias: las ya ancladas
dejarian de coincidir con su recibo de la TSA y se reportarian como
adulteradas.

Estos tests fijan que v1 siga produciendo exactamente el hash de antes.
"""

import hashlib
import json

import pytest

from app.utils.hashing import (
    PAYLOAD_VERSION_ACTUAL,
    campos_payload,
    filtra_activas,
    generar_hash,
    generar_hash_historia,
    payload_historia,
    versiones_soportadas,
)

EVOLUCIONES = [
    {
        "id": 1,
        "fecha": "2026-01-15",
        "contenido": "Primera consulta",
        "indicaciones": "Reposo",
        "usuario_id": 3,
        "activo": 1,
    },
    {
        "id": 2,
        "fecha": "2026-02-20",
        "contenido": "Control",
        "indicaciones": "Continuar tratamiento",
        "usuario_id": 3,
        "activo": 1,
    },
]


def _hash_v1_historico(evoluciones):
    """Reimplementa el calculo original, tal como estaba antes de versionar.

    Es la referencia contra la que se compara: si v1 deja de coincidir con
    esto, cualquier historia anclada antes del cambio deja de verificar.
    """
    filas = [
        {
            "id": e["id"],
            "fecha": e["fecha"],
            "contenido": e["contenido"],
            "usuario_id": e["usuario_id"],
        }
        for e in evoluciones
    ]
    resumen = json.dumps(filas, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(resumen.encode()).hexdigest()


def test_v1_reproduce_el_hash_original():
    """Este es el test que protege las historias ya ancladas."""
    esperado = _hash_v1_historico(EVOLUCIONES)
    obtenido, _ = generar_hash_historia(EVOLUCIONES, version=1)
    assert obtenido == esperado


def test_v1_ignora_indicaciones():
    con_indicaciones = generar_hash_historia(EVOLUCIONES, version=1)[0]
    sin_indicaciones = generar_hash_historia(
        [{k: v for k, v in e.items() if k != "indicaciones"} for e in EVOLUCIONES],
        version=1,
    )[0]
    assert con_indicaciones == sin_indicaciones


def test_v2_incluye_indicaciones():
    original = generar_hash_historia(EVOLUCIONES, version=2)[0]

    modificadas = [dict(e) for e in EVOLUCIONES]
    modificadas[0]["indicaciones"] = "Otra indicacion"

    assert generar_hash_historia(modificadas, version=2)[0] != original


def test_v1_y_v2_dan_hashes_distintos():
    """Justifica el versionado: no son intercambiables."""
    assert (
        generar_hash_historia(EVOLUCIONES, version=1)[0]
        != generar_hash_historia(EVOLUCIONES, version=2)[0]
    )


def test_el_hash_no_depende_del_orden_de_las_claves():
    invertidas = [dict(reversed(list(e.items()))) for e in EVOLUCIONES]
    assert (
        generar_hash_historia(invertidas, version=2)[0]
        == generar_hash_historia(EVOLUCIONES, version=2)[0]
    )


def test_el_payload_solo_trae_los_campos_de_la_version():
    for version in versiones_soportadas():
        for fila in payload_historia(EVOLUCIONES, version):
            assert set(fila) == set(campos_payload(version))


def test_solo_v2_filtra_por_activo():
    assert filtra_activas(1) is False
    assert filtra_activas(2) is True


def test_version_desconocida_falla_ruidosamente():
    with pytest.raises(ValueError):
        generar_hash_historia(EVOLUCIONES, version=99)


def test_la_version_actual_esta_soportada():
    assert PAYLOAD_VERSION_ACTUAL in versiones_soportadas()


def test_generar_hash_suelto_no_cambio():
    """generar_hash() no se puede tocar: hay hashes anclados que dependen de el."""
    assert generar_hash("hola") == hashlib.sha256(b"hola").hexdigest()
    assert generar_hash("  hola  ") == generar_hash("hola")
    assert generar_hash(None) == generar_hash("")


def test_la_fecha_se_serializa_igual_venga_como_date_o_string():
    from datetime import date

    como_date = [dict(EVOLUCIONES[0], fecha=date(2026, 1, 15))]
    como_texto = [dict(EVOLUCIONES[0], fecha="2026-01-15")]

    assert (
        generar_hash_historia(como_date, version=2)[0]
        == generar_hash_historia(como_texto, version=2)[0]
    )
