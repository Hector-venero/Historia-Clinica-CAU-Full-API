from flask import Blueprint, request, jsonify, send_from_directory, send_file, current_app
from flask_login import login_required, current_user
from app.database import get_connection
from werkzeug.utils import secure_filename
from io import BytesIO
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from datetime import datetime
from app.routes.historias_routes import actualizar_historia
import os
from reportlab.lib.colors import Color

# Registrar fuente compatible con UTF-8 (caracteres acentuados, español)
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))

bp_pacientes = Blueprint("pacientes", __name__)

# ==========================================================
# 📁 CRUD de Pacientes
# ==========================================================

@bp_pacientes.route('/api/pacientes', methods=['POST'])
@login_required
def api_crear_paciente():
    """Crea un nuevo paciente."""
        # 🧩 Soporta tanto JSON como form-data
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Verificar duplicado por DNI
    cursor.execute("SELECT id FROM pacientes WHERE dni = %s", (data.get('dni'),))
    if cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify({'error': f"⚠️ Ya existe un paciente con DNI {data.get('dni')}"}), 400

    # Normalizar campo discapacidad
    cert_discapacidad = data.get('cert_discapacidad')
    if cert_discapacidad:
        cert_discapacidad = 'Sí' if cert_discapacidad.lower() in ['si', 'sí'] else 'No' if cert_discapacidad.lower() == 'no' else None

    usuario_id = current_user.id if current_user.is_authenticated else None

    cursor.execute("""
        INSERT INTO pacientes (
            nro_hc, dni, apellido, nombre, fecha_nacimiento, sexo, nacionalidad,
            ocupacion, direccion, codigo_postal, telefono, celular, email, contacto,
            cobertura, cert_discapacidad, nro_certificado, derivado_por, diagnostico,
            motivo_derivacion, medico_cabecera, comentarios, motivo_ingreso, enfermedad_actual, antecedentes_enfermedad_actual,
            antecedentes_personales, antecedentes_heredofamiliares, registrado_por
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s, %s
        )
    """, (
        data.get('nro_hc'),
        data.get('dni'),
        data.get('apellido', '').upper(),
        data.get('nombre', '').upper(),
        data.get('fecha_nacimiento'),
        data.get('sexo'),
        data.get('nacionalidad'),
        data.get('ocupacion'),
        data.get('direccion'),
        data.get('codigo_postal'),
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
        data.get('motivo_ingreso'),
        data.get('enfermedad_actual'),
        data.get('antecedentes_enfermedad_actual'),
        data.get('antecedentes_personales'),
        data.get('antecedentes_heredofamiliares'),
        usuario_id
    ))

    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'message': 'Paciente registrado correctamente ✅'})

@bp_pacientes.route('/api/pacientes/<int:id>', methods=['PUT'])
@login_required
def api_modificar_paciente(id):
    """Modifica los datos de un paciente existente."""
    data = request.get_json() if request.is_json else request.form.to_dict()
    conn = get_connection()
    cursor = conn.cursor()

    cert_discapacidad = data.get('cert_discapacidad')
    if cert_discapacidad:
        cert_discapacidad = 'Sí' if cert_discapacidad.lower() in ['si', 'sí'] else 'No' if cert_discapacidad.lower() == 'no' else None

    usuario_id = current_user.id if current_user.is_authenticated else None

    campos_validos = {
        'nro_hc': data.get('nro_hc'),
        'dni': data.get('dni'),
        'apellido': data.get('apellido', '').upper() if data.get('apellido') else None,
        'nombre': data.get('nombre', '').upper() if data.get('nombre') else None,
        'fecha_nacimiento': data.get('fecha_nacimiento'),
        'sexo': data.get('sexo'),
        'nacionalidad': data.get('nacionalidad'),
        'ocupacion': data.get('ocupacion'),
        'direccion': data.get('direccion'),
        'codigo_postal': data.get('codigo_postal'),
        'telefono': data.get('telefono'),
        'celular': data.get('celular'),
        'email': data.get('email'),
        'contacto': data.get('contacto'),
        'cobertura': data.get('cobertura'),
        'cert_discapacidad': cert_discapacidad,
        'nro_certificado': data.get('nro_certificado'),
        'derivado_por': data.get('derivado_por'),
        'diagnostico': data.get('diagnostico'),
        'motivo_derivacion': data.get('motivo_derivacion'),
        'medico_cabecera': data.get('medico_cabecera'),
        'comentarios': data.get('comentarios'),
        'motivo_ingreso': data.get('motivo_ingreso'),
        'enfermedad_actual': data.get('enfermedad_actual'),
        'antecedentes_enfermedad_actual': data.get('antecedentes_enfermedad_actual'),
        'antecedentes_personales': data.get('antecedentes_personales'),
        'antecedentes_heredofamiliares': data.get('antecedentes_heredofamiliares'),

    }

    # Solo actualizar campos enviados
    campos_no_vacios = {k: v for k, v in campos_validos.items() if v is not None}
    set_clause = ", ".join([f"{campo}=%s" for campo in campos_no_vacios.keys()])
    values = list(campos_no_vacios.values()) + [usuario_id, id]

    query = f"UPDATE pacientes SET {set_clause}, modificado_por=%s WHERE id=%s"
    cursor.execute(query, values)

    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'message': 'Paciente modificado correctamente ✅'})


@bp_pacientes.route('/api/pacientes', methods=['GET'])
@login_required
def api_listar_pacientes():
    """Devuelve el listado completo de pacientes."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id, dni, nombre, apellido, fecha_nacimiento, sexo, telefono, email
            FROM pacientes
            ORDER BY apellido, nombre
        """)
        pacientes = cursor.fetchall()
        return jsonify(pacientes)
    except Exception as e:
        print("⚠️ Error en /api/pacientes:", e)
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close(); conn.close()


@bp_pacientes.route('/api/pacientes/<int:id>', methods=['GET'])
@login_required
def api_get_paciente(id):
    """Obtiene los datos de un paciente por ID."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM pacientes WHERE id = %s", (id,))
    paciente = cursor.fetchone()
    cursor.close(); conn.close()

    if not paciente:
        return jsonify({'error': 'Paciente no encontrado'}), 404

    if paciente.get('fecha_nacimiento'):
        try:
            paciente['fecha_nacimiento'] = paciente['fecha_nacimiento'].strftime('%Y-%m-%d')
        except Exception:
            pass

    return jsonify(paciente)


@bp_pacientes.route('/api/pacientes/<int:id>', methods=['DELETE'])
@login_required
def api_eliminar_paciente(id):
    """Elimina un paciente."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM pacientes WHERE id = %s", (id,))
    if not cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify({'error': 'Paciente no encontrado'}), 404

    cursor.execute("DELETE FROM pacientes WHERE id = %s", (id,))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'message': 'Paciente eliminado correctamente ✅'})


@bp_pacientes.route('/api/pacientes/buscar', methods=['GET'])
@login_required
def buscar_pacientes():
    """Busca pacientes por nombre, apellido, DNI o N° de historia clínica."""
    term = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    per_page = 10

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    like_term = f"%{term}%"

    cursor.execute("""
        SELECT COUNT(*) as total 
        FROM pacientes
        WHERE dni LIKE %s OR nombre LIKE %s OR apellido LIKE %s OR nro_hc LIKE %s
    """, (like_term, like_term, like_term, like_term))
    total = cursor.fetchone()['total']

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


# ==========================================================
# 🩺 Evoluciones
# ==========================================================

@bp_pacientes.route('/api/pacientes/<int:id>/evolucion', methods=['POST'])
@login_required
def agregar_evolucion(id):
    """Agrega una nueva evolución a un paciente."""
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

    upload_dir = os.path.join(os.getcwd(), 'uploads', 'evoluciones', str(evolucion_id))
    os.makedirs(upload_dir, exist_ok=True)

    for archivo in archivos:
        if archivo.filename:
            filename = secure_filename(archivo.filename)
            archivo.save(os.path.join(upload_dir, filename))
            cursor.execute("""
                INSERT INTO evolucion_archivos (evolucion_id, filename)
                VALUES (%s, %s)
            """, (evolucion_id, filename))
            conn.commit()

    cursor.close()
    conn.close()

    # 🔁 Actualizar historia consolidada automáticamente
    try:
        hash_local = actualizar_historia(id, current_user.id)
        msg_extra = f" (Historia actualizada, hash {hash_local[:10]}...)" if hash_local else ""
    except Exception as e:
        print(f"⚠️ Error actualizando historia consolidada: {e}")
        msg_extra = " (⚠️ No se pudo actualizar historia)"

    return jsonify({'message': f'Evolución guardada correctamente ✅{msg_extra}'})

@bp_pacientes.route('/api/pacientes/<int:id>/evoluciones', methods=['GET'])
@login_required
def get_evoluciones(id):
    """Obtiene las evoluciones de un paciente, mostrando también el médico y su especialidad."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            e.id,
            e.fecha,
            e.contenido,
            e.usuario_id,
            u.nombre AS nombre_usuario,
            CASE 
                WHEN u.rol = 'director' THEN 'Director'
                ELSE COALESCE(u.especialidad, 'Sin especificar')
            END AS especialidad_usuario
        FROM evoluciones e
        JOIN usuarios u ON e.usuario_id = u.id
        WHERE e.paciente_id = %s
        ORDER BY e.fecha DESC
    """, (id,))
    evoluciones = cursor.fetchall()

    # Adjuntar archivos de cada evolución
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

    cursor.close()
    conn.close()
    return jsonify(evoluciones)

@bp_pacientes.route('/api/uploads/evoluciones/<int:evo_id>/<filename>')
@login_required
def uploaded_file(evo_id, filename):
    """Sirve los archivos adjuntos de evoluciones."""
    folder = os.path.join(os.getcwd(), 'uploads', 'evoluciones', str(evo_id))
    return send_from_directory(folder, filename)

# ==========================================================
# 📄 Exportar Historia Clínica en PDF (versión institucional)
# ==========================================================
@bp_pacientes.route('/api/pacientes/<int:id>/historia/pdf', methods=['GET'])
@login_required
def exportar_historia_pdf(id):
    """Genera un PDF con toda la historia clínica del paciente, incluyendo adjuntos (imágenes y enlaces)."""
    from flask import current_app
    from PIL import Image as PILImage

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Paciente
    cursor.execute("SELECT * FROM pacientes WHERE id = %s", (id,))
    paciente = cursor.fetchone()
    if not paciente:
        cursor.close(); conn.close()
        return jsonify({'error': 'Paciente no encontrado'}), 404

    # Evoluciones
    cursor.execute("""
        SELECT e.id, e.fecha, e.contenido, u.nombre AS medico, u.rol AS especialidad
        FROM evoluciones e
        JOIN usuarios u ON e.usuario_id = u.id
        WHERE e.paciente_id = %s
        ORDER BY e.fecha DESC
    """, (id,))
    evoluciones = cursor.fetchall()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=3*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Center", alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="Right", alignment=TA_RIGHT, fontSize=9, textColor="#666666"))

    elements = []
    # -------------------------------------------------------
    # 🔹 ENCABEZADO con logo y título
    # -------------------------------------------------------
    logo_path = os.path.join(current_app.root_path, "static", "img", "logo_cau_unsam2.png")

    if os.path.exists(logo_path):
        # 🔸 Logo apenas más grande
        logo = Image(logo_path, width=5*cm, height=2*cm)
    else:
        logo = Paragraph("<b>CAU UNSAM</b>", styles["Normal"])

    titulo = Paragraph("<b>Centro Asistencial Universitario </b>", styles["Title"])

    # Tabla de dos columnas: título (izquierda) y logo (derecha)
    encabezado = Table([[titulo, logo]], colWidths=[11*cm, 5*cm])
    encabezado.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(encabezado)
    elements.append(Spacer(1, 0.2*cm))

    # Fecha alineada a la derecha
    fecha_actual = datetime.now().strftime("%d/%m/%Y - %H:%M")
    elements.append(Paragraph(f"<i>Fecha de generación: {fecha_actual}</i>", styles["Right"]))
    elements.append(Spacer(1, 0.5*cm))

    # -------------------------------------------------------
    # 🔹 TÍTULO PRINCIPAL Y DATOS DEL PACIENTE
    # -------------------------------------------------------
    elements.append(Paragraph("<b>Historia Clínica</b>", styles["Heading1"]))
    elements.append(Spacer(1, 0.3*cm))

    datos_paciente = f"""
        <b>Paciente:</b> {paciente['apellido'].upper()} {paciente['nombre'].upper()}<br/>
        <b>DNI:</b> {paciente['dni']}<br/>
        <b>Cobertura:</b> {paciente.get('cobertura', '-')}<br/>
        <b>N° HC:</b> {paciente['nro_hc']}<br/>
        <b>Fecha de nacimiento:</b> {paciente.get('fecha_nacimiento', '-') or '-'}<br/>
        <b>Sexo:</b> {paciente.get('sexo', '-') or '-'}
    """
    elements.append(Paragraph(datos_paciente, styles["Normal"]))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph("<b>Evoluciones:</b>", styles["Heading2"]))
    elements.append(Spacer(1, 0.3*cm))

    # -------------------------------------------------------
    # 🔹 EVOLUCIONES CON ARCHIVOS ADJUNTOS
    # -------------------------------------------------------
    if not evoluciones:
        elements.append(Paragraph("No hay evoluciones registradas.", styles["Normal"]))
    else:
        for evo in evoluciones:
            fecha_str = evo["fecha"].strftime("%d/%m/%Y") if hasattr(evo["fecha"], "strftime") else str(evo["fecha"])
            medico = evo["medico"]
            especialidad = "Director" if evo["especialidad"] == "director" else evo["especialidad"].capitalize()

            elements.append(Paragraph(f"<b>Fecha:</b> {fecha_str}", styles["Normal"]))
            elements.append(Paragraph(f"<b>Médico:</b> {medico} ({especialidad})", styles["Normal"]))
            elements.append(Spacer(1, 0.2*cm))
            elements.append(Paragraph(evo["contenido"].replace("\n", "<br/>"), styles["Normal"]))
            elements.append(Spacer(1, 0.3*cm))

            # 🔸 Buscar archivos adjuntos
            cursor.execute("""
                SELECT filename
                FROM evolucion_archivos
                WHERE evolucion_id = %s
            """, (evo["id"],))
            archivos = cursor.fetchall()

            if archivos:
                elements.append(Paragraph("<b>Archivos adjuntos:</b>", styles["Heading3"]))
                for a in archivos:
                    filename = a["filename"]
                    ext = filename.lower().split(".")[-1]
                    file_path = os.path.join(os.getcwd(), "uploads", "evoluciones", str(evo["id"]), filename)

                    if os.path.exists(file_path):
                        if ext in ["jpg", "jpeg", "png"]:
                            try:
                                with PILImage.open(file_path) as im:
                                    width, height = im.size
                                    aspect = height / float(width)
                                    new_width = 12 * cm
                                    new_height = new_width * aspect
                                    img = Image(file_path, width=new_width, height=new_height)
                                    img.hAlign = 'CENTER'
                                    elements.append(img)
                                    elements.append(Spacer(1, 0.3*cm))
                            except Exception as e:
                                elements.append(Paragraph(f"⚠️ No se pudo mostrar {filename}", styles["Normal"]))
                        else:
                            base_url = request.host_url.rstrip('/')
                            url = f"{base_url}/api/uploads/evoluciones/{evo['id']}/{filename}"

                            elements.append(Paragraph(
                                f"• <b>{filename}</b> — "
                                f"<a href='{url}' color='blue'>Haga clic aquí para descargar</a>",
                                styles['Normal']
                            ))

                            elements.append(Spacer(1, 0.5*cm))

                        # Salto de página cada 4 evoluciones aprox.
                        if evoluciones.index(evo) % 4 == 3:
                            elements.append(PageBreak())

    # -------------------------------------------------------
    # 🔹 PIE DE PÁGINA
    # -------------------------------------------------------
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        text = "Documento emitido por el Sistema de Historia Clínica - Centro Asistencial Universitario UNSAM"
        fecha_texto = datetime.now().strftime("%d/%m/%Y")
        canvas.drawString(2 * cm, 1.5 * cm, text)
        canvas.drawRightString(19 * cm, 1.5 * cm, f"Fecha de emisión: {fecha_texto}")
        canvas.restoreState()

    # -------------------------------------------------------
    # 🔹 Páginas con marca de agua + footer
    # -------------------------------------------------------
    def first_page(canvas, doc):
        dibujar_marca_agua(canvas, doc)
        footer(canvas, doc)

    def later_pages(canvas, doc):
        dibujar_marca_agua(canvas, doc)
        footer(canvas, doc)

    # -------------------------------------------------------
    # 🔹 CONSTRUCCIÓN FINAL
    # -------------------------------------------------------
    doc.build(elements, onFirstPage=first_page, onLaterPages=later_pages )
    buffer.seek(0)
    cursor.close(); conn.close()

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"historia_paciente_{id}.pdf",
        mimetype="application/pdf"
    )


# ==========================================================
# 📄 Exportar Evolución individual en PDF
# ==========================================================

@bp_pacientes.route('/api/pacientes/<int:paciente_id>/evolucion/<int:evo_id>/pdf', methods=['GET'])
@login_required
def exportar_evolucion_pdf(paciente_id, evo_id):
    """Genera un PDF con una sola evolución clínica del paciente."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Paciente
    cursor.execute("SELECT * FROM pacientes WHERE id = %s", (paciente_id,))
    paciente = cursor.fetchone()
    if not paciente:
        cursor.close(); conn.close()
        return jsonify({'error': 'Paciente no encontrado'}), 404

    # Evolución específica
    cursor.execute("""
        SELECT e.id, e.fecha, e.contenido, u.nombre AS medico, 
               CASE WHEN u.rol = 'director' THEN 'Director'
                    ELSE COALESCE(u.especialidad, 'Sin especificar')
               END AS especialidad
        FROM evoluciones e
        JOIN usuarios u ON e.usuario_id = u.id
        WHERE e.paciente_id = %s AND e.id = %s
        LIMIT 1
    """, (paciente_id, evo_id))
    evolucion = cursor.fetchone()

    if not evolucion:
        cursor.close(); conn.close()
        return jsonify({'error': 'Evolución no encontrada'}), 404

    # Archivos adjuntos
    cursor.execute("""
        SELECT filename
        FROM evolucion_archivos
        WHERE evolucion_id = %s
    """, (evo_id,))
    archivos = cursor.fetchall()
    cursor.close(); conn.close()

    # -------------------------------------------------------
    # 📄 Construcción del PDF
    # -------------------------------------------------------
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=3*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Right", alignment=TA_RIGHT, fontSize=9, textColor="#666666"))

    elements = []

    # 🔹 Encabezado institucional
    logo_path = os.path.join(current_app.root_path, "static", "img", "logo_cau_unsam2.png")

    if os.path.exists(logo_path):
        logo = Image(logo_path, width=5*cm, height=2*cm)
    else:
        logo = Paragraph("<b>CAU UNSAM</b>", styles["Normal"])

    titulo = Paragraph("<b>Centro Asistencial Universitario UNSAM</b>", styles["Title"])

    # Crear tabla con dos columnas: título (izquierda), logo (derecha)
    encabezado = Table([[titulo, logo]], colWidths=[11*cm, 5*cm])
    encabezado.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(encabezado)
    elements.append(Spacer(1, 0.2*cm))

    # Fecha de generación alineada a la derecha
    fecha_actual = datetime.now().strftime("%d/%m/%Y - %H:%M")
    elements.append(Paragraph(f"<i>Fecha de generación: {fecha_actual}</i>", styles["Right"]))
    elements.append(Spacer(1, 0.5*cm))

    # 🔹 Datos del paciente
    datos_paciente = f"""
        <b>Paciente:</b> {paciente['apellido'].upper()} {paciente['nombre'].upper()}<br/>
        <b>DNI:</b> {paciente['dni']}<br/>
        <b>N° HC:</b> {paciente['nro_hc']}<br/>
        <b>Cobertura:</b> {paciente.get('cobertura', '-')}
    """
    elements.append(Paragraph(datos_paciente, styles["Normal"]))
    elements.append(Spacer(1, 0.5*cm))

    # 🔹 Detalle de la evolución
    fecha_str = evolucion["fecha"].strftime("%d/%m/%Y") if hasattr(evolucion["fecha"], "strftime") else str(evolucion["fecha"])
    medico = evolucion["medico"]
    especialidad = evolucion["especialidad"]

    elements.append(Paragraph(f"<b>Fecha:</b> {fecha_str}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Médico:</b> {medico} ({especialidad})", styles["Normal"]))
    elements.append(Spacer(1, 0.4*cm))
    elements.append(Paragraph(evolucion["contenido"].replace("\n", "<br/>"), styles["Normal"]))
    elements.append(Spacer(1, 0.5*cm))

    # 🔹 Archivos adjuntos
    if archivos:
        elements.append(Paragraph("<b>Archivos adjuntos:</b>", styles["Heading3"]))
        for a in archivos:
            nombre_archivo = a["filename"]
            url = f"/api/uploads/evoluciones/{evo_id}/{nombre_archivo}"
            elements.append(Paragraph(f"• {nombre_archivo}", styles["Normal"]))
    else:
        elements.append(Paragraph("<i>Sin archivos adjuntos</i>", styles["Normal"]))

    # 🔹 Pie de página
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        text = "Documento emitido por el Sistema de Historia Clínica - Centro Asistencial Universitario UNSAM"
        fecha_texto = datetime.now().strftime("%d/%m/%Y")
        canvas.drawString(2 * cm, 1.5 * cm, text)
        canvas.drawRightString(19 * cm, 1.5 * cm, f"Fecha de emisión: {fecha_texto}")
        canvas.restoreState()

    # 🔹 Construcción final
    doc.build(elements, onFirstPage=footer, onLaterPages=footer)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"evolucion_{evo_id}_paciente_{paciente_id}.pdf",
        mimetype="application/pdf"
    )


from reportlab.lib.colors import Color

def dibujar_marca_agua(canvas, doc):
    """
    Dibuja una marca de agua diagonal suave en cada página.
    """
    canvas.saveState()

    canvas.setFont("Helvetica-Bold", 50)
    canvas.setFillColor(Color(0.6, 0.6, 0.6, alpha=0.12))  # gris suave transparente

    # Mover al centro de página
    width, height = A4
    canvas.translate(width / 2, height / 2)

    # Rotar texto 45 grados
    canvas.rotate(35)

    # Dibujar texto centrado
    texto = "DOCUMENTO CONFIDENCIAL – CAU UNSAM"
    canvas.drawCentredString(0, 0, texto)

    canvas.restoreState()
