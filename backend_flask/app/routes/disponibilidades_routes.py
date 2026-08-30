from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.database import db_cursor
from app.utils.permisos import requiere_rol
from datetime import datetime, timedelta

bp_disponibilidades = Blueprint("disponibilidades", __name__)

# ==========================================================
# 📅 CRUD de Disponibilidades de los Médicos
# ==========================================================

# Sin tildes, igual que el ENUM de la columna `dia_semana`.
#
# Antes esta lista y normalizar_dia devolvían "Miércoles" y "Sábado" con tilde,
# valores que no existen en el ENUM: guardar disponibilidad para esos dos días
# fallaba con error 1265 "Data truncated". La entrada sí se acepta con o sin
# tilde; lo que se canonicaliza es lo que va a la base.
DIAS_ORDENADOS = [
    "Lunes", "Martes", "Miercoles",
    "Jueves", "Viernes", "Sabado", "Domingo"
]
orden_sql = ",".join([f"'{d}'" for d in DIAS_ORDENADOS])


def normalizar_dia(dia):
    mapa = {
        "lunes": "Lunes",
        "martes": "Martes",
        "miercoles": "Miercoles",
        "miércoles": "Miercoles",
        "jueves": "Jueves",
        "viernes": "Viernes",
        "sabado": "Sabado",
        "sábado": "Sabado",
        "domingo": "Domingo"
    }
    if not dia:
        return None
    return mapa.get(dia.lower().strip())


# ==========================================================
# GET — Listar disponibilidades
# ==========================================================

@bp_disponibilidades.route('/api/disponibilidades', methods=['GET'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
def listar_disponibilidades():

    with db_cursor() as (_conn, cursor):

        # 👇 CAMBIO: 'area' se comporta como 'profesional' (ve solo lo suyo)
        if current_user.rol in ['profesional', 'area']:
            cursor.execute(f"""
                SELECT id, usuario_id, dia_semana, hora_inicio, hora_fin, activo
                FROM disponibilidades
                WHERE usuario_id = %s
                ORDER BY FIELD(dia_semana, {orden_sql})
            """, (current_user.id,))
        else:
            # Directores y administrativos ven las de todos
            # Agregamos filtro opcional por usuario_id si viene en la URL (?usuario_id=5)
            filtro_usuario = request.args.get('usuario_id')
        
            if filtro_usuario:
                cursor.execute(f"""
                    SELECT d.id, d.usuario_id, u.nombre AS profesional,
                           d.dia_semana, d.hora_inicio, d.hora_fin, d.activo
                    FROM disponibilidades d
                    JOIN usuarios u ON d.usuario_id = u.id
                    WHERE d.usuario_id = %s
                    ORDER BY u.nombre ASC, FIELD(d.dia_semana, {orden_sql})
                """, (filtro_usuario,))
            else:
                cursor.execute(f"""
                    SELECT d.id, d.usuario_id, u.nombre AS profesional,
                           d.dia_semana, d.hora_inicio, d.hora_fin, d.activo
                    FROM disponibilidades d
                    JOIN usuarios u ON d.usuario_id = u.id
                    ORDER BY u.nombre ASC, FIELD(d.dia_semana, {orden_sql})
                """)

        disponibilidades = cursor.fetchall()

    # 🟢 Normalizar resultados
    for d in disponibilidades:
        # Canonicalizar siempre: si quedó alguna fila vieja con tilde, sale igual
        # que el resto y el frontend no tiene que contemplar dos formatos.
        d["dia_semana"] = normalizar_dia(d["dia_semana"]) or d["dia_semana"]

        # convertir TIME → string
        if isinstance(d.get("hora_inicio"), timedelta):
            d["hora_inicio"] = (datetime.min + d["hora_inicio"]).time().strftime("%H:%M")
        if isinstance(d.get("hora_fin"), timedelta):
            d["hora_fin"] = (datetime.min + d["hora_fin"]).time().strftime("%H:%M")

    return jsonify(disponibilidades)


# ==========================================================
# POST — Crear disponibilidad
# ==========================================================

@bp_disponibilidades.route('/api/disponibilidades', methods=['POST'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
def crear_disponibilidad():

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"error": "Faltan datos"}), 400

    # Lógica para asignar usuario
    # Si es Director, permitimos que venga "usuario_id" en el JSON
    # Si es Profesional o Area, forzamos que sea su propio ID
    if current_user.rol in ['profesional', 'area']:
        usuario_id = current_user.id
    else:
        usuario_id = data.get("usuario_id") or current_user.id

    dia_semana = normalizar_dia(data.get("dia_semana", ""))
    hora_inicio = data.get("hora_inicio")
    hora_fin = data.get("hora_fin")
    activo = data.get("activo", True)

    if not dia_semana:
        return jsonify({"error": "Día inválido"}), 400
    
    with db_cursor(commit=True) as (_conn, cursor):
        cursor.execute("""
            INSERT INTO disponibilidades (usuario_id, dia_semana, hora_inicio, hora_fin, activo)
            VALUES (%s, %s, %s, %s, %s)
        """, (usuario_id, dia_semana, hora_inicio, hora_fin, activo))

        return jsonify({"id": cursor.lastrowid, "message": "Disponibilidad creada correctamente"}), 201


# ==========================================================
# PUT — Actualizar disponibilidad (solo horas y activo)
# ==========================================================

@bp_disponibilidades.route('/api/disponibilidades/<int:id>', methods=['PUT'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
def editar_disponibilidad(id):

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"error": "Faltan datos"}), 400

    # Los cierres a mano en cada `return` eran el problema: alcanzaba con que uno
    # se olvidara, o con una excepcion entre medio, para dejar la conexion abierta
    # hasta que MySQL la matara por timeout.
    with db_cursor(commit=True) as (_conn, cursor):
        cursor.execute("SELECT usuario_id FROM disponibilidades WHERE id=%s", (id,))
        disp = cursor.fetchone()
        if not disp:
            return jsonify({"error": "Disponibilidad no encontrada"}), 404

        # Un profesional o un area solo puede editar lo suyo; el director,
        # lo de cualquiera.
        if current_user.rol in ['profesional', 'area'] and disp["usuario_id"] != current_user.id:
            return jsonify({"error": "No autorizado"}), 403

        cursor.execute("""
            UPDATE disponibilidades
            SET hora_inicio=%s, hora_fin=%s, activo=%s
            WHERE id=%s
        """, (data.get("hora_inicio"), data.get("hora_fin"), data.get("activo"), id))

    return jsonify({"message": "Disponibilidad actualizada correctamente"})


# ==========================================================
# DELETE
# ==========================================================

@bp_disponibilidades.route('/api/disponibilidades/<int:id>', methods=['DELETE'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
def eliminar_disponibilidad(id):

    with db_cursor(commit=True) as (_conn, cursor):
        cursor.execute("SELECT usuario_id FROM disponibilidades WHERE id=%s", (id,))
        disp = cursor.fetchone()

        if not disp:
            return jsonify({"error": "Disponibilidad no encontrada"}), 404

        if current_user.rol in ['profesional', 'area'] and disp["usuario_id"] != current_user.id:
            return jsonify({"error": "No autorizado"}), 403

        cursor.execute("DELETE FROM disponibilidades WHERE id=%s", (id,))

    return jsonify({"message": "Disponibilidad eliminada correctamente"})


# ==========================================================
# POST — Validar una disponibilidad propuesta contra los turnos ya dados
# ==========================================================

DIAS_EN_A_ES = {
    "Monday": "Lunes",
    "Tuesday": "Martes",
    "Wednesday": "Miercoles",
    "Thursday": "Jueves",
    "Friday": "Viernes",
    "Saturday": "Sabado",
    "Sunday": "Domingo",
}


def _a_hhmmss(hora):
    """'09:00' -> '09:00:00'. Permite comparar horas como texto."""
    if not hora:
        return None
    return f"{hora}:00" if len(hora) == 5 else hora


@bp_disponibilidades.route('/api/disponibilidades/validar', methods=['POST'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo', 'area')
def validar_disponibilidad():
    """Devuelve los turnos futuros que quedarian fuera de la disponibilidad propuesta.

    Reducir o mover una franja no cancela los turnos ya asignados: quedan
    agendados en un horario en el que el profesional ya no atiende, y nadie se
    entera hasta que el paciente se presenta. Esto permite avisar antes de
    guardar.
    """
    data = request.get_json(silent=True) or {}

    # Un profesional solo puede validar su propia agenda.
    if current_user.rol in ('profesional', 'area'):
        usuario_id = current_user.id
    else:
        usuario_id = data.get("usuario_id") or current_user.id

    franjas = []
    for propuesta in data.get("disponibilidades", []):
        if not propuesta.get("activo"):
            continue
        dia = normalizar_dia(propuesta.get("dia_semana", ""))
        inicio = _a_hhmmss(propuesta.get("hora_inicio"))
        fin = _a_hhmmss(propuesta.get("hora_fin"))
        if dia and inicio and fin:
            franjas.append({"dia": dia, "inicio": inicio, "fin": fin})

    with db_cursor() as (_conn, cursor):
        cursor.execute("""
            SELECT t.id, t.fecha_inicio, t.fecha_fin, t.motivo, p.nombre AS paciente
            FROM turnos t
            JOIN pacientes p ON t.paciente_id = p.id
            WHERE t.usuario_id = %s AND t.fecha_inicio >= NOW()
            ORDER BY t.fecha_inicio ASC
        """, (usuario_id,))
        turnos_futuros = cursor.fetchall()

    fuera_de_rango = []
    for turno in turnos_futuros:
        inicio = turno["fecha_inicio"]
        dia_es = DIAS_EN_A_ES.get(inicio.strftime("%A"))
        desde = inicio.time().strftime("%H:%M:%S")
        hasta = turno["fecha_fin"].time().strftime("%H:%M:%S")

        cubierto = any(
            f["dia"] == dia_es and desde >= f["inicio"] and hasta <= f["fin"]
            for f in franjas
        )

        if not cubierto:
            fuera_de_rango.append({
                "id": turno["id"],
                "paciente": turno["paciente"],
                "fecha": inicio.strftime("%d/%m/%Y %H:%M"),
                "motivo": turno["motivo"],
            })

    return jsonify(fuera_de_rango)
