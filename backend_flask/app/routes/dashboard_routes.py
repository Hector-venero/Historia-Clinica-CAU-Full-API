from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.database import get_connection
from datetime import date, timedelta

bp_dashboard = Blueprint("dashboard", __name__)

# ============================================================
# 📊 ENDPOINT PRINCIPAL DEL DASHBOARD
# ============================================================
@bp_dashboard.route("/api/dashboard", methods=["GET"])
@login_required
def get_dashboard():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    rol = current_user.rol
    user_id = current_user.id
    hoy = date.today()

    data = {
        "rol": rol,
        "turnos_hoy": 0,
        "proximo_turno": None,
        "turnos": [],
        "ausencias": [],
        "estadisticas": {},
    }

    try:
        # ======================================================
        # 👨‍⚕️ PROFESIONAL
        # ======================================================
        if rol == "profesional":

            # Turnos del día (filtrados por fecha_inicio)
            cursor.execute("""
                SELECT t.id, t.fecha_inicio, t.fecha_fin, t.motivo,
                       p.id AS paciente_id,  -- 👈 AGREGADO AQUÍ
                       p.nombre AS paciente, p.apellido,
                       u.nombre AS profesional
                FROM turnos t
                JOIN pacientes p ON p.id = t.paciente_id
                JOIN usuarios u ON u.id = t.usuario_id
                WHERE DATE(t.fecha_inicio) = %s
                AND t.usuario_id = %s
                ORDER BY t.fecha_inicio ASC
            """, (hoy, user_id))

            turnos_hoy = cursor.fetchall()
            data["turnos_hoy"] = len(turnos_hoy)
            data["turnos"] = turnos_hoy

            # Próximo turno (fecha futura)
            cursor.execute("""
                SELECT t.id, t.fecha_inicio, t.fecha_fin, t.motivo,
                       p.id AS paciente_id, -- 👈 AGREGADO AQUÍ
                       p.nombre AS paciente, p.apellido
                FROM turnos t
                JOIN pacientes p ON p.id = t.paciente_id
                WHERE t.usuario_id = %s
                AND t.fecha_inicio > NOW()
                ORDER BY t.fecha_inicio ASC
                LIMIT 1
            """, (user_id,))

            proximo = cursor.fetchone()
            if proximo:
                proximo["fecha_inicio"] = proximo["fecha_inicio"].isoformat()
                proximo["fecha_fin"] = proximo["fecha_fin"].isoformat()
            data["proximo_turno"] = proximo

            # Ausencias personales
            cursor.execute("""
                SELECT id, fecha_inicio, fecha_fin, motivo
                FROM ausencias
                WHERE usuario_id = %s AND fecha_fin >= %s
                ORDER BY fecha_inicio ASC
            """, (user_id, hoy))

            data["ausencias"] = cursor.fetchall()

        # ======================================================
        # 🧑‍💼 DIRECTOR / ADMIN
        # ======================================================
        elif rol in ("director", "administrativo"):

            cursor.execute("SELECT COUNT(*) AS total FROM pacientes")
            data["estadisticas"]["pacientes"] = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) AS total FROM usuarios")
            data["estadisticas"]["usuarios"] = cursor.fetchone()["total"]

            # Turnos de hoy
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM turnos
                WHERE DATE(fecha_inicio) = %s
            """, (hoy,))
            data["estadisticas"]["turnos_hoy"] = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) AS total FROM evoluciones")
            data["estadisticas"]["evoluciones"] = cursor.fetchone()["total"]

            # Listado de turnos del día
            cursor.execute("""
                SELECT t.id, t.fecha_inicio, t.fecha_fin, t.motivo,
                       p.id AS paciente_id, -- 👈 AGREGADO AQUÍ
                       p.nombre AS paciente, p.apellido,
                       u.nombre AS profesional
                FROM turnos t
                JOIN pacientes p ON p.id = t.paciente_id
                JOIN usuarios u ON u.id = t.usuario_id
                WHERE DATE(t.fecha_inicio) = %s
                ORDER BY t.fecha_inicio ASC
            """, (hoy,))
            data["turnos"] = cursor.fetchall()

            # Ausencias globales
            cursor.execute("""
                SELECT a.id, a.fecha_inicio, a.fecha_fin, a.motivo,
                       u.nombre AS profesional
                FROM ausencias a
                JOIN usuarios u ON u.id = a.usuario_id
                WHERE a.fecha_fin >= %s
                ORDER BY a.fecha_inicio ASC
            """, (hoy,))
            data["ausencias"] = cursor.fetchall()

        else:
            return jsonify({"error": "Rol no reconocido"}), 403

        return jsonify(data)

    except Exception as e:
        print("⚠️ Error en /api/dashboard:", e)
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ============================================================
# 📈 ENDPOINT SEMANAL (PRÓXIMOS 7 DÍAS)
# ============================================================
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
        # ===========================
        # TURNOS
        # ===========================
        if rol == "profesional":
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

        # ===========================
        # AUSENCIAS
        # ===========================
        if rol == "profesional":
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

        # ===========================
        # Normalización de datos
        # ===========================
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
        print("⚠️ Error en /api/dashboard/semanal:", e)
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()