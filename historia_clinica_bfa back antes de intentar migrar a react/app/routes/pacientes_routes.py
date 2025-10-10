from flask import Blueprint, request, jsonify, send_file, send_from_directory
from flask_login import login_required, current_user
from app.database import get_connection
from werkzeug.utils import secure_filename
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os

bp_pacientes = Blueprint("pacientes", __name__)

# ------------------------
# CRUD de Pacientes
# ------------------------

@bp_pacientes.route('/api/pacientes', methods=['POST'])
@login_required
def api_crear_paciente():
    data = request.form.to_dict()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Verificar si ya existe el DNI
    cursor.execute("SELECT id FROM pacientes WHERE dni = %s", (data.get('dni'),))
    existente = cursor.fetchone()
    if existente:
        cursor.close(); conn.close()
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
            nro_certificado, derivado_por, diagnostico, motivo_derivacion, medico_cabecera,
            comentarios, registrado_por)
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
    cursor.close(); conn.close()

    return jsonify({'message': 'Paciente registrado correctamente ✅'})


@bp_pacientes.route('/api/pacientes/<int:id>', methods=['PUT'])
@login_required
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
    cursor.close(); conn.close()

    return jsonify({'message': 'Paciente modificado correctamente ✅'})


@bp_pacientes.route('/api/pacientes', methods=['GET'])
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
    cursor.close(); conn.close()
    return jsonify(pacientes)


@bp_pacientes.route('/api/pacientes/<int:id>', methods=['GET'])
@login_required
def api_get_paciente(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM pacientes WHERE id = %s", (id,))
    paciente = cursor.fetchone()
    cursor.close(); conn.close()

    if not paciente:
        return jsonify({'error': 'Paciente no encontrado'}), 404
    return jsonify(paciente)


@bp_pacientes.route('/api/pacientes/<int:id>', methods=['DELETE'])
@login_required
def api_eliminar_paciente(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM pacientes WHERE id = %s", (id,))
    paciente = cursor.fetchone()

    if not paciente:
        cursor.close(); conn.close()
        return jsonify({'error': 'Paciente no encontrado'}), 404

    cursor.execute("DELETE FROM pacientes WHERE id = %s", (id,))
    conn.commit()
    cursor.close(); conn.close()

    return jsonify({'message': 'Paciente eliminado correctamente ✅'})


@bp_pacientes.route('/api/pacientes/buscar', methods=['GET'])
def buscar_pacientes():
    term = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    per_page = 10

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    like_term = f"%{term}%"

    # Total
    cursor.execute("""
        SELECT COUNT(*) as total 
        FROM pacientes
        WHERE dni LIKE %s OR nombre LIKE %s OR apellido LIKE %s OR nro_hc LIKE %s
    """, (like_term, like_term, like_term, like_term))
    total = cursor.fetchone()['total']

    # Página
    offset = (page - 1) * per_page
    cursor.execute("""
        SELECT id, nro_hc, dni, nombre, apellido 
        FROM pacientes
        WHERE dni LIKE %s OR nombre LIKE %s OR apellido LIKE %s OR nro_hc LIKE %s
        ORDER BY apellido, nombre
        LIMIT %s OFFSET %s
    """, (like_term, like_term, like_term, like_term, per_page, offset))
    results = cursor.fetchall()

    cursor.close(); conn.close()

    return jsonify({
        'pacientes': results,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total // per_page) + (1 if total % per_page else 0)
    })


# ------------------------
# Evoluciones
# ------------------------

@bp_pacientes.route('/api/pacientes/<int:id>/evolucion', methods=['POST'])
@login_required
def agregar_evolucion(id):
    fecha = request.form.get('fecha')
    contenido = request.form.get('contenido')
    archivos = request.files.getlist('archivos')

    if not fecha or not contenido:
        return jsonify({'error': 'Faltan campos obligatorios'}), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO evoluciones (paciente_id, fecha, contenido, usuario_id)
        VALUES (%s, %s, %s, %s)
    """, (id, fecha, contenido, current_user.id))
    conn.commit()
    evolucion_id = cursor.lastrowid

    # Guardar archivos
    upload_dir = os.path.join(os.getcwd(), 'uploads', 'evoluciones', str(evolucion_id))
    os.makedirs(upload_dir, exist_ok=True)
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

    cursor.close(); conn.close()
    return jsonify({'message': 'Evolución guardada correctamente ✅'})


@bp_pacientes.route('/api/pacientes/<int:id>/evoluciones', methods=['GET'])
@login_required
def get_evoluciones(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT e.id, e.fecha, e.contenido, e.usuario_id, u.nombre AS nombre_usuario
        FROM evoluciones e
        JOIN usuarios u ON e.usuario_id = u.id
        WHERE e.paciente_id = %s
        ORDER BY e.fecha DESC
    """, (id,))
    evoluciones = cursor.fetchall()

    # Archivos de cada evolución
    for evo in evoluciones:
        cursor.execute("""
            SELECT filename
            FROM evolucion_archivos
            WHERE evolucion_id = %s
        """, (evo['id'],))
        archivos = cursor.fetchall()
        evo['archivos'] = [{
            'nombre': a['filename'],
            'url': f"/api/uploads/evoluciones/{evo['id']}/{a['filename']}"
        } for a in archivos]

    cursor.close(); conn.close()
    return jsonify(evoluciones)


@bp_pacientes.route('/api/uploads/evoluciones/<int:evo_id>/<filename>')
@login_required
def uploaded_file(evo_id, filename):
    folder = os.path.join(os.getcwd(), 'uploads', 'evoluciones', str(evo_id))
    return send_from_directory(folder, filename)
