from flask import Blueprint, request, jsonify
from flask_login import login_required
from werkzeug.security import generate_password_hash
from app.database import get_connection
from app.utils.permisos import requiere_rol

bp_usuarios = Blueprint("usuarios", __name__)

ROLES_VALIDOS = {"director", "profesional", "administrativo"}

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

@bp_usuarios.route('/api/usuarios', methods=['GET'])
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

@bp_usuarios.route('/api/usuarios/<int:usuario_id>', methods=['GET'])
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

@bp_usuarios.route('/api/usuarios/<int:usuario_id>', methods=['PUT'])
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

@bp_usuarios.route('/api/usuarios/<int:usuario_id>', methods=['DELETE'])
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

@bp_usuarios.route('/api/usuarios/<int:usuario_id>/activar', methods=['PUT'])
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