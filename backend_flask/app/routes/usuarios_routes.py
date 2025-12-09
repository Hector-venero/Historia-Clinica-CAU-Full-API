from flask import Blueprint, request, jsonify, current_app as app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from app.database import get_connection
from app.utils.permisos import requiere_rol
import os
from PIL import Image
import io
from app.utils.validacion import password_valida, validar_email


bp_usuarios = Blueprint("usuarios", __name__)

ROLES_VALIDOS = {"director", "profesional", "administrativo"}

# ============================================================
#  RUTAS ORIGINALES (NO MODIFICADAS)
# ============================================================

@bp_usuarios.route('/api/usuarios', methods=['POST'])
@login_required
@requiere_rol('director')
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

    if not validar_email(email):
        return jsonify({'error': 'Email inválido'}), 400

    if not password_valida(password):
        return jsonify({
            'error': 'La contraseña debe tener mínimo 8 caracteres, incluir mayúscula, minúscula y número.'
        }), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id FROM usuarios WHERE username = %s OR email = %s",
                   (username, email))
    existente = cursor.fetchone()

    if existente:
        return jsonify({'error': 'Ya existe un usuario con ese nombre de usuario o email'}), 400

    password_hash = generate_password_hash(password, method="scrypt")

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


@bp_usuarios.route('/api/usuarios/me', methods=['GET'])
@login_required
@requiere_rol('director')
def api_usuarios_listado():
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


@bp_usuarios.route('/api/usuarios/<int:usuario_id>', methods=['GET'])
@login_required
@requiere_rol('director')
def api_usuarios_detalle(usuario_id):
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


@bp_usuarios.route('/api/usuarios/<int:usuario_id>', methods=['PUT'])
@login_required
@requiere_rol('director')
def api_usuarios_editar(usuario_id):
    data = request.get_json(silent=True) or {}
    nombre = (data.get("nombre") or "").strip()
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    rol = (data.get("rol") or "").strip()
    especialidad = (data.get("especialidad") or "").strip()
    password = data.get("password")

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
    actual = cur.fetchone()
    if not actual:
        cur.close(); conn.close()
        return jsonify({"error": "Usuario no encontrado"}), 404

    # Validaciones
    if username and username != actual["username"]:
        cur.execute("SELECT id FROM usuarios WHERE username=%s AND id<>%s",
                    (username, usuario_id))
        if cur.fetchone():
            cur.close(); conn.close()
            return jsonify({"error": "Ya existe otro usuario con ese username"}), 400

    if email and email != actual["email"]:
        cur.execute("SELECT id FROM usuarios WHERE email=%s AND id<>%s",
                    (email, usuario_id))
        if cur.fetchone():
            cur.close(); conn.close()
            return jsonify({"error": "Ya existe otro usuario con ese email"}), 400

    if rol and rol not in ROLES_VALIDOS:
        cur.close(); conn.close()
        return jsonify({"error": "Rol inválido"}), 400

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
        if rol == "profesional":
            sets.append("especialidad=%s")
            params.append(especialidad.upper() if especialidad else None)
        else:
            sets.append("especialidad=%s"); params.append(None)

    if password:
        if not password_valida(password):
            cur.close(); conn.close()
            return jsonify({
                "error": "La contraseña debe tener mínimo 8 caracteres e incluir mayúscula, minúscula, número y símbolo."
            }), 400

        sets.append("password_hash=%s")
        params.append(generate_password_hash(password, method="scrypt"))

    if not sets:
        cur.close(); conn.close()
        return jsonify({"message": "Sin cambios"}), 200

    params.append(usuario_id)
    q = f"UPDATE usuarios SET {', '.join(sets)} WHERE id=%s"
    cur.execute(q, tuple(params))

    conn.commit()
    cur.close(); conn.close()

    return jsonify({"message": "Usuario actualizado ✅"})


@bp_usuarios.route('/api/usuarios/<int:usuario_id>', methods=['DELETE'])
@login_required
@requiere_rol('director')
def api_usuarios_eliminar(usuario_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT id, activo FROM usuarios WHERE id=%s", (usuario_id,))
    usuario = cur.fetchone()
    if not usuario:
        cur.close(); conn.close()
        return jsonify({"error": "Usuario no encontrado"}), 404

    if usuario["activo"] == 0:
        cur.close(); conn.close()
        return jsonify({"message": "Usuario ya estaba inactivo"}), 200

    cur.execute("UPDATE usuarios SET activo=0 WHERE id=%s", (usuario_id,))
    conn.commit()

    cur.close(); conn.close()
    return jsonify({"message": "Usuario marcado como inactivo ✅"})


@bp_usuarios.route('/api/usuarios/<int:usuario_id>/activar', methods=['PUT'])
@login_required
@requiere_rol('director')
def api_usuarios_activar(usuario_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT id, activo FROM usuarios WHERE id=%s", (usuario_id,))
    usuario = cur.fetchone()
    if not usuario:
        cur.close(); conn.close()
        return jsonify({"error": "Usuario no encontrado"}), 404

    cur.execute("UPDATE usuarios SET activo=1 WHERE id=%s", (usuario_id,))
    conn.commit()

    cur.close(); conn.close()
    return jsonify({"message": "Usuario reactivado ✅"})


@bp_usuarios.route('/api/profesionales', methods=['GET'])
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


@bp_usuarios.route("/api/usuarios/<int:usuario_id>/duracion", methods=["PATCH"])
@login_required
def actualizar_duracion_turno(usuario_id):
    data = request.get_json()
    nueva_duracion = data.get("duracion_turno")

    if not nueva_duracion:
        return jsonify({"error": "Duración no especificada"}), 400

    try:
        nueva_duracion = int(nueva_duracion)
        if nueva_duracion <= 0:
            return jsonify({"error": "La duración debe ser positiva"}), 400
    except:
        return jsonify({"error": "Duración inválida"}), 400

    if current_user.rol == "profesional" and current_user.id != usuario_id:
        return jsonify({"error": "No autorizado"}), 403

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE usuarios
        SET duracion_turno = %s
        WHERE id = %s
    """, (nueva_duracion, usuario_id))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Duración actualizada correctamente"})


# ============================================================
#  NUEVAS RUTAS DE PERFIL
# ============================================================

UPLOAD_FOLDER = "static/fotos_usuarios"


@bp_usuarios.route('/api/usuario/perfil', methods=['GET'])
@login_required
def obtener_perfil():
    return jsonify({
        "id": current_user.id,
        "nombre": current_user.nombre,
        "email": current_user.email,
        "foto": current_user.foto,
        "rol": current_user.rol
    })

from PIL import Image
import io

@bp_usuarios.route('/api/usuario/perfil', methods=['POST'])
@login_required
def actualizar_perfil():
    print("🔵 INICIO actualizar_perfil()")

    conn = get_connection()
    cursor = conn.cursor()

    nuevo_nombre = request.form.get('nombre')
    nuevo_email = request.form.get('email')

    print("📥 Nombre recibido:", nuevo_nombre)
    print("📥 Email recibido:", nuevo_email)

    # Ruta donde se guardan las fotos
    carpeta_fotos = os.path.join(app.root_path, "static/fotos_usuarios")
    os.makedirs(carpeta_fotos, exist_ok=True)

    foto_anterior = current_user.foto
    nueva_foto = foto_anterior  # valor por defecto si no se cambia

    # Si llega archivo
    if "foto" in request.files:
        archivo = request.files["foto"]

        if archivo.filename:
            print("📁 Nueva foto recibida:", archivo.filename)

            # --------------------------
            # 1) BORRAR FOTO ANTERIOR
            # --------------------------
            if foto_anterior:
                path_anterior = os.path.join(carpeta_fotos, foto_anterior)
                if os.path.exists(path_anterior):
                    os.remove(path_anterior)
                    print("🗑 Foto anterior eliminada:", foto_anterior)

            # --------------------------
            # 2) RENOMBRAR FOTO
            # --------------------------
            extension = archivo.filename.rsplit(".", 1)[-1].lower()
            filename = f"user_{current_user.id}.{extension}"
            nueva_foto = filename
            path_nuevo = os.path.join(carpeta_fotos, filename)

            print(" La nueva foto se guardará como:", filename)

            # --------------------------
            # 3) OPTIMIZAR / COMPRIMIR IMAGEN
            # --------------------------
            try:
                image = Image.open(archivo)

                # Convertir a RGB si viene como PNG con transparencia
                if image.mode in ("RGBA", "P", "LA"):
                    image = image.convert("RGB")

                # Guardar optimizada
                image.save(path_nuevo, optimize=True, quality=85)
                print(" Imagen comprimida y guardada correctamente")

            except Exception as e:
                print("⚠ Error al procesar imagen, guardando sin optimizar:", e)
                archivo.save(path_nuevo)

    else:
        print("⚠ No llegó campo foto")

    print(" Foto final:", nueva_foto)

    # GUARDAR EN BASE DE DATOS
    cursor.execute("""
        UPDATE usuarios
        SET nombre = %s,
            email = %s,
            foto = %s
        WHERE id = %s
    """, (nuevo_nombre, nuevo_email, nueva_foto, current_user.id))

    conn.commit()
    conn.close()

    print("💾 UPDATE ejecutado")
    print("🔵 FIN actualizar_perfil()")

    return jsonify({"message": "Perfil actualizado correctamente.", "foto": nueva_foto})

@bp_usuarios.route('/api/usuario/cambiar-password', methods=['POST'])
@login_required
def cambiar_password():
    data = request.json

    actual = data.get("actual")
    nueva = data.get("nueva")
    confirmar = data.get("confirmar")

    # Validación 1: campos completos
    if not actual or not nueva or not confirmar:
        return jsonify({"error": "Todos los campos son obligatorios"}), 400

    # Validación 2: actual correcta
    if not check_password_hash(current_user.password_hash, actual):
        return jsonify({"error": "La contraseña actual es incorrecta"}), 400

    # Validación 3: fuerza de la nueva contraseña
    if not password_valida(nueva):
        return jsonify({
            "error": "La contraseña debe tener mínimo 8 caracteres, incluir mayúscula, minúscula y número."
        }), 400

    # Validación 4: no permitir repetir contraseña
    if actual == nueva:
        return jsonify({"error": "La nueva contraseña no puede ser igual a la actual"}), 400

    # Validación 5: confirmación
    if nueva != confirmar:
        return jsonify({"error": "Las contraseñas no coinciden"}), 400

    # Guardar nueva contraseña usando método scrypt
    nuevo_hash = generate_password_hash(nueva, method="scrypt")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE usuarios
        SET password_hash=%s
        WHERE id=%s
    """, (nuevo_hash, current_user.id))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Contraseña actualizada correctamente"})


@bp_usuarios.route('/api/usuario/foto', methods=['DELETE'])
@login_required
def borrar_foto():
    user_id = current_user.id
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT foto FROM usuarios WHERE id=%s", (user_id,))
    data = cursor.fetchone()

    if not data or not data.get("foto"):
        return jsonify({"message": "No hay foto para borrar", "foto": None}), 200

    foto = data["foto"]
    carpeta = os.path.join(app.root_path, "static/fotos_usuarios")
    ruta_foto = os.path.join(carpeta, foto)

    # Borrar archivo físico
    if os.path.exists(ruta_foto):
        os.remove(ruta_foto)
        print(f"🗑 Foto eliminada: {ruta_foto}")

    # Actualizar BD
    cursor.execute("UPDATE usuarios SET foto=NULL WHERE id=%s", (user_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Foto eliminada", "foto": None}), 200
