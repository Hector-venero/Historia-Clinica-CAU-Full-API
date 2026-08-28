"""Estado de la cuenta y exportacion de los datos.

Estas rutas siguen atendiendo con la cuenta suspendida (ver
`RUTAS_CON_CUENTA_SUSPENDIDA` en tenancy). Es deliberado: cortar el acceso por
falta de pago no puede significar quedarse con las historias clinicas de los
pacientes de otro. Se corta el uso del sistema para trabajar, no el derecho a
llevarse lo propio.
"""

import csv
import io
import json
import os
import zipfile
from datetime import datetime

from flask import Blueprint, jsonify, send_file
from flask_login import login_required

from app import marca, suscripcion
from app.database import db_cursor
from app.tenancy import cliente_actual
from app.utils.permisos import requiere_rol

bp_cuenta = Blueprint("cuenta", __name__, url_prefix="/api/cuenta")

# Tablas que se exportan, en orden de dependencia para que el archivo se lea
# solo. Se enumeran en lugar de recorrer information_schema: asi agregar una
# tabla al sistema obliga a decidir si es dato del cliente o mecanica interna
# (schema_migrations no le sirve a nadie).
TABLAS_EXPORTABLES = (
    "usuarios",
    "pacientes",
    "historias",
    "evoluciones",
    "evolucion_archivos",
    "turnos",
    "turnos_grupales",
    "disponibilidades",
    "ausencias",
    "grupos_profesionales",
    "grupo_miembros",
    "grupo_posteos",
    "comunicados",
    "comunicado_lecturas",
    "recetas_electronicas",
    "anclajes_blockchain",
    "auditorias_blockchain",
)

# No se exporta: es el hash de la contrasena de cada usuario. No le sirve a quien
# se lleva sus datos y no hay motivo para ponerlo en un archivo que va a viajar
# por correo o quedar en una carpeta de descargas.
COLUMNAS_OMITIDAS = {"password_hash"}


@bp_cuenta.get("/estado")
@login_required
def estado_cuenta():
    """Que le pasa a la cuenta. Lo consulta la pantalla de suspension."""
    cliente = cliente_actual()

    if cliente is None:
        # Instalacion de un solo centro: no hay suscripcion que mostrar.
        return jsonify({"estado": "activo", "plan": None, "dias_restantes": None,
                        "activo": True})

    return jsonify(suscripcion.estado_para_mostrar(cliente))


def _filas(cursor, tabla):
    cursor.execute(f"SELECT * FROM {tabla}")
    return cursor.fetchall()


def _a_csv(filas):
    if not filas:
        return ""
    columnas = [c for c in filas[0].keys() if c not in COLUMNAS_OMITIDAS]
    salida = io.StringIO()
    escritor = csv.DictWriter(salida, fieldnames=columnas, extrasaction="ignore")
    escritor.writeheader()
    for fila in filas:
        escritor.writerow({c: fila.get(c) for c in columnas})
    return salida.getvalue()


@bp_cuenta.get("/exportar")
@login_required
@requiere_rol("director")
def exportar():
    """Todos los datos del consultorio en un ZIP.

    Solo el director: es la base entera, incluidas las historias clinicas de
    todos los pacientes.

    Se exporta en CSV y no en un volcado de MySQL a proposito: el destinatario es
    el profesional, no otro sistema. Tiene que poder abrirlo en una planilla sin
    instalar nada. Va tambien un JSON por si alguna vez hay que reimportarlo.
    """
    cliente = cliente_actual()
    nombre_consultorio = marca.nombre_corto()
    marca_tiempo = datetime.now().strftime("%Y%m%d-%H%M")

    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as zip_archivo:
        completo = {}

        with db_cursor() as (_conn, cursor):
            for tabla in TABLAS_EXPORTABLES:
                try:
                    filas = _filas(cursor, tabla)
                except Exception:
                    # Una tabla que no exista en esta base no puede frustrar la
                    # exportacion entera: se sigue con las demas.
                    continue

                limpias = [
                    {k: v for k, v in f.items() if k not in COLUMNAS_OMITIDAS}
                    for f in filas
                ]
                completo[tabla] = limpias
                zip_archivo.writestr(f"csv/{tabla}.csv", _a_csv(filas))

        zip_archivo.writestr(
            "datos.json",
            json.dumps(completo, ensure_ascii=False, indent=2, default=str),
        )

        # Los adjuntos de las evoluciones: estudios, imagenes, informes. Sin
        # ellos la exportacion estaria incompleta justo en lo que mas cuesta
        # volver a conseguir.
        # La carpeta DE ESTE consultorio, no la raiz de adjuntos: `carpeta_base()`
        # es el directorio comun a todos, y exportar desde ahi le entregaria a un
        # cliente los archivos clinicos de los demas.
        from app.utils.adjuntos import carpeta_base, segmento_cliente

        base = str(carpeta_base() / segmento_cliente())
        if base and os.path.isdir(base):
            for raiz, _dirs, archivos in os.walk(base):
                for archivo in archivos:
                    ruta = os.path.join(raiz, archivo)
                    zip_archivo.write(ruta, f"adjuntos/{os.path.relpath(ruta, base)}")

        zip_archivo.writestr(
            "LEEME.txt",
            f"""Exportacion de datos - {nombre_consultorio}
Generada el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}

Contenido:

  csv/          Una planilla por tabla. Se abren con Excel o LibreOffice.
  datos.json    Lo mismo en un solo archivo, para reimportar en otro sistema.
  adjuntos/     Los archivos subidos a las evoluciones.

No se incluyen las contrasenas de los usuarios: estan guardadas como hash y no
le sirven a nadie fuera de este sistema.

Estos datos son de los pacientes del consultorio. Guardalos con el mismo
cuidado que la historia clinica en papel.
""",
        )

    memoria.seek(0)
    slug = cliente.slug if cliente is not None else "consultorio"
    return send_file(
        memoria,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"datos-{slug}-{marca_tiempo}.zip",
    )
