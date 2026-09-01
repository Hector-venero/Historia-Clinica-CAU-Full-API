from datetime import date, datetime, timedelta

from flask import Blueprint, current_app, jsonify
from flask_login import current_user, login_required

from app.database import db_cursor, get_connection

bp_dashboard = Blueprint("dashboard", __name__)

ROLES_ADMIN = ("director", "administrativo")
ROLES_PERSONALES = ("profesional", "area")

# Hasta cuantos lugares libres se cuentan para el resumen del dia.
#
# proximos_slots_libres() recibe cuantos quiere, y pedir "todos" no existe. Un
# dia de 8 horas con turnos de 15 minutos son 32 lugares, asi que 100 cubre
# cualquier agenda real y evita que el numero quede recortado sin que se note.
TOPE_LUGARES_LIBRES = 100

DIAS_ES = {
    0: "Lunes",
    1: "Martes",
    2: "Miercoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sabado",
    6: "Domingo",
}


def _to_json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"
    return value


def _normalizar_row(row):
    if not row:
        return row
    return {key: _to_json_value(value) for key, value in row.items()}


def _normalizar_rows(rows):
    return [_normalizar_row(row) for row in rows or []]


def _tipo_evento_ausencia(motivo):
    texto = (motivo or "").strip()
    if texto.startswith("[") and "]" in texto:
        tipo, detalle = texto[1:].split("]", 1)
        return (tipo.strip() or "Bloqueo"), detalle.strip()
    return "Bloqueo", texto


def _enriquecer_ausencias(rows):
    enriquecidas = []
    for row in rows or []:
        item = dict(row)
        tipo, detalle = _tipo_evento_ausencia(item.get("motivo"))
        item["tipo_evento"] = tipo
        item["detalle"] = detalle
        enriquecidas.append(_normalizar_row(item))
    return enriquecidas


def _primer_evento(turno, ausencia):
    eventos = []
    if turno:
        eventos.append({
            **turno,
            "tipo": "Turno",
            "titulo": f"{turno.get('paciente', '')} {turno.get('apellido', '')}".strip(),
            "detalle": turno.get("motivo") or "",
        })
    if ausencia:
        tipo, detalle = _tipo_evento_ausencia(ausencia.get("motivo"))
        eventos.append({
            **ausencia,
            "tipo": tipo,
            "titulo": tipo,
            "detalle": detalle,
            "paciente_id": None,
        })
    if not eventos:
        return None
    eventos.sort(key=lambda evento: evento.get("fecha_inicio"))
    return _normalizar_row(eventos[0])


def _payload_base(rol):
    return {
        "rol": rol,
        "resumen": {},
        "turnos_hoy": 0,
        "turnos": [],
        "proximo_turno": None,
        "proximo_evento": None,
        "disponibilidad_hoy": [],
        "ausencias": [],
        "ausencias_bloqueos": [],
        "alertas": {
            "turnos_superpuestos": [],
            "disponibilidad_hoy": [],
            "agenda_vacia": [],
        },
        "comunicados": [],
        "estadisticas": {},
    }


def _agregar_comunicados(cursor, data, rol, user_id):
    cursor.execute("""
        SELECT
            c.id,
            'institucional' AS origen,
            c.titulo,
            c.contenido,
            c.creado_en,
            u.nombre AS autor_nombre,
            NULL AS grupo_id,
            NULL AS grupo_nombre
        FROM comunicados c
        JOIN usuarios u ON u.id = c.autor_id
        ORDER BY c.creado_en DESC
        LIMIT 5
    """)
    comunicados = _normalizar_rows(cursor.fetchall())

    if rol in ROLES_ADMIN:
        cursor.execute("""
            SELECT
                gp.id,
                'grupo' AS origen,
                COALESCE(NULLIF(gp.titulo, ''), gp.contenido) AS titulo,
                gp.contenido,
                gp.creado_en,
                u.nombre AS autor_nombre,
                g.id AS grupo_id,
                g.nombre AS grupo_nombre
            FROM grupo_posteos gp
            JOIN grupos_profesionales g ON g.id = gp.grupo_id
            JOIN usuarios u ON u.id = gp.autor_id
            ORDER BY gp.creado_en DESC
            LIMIT 5
        """)
    else:
        cursor.execute("""
            SELECT
                gp.id,
                'grupo' AS origen,
                COALESCE(NULLIF(gp.titulo, ''), gp.contenido) AS titulo,
                gp.contenido,
                gp.creado_en,
                u.nombre AS autor_nombre,
                g.id AS grupo_id,
                g.nombre AS grupo_nombre
            FROM grupo_posteos gp
            JOIN grupos_profesionales g ON g.id = gp.grupo_id
            JOIN grupo_miembros gm ON gm.grupo_id = g.id
            JOIN usuarios u ON u.id = gp.autor_id
            WHERE gm.usuario_id = %s
            ORDER BY gp.creado_en DESC
            LIMIT 5
        """, (user_id,))

    comunicados.extend(_normalizar_rows(cursor.fetchall()))
    comunicados.sort(key=lambda item: item.get("creado_en") or "", reverse=True)
    data["comunicados"] = comunicados[:8]


@bp_dashboard.route("/api/dashboard", methods=["GET"])
@login_required
def get_dashboard():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    rol = current_user.rol
    user_id = current_user.id
    hoy = date.today()
    dia_hoy = DIAS_ES[hoy.weekday()]
    data = _payload_base(rol)

    try:
        if rol in ROLES_PERSONALES:
            cursor.execute("""
                SELECT t.id, t.fecha_inicio, t.fecha_fin, t.motivo,
                       p.id AS paciente_id,
                       p.nombre AS paciente, p.apellido,
                       u.nombre AS profesional
                FROM turnos t
                JOIN pacientes p ON p.id = t.paciente_id
                JOIN usuarios u ON u.id = t.usuario_id
                WHERE DATE(t.fecha_inicio) = %s
                  AND t.usuario_id = %s
                ORDER BY t.fecha_inicio ASC
            """, (hoy, user_id))
            data["turnos"] = _normalizar_rows(cursor.fetchall())
            data["turnos_hoy"] = len(data["turnos"])

            cursor.execute("""
                SELECT t.id, t.fecha_inicio, t.fecha_fin, t.motivo,
                       p.id AS paciente_id,
                       p.nombre AS paciente, p.apellido,
                       u.nombre AS profesional
                FROM turnos t
                JOIN pacientes p ON p.id = t.paciente_id
                JOIN usuarios u ON u.id = t.usuario_id
                WHERE t.usuario_id = %s
                  AND t.fecha_inicio > NOW()
                ORDER BY t.fecha_inicio ASC
                LIMIT 1
            """, (user_id,))
            proximo_turno = cursor.fetchone()

            cursor.execute("""
                SELECT a.id, a.usuario_id, a.fecha_inicio, a.fecha_fin, a.motivo,
                       u.nombre AS profesional
                FROM ausencias a
                JOIN usuarios u ON u.id = a.usuario_id
                WHERE a.usuario_id = %s
                  AND a.fecha_inicio > NOW()
                ORDER BY a.fecha_inicio ASC
                LIMIT 1
            """, (user_id,))
            proxima_ausencia = cursor.fetchone()

            data["proximo_turno"] = _normalizar_row(proximo_turno)
            data["proximo_evento"] = _primer_evento(proximo_turno, proxima_ausencia)

            cursor.execute("""
                SELECT id, usuario_id, dia_semana, hora_inicio, hora_fin, activo
                FROM disponibilidades
                WHERE usuario_id = %s
                  AND dia_semana = %s
                  AND activo = 1
                ORDER BY hora_inicio ASC
            """, (user_id, dia_hoy))
            data["disponibilidad_hoy"] = _normalizar_rows(cursor.fetchall())

            cursor.execute("""
                SELECT a.id, a.usuario_id, a.fecha_inicio, a.fecha_fin, a.motivo,
                       u.nombre AS profesional
                FROM ausencias a
                JOIN usuarios u ON u.id = a.usuario_id
                WHERE a.usuario_id = %s
                  AND a.fecha_fin >= %s
                ORDER BY a.fecha_inicio ASC
                LIMIT 5
            """, (user_id, hoy))
            data["ausencias"] = _enriquecer_ausencias(cursor.fetchall())

            # Lugares que todavia quedan libres HOY, no franjas configuradas.
            #
            # El resumen mostraba `len(disponibilidad_hoy)`, o sea cuantas franjas
            # de atencion tenia cargadas para el dia. Bajo el rotulo "Disponibles
            # hoy" eso se lee como "me quedan N lugares", y no es lo mismo: un
            # profesional con una sola franja de 09:00 a 17:00 veia un 1, con la
            # agenda entera vacia.
            #
            # Se calcula con proximos_slots_libres(), la misma funcion que usan
            # Nuevo Turno y el portal: si fuera un conteo aparte, el dashboard
            # diria que hay lugar donde la pantalla de turnos no lo ofrece.
            from app.routes.turnos_routes import proximos_slots_libres

            libres_hoy = proximos_slots_libres(user_id, datetime.now(), cantidad=TOPE_LUGARES_LIBRES)

            data["resumen"] = {
                "turnos_hoy": len(data["turnos"]),
                "lugares_libres_hoy": len(libres_hoy),
                "franjas_hoy": len(data["disponibilidad_hoy"]),
            }

        elif rol in ROLES_ADMIN:
            cursor.execute("""
                SELECT t.id, t.fecha_inicio, t.fecha_fin, t.motivo,
                       p.id AS paciente_id,
                       p.nombre AS paciente, p.apellido,
                       u.nombre AS profesional
                FROM turnos t
                JOIN pacientes p ON p.id = t.paciente_id
                JOIN usuarios u ON u.id = t.usuario_id
                WHERE DATE(t.fecha_inicio) = %s
                ORDER BY t.fecha_inicio ASC
            """, (hoy,))
            data["turnos"] = _normalizar_rows(cursor.fetchall())
            data["turnos_hoy"] = len(data["turnos"])

            cursor.execute("""
                SELECT t.id, t.fecha_inicio, t.fecha_fin, t.motivo,
                       p.id AS paciente_id,
                       p.nombre AS paciente, p.apellido,
                       u.nombre AS profesional
                FROM turnos t
                JOIN pacientes p ON p.id = t.paciente_id
                JOIN usuarios u ON u.id = t.usuario_id
                WHERE t.fecha_inicio > NOW()
                ORDER BY t.fecha_inicio ASC
                LIMIT 1
            """)
            proximo_turno = cursor.fetchone()

            cursor.execute("""
                SELECT a.id, a.usuario_id, a.fecha_inicio, a.fecha_fin, a.motivo,
                       u.nombre AS profesional
                FROM ausencias a
                JOIN usuarios u ON u.id = a.usuario_id
                WHERE a.fecha_inicio > NOW()
                ORDER BY a.fecha_inicio ASC
                LIMIT 1
            """)
            proxima_ausencia = cursor.fetchone()

            data["proximo_turno"] = _normalizar_row(proximo_turno)
            data["proximo_evento"] = _primer_evento(proximo_turno, proxima_ausencia)

            cursor.execute("""
                SELECT d.id, d.usuario_id, u.nombre AS profesional,
                       d.dia_semana, d.hora_inicio, d.hora_fin, d.activo
                FROM disponibilidades d
                JOIN usuarios u ON u.id = d.usuario_id
                WHERE d.dia_semana = %s
                  AND d.activo = 1
                  AND u.activo = 1
                ORDER BY u.nombre ASC, d.hora_inicio ASC
            """, (dia_hoy,))
            disponibilidad_hoy = _normalizar_rows(cursor.fetchall())
            data["disponibilidad_hoy"] = disponibilidad_hoy
            data["alertas"]["disponibilidad_hoy"] = disponibilidad_hoy

            cursor.execute("""
                SELECT a.id, a.usuario_id, a.fecha_inicio, a.fecha_fin, a.motivo,
                       u.nombre AS profesional
                FROM ausencias a
                JOIN usuarios u ON u.id = a.usuario_id
                WHERE a.fecha_inicio < DATE_ADD(%s, INTERVAL 1 DAY)
                  AND a.fecha_fin >= %s
                ORDER BY a.fecha_inicio ASC
                LIMIT 8
            """, (hoy, hoy))
            data["ausencias"] = _enriquecer_ausencias(cursor.fetchall())
            data["ausencias_bloqueos"] = data["ausencias"]

            cursor.execute("""
                SELECT
                    t1.id AS turno_id,
                    t2.id AS turno_solapado_id,
                    t1.fecha_inicio,
                    t1.fecha_fin,
                    t2.fecha_inicio AS fecha_inicio_solapada,
                    t2.fecha_fin AS fecha_fin_solapada,
                    u.id AS usuario_id,
                    u.nombre AS profesional,
                    CONCAT(p1.nombre, ' ', p1.apellido) AS paciente,
                    CONCAT(p2.nombre, ' ', p2.apellido) AS paciente_solapado
                FROM turnos t1
                JOIN turnos t2
                  ON t1.usuario_id = t2.usuario_id
                 AND t1.id < t2.id
                 AND t1.fecha_inicio < t2.fecha_fin
                 AND t1.fecha_fin > t2.fecha_inicio
                JOIN usuarios u ON u.id = t1.usuario_id
                JOIN pacientes p1 ON p1.id = t1.paciente_id
                JOIN pacientes p2 ON p2.id = t2.paciente_id
                WHERE DATE(t1.fecha_inicio) = %s
                  AND DATE(t2.fecha_inicio) = %s
                ORDER BY u.nombre ASC, t1.fecha_inicio ASC
            """, (hoy, hoy))
            data["alertas"]["turnos_superpuestos"] = _normalizar_rows(cursor.fetchall())

            cursor.execute("""
                SELECT u.id AS usuario_id, u.nombre AS profesional,
                       d.hora_inicio, d.hora_fin
                FROM usuarios u
                JOIN disponibilidades d ON d.usuario_id = u.id
                LEFT JOIN turnos t
                  ON t.usuario_id = u.id
                 AND DATE(t.fecha_inicio) = %s
                WHERE u.activo = 1
                  AND u.rol IN ('profesional', 'area')
                  AND d.dia_semana = %s
                  AND d.activo = 1
                  AND t.id IS NULL
                ORDER BY u.nombre ASC
            """, (hoy, dia_hoy))
            data["alertas"]["agenda_vacia"] = _normalizar_rows(cursor.fetchall())

            # Para quien dirige, la pregunta del dia no es cuantas franjas hay
            # cargadas —el numero de filas de una tabla de configuracion— sino
            # **cuanta gente esta atendiendo**. Contar los profesionales
            # distintos responde eso; contar franjas daba 3 con un solo medico
            # que atiende en tres bloques.
            #
            # No se calculan lugares libres como en la vista del profesional: ahi
            # es una consulta para una sola agenda, y aca serian tres por cada
            # profesional del centro en el endpoint mas golpeado de la app.
            profesionales_hoy = {d.get("usuario_id") for d in data["disponibilidad_hoy"]}

            data["resumen"] = {
                "turnos_hoy": len(data["turnos"]),
                "profesionales_hoy": len(profesionales_hoy),
                "turnos_superpuestos": len(data["alertas"]["turnos_superpuestos"]),
            }

        else:
            return jsonify({"error": "Rol no reconocido"}), 403

        _agregar_comunicados(cursor, data, rol, user_id)
        data["estadisticas"] = data["resumen"]
        return jsonify(data)

    except Exception as e:
        current_app.logger.exception("Error en /api/dashboard")
        return jsonify({"error": str(e)}), 500

    finally:
        # Sin este finally la conexion quedaba abierta en cada carga del
        # dashboard, que es el endpoint mas golpeado de la app.
        cursor.close()
        conn.close()



@bp_dashboard.route("/api/dashboard/semanal", methods=["GET"])
@login_required
def get_dashboard_semanal():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    rol = current_user.rol
    user_id = current_user.id

    hoy = date.today()
    hasta_7_dias = hoy + timedelta(days=6)

    try:
        if rol in ["profesional", "area"]:
            cursor.execute("""
                SELECT DATE(fecha_inicio) AS dia, COUNT(*) AS total
                FROM turnos
                WHERE usuario_id = %s
                AND DATE(fecha_inicio) BETWEEN %s AND %s
                GROUP BY DATE(fecha_inicio)
                ORDER BY dia ASC
            """, (user_id, hoy, hasta_7_dias))
        else:
            cursor.execute("""
                SELECT DATE(fecha_inicio) AS dia, COUNT(*) AS total
                FROM turnos
                WHERE DATE(fecha_inicio) BETWEEN %s AND %s
                GROUP BY DATE(fecha_inicio)
                ORDER BY dia ASC
            """, (hoy, hasta_7_dias))

        turnos = cursor.fetchall()

        if rol in ["profesional", "area"]:
            cursor.execute("""
                SELECT DATE(fecha_inicio) AS dia, COUNT(*) AS total
                FROM ausencias
                WHERE usuario_id = %s
                AND DATE(fecha_inicio) BETWEEN %s AND %s
                GROUP BY DATE(fecha_inicio)
                ORDER BY dia ASC
            """, (user_id, hoy, hasta_7_dias))
        else:
            cursor.execute("""
                SELECT DATE(fecha_inicio) AS dia, COUNT(*) AS total
                FROM ausencias
                WHERE DATE(fecha_inicio) BETWEEN %s AND %s
                GROUP BY DATE(fecha_inicio)
                ORDER BY dia ASC
            """, (hoy, hasta_7_dias))

        ausencias = cursor.fetchall()

        labels = []
        valores_turnos = []
        valores_ausencias = []

        for i in range(7):
            dia = hoy + timedelta(days=i)
            labels.append(dia.strftime("%d/%m"))

            turno = next((t["total"] for t in turnos if t["dia"] == dia), 0)
            ausencia = next((a["total"] for a in ausencias if a["dia"] == dia), 0)

            valores_turnos.append(turno)
            valores_ausencias.append(ausencia)

        return jsonify({
            "labels": labels,
            "turnos": valores_turnos,
            "ausencias": valores_ausencias
        })

    except Exception as e:
        current_app.logger.exception("Error en /api/dashboard/semanal")
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()



# Cuanto se puede mirar hacia atras de una vez.
#
# No es una restriccion tecnica sino de sentido: el panel responde "como viene
# la cosa", no es una herramienta de estadistica historica. Un rango abierto
# ademas invita a pedir cinco anios de turnos en una consulta.
DIAS_MAXIMOS_PERIODO = 366


def _rango_pedido():
    """Lee desde/hasta del pedido, con el mes en curso como valor por defecto.

    Devuelve (desde, hasta, error).
    """
    from flask import request

    hoy = date.today()
    crudo_desde = request.args.get("desde")
    crudo_hasta = request.args.get("hasta")

    def _parsear(valor, defecto):
        if not valor:
            return defecto, None
        try:
            return datetime.strptime(valor, "%Y-%m-%d").date(), None
        except ValueError:
            return None, "Fecha invalida. Se espera AAAA-MM-DD."

    desde, error = _parsear(crudo_desde, hoy - timedelta(days=29))
    if error:
        return None, None, error
    hasta, error = _parsear(crudo_hasta, hoy)
    if error:
        return None, None, error

    if hasta < desde:
        return None, None, "El fin del periodo es anterior al inicio."
    if (hasta - desde).days > DIAS_MAXIMOS_PERIODO:
        return None, None, f"El periodo no puede superar los {DIAS_MAXIMOS_PERIODO} dias."

    return desde, hasta, None


@bp_dashboard.route("/api/dashboard/periodo", methods=["GET"])
@login_required
def get_dashboard_periodo():
    """Como vinieron los turnos en un periodo, no solo hoy.

    El panel entero respondia por **hoy**, que sirve para arrancar el dia y no
    para nada mas: no habia forma de ver si el mes viene mejor o peor, ni cuanta
    gente falta sin avisar.

    Se responde en una sola consulta agrupada y no una por estado: son cuatro
    numeros de la misma tabla y el mismo rango.

    `ausencia` es NULL cuando el paciente vino —o cuando todavia no paso—, y por
    eso los que faltan se separan de los que quedan por delante mirando la fecha:
    un turno de la semana que viene sin marca no es "atendido", es futuro.
    """
    desde, hasta, error = _rango_pedido()
    if error:
        return jsonify({"error": error}), 400

    rol = current_user.rol
    propio = rol in ROLES_PERSONALES

    condicion = "DATE(t.fecha_inicio) BETWEEN %s AND %s"
    parametros = [desde, hasta]
    if propio:
        condicion += " AND t.usuario_id = %s"
        parametros.append(current_user.id)

    with db_cursor() as (_conn, cursor):
        cursor.execute(
            f"""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN t.ausencia = 'con_aviso' THEN 1 ELSE 0 END) AS con_aviso,
                SUM(CASE WHEN t.ausencia = 'sin_aviso' THEN 1 ELSE 0 END) AS sin_aviso,
                SUM(CASE WHEN t.ausencia IS NULL AND t.fecha_inicio < NOW() THEN 1 ELSE 0 END) AS atendidos,
                SUM(CASE WHEN t.ausencia IS NULL AND t.fecha_inicio >= NOW() THEN 1 ELSE 0 END) AS por_delante
            FROM turnos t
            WHERE {condicion}
            """,
            tuple(parametros),
        )
        fila = cursor.fetchone() or {}

        # La serie por dia, para el grafico. Se pide aparte porque es otra forma
        # de agrupar la misma tabla, no otro dato.
        cursor.execute(
            f"""
            SELECT DATE(t.fecha_inicio) AS dia, COUNT(*) AS total
            FROM turnos t
            WHERE {condicion}
            GROUP BY DATE(t.fecha_inicio)
            ORDER BY dia
            """,
            tuple(parametros),
        )
        por_dia = cursor.fetchall()

    def _entero(clave):
        # SUM() sobre cero filas devuelve NULL, no 0.
        return int(fila.get(clave) or 0)

    total = _entero("total")
    faltaron = _entero("con_aviso") + _entero("sin_aviso")

    return jsonify({
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "propio": propio,
        "total": total,
        "atendidos": _entero("atendidos"),
        "por_delante": _entero("por_delante"),
        "con_aviso": _entero("con_aviso"),
        "sin_aviso": _entero("sin_aviso"),
        # El porcentaje se calcula aca y no en la pantalla: es el numero que se
        # lee, y dos implementaciones del mismo redondeo terminan discrepando.
        # Sobre el total del periodo, no sobre los que ya pasaron: el que mira
        # quiere saber cuanto de lo que agendo se perdio.
        "ausentismo": round(faltaron * 100 / total, 1) if total else 0.0,
        "por_dia": [
            {"dia": f["dia"].isoformat(), "total": int(f["total"])} for f in por_dia
        ],
    })
