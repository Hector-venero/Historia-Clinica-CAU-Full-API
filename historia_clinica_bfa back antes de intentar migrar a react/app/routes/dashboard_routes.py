from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.database import get_connection
from datetime import datetime, date, timedelta

bp_dashboard = Blueprint("dashboard", __name__)

# ============================================================
# 📊 ENDPOINT PRINCIPAL DEL DASHBOARD
# ============================================================
@bp_dashboard.route("/api/dashboard", methods=["GET"])
@login_required
def get_dashboard():
    """
    Devuelve datos dinámicos del panel principal según el rol del usuario:
    - Profesional: turnos del día, próximo turno, ausencias personales
    - Director/Admin: totales generales y actividad reciente
    """

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
        # -------------------------
        # 👨‍⚕️ Profesional
        # -------------------------
        if rol == "profesional":
            # Turnos del día del profesional logueado
            cursor.execute("""
                SELECT t.id, t.fecha, t.motivo,
                       p.nombre AS paciente, p.apellido,
                       u.nombre AS profesional
                FROM turnos t
                JOIN pacientes p ON p.id = t.paciente_id
                JOIN usuarios u ON u.id = t.usuario_id
                WHERE DATE(t.fecha) = %s AND t.usuario_id = %s
                ORDER BY t.fecha ASC
            """, (hoy, user_id))
            turnos_hoy = cursor.fetchall()
            data["turnos_hoy"] = len(turnos_hoy)
            data["turnos"] = turnos_hoy

            # Próximo turno (futuro más cercano)
            cursor.execute("""
                SELECT t.id, t.fecha, t.motivo,
                       p.nombre AS paciente, p.apellido
                FROM turnos t
                JOIN pacientes p ON p.id = t.paciente_id
                WHERE t.usuario_id = %s 
                AND t.fecha > NOW()
                ORDER BY t.fecha ASC
                LIMIT 1
            """, (user_id,))  # ✅ Tupla correcta
            proximo = cursor.fetchone()
            if proximo:
                proximo["fecha"] = proximo["fecha"].isoformat()
            data["proximo_turno"] = proximo

            # Ausencias del profesional
            cursor.execute("""
                SELECT id, fecha_inicio, fecha_fin, motivo
                FROM ausencias
                WHERE usuario_id = %s AND fecha_fin >= %s
                ORDER BY fecha_inicio ASC
            """, (user_id, hoy))
            data["ausencias"] = cursor.fetchall()

        # -------------------------
        # 🧑‍💼 Director o Administrativo
        # -------------------------
        elif rol in ("director", "administrativo"):
            # Totales globales
            cursor.execute("SELECT COUNT(*) AS total FROM pacientes")
            data["estadisticas"]["pacientes"] = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) AS total FROM usuarios")
            data["estadisticas"]["usuarios"] = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) AS total FROM turnos WHERE DATE(fecha) = %s", (hoy,))
            data["estadisticas"]["turnos_hoy"] = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) AS total FROM evoluciones")
            data["estadisticas"]["evoluciones"] = cursor.fetchone()["total"]

            # Turnos de hoy (global)
            cursor.execute("""
                SELECT t.id, t.fecha, t.motivo,
                       p.nombre AS paciente, p.apellido,
                       u.nombre AS profesional
                FROM turnos t
                JOIN pacientes p ON p.id = t.paciente_id
                JOIN usuarios u ON u.id = t.usuario_id
                WHERE DATE(t.fecha) = %s
                ORDER BY t.fecha ASC
            """, (hoy,))
            data["turnos"] = cursor.fetchall()

            # Ausencias globales
            cursor.execute("""
                SELECT a.id, a.fecha_inicio, a.fecha_fin, a.motivo, u.nombre AS profesional
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
    """
    Devuelve la cantidad de turnos y ausencias por día (próximos 7 días)
    Si el usuario es profesional, filtra los suyos.
    Si es director o administrativo, devuelve global.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    rol = current_user.rol
    user_id = current_user.id
    hoy = date.today()
    hasta_7_dias = hoy + timedelta(days=6)

    try:
        # --- Turnos ---
        if rol == "profesional":
            cursor.execute("""
                SELECT DATE(fecha) AS dia, COUNT(*) AS total
                FROM turnos
                WHERE usuario_id = %s AND DATE(fecha) BETWEEN %s AND %s
                GROUP BY DATE(fecha)
                ORDER BY dia ASC
            """, (user_id, hoy, hasta_7_dias))
        else:
            cursor.execute("""
                SELECT DATE(fecha) AS dia, COUNT(*) AS total
                FROM turnos
                WHERE DATE(fecha) BETWEEN %s AND %s
                GROUP BY DATE(fecha)
                ORDER BY dia ASC
            """, (hoy, hasta_7_dias))
        turnos = cursor.fetchall()

        # --- Ausencias ---
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

        # --- Normalizar datos ---
        labels = [(hoy + timedelta(days=i)).strftime("%d/%m") for i in range(7)]
        valores_turnos = []
        valores_ausencias = []

        for dia_str in labels:
            dia_dt = datetime.strptime(dia_str, "%d/%m").date()
            turno = next((t["total"] for t in turnos if t["dia"] == dia_dt), 0)
            ausencia = next((a["total"] for a in ausencias if a["dia"] == dia_dt), 0)
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
