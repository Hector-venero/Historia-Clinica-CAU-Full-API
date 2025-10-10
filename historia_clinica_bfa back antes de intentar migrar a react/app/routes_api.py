# app/routes_api.py

from flask import request, jsonify, send_file, session, url_for, send_from_directory
from datetime import datetime, timedelta
from . import app, mail
from .database import get_connection
from .auth import Usuario
from .utils.hashing import generar_hash
from .utils.utils import validar_integridad
from .utils.blockchain import publicar_hash_en_bfa
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from .utils.permisos import requiere_rol
import secrets
from flask_mail import Message
from flask_login import current_user
import os

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    user = Usuario.obtener_por_username(username)

    if user and user.verificar_password(password):
        login_user(user)
        session.permanent = True
        return jsonify({
            'message': 'Login exitoso ✅',
            'user': {
                'id': user.id,
                'nombre': user.nombre,
                'username': user.username,
                'email': user.email,
                'rol': user.rol
            }
        })
    return jsonify({'error': 'Credenciales incorrectas ❌'}), 401

@app.route('/api/logout', methods=['POST'])
@login_required
def api_logout():
    logout_user()
    return jsonify({'message': 'Logout exitoso ✅'})

@app.route('/api/user', methods=['GET'])
@login_required
def api_user():
    return jsonify({
        "id": current_user.id,
        "nombre": current_user.nombre,
        "username": current_user.username,
        "email": current_user.email,
        "rol": current_user.rol
    })

@app.route('/api/pacientes', methods=['POST'])
@login_required  # Para que solo usuarios logueados puedan crear
def api_crear_paciente():
    data = request.form.to_dict()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Verificar si ya existe el DNI
    cursor.execute("SELECT id FROM pacientes WHERE dni = %s", (data.get('dni'),))
    existente = cursor.fetchone()

    if existente:
        cursor.close()
        conn.close()
        return jsonify({'error': f"⚠️ Ya existe un paciente con DNI {data.get('dni')}"}), 400

    # Normalizar campo cert_discapacidad
    cert_discapacidad = data.get('cert_discapacidad')
    if cert_discapacidad and cert_discapacidad.lower() in ['si', 'sí']:
        cert_discapacidad = 'Sí'
    elif cert_discapacidad and cert_discapacidad.lower() == 'no':
        cert_discapacidad = 'No'
    else:
        cert_discapacidad = None

    usuario_id = current_user.id if current_user.is_authenticated else None

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pacientes (dni, apellido, nombre, fecha_nacimiento, sexo, nro_hc, nacionalidad,
            direccion, telefono, celular, email, contacto, cobertura, cert_discapacidad,
            nro_certificado, derivado_por, diagnostico, motivo_derivacion, medico_cabecera, comentarios, registrado_por)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        data.get('dni'),
        data.get('apellido', '').upper(),
        data.get('nombre', '').upper(),
        data.get('fecha_nacimiento'),
        data.get('sexo'),
        data.get('nro_hc'),
        data.get('nacionalidad'),
        data.get('direccion'),
        data.get('telefono'),
        data.get('celular'),
        data.get('email'),
        data.get('contacto'),
        data.get('cobertura'),
        cert_discapacidad,
        data.get('nro_certificado'),
        data.get('derivado_por'),
        data.get('diagnostico'),
        data.get('motivo_derivacion'),
        data.get('medico_cabecera'),
        data.get('comentarios'),
        usuario_id
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': 'Paciente registrado correctamente ✅'})


@app.route('/api/pacientes/<int:id>', methods=['PUT'])
@login_required  # Para que solo logueados puedan modificar
def api_modificar_paciente(id):
    data = request.form.to_dict()

    conn = get_connection()
    cursor = conn.cursor()

    cert_discapacidad = data.get('cert_discapacidad')
    if cert_discapacidad and cert_discapacidad.lower() in ['si', 'sí']:
        cert_discapacidad = 'Sí'
    elif cert_discapacidad and cert_discapacidad.lower() == 'no':
        cert_discapacidad = 'No'
    else:
        cert_discapacidad = None

    usuario_id = current_user.id if current_user.is_authenticated else None

    cursor.execute("""
        UPDATE pacientes
        SET apellido=%s, nombre=%s, fecha_nacimiento=%s, sexo=%s, nro_hc=%s, nacionalidad=%s,
            direccion=%s, telefono=%s, celular=%s, email=%s, contacto=%s, cobertura=%s,
            cert_discapacidad=%s, nro_certificado=%s, derivado_por=%s, diagnostico=%s,
            motivo_derivacion=%s, medico_cabecera=%s, comentarios=%s, modificado_por=%s
        WHERE id=%s
    """, (
        data.get('apellido', '').upper(),
        data.get('nombre', '').upper(),
        data.get('fecha_nacimiento'),
        data.get('sexo'),
        data.get('nro_hc'),
        data.get('nacionalidad'),
        data.get('direccion'),
        data.get('telefono'),
        data.get('celular'),
        data.get('email'),
        data.get('contacto'),
        data.get('cobertura'),
        cert_discapacidad,
        data.get('nro_certificado'),
        data.get('derivado_por'),
        data.get('diagnostico'),
        data.get('motivo_derivacion'),
        data.get('medico_cabecera'),
        data.get('comentarios'),
        usuario_id,
        id
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': 'Paciente modificado correctamente ✅'})

@app.route('/api/pacientes', methods=['GET'])
@login_required
def api_listar_pacientes():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, dni, nombre, apellido, fecha_nacimiento, sexo, telefono, email
        FROM pacientes
        ORDER BY apellido, nombre
    """)
    pacientes = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(pacientes)

@app.route('/api/pacientes/<int:id>', methods=['GET'])
@login_required
def api_get_paciente(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM pacientes WHERE id = %s", (id,))
    paciente = cursor.fetchone()
    cursor.close()
    conn.close()

    if not paciente:
        return jsonify({'error': 'Paciente no encontrado'}), 404

    return jsonify(paciente)

@app.route('/api/pacientes/<int:id>', methods=['DELETE'])
@login_required
def api_eliminar_paciente(id):
    conn = get_connection()
    cursor = conn.cursor()

    # Primero podrías verificar si existe
    cursor.execute("SELECT id FROM pacientes WHERE id = %s", (id,))
    paciente = cursor.fetchone()

    if not paciente:
        cursor.close()
        conn.close()
        return jsonify({'error': 'Paciente no encontrado'}), 404

    # Eliminar el paciente
    cursor.execute("DELETE FROM pacientes WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': 'Paciente eliminado correctamente ✅'})

@app.route('/api/pacientes/buscar', methods=['GET'])
def buscar_pacientes():
    term = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    per_page = 10  # cantidad de resultados por página

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    like_term = f"%{term}%"

    # Contar total
    count_query = """
        SELECT COUNT(*) as total 
        FROM pacientes
        WHERE dni LIKE %s
            OR nombre LIKE %s
            OR apellido LIKE %s
            OR nro_hc LIKE %s
    """
    cursor.execute(count_query, (like_term, like_term, like_term, like_term))
    total_result = cursor.fetchone()
    total = total_result['total']

    # Traer página
    offset = (page - 1) * per_page
    query = """
        SELECT id, nro_hc, dni, nombre, apellido 
        FROM pacientes
        WHERE dni LIKE %s
            OR nombre LIKE %s
            OR apellido LIKE %s
            OR nro_hc LIKE %s
        ORDER BY apellido, nombre
        LIMIT %s OFFSET %s
    """
    cursor.execute(query, (like_term, like_term, like_term, like_term, per_page, offset))
    results = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({
        'pacientes': results,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total // per_page) + (1 if total % per_page else 0)
    })

@app.route('/api/pacientes/<int:paciente_id>/historias', methods=['GET'])
@login_required
def api_get_historias(paciente_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT h.*, u.nombre AS nombre_usuario
        FROM historias h
        JOIN usuarios u ON h.usuario_id = u.id
        WHERE h.paciente_id = %s
        ORDER BY h.fecha DESC
    """, (paciente_id,))
    historias = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(historias)

@app.route('/api/pacientes/<int:paciente_id>/historias', methods=['POST'])
@login_required
def api_agregar_historia(paciente_id):
    data = request.json

    motivo = data.get('motivo_consulta', '')
    antecedentes = data.get('antecedentes', '')
    examen_fisico = data.get('examen_fisico', '')
    diagnostico = data.get('diagnostico', '')
    tratamiento = data.get('tratamiento', '')
    observaciones = data.get('observaciones', '')

    # Generar hash local
    concat_text = f"{paciente_id}|{motivo}|{antecedentes}|{examen_fisico}|{diagnostico}|{tratamiento}|{observaciones}"
    hash_local = generar_hash(concat_text)

    # Publicar en BFA (tu función propia)
    tx_hash = publicar_hash_en_bfa(hash_local)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO historias (paciente_id, usuario_id, motivo_consulta, antecedentes, examen_fisico,
                               diagnostico, tratamiento, observaciones, hash, tx_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (paciente_id, current_user.id, motivo, antecedentes, examen_fisico,
          diagnostico, tratamiento, observaciones, hash_local, tx_hash))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': 'Evento agregado ✅', 'hash': hash_local, 'tx_hash': tx_hash})

@app.route('/api/pacientes/<int:paciente_id>/historias/pdf', methods=['GET'])
@login_required
def api_descargar_historia_pdf(paciente_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT h.*, u.nombre AS nombre_usuario
        FROM historias h
        JOIN usuarios u ON h.usuario_id = u.id
        WHERE h.paciente_id = %s
        ORDER BY h.fecha DESC
    """, (paciente_id,))
    historias = cursor.fetchall()

    cursor.close()
    conn.close()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setFont("Helvetica", 12)

    pdf.drawString(50, 800, f"Historia clínica del paciente ID {paciente_id}")

    y = 780
    for h in historias:
        pdf.drawString(50, y, f"Fecha: {h['fecha']} - Motivo: {h['motivo_consulta']}")
        y -= 20
        pdf.drawString(60, y, f"Usuario: {h['nombre_usuario']} - Hash: {h['hash']}")
        y -= 30
        if y < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 12)
            y = 800

    pdf.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name=f"historia_paciente_{paciente_id}.pdf", mimetype='application/pdf')

# Ruta para guardar evolución
@app.route('/api/pacientes/<int:id>/evolucion', methods=['POST'])
@login_required
def agregar_evolucion(id):
    fecha = request.form.get('fecha')
    contenido = request.form.get('contenido')
    archivos = request.files.getlist('archivos')

    if not fecha or not contenido:
        return jsonify({'error': 'Faltan campos obligatorios'}), 400

    conn = get_connection()
    cursor = conn.cursor()

    # Insertar evolución
    cursor.execute("""
        INSERT INTO evoluciones (paciente_id, fecha, contenido, usuario_id)
        VALUES (%s, %s, %s, %s)
    """, (id, fecha, contenido, current_user.id))
    conn.commit()
    evolucion_id = cursor.lastrowid

    # Crear carpeta para archivos
    upload_dir = os.path.join(os.getcwd(), 'uploads', 'evoluciones', str(evolucion_id))
    os.makedirs(upload_dir, exist_ok=True)

    # Guardar archivos y registrar en DB
    for archivo in archivos:
        if archivo.filename != '':
            filename = secure_filename(archivo.filename)
            filepath = os.path.join(upload_dir, filename)
            archivo.save(filepath)

            cursor.execute("""
                INSERT INTO evolucion_archivos (evolucion_id, filename)
                VALUES (%s, %s)
            """, (evolucion_id, filename))
            conn.commit()

    cursor.close()
    conn.close()

    return jsonify({'message': 'Evolución guardada correctamente ✅'})


# Ruta para traer evoluciones (con archivos adjuntos)
@app.route('/api/pacientes/<int:id>/evoluciones', methods=['GET'])
@login_required
def get_evoluciones(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Obtener evoluciones
    cursor.execute("""
        SELECT e.id, e.fecha, e.contenido, e.usuario_id, u.nombre AS nombre_usuario
        FROM evoluciones e
        JOIN usuarios u ON e.usuario_id = u.id
        WHERE e.paciente_id = %s
        ORDER BY e.fecha DESC
    """, (id,))
    evoluciones = cursor.fetchall()

    # Para cada evolución, buscar archivos
    for evo in evoluciones:
        cursor.execute("""
            SELECT filename
            FROM evolucion_archivos
            WHERE evolucion_id = %s
        """, (evo['id'],))
        archivos = cursor.fetchall()
        archivos_list = []
        for archivo in archivos:
            archivo_nombre = archivo['filename']
            archivo_url = f"/api/uploads/evoluciones/{evo['id']}/{archivo_nombre}"
            archivos_list.append({
                'nombre': archivo_nombre,
                'url': archivo_url
            })
        evo['archivos'] = archivos_list

    cursor.close()
    conn.close()

    return jsonify(evoluciones)

@app.route('/api/usuarios', methods=['POST'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo')
def api_crear_usuario():
    data = request.json
    nombre = data.get('nombre')
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    rol = data.get('rol')
    especialidad = data.get('especialidad')

    if not nombre or not username or not email or not password or not rol:
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400

    if len(password) < 4:
        return jsonify({'error': 'La contraseña debe tener al menos 4 caracteres'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id FROM usuarios WHERE username = %s OR email = %s", (username, email))
    existente = cursor.fetchone()

    if existente:
        return jsonify({'error': 'Ya existe un usuario con ese nombre de usuario o email'}), 400

    password_hash = generate_password_hash(password)

    # Normalizar especialidad solo si es profesional
    if rol.lower() == 'profesional' and especialidad:
        especialidad = especialidad.upper()
    else:
        especialidad = None

    cursor.execute("""
        INSERT INTO usuarios (nombre, username, email, password_hash, rol, especialidad)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (nombre, username, email, password_hash, rol, especialidad))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': f"Usuario '{username}' creado con éxito ✅"})

@app.route('/api/profesionales', methods=['GET'])
@login_required
def api_listar_profesionales():
    especialidad = request.args.get('especialidad')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if especialidad:
        cursor.execute("""
            SELECT id, nombre, username, especialidad 
            FROM usuarios 
            WHERE rol = 'profesional' AND UPPER(especialidad) = UPPER(%s)
            ORDER BY nombre
        """, (especialidad,))
    else:
        cursor.execute("""
            SELECT id, nombre, username, especialidad 
            FROM usuarios 
            WHERE rol = 'profesional'
            ORDER BY nombre
        """)
    
    profesionales = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify(profesionales)

@app.route('/api/turnos', methods=['GET', 'POST'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo')
def api_turnos():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'GET':
        if current_user.rol == 'profesional':
            # Solo ve sus propios turnos
            cursor.execute("""
                SELECT t.id, t.fecha, t.motivo, p.nombre, p.dni, u.nombre AS profesional
                FROM turnos t
                JOIN pacientes p ON t.paciente_id = p.id
                JOIN usuarios u ON t.usuario_id = u.id
                WHERE t.usuario_id = %s
                ORDER BY t.fecha ASC
            """, (current_user.id,))
        else:
            # Administrativos o director → ven todos los turnos
            cursor.execute("""
                SELECT t.id, t.fecha, t.motivo, p.nombre, p.dni, u.nombre AS profesional
                FROM turnos t
                JOIN pacientes p ON t.paciente_id = p.id
                JOIN usuarios u ON t.usuario_id = u.id
                ORDER BY t.fecha ASC
            """)

        turnos = cursor.fetchall()
        cursor.close()
        conn.close()

        eventos = [{
            "id": t["id"],
            "paciente": t["nombre"],
            "dni": t["dni"],
            "start": t["fecha"].isoformat(),
            "description": t["motivo"],
            "profesional": t["profesional"]
        } for t in turnos]

        return jsonify(eventos)
        

    elif request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({"error": "Faltan datos"}), 400

        paciente_id = data.get("paciente_id")
        usuario_id = data.get("usuario_id")
        fecha = data.get("fecha")
        motivo = data.get("motivo")

        if not (paciente_id and usuario_id and fecha):
            return jsonify({"error": "Campos obligatorios faltantes"}), 400

        # 🔒 Restricción: un profesional solo puede asignarse turnos a sí mismo
        if current_user.rol == 'profesional' and usuario_id != current_user.id:
            return jsonify({"error": "No puede asignar turnos a otros profesionales"}), 403

        try:
            cursor.execute("""
                INSERT INTO turnos (paciente_id, usuario_id, fecha, motivo)
                VALUES (%s, %s, %s, %s)
            """, (paciente_id, usuario_id, fecha, motivo))
            conn.commit()

            # 🔔 Enviar mail al paciente si tiene email
            cursor.execute("SELECT email, nombre, apellido FROM pacientes WHERE id = %s", (paciente_id,))
            paciente = cursor.fetchone()

            cursor.execute("SELECT nombre FROM usuarios WHERE id = %s", (usuario_id,))
            profesional = cursor.fetchone()

            if paciente and paciente.get("email"):
                try:
                    fecha_dt = datetime.fromisoformat(fecha)
                    fecha_legible = fecha_dt.strftime("%d/%m/%Y")
                    hora_legible = fecha_dt.strftime("%H:%M")
                    msg = Message(
                        subject="Confirmación de turno médico",
                        recipients=[paciente["email"]],
                        body=f"""
Estimado {paciente['nombre']} {paciente['apellido']},

Le confirmamos que su turno ha sido registrado con éxito. A continuación, los detalles:

📅 Fecha: {fecha_legible}
🕒 Hora: {hora_legible} hs
👨‍⚕️ Profesional: {profesional['nombre'] if profesional else 'Asignado'}
📋 Motivo: {motivo}

Por favor, le solicitamos presentarse con 10 minutos de anticipación a su cita.

Muchas gracias,  
Centro Asistencial Universitario
"""
                    )
                    mail.send(msg)
                except Exception as e:
                    print("⚠️ Error enviando mail:", e)

            return jsonify({"message": "Turno creado correctamente ✅"}), 201
        except Exception as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            cursor.close()
            conn.close()

@app.route('/api/turnos/<int:id>', methods=['DELETE'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo')
def eliminar_turno(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT usuario_id FROM turnos WHERE id=%s", (id,))
    turno = cursor.fetchone()
    if not turno:
        cursor.close()
        conn.close()
        return jsonify({"error": "Turno no encontrado"}), 404

    if current_user.rol == 'profesional' and turno['usuario_id'] != current_user.id:
        cursor.close()
        conn.close()
        return jsonify({"error": "No autorizado"}), 403

    cursor.execute("DELETE FROM turnos WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Turno eliminado correctamente ✅"})

@app.route('/api/turnos/<int:id>', methods=['PUT'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo')
def editar_turno(id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Faltan datos"}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT usuario_id FROM turnos WHERE id=%s", (id,))
    turno = cursor.fetchone()
    if not turno:
        cursor.close()
        conn.close()
        return jsonify({"error": "Turno no encontrado"}), 404

    if current_user.rol == 'profesional' and turno['usuario_id'] != current_user.id:
        cursor.close()
        conn.close()
        return jsonify({"error": "No autorizado"}), 403

    fecha = data.get("fecha")
    motivo = data.get("motivo")

    cursor.execute("""
        UPDATE turnos
        SET fecha=%s, motivo=%s
        WHERE id=%s
    """, (fecha, motivo, id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Turno actualizado correctamente ✅"})

@app.route('/api/recover', methods=['POST'])
def api_recover():
    data = request.json
    email = data.get('email').strip().lower()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
    usuario = cursor.fetchone()
    conn.close()

    if usuario:
        token = secrets.token_urlsafe(32)
        session['reset_token'] = token
        session['reset_user'] = usuario['username']
        reset_url = url_for('api_reset_password', token=token, _external=True)

        msg = Message("Recuperación de contraseña", recipients=[email])
        msg.body = (
            f"Hola,\n\n"
            f"Recibimos una solicitud para restablecer la contraseña del usuario asociado al correo {email}.\n\n"
            f"Si fuiste vos, hacé clic en el siguiente enlace:\n\n"
            f"{reset_url}\n\n"
            f"Si no realizaste esta solicitud, podés ignorar este mensaje.\n\n"
            f"Gracias,\nSistema HC"
        )
        mail.send(msg)

        return jsonify({'message': 'Email enviado con enlace para restablecer contraseña ✅'})
    else:
        return jsonify({'error': 'No se encontró un usuario con ese email'}), 404

@app.route('/api/reset/<token>', methods=['POST'])
def api_reset_password(token):
    if session.get('reset_token') != token:
        return jsonify({'error': 'Token inválido o expirado'}), 403

    data = request.json
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if new_password != confirm_password:
        return jsonify({'error': 'Las contraseñas no coinciden'}), 400

    username = session['reset_user']
    conn = get_connection()
    cursor = conn.cursor()
    hash_pw = generate_password_hash(new_password)
    cursor.execute("UPDATE usuarios SET password_hash = %s WHERE username = %s", (hash_pw, username))
    conn.commit()
    conn.close()

    session.pop('reset_token', None)
    session.pop('reset_user', None)

    return jsonify({'message': 'Contraseña actualizada correctamente ✅'})

#PARA EXPONER LOS ARCHIVOS ADJUNTOS
@app.route('/api/uploads/evoluciones/<int:evo_id>/<filename>')  # <- AGREGADA
def uploaded_file(evo_id, filename):
    folder = os.path.join(os.getcwd(), 'uploads', 'evoluciones', str(evo_id))
    return send_from_directory(folder, filename)


ROLES_VALIDOS = {"director", "profesional", "administrativo"}

@app.route('/api/usuarios', methods=['GET'])
@login_required
@requiere_rol('director')
def api_usuarios_listado():
    """
    Listado de usuarios activos (solo director).
    Soporta filtros opcionales: ?q=texto (busca en nombre/username/email).
    Si se pasa ?inactivos=1, devuelve también los inactivos.
    """
    q = (request.args.get('q') or "").strip()
    incluir_inactivos = request.args.get('inactivos') == '1'

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    filtro_activo = "" if incluir_inactivos else "AND activo=1"

    if q:
        like = f"%{q}%"
        cursor.execute(f"""
            SELECT id, nombre, username, email, rol, especialidad, activo
            FROM usuarios
            WHERE (nombre LIKE %s OR username LIKE %s OR email LIKE %s)
            {filtro_activo}
            ORDER BY nombre
        """, (like, like, like))
    else:
        cursor.execute(f"""
            SELECT id, nombre, username, email, rol, especialidad, activo
            FROM usuarios
            WHERE 1=1 {filtro_activo}
            ORDER BY nombre
        """)

    usuarios = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(usuarios)

@app.route('/api/usuarios/<int:usuario_id>', methods=['GET'])
@login_required
@requiere_rol('director')
def api_usuarios_detalle(usuario_id):
    """Detalle de un usuario (solo director)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, nombre, username, email, rol, especialidad
        FROM usuarios
        WHERE id = %s
    """, (usuario_id,))
    u = cursor.fetchone()
    cursor.close()
    conn.close()
    if not u:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify(u)


@app.route('/api/usuarios/<int:usuario_id>', methods=['PUT'])
@login_required
@requiere_rol('director')
def api_usuarios_editar(usuario_id):
    """
    Editar usuario (solo director).
    Body JSON opcional por campo: nombre, username, email, rol, especialidad, password
    - Valida unicidad de username/email si cambian
    - Si rol = profesional, guarda especialidad (en MAYÚSCULAS); si no, la pone en NULL
    - Si viene 'password', se re-hashea
    """
    data = request.get_json(silent=True) or {}
    nombre = (data.get("nombre") or "").strip()
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    rol = (data.get("rol") or "").strip()
    especialidad = (data.get("especialidad") or "").strip()
    password = data.get("password")  # puede venir vacío o no venir

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    # Existe el usuario?
    cur.execute("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
    actual = cur.fetchone()
    if not actual:
        cur.close(); conn.close()
        return jsonify({"error": "Usuario no encontrado"}), 404

    # Validaciones básicas
    if username and username != actual["username"]:
        cur.execute("SELECT id FROM usuarios WHERE username=%s AND id<>%s", (username, usuario_id))
        if cur.fetchone():
            cur.close(); conn.close()
            return jsonify({"error": "Ya existe otro usuario con ese username"}), 400

    if email and email != actual["email"]:
        cur.execute("SELECT id FROM usuarios WHERE email=%s AND id<>%s", (email, usuario_id))
        if cur.fetchone():
            cur.close(); conn.close()
            return jsonify({"error": "Ya existe otro usuario con ese email"}), 400

    if rol and rol not in ROLES_VALIDOS:
        cur.close(); conn.close()
        return jsonify({"error": "Rol inválido"}), 400

    # Construir SET dinámico
    sets = []
    params = []

    if nombre:
        sets.append("nombre=%s"); params.append(nombre)
    if username:
        sets.append("username=%s"); params.append(username)
    if email:
        sets.append("email=%s"); params.append(email)
    if rol:
        sets.append("rol=%s"); params.append(rol)
        # manejar especialidad según rol
        if rol == "profesional":
            sets.append("especialidad=%s"); params.append(especialidad.upper() if especialidad else None)
        else:
            sets.append("especialidad=%s"); params.append(None)
    else:
        # si no cambia rol pero sí especialidad y el actual es profesional
        if especialidad and actual["rol"] == "profesional":
            sets.append("especialidad=%s"); params.append(especialidad.upper())

    if password:
        sets.append("password_hash=%s"); params.append(generate_password_hash(password))

    if not sets:
        cur.close(); conn.close()
        return jsonify({"message": "Sin cambios"}), 200

    params.append(usuario_id)
    q = f"UPDATE usuarios SET {', '.join(sets)} WHERE id=%s"
    cur.execute(q, tuple(params))
    conn.commit()
    cur.close(); conn.close()

    return jsonify({"message": "Usuario actualizado ✅"})


@app.route('/api/usuarios/<int:usuario_id>', methods=['DELETE'])
@login_required
@requiere_rol('director')
def api_usuarios_eliminar(usuario_id):
    """
    Soft delete: marcar usuario como inactivo en lugar de eliminarlo.
    """
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    # Verificar si existe
    cur.execute("SELECT id, activo FROM usuarios WHERE id=%s", (usuario_id,))
    usuario = cur.fetchone()
    if not usuario:
        cur.close(); conn.close()
        return jsonify({"error": "Usuario no encontrado"}), 404

    if usuario["activo"] == 0:
        cur.close(); conn.close()
        return jsonify({"message": "Usuario ya estaba inactivo"}), 200

    # Marcar como inactivo
    cur.execute("UPDATE usuarios SET activo=0 WHERE id=%s", (usuario_id,))
    conn.commit()
    cur.close(); conn.close()

    return jsonify({"message": "Usuario marcado como inactivo ✅"})

@app.route('/api/usuarios/<int:usuario_id>/activar', methods=['PUT'])
@login_required
@requiere_rol('director')
def api_usuarios_activar(usuario_id):
    """
    Reactivar un usuario marcado como inactivo.
    Solo accesible por director.
    """
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    # Verificar si existe
    cur.execute("SELECT id, activo FROM usuarios WHERE id=%s", (usuario_id,))
    usuario = cur.fetchone()
    if not usuario:
        cur.close(); conn.close()
        return jsonify({"error": "Usuario no encontrado"}), 404

    if usuario["activo"] == 1:
        cur.close(); conn.close()
        return jsonify({"message": "Usuario ya estaba activo"}), 200

    # Reactivar
    cur.execute("UPDATE usuarios SET activo=1 WHERE id=%s", (usuario_id,))
    conn.commit()
    cur.close(); conn.close()

    return jsonify({"message": "Usuario reactivado ✅"})

from flask import request, jsonify
from web3 import Web3
import hashlib

# 🔹 Conexión a tu nodo local BFA / Ethereum
w3 = Web3(Web3.HTTPProvider("http://geth:8545"))  # ajustá a tu contenedor/nodo
cuenta = w3.eth.accounts[0] if w3.is_connected() else None

@app.route('/api/blockchain/hash', methods=['POST'])
@login_required
def registrar_hash():
    """
    Recibe datos (ej: historia clínica), calcula hash SHA256 y lo registra en blockchain.
    Guarda también el tx_hash.
    """
    data = request.get_json(silent=True) or {}
    contenido = (data.get("contenido") or "").strip()

    if not contenido:
        return jsonify({"error": "Falta contenido"}), 400

    # 🔹 Calcular hash SHA256
    hash_local = hashlib.sha256(contenido.encode()).hexdigest()

    # 🔹 Enviar a blockchain (ejemplo simple: almacenamos hash en data del tx)
    if not cuenta:
        return jsonify({"error": "Nodo no conectado"}), 500

    tx_hash = w3.eth.send_transaction({
        "from": cuenta,
        "to": cuenta,
        "value": 0,
        "data": hash_local.encode()
    })

    return jsonify({
        "message": "Hash registrado ✅",
        "hash": hash_local,
        "tx_hash": tx_hash.hex()
    })


@app.route('/api/blockchain/verificar', methods=['POST'])
@login_required
def verificar_hash():
    """
    Verifica si un hash existe en la blockchain.
    """
    data = request.get_json(silent=True) or {}
    hash_a_verificar = (data.get("hash") or "").strip()

    if not hash_a_verificar:
        return jsonify({"error": "Falta hash"}), 400

    # 🔹 Buscar en la blockchain (ejemplo simple, escaneando últimas N txs)
    ultimo_bloque = w3.eth.block_number
    encontrados = []

    for i in range(max(0, ultimo_bloque - 100), ultimo_bloque + 1):  # solo últimos 100 bloques
        bloque = w3.eth.get_block(i, full_transactions=True)
        for tx in bloque.transactions:
            if tx["input"] and hash_a_verificar in tx["input"]:
                encontrados.append({
                    "blockNumber": tx["blockNumber"],
                    "tx_hash": tx["hash"].hex()
                })

    if encontrados:
        return jsonify({"exists": True, "detalles": encontrados})
    else:
        return jsonify({"exists": False, "message": "Hash no encontrado ❌"})
    

# routes_blockchain.py
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.utils.hashing import generar_hash
from app.utils.blockchain import publicar_hash_en_bfa
from app.database import get_connection
from datetime import datetime

bp_blockchain = Blueprint("blockchain", __name__)

@bp_blockchain.route("/api/blockchain/registro", methods=["POST"])
@login_required
def registrar_hash():
    data = request.json
    paciente_id = data.get("paciente_id")
    motivo = data.get("motivo", "")
    antecedentes = data.get("antecedentes", "")
    examen = data.get("examen_fisico", "")
    diagnostico = data.get("diagnostico", "")
    tratamiento = data.get("tratamiento", "")
    observaciones = data.get("observaciones", "")

    # 1) Concatenar contenido
    contenido = f"{motivo}{antecedentes}{examen}{diagnostico}{tratamiento}{observaciones}"

    # 2) Generar hash local
    hash_local = generar_hash(contenido)

    # 3) Publicar en BFA
    try:
        tx_hash = publicar_hash_en_bfa(hash_local)
    except Exception as e:
        tx_hash = None
        print("⚠️ Error publicando en BFA:", str(e))

    # 4) Guardar en DB
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO historias 
        (paciente_id, usuario_id, fecha, motivo_consulta, antecedentes, examen_fisico, diagnostico, tratamiento, observaciones, hash, tx_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (paciente_id, current_user.id, datetime.now(), motivo, antecedentes, examen, diagnostico, tratamiento, observaciones, hash_local, tx_hash))
    conn.commit()
    historia_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "message": "Historia registrada",
        "historia_id": historia_id,
        "hash": hash_local,
        "tx_hash": tx_hash
    })

@bp_blockchain.route("/api/blockchain/verificar/<int:historia_id>", methods=["GET"])
@login_required
def verificar_historia(historia_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM historias WHERE id = %s", (historia_id,))
    historia = cursor.fetchone()
    conn.close()

    if not historia:
        return jsonify({"error": "Historia no encontrada"}), 404

    # Recalcular hash local
    contenido = f"{historia['motivo_consulta']}{historia['antecedentes']}{historia['examen_fisico']}{historia['diagnostico']}{historia['tratamiento']}{historia['observaciones']}"
    hash_actual = generar_hash(contenido)
    es_valido = (hash_actual == historia["hash"])

    return jsonify({
        "historia_id": historia_id,
        "hash_guardado": historia["hash"],
        "hash_recalculado": hash_actual,
        "valido": es_valido,
        "tx_hash": historia["tx_hash"]
    })
# routes_api.py
from flask import request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app.database import get_connection
from app.utils.hashing import generar_hash
from app.utils.blockchain import publicar_hash_en_bfa
from app.utils.permisos import requiere_rol

@app.route('/api/historias', methods=['POST'])
@login_required
@requiere_rol('director', 'profesional', 'administrativo')
def api_crear_historia():
    data = request.json

    paciente_id = data.get("paciente_id")
    motivo = data.get("motivo_consulta", "").strip()
    antecedentes = data.get("antecedentes", "").strip()
    examen_fisico = data.get("examen_fisico", "").strip()
    diagnostico = data.get("diagnostico", "").strip()
    tratamiento = data.get("tratamiento", "").strip()
    observaciones = data.get("observaciones", "").strip()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1) Generar hash del contenido
    contenido = motivo + antecedentes + examen_fisico + diagnostico + tratamiento + observaciones
    hash_hex = generar_hash(contenido)

    # 2) Intentar publicar en blockchain
    try:
        tx_hash = publicar_hash_en_bfa(hash_hex)
    except Exception as e:
        tx_hash = None
        print(f"⚠️ Error publicando hash en BFA: {e}")

    # 3) Guardar en DB
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO historias (paciente_id, usuario_id, fecha, motivo_consulta, antecedentes,
                               examen_fisico, diagnostico, tratamiento, observaciones, hash, tx_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (paciente_id, current_user.id, fecha, motivo, antecedentes, examen_fisico,
          diagnostico, tratamiento, observaciones, hash_hex, tx_hash))
    conn.commit()

    historia_id = cursor.lastrowid
    cursor.close()
    conn.close()

    return jsonify({
        "message": "Historia guardada ✅",
        "id": historia_id,
        "hash": hash_hex,
        "tx_hash": tx_hash
    }), 201
