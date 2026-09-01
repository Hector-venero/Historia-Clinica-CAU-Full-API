from flask import Blueprint, request, jsonify, send_from_directory, send_file, current_app, g
from flask_login import login_required, current_user
from app import marca
from app.database import db_cursor
from app.utils.adjuntos import carpeta_evolucion, ruta_adjunto, url_adjunto
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
from reportlab.lib import colors

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

    with db_cursor() as (conn, cursor):
        # Verificar duplicado por DNI
        cursor.execute("SELECT id FROM pacientes WHERE dni = %s", (data.get('dni'),))
        if cursor.fetchone():
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

    return jsonify({'message': 'Paciente registrado correctamente ✅'})

@bp_pacientes.route('/api/pacientes/<int:id>', methods=['PUT'])
@login_required
def api_modificar_paciente(id):
    """Modifica los datos de un paciente existente."""
    data = request.get_json() if request.is_json else request.form.to_dict()

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

    with db_cursor(dictionary=False) as (conn, cursor):
        cursor.execute(query, values)
        conn.commit()

    return jsonify({'message': 'Paciente modificado correctamente ✅'})


@bp_pacientes.route('/api/pacientes', methods=['GET'])
@login_required
def api_listar_pacientes():
    """Devuelve el listado completo de pacientes."""
    try:
        with db_cursor() as (conn, cursor):
            cursor.execute("""
                SELECT id, dni, nombre, apellido, fecha_nacimiento, sexo, telefono, email
                FROM pacientes
                ORDER BY apellido, nombre
            """)
            pacientes = cursor.fetchall()
        return jsonify(pacientes)
    except Exception as e:
        current_app.logger.exception("Error en /api/pacientes")
        return jsonify({"error": str(e)}), 500


@bp_pacientes.route('/api/pacientes/<int:id>', methods=['GET'])
@login_required
def api_get_paciente(id):
    """Obtiene los datos de un paciente por ID."""
    with db_cursor() as (_conn, cursor):
        cursor.execute("SELECT * FROM pacientes WHERE id = %s", (id,))
        paciente = cursor.fetchone()

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
    with db_cursor(dictionary=False) as (conn, cursor):
        cursor.execute("SELECT id FROM pacientes WHERE id = %s", (id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Paciente no encontrado'}), 404

        cursor.execute("DELETE FROM pacientes WHERE id = %s", (id,))
        conn.commit()

    return jsonify({'message': 'Paciente eliminado correctamente ✅'})


@bp_pacientes.route('/api/pacientes/proximo-nro-hc', methods=['GET'])
@login_required
def proximo_nro_hc():
    """Sugiere el próximo número de historia clínica libre.

    Se toma el máximo de los nro_hc puramente numéricos y se le suma uno. El
    REGEXP es necesario porque la columna es VARCHAR y puede tener valores con
    letras o guiones de cargas viejas: un CAST directo los convertiría en 0 y
    además haría un full scan comparando basura.

    Es una sugerencia, no una reserva: el alta sigue validando duplicados, que
    es lo que resuelve dos usuarios cargando al mismo tiempo.
    """
    with db_cursor() as (_conn, cursor):
        cursor.execute("""
            SELECT MAX(CAST(nro_hc AS UNSIGNED)) AS max_hc
            FROM pacientes
            WHERE nro_hc REGEXP '^[0-9]+$'
        """)
        fila = cursor.fetchone()

    max_hc = (fila or {}).get('max_hc') or 0
    return jsonify({'proximo_nro_hc': str(max_hc + 1)})


@bp_pacientes.route('/api/pacientes/buscar', methods=['GET'])
@login_required
def buscar_pacientes():
    """Busca pacientes por nombre, apellido, DNI o N° de historia clínica."""
    term = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    per_page = 10

    like_term = f"%{term}%"

    with db_cursor() as (_conn, cursor):
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
    indicaciones = request.form.get('indicaciones')  
    archivos = request.files.getlist('archivos')

    if not fecha or not contenido:
        return jsonify({'error': 'Faltan campos obligatorios'}), 400

    # El guardado de archivos a disco puede fallar (permisos, espacio); sin el
    # context manager, esa excepcion dejaba la conexion abierta.
    with db_cursor(dictionary=False) as (conn, cursor):
        cursor.execute("""
                INSERT INTO evoluciones (paciente_id, fecha, contenido, indicaciones, usuario_id)
                VALUES (%s, %s, %s, %s, %s)
        """, (id, fecha, contenido, indicaciones, current_user.id))
        conn.commit()
        evolucion_id = cursor.lastrowid

        upload_dir = carpeta_evolucion(evolucion_id, crear=True)

        for archivo in archivos:
            if archivo.filename:
                filename = secure_filename(archivo.filename)
                archivo.save(os.path.join(upload_dir, filename))
                cursor.execute("""
                    INSERT INTO evolucion_archivos (evolucion_id, filename)
                    VALUES (%s, %s)
                """, (evolucion_id, filename))
                conn.commit()

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
    from app import accesos

    accesos.registrar(id, accesos.VER_EVOLUCIONES)

    with db_cursor() as (_conn, cursor):
        cursor.execute("""
            SELECT
                e.id,
                e.fecha,
                e.contenido,
                e.indicaciones,
                e.creado_en,
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
                'url': url_adjunto(evo['id'], a['filename'])
            } for a in archivos]

    return jsonify(evoluciones)

@bp_pacientes.route('/api/uploads/evoluciones/<int:evo_id>/<filename>')
@login_required
def uploaded_file(evo_id, filename):
    """Sirve los archivos adjuntos de evoluciones.

    Es el unico camino hacia estos archivos. nginx los publicaba ademas en
    /uploads/ directamente desde el volumen, sin pasar por aca y por lo tanto
    sin exigir sesion: cualquiera con la URL se descargaba un adjunto clinico.
    """
    # La URL no trae el paciente, asi que hay que resolverlo. Es una consulta
    # por clave primaria y vale la pena: bajarse una radiografia es exactamente
    # lo que se quiere poder auditar, y sin el paciente la fila no sirve para
    # responder "quien miro esta historia".
    from app import accesos

    paciente_id = None
    try:
        with db_cursor() as (_conn, cursor):
            cursor.execute("SELECT paciente_id FROM evoluciones WHERE id = %s", (evo_id,))
            fila = cursor.fetchone()
            paciente_id = fila and fila.get("paciente_id")
    except Exception:
        paciente_id = None

    if paciente_id:
        accesos.registrar(
            paciente_id, accesos.DESCARGAR_ADJUNTO, detalle=str(filename)[:255]
        )

    return send_from_directory(carpeta_evolucion(evo_id), filename)

# ==========================================================
# 📄 Exportar Historia Clínica en PDF (versión institucional)
# ==========================================================
@bp_pacientes.route('/api/pacientes/<int:id>/historia/pdf', methods=['GET'])
@login_required
def exportar_historia_pdf(id):
    """Genera un PDF con toda la historia clínica del paciente, incluyendo adjuntos (imágenes y enlaces)."""
    from flask import current_app
    from PIL import Image as PILImage

    # La exportación se anota aparte de la lectura: llevarse la historia entera
    # en un archivo no es lo mismo que mirarla en pantalla, y es lo que
    # realmente se investiga cuando algo se filtra.
    from app import accesos

    accesos.registrar(id, accesos.EXPORTAR_HISTORIA)

    # Se leen todos los datos primero y se suelta la conexion antes de generar
    # el PDF: el render con reportlab puede tardar segundos y no tiene sentido
    # retener una conexion de MySQL mientras tanto.
    with db_cursor() as (_conn, cursor):
        # Paciente
        cursor.execute("SELECT * FROM pacientes WHERE id = %s", (id,))
        paciente = cursor.fetchone()
        if not paciente:
            return jsonify({'error': 'Paciente no encontrado'}), 404

        # Evoluciones
        cursor.execute("""
            SELECT
                e.id,
                e.fecha,
                e.contenido,
                e.indicaciones,
                e.creado_en,
                u.nombre AS medico,
                CASE
                    WHEN u.rol = 'director' THEN 'Director'
                    ELSE COALESCE(u.especialidad, 'Sin especificar')
                END AS especialidad
            FROM evoluciones e
            JOIN usuarios u ON e.usuario_id = u.id
            WHERE e.paciente_id = %s
            ORDER BY e.fecha DESC
        """, (id,))

        evoluciones = cursor.fetchall()

        # Adjuntos de todas las evoluciones en una sola query, en vez de una por
        # evolucion dentro del loop de render (era un N+1 y ademas obligaba a
        # sostener la conexion durante todo el armado del PDF).
        archivos_por_evolucion = {}
        if evoluciones:
            ids_evo = [e["id"] for e in evoluciones]
            marcadores = ", ".join(["%s"] * len(ids_evo))
            cursor.execute(f"""
                SELECT evolucion_id, filename
                FROM evolucion_archivos
                WHERE evolucion_id IN ({marcadores})
            """, tuple(ids_evo))
            for fila in cursor.fetchall():
                archivos_por_evolucion.setdefault(fila["evolucion_id"], []).append(fila)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Right", alignment=TA_RIGHT, fontSize=9, textColor="#666666"))

    style_box = TableStyle([
        ('BOX', (0,0), (-1,-1), 0.6, colors.lightgrey),
        ('INNERGRID', (0,0), (-1,-1), 0.3, colors.lightgrey),
        ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ])

    elements = []
    # -------------------------------------------------------
    # 🔹 ENCABEZADO con logo y título
    # -------------------------------------------------------
    # El logo sale de la marca del consultorio, NO de una ruta escrita a mano.
    #
    # Estaba fijo en el escudo de la UNSAM, asi que cualquier consultorio de la
    # plataforma emitia historias clinicas con la identidad de otra institucion.
    # Sin logo propio va el nombre en texto: nunca el de otro.
    logo_path = marca.logo_archivo()

    if logo_path:
        logo = Image(logo_path, width=5*cm, height=2*cm)
    else:
        logo = Paragraph(f"<b>{marca.nombre_corto()}</b>", styles["Normal"])

    titulo = Paragraph(f"<b>{marca.nombre()}</b>", styles["Title"])

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
    elements.append(Spacer(1, 0.1*cm))

    # -------------------------------------------------------
    # 🔹 TÍTULO PRINCIPAL Y DATOS DEL PACIENTE
    # -------------------------------------------------------
    elements.append(Paragraph("<b>Historia Clínica</b>", styles["Heading1"]))
    elements.append(Spacer(1, 0.3*cm))

    datos_paciente = f"""
        <b>Paciente:</b> {paciente['apellido'].upper()} {paciente['nombre'].upper()}<br/>
        <b>DNI:</b> {paciente['dni']}<br/>
        <b>Cobertura:</b> {paciente.get('cobertura') or '-'}<br/>
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

            fecha_registro = evo["creado_en"].strftime("%d/%m/%Y %H:%M")

            fila_superior = Table([
                [
                    Paragraph(f"<b>Fecha:</b> {fecha_str}", styles["Normal"]),
                    Paragraph(f"<font size='9' color='gray'>Registrado: {fecha_registro}</font>", styles["Right"])
                ]
            ], colWidths=[8*cm, 8*cm])

            fila_superior.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ]))

            fila_medico = Paragraph(f"<b>Médico:</b> {medico} ({especialidad})", styles["Normal"])

            fila_contenido = Paragraph(evo["contenido"].replace("\n", "<br/>"), styles["Normal"])

            if evo.get("indicaciones"):
                fila_indicaciones = Paragraph(f"<b>Indicaciones:</b> {evo['indicaciones'].replace('\n','<br/>')}", styles["Normal"])
            else:
                fila_indicaciones = Paragraph("", styles["Normal"])

            # --- ARMADO DEL BLOQUE FINAL ---
            filas = [
                [fila_superior],
                [fila_medico],
                [fila_contenido], 
            ]

            if evo.get("indicaciones"):
                filas.append([fila_indicaciones])

            bloque = Table(filas, colWidths=[16.5*cm])
            bloque.setStyle(style_box)

            elements.append(bloque)
            elements.append(Spacer(1, 0.4*cm))
            elements.append(Spacer(1, 0.1*cm))

            # 🔸 Archivos adjuntos (ya prefetcheados, sin tocar la DB aca)
            archivos = archivos_por_evolucion.get(evo["id"], [])

            if archivos:
                elements.append(Paragraph("<b>Archivos adjuntos:</b>", styles["Heading3"]))
                for a in archivos:
                    filename = a["filename"]
                    ext = filename.lower().split(".")[-1]
                    file_path = str(ruta_adjunto(evo["id"], filename))

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
                            url = url_adjunto(evo["id"], filename, base=request.host_url.rstrip('/'))

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
        canvas.setFillColorRGB(0.4, 0.4, 0.4)

        # Texto institucional
        texto = f"Documento emitido por el Sistema de Historia Clínica – {marca.nombre()}"
        canvas.drawString(2 * cm, 1.4 * cm, texto)

        # Fecha y hora de emisión
        fecha_hora = datetime.now().strftime("%d/%m/%Y - %H:%M")
        canvas.drawRightString(19 * cm, 1.4 * cm, f"Emitido: {fecha_hora}")

        # Número de página
        numero_pagina = canvas.getPageNumber()
        canvas.drawRightString(19 * cm, 1.0 * cm, f"Página {numero_pagina}")

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
    """Genera un PDF institucional con una sola evolución clínica."""

    from flask import current_app
    from PIL import Image as PILImage

    from app import accesos

    accesos.registrar(
        paciente_id, accesos.EXPORTAR_EVOLUCION, detalle=f"evolución {evo_id}"
    )

    with db_cursor() as (_conn, cursor):
        # ==========================================================
        #  1) DATOS DEL PACIENTE
        # ==========================================================
        cursor.execute("SELECT * FROM pacientes WHERE id = %s", (paciente_id,))
        paciente = cursor.fetchone()
        if not paciente:
            return jsonify({'error': 'Paciente no encontrado'}), 404

        # ==========================================================
        #  2) DATOS DE LA EVOLUCIÓN
        # ==========================================================
        cursor.execute("""
            SELECT e.id, e.fecha, e.contenido, e.indicaciones, e.creado_en,
                   u.nombre AS medico,
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
            return jsonify({'error': 'Evolución no encontrada'}), 404

        # ==========================================================
        #  3) ARCHIVOS ADJUNTOS
        # ==========================================================
        cursor.execute("SELECT filename FROM evolucion_archivos WHERE evolucion_id = %s", (evo_id,))
        archivos = cursor.fetchall()

    # ==========================================================
    #  4) PDF – Construcción principal
    # ==========================================================
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Right", alignment=TA_RIGHT, fontSize=9, textColor="#666666"))

    elements = []

    # ----------------------------------------------------------
    # 🔹 ENCABEZADO CON LOGO Y TÍTULO
    # ----------------------------------------------------------
    # Ver la nota del otro generador: el logo es el del consultorio o ninguno.
    logo_path = marca.logo_archivo()

    if logo_path:
        logo = Image(logo_path, width=5*cm, height=2*cm)
    else:
        logo = Paragraph(f"<b>{marca.nombre_corto()}</b>", styles["Normal"])

    titulo = Paragraph(f"<b>{marca.nombre()}</b>", styles["Title"])

    encabezado = Table([[titulo, logo]], colWidths=[11*cm, 5*cm])
    encabezado.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0)
    ]))

    elements.append(encabezado)
    elements.append(Spacer(1, 0.3*cm))

    # Fecha de generación
    fecha_actual = datetime.now().strftime("%d/%m/%Y - %H:%M")
    elements.append(Paragraph(f"<i>Fecha de generación: {fecha_actual}</i>", styles["Right"]))
    elements.append(Spacer(1, 0.5*cm))

    # ----------------------------------------------------------
    # 🔹 DATOS DEL PACIENTE
    # ----------------------------------------------------------
    datos_paciente = f"""
        <b>Paciente:</b> {paciente['apellido']} {paciente['nombre']}<br/>
        <b>DNI:</b> {paciente['dni']}<br/>
        <b>N° HC:</b> {paciente['nro_hc']}<br/>
        <b>Cobertura:</b> {paciente.get('cobertura') or '-'}
    """
    elements.append(Paragraph(datos_paciente, styles["Normal"]))
    elements.append(Spacer(1, 0.5*cm))

    # ----------------------------------------------------------
    # INFORMACIÓN DE LA EVOLUCIÓN
    # ----------------------------------------------------------
    fecha_evo = evolucion["fecha"].strftime("%d/%m/%Y")

    elements.append(Paragraph(f"<b>Fecha:</b> {fecha_evo}", styles["Normal"]))
    elements.append(Spacer(1, 0.1*cm))
    elements.append(Paragraph(f"<b>Médico:</b> {evolucion['medico']} ({evolucion['especialidad']})", styles["Normal"]))
    elements.append(Spacer(1, 0.1*cm))
    fecha_creacion = evolucion["creado_en"].strftime("%d/%m/%Y %H:%M")
    elements.append(Paragraph(f"<b>Registrado en el sistema:</b> {fecha_creacion}", styles["Normal"]))
    elements.append(Spacer(1, 0.25*cm))

    # --- CONTENIDO DE LA EVOLUCIÓN ---
    elements.append(Paragraph("<b>Evolución:</b>", styles["Normal"]))
    elements.append(Paragraph(evolucion["contenido"].replace("\n", "<br/>"), styles["Normal"]))
    elements.append(Spacer(1, 0.3*cm))

    # --- INDICACIONES (OPCIONAL) ---
    if evolucion.get("indicaciones"):
        elements.append(Paragraph("<b>Indicaciones:</b>", styles["Normal"]))
        elements.append(Paragraph(evolucion["indicaciones"].replace("\n","<br/>"), styles["Normal"]))
        elements.append(Spacer(1, 0.3*cm))

    # ----------------------------------------------------------
    # ARCHIVOS ADJUNTOS (IMÁGENES + LINKS)
    # ----------------------------------------------------------
    if archivos:
        elements.append(Paragraph("<b>Archivos adjuntos:</b>", styles["Heading3"]))
        elements.append(Spacer(1, 0.1*cm))

        for a in archivos:
            nombre = a["filename"]
            # Era una ruta relativa, asi que dependia por completo del directorio
            # de trabajo del proceso: con gunicorn (--chdir /) apuntaba a
            # /uploads, fuera del volumen.
            file_path = str(ruta_adjunto(evo_id, nombre))
            ext = nombre.lower().split(".")[-1]

            # IMÁGENES
            if ext in ["jpg", "jpeg", "png"]:
                try:
                    with PILImage.open(file_path) as im:
                        w, h = im.size
                        aspect = h / w
                        new_width = 12 * cm
                        new_height = new_width * aspect

                        img = Image(file_path, width=new_width, height=new_height)
                        img.hAlign = "CENTER"
                        elements.append(img)
                        elements.append(Spacer(1, 0.3*cm))
                except:
                    elements.append(Paragraph(f"⚠️ No se pudo mostrar {nombre}", styles["Normal"]))
            else:
                # LINK CLICKEABLE
                url = url_adjunto(evo_id, nombre, base=request.host_url.rstrip('/'))
                elements.append(Paragraph(f"• <a href='{url}' color='blue'>{nombre}</a>", styles["Normal"]))
                elements.append(Spacer(1, 0.1*cm))

    else:
        elements.append(Paragraph("<i>Sin archivos adjuntos</i>", styles["Normal"]))

    # ----------------------------------------------------------
    #  FOOTER + MARCA DE AGUA
    # ----------------------------------------------------------
    def footer(canvas, doc):
        dibujar_marca_agua(canvas, doc)
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawString(2 * cm, 1.5 * cm,
            f"Documento emitido por el Sistema de Historia Clínica – {marca.nombre_corto()}")
        canvas.restoreState()

    doc.build(elements, onFirstPage=footer, onLaterPages=footer)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"evolucion_{evo_id}.pdf",
        mimetype="application/pdf"
    )


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
    texto = f"DOCUMENTO CONFIDENCIAL – {marca.nombre_corto()}"
    canvas.drawCentredString(0, 0, texto)

    canvas.restoreState()

# ==========================================================
# 📤 Enviar un documento al paciente (portal de Ficha Salud)
# ==========================================================

@bp_pacientes.route('/api/pacientes/<int:paciente_id>/enviar_al_portal', methods=['POST'])
@login_required
def enviar_al_portal(paciente_id):
    """Publica un estudio, receta o informe en el buzon del paciente.

    Es **el unico punto** donde el sistema de un consultorio escribe en el plano
    del paciente, y por eso esta acotado a una sola operacion explicita: alguien
    del equipo decide, documento por documento, que sale del consultorio.

    Lo que se envia se COPIA, no se referencia:

      - El archivo va a uploads/_portal/<token>/, fuera de la carpeta del
        consultorio. Si ese consultorio cancela y se borra su carpeta, lo que el
        paciente ya recibio tiene que seguir estando.
      - El nombre del consultorio y del profesional viajan como texto. Por lo
        mismo: el paciente tiene que poder saber quien le mando su estudio
        aunque ese consultorio ya no exista.

    Si el paciente todavia no tiene cuenta, el documento queda esperando por su
    numero de documento y aparece cuando se registra.
    """
    import shutil

    from app import marca, portal
    from app.utils.adjuntos import carpeta_portal, ruta_adjunto
    from app.utils.correo import enviar_en_segundo_plano
    from app.utils.mails_portal import mail_documento_enviado

    datos = request.get_json(silent=True) or {}

    tipo = (datos.get("tipo") or "informe").strip().lower()
    titulo = (datos.get("titulo") or "").strip()
    descripcion = (datos.get("descripcion") or "").strip() or None
    evolucion_id = datos.get("evolucion_id")
    nombre_archivo = (datos.get("archivo") or "").strip() or None

    if not titulo:
        return jsonify({"error": "El documento necesita un titulo."}), 400

    # Se anota despues de validar y antes de escribir: es el unico punto donde
    # algo clinico sale del consultorio, asi que la fila tiene que existir
    # aunque el envio falle mas adelante.
    from app import accesos

    accesos.registrar(paciente_id, accesos.ENVIAR_AL_PORTAL, detalle=titulo)

    with db_cursor() as (_conn, cursor):
        cursor.execute("SELECT * FROM pacientes WHERE id = %s", (paciente_id,))
        paciente = cursor.fetchone()

    if not paciente:
        return jsonify({"error": "Paciente no encontrado"}), 404

    if not paciente.get("dni"):
        # Sin documento no hay a quien dirigirlo: es la identidad con la que el
        # paciente se registra en el portal.
        return jsonify({
            "error": "El paciente no tiene documento cargado.",
            "detalle": "Es el dato con el que va a encontrar sus estudios.",
        }), 400

    # El archivo se copia a la carpeta del portal. Si falla la copia no se
    # registra el envio: es preferible a dejar en el buzon un documento que
    # apunta a un archivo que no existe.
    archivo_token = None
    if nombre_archivo and evolucion_id:
        origen = ruta_adjunto(int(evolucion_id), nombre_archivo)
        if not os.path.isfile(origen):
            return jsonify({"error": "No se encontro el archivo adjunto."}), 404

        archivo_token = portal.nuevo_token_archivo()
        destino = carpeta_portal(archivo_token, crear=True)
        try:
            shutil.copy2(origen, destino / nombre_archivo)
        except OSError:
            current_app.logger.exception("No se pudo copiar el adjunto al portal")
            return jsonify({"error": "No se pudo preparar el archivo."}), 500

    try:
        documento_id = portal.guardar_documento(
            tipo_documento=paciente.get("tipo_documento") or "DNI",
            numero_documento=paciente["dni"],
            consultorio_slug=getattr(getattr(g, "cliente", None), "slug", "principal"),
            consultorio_nombre=marca.nombre_corto(),
            profesional_nombre=current_user.nombre,
            tipo=tipo,
            titulo=titulo,
            descripcion=descripcion,
            archivo_token=archivo_token,
            archivo_nombre=nombre_archivo,
        )
    except portal.ErrorPortal as exc:
        return jsonify({"error": str(exc)}), 400

    # Aviso por correo, sin adjuntar el documento: un estudio clinico en un mail
    # viaja sin cifrar y queda en la bandeja de quien sea que lo reenvie.
    #
    # Y solo si el paciente lo quiere: puede compartir la casilla, o no querer
    # que un asunto delate de que consultorio le escriben. El documento se
    # guarda igual en el portal — lo que se apaga es el aviso, no el envio.
    if paciente.get("email") and _quiere_aviso_de_documentos(paciente.get("email")):
        dominio = (current_app.config.get("DOMINIO_BASE") or "").strip().strip(".")
        url_portal = f"https://mi.{dominio}" if dominio else "http://mi.localhost:5173"
        mensaje = mail_documento_enviado(
            destinatario=paciente["email"],
            nombre_paciente=paciente.get("nombre") or "",
            consultorio=marca.nombre_corto(),
            tipo=tipo,
            titulo=titulo,
            url_portal=url_portal,
        )
        if mensaje is not None:
            enviar_en_segundo_plano(mensaje)

    return jsonify({
        "mensaje": "Enviado al portal del paciente",
        "documento_id": documento_id,
        # Le dice al profesional si el paciente lo va a ver ya o cuando se
        # registre. Sin esto parece que no llego.
        "tiene_cuenta": portal.buscar_por_documento(
            paciente.get("tipo_documento") or "DNI", paciente["dni"]
        ) is not None,
    }), 201


def _quiere_aviso_de_documentos(email):
    """Si el paciente tiene cuenta en el portal y apago este aviso.

    Sin cuenta no hay preferencia que respetar: el aviso es justamente lo que le
    dice que le mandaron algo y que puede registrarse para verlo.

    Un error consultando el plano del portal no puede impedir el envio: se
    prefiere avisar de mas antes que dejar a alguien sin enterarse de un estudio.
    """
    try:
        from app import portal

        cuenta = portal.buscar_por_email(email)
        if cuenta is None:
            return True
        return bool(getattr(cuenta, "avisar_documentos", True))
    except Exception:
        current_app.logger.exception(
            "No se pudo leer la preferencia de avisos del paciente"
        )
        return True
