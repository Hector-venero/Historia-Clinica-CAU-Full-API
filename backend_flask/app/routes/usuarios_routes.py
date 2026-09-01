from flask import Blueprint, request, jsonify, current_app as app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from app.database import db_cursor
from app.utils.permisos import requiere_rol
import os
from PIL import Image
import io
from app.utils.validacion import password_valida, validar_email

bp_usuarios = Blueprint("usuarios", __name__)

# ✅ AGREGADO "area"
ROLES_VALIDOS = {"director", "profesional", "administrativo", "area"}

# Roles que firman recetas. `especialidad` solo tiene sentido para ellos, y son
# los que necesitan matricula y lugar de atencion cargados.
ROLES_QUE_PRESCRIBEN = {"profesional", "director"}

# Datos de identidad profesional. Sin ellos el modulo de recetas no puede
# emitir: _validar_payload() en recetas_routes.py exige apellido, dni,
# matricula_numero y lugar_atencion_direccion.
#
# `apellido` va incluido a proposito. Se deduce del nombre completo como
# fallback, pero si el nombre es de una sola palabra no hay de donde sacarlo y
# la receta queda bloqueada sin forma de arreglarla desde la app.
PROFESSIONAL_FIELDS = (
    "apellido",
    "dni",
    "sexo",
    "telefono",
    "matricula_tipo",
    "matricula_numero",
    "matricula_provincia",
    "lugar_atencion_nombre",
    "lugar_atencion_direccion",
    "lugar_atencion_contacto",
    "lugar_atencion_email",
)

# Valores admitidos por los ENUM de la tabla. Un valor fuera de la lista se
# guarda como NULL en vez de reventar el INSERT con error 1265.
SEXOS_VALIDOS = ("M", "F", "X", "O")
TIPOS_MATRICULA = ("MN", "MP", "OP")


def _professional_values(data):
    """Normaliza los campos profesionales que vengan en `data`.

    Sirve tanto para un dict JSON como para un `request.form` (multipart), que
    es lo que manda la pantalla de perfil junto con la foto.
    """
    valores = {campo: (data.get(campo) or None) for campo in PROFESSIONAL_FIELDS}

    if valores["sexo"] not in SEXOS_VALIDOS:
        valores["sexo"] = None
    if valores["matricula_tipo"] not in TIPOS_MATRICULA:
        valores["matricula_tipo"] = None

    return valores


def _normalizar_especialidad(rol, especialidad):
    """La especialidad solo se guarda para quienes prescriben."""
    if (rol or "").lower() in ROLES_QUE_PRESCRIBEN and especialidad:
        return especialidad.upper()
    return None


def _current_user_payload():
    """Datos del usuario logueado, incluidos los profesionales.

    Es lo que consume Mi Perfil para hidratar el formulario: sin los campos
    profesionales, editarlos ahí sería imposible.
    """
    payload = {
        "id": current_user.id,
        "nombre": current_user.nombre,
        "username": current_user.username,
        "email": current_user.email,
        "rol": current_user.rol,
        "foto": getattr(current_user, "foto", None),
        "duracion_turno": getattr(current_user, "duracion_turno", 20),
        "especialidad": getattr(current_user, "especialidad", None),
        "profesion": getattr(current_user, "profesion", None),
    }
    for campo in PROFESSIONAL_FIELDS:
        payload[campo] = getattr(current_user, campo, None)

    # Que modulos incluye el plan del consultorio. Viaja con sesion y no en el
    # endpoint publico de marca: saber que contrato tiene un consultorio no es
    # informacion para cualquiera.
    #
    # El frontend lo usa para no mostrar pantallas que van a dar 403. Es
    # presentacion: quien decide es @requiere_modulo, en el servidor.
    from app import marca

    payload["modulos"] = sorted(marca.modulos())
    payload["marca"] = marca.publica()
    return payload

# ============================================================
#  CREAR USUARIO
# ============================================================
@bp_usuarios.route('/api/usuarios', methods=['POST'])
@login_required
@requiere_rol('director')
def api_crear_usuario():
    data = request.get_json(silent=True) or {}
    nombre = data.get('nombre')
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    rol = data.get('rol')

    if not nombre or not username or not email or not password or not rol:
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400

    if not validar_email(email):
        return jsonify({'error': 'Email inválido'}), 400

    if not password_valida(password):
        return jsonify({
            'error': 'La contraseña debe tener mínimo 8 caracteres, incluir mayúscula, minúscula y número.'
        }), 400

    especialidad = _normalizar_especialidad(rol, data.get('especialidad'))
    profesionales = _professional_values(data)

    with db_cursor() as (conn, cursor):
        cursor.execute(
            "SELECT id FROM usuarios WHERE username = %s OR email = %s",
            (username, email),
        )
        if cursor.fetchone():
            # El return temprano dejaba la conexion abierta.
            return jsonify({'error': 'Ya existe un usuario con ese nombre de usuario o email'}), 400

        columnas = ['nombre', 'username', 'email', 'password_hash', 'rol', 'especialidad']
        valores = [
            nombre, username, email,
            generate_password_hash(password, method="scrypt"),
            rol, especialidad,
        ]
        columnas += list(PROFESSIONAL_FIELDS)
        valores += [profesionales[campo] for campo in PROFESSIONAL_FIELDS]

        marcadores = ", ".join(["%s"] * len(columnas))
        cursor.execute(
            f"INSERT INTO usuarios ({', '.join(columnas)}) VALUES ({marcadores})",
            tuple(valores),
        )
        conn.commit()

    return jsonify({'message': f"Usuario '{username}' creado con éxito ✅"})


# ============================================================
#  LISTADO DE USUARIOS
# ============================================================
@bp_usuarios.route('/api/usuarios', methods=['GET'])
@login_required
@requiere_rol('director')
def api_usuarios_listado():
    q = (request.args.get('q') or "").strip()
    incluir_inactivos = request.args.get('inactivos') == '1'

    filtro_activo = "" if incluir_inactivos else "AND activo=1"

    with db_cursor() as (_conn, cursor):
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

    return jsonify(usuarios)


# ============================================================
#  DETALLE USUARIO
# ============================================================
@bp_usuarios.route('/api/usuarios/<int:usuario_id>', methods=['GET'])
@login_required
@requiere_rol('director')
def api_usuarios_detalle(usuario_id):
    # El SELECT trae tambien los campos profesionales porque EditarUsuario.vue
    # hidrata el formulario con Object.assign sobre esta respuesta: si no
    # vinieran, el formulario los mostraria vacios y al guardar los borraria.
    columnas = ", ".join(("id", "nombre", "username", "email", "rol", "especialidad") + PROFESSIONAL_FIELDS)

    with db_cursor() as (_conn, cursor):
        cursor.execute(f"SELECT {columnas} FROM usuarios WHERE id = %s", (usuario_id,))
        u = cursor.fetchone()

    if not u:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify(u)


# ============================================================
#  EDITAR USUARIO
# ============================================================
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

    profesionales = _professional_values(data)

    # Todos los returns tempranos de abajo dejaban la conexion abierta.
    with db_cursor() as (conn, cur):
        cur.execute("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
        actual = cur.fetchone()
        if not actual:
            return jsonify({"error": "Usuario no encontrado"}), 404

        if username and username != actual["username"]:
            cur.execute("SELECT id FROM usuarios WHERE username=%s AND id<>%s", (username, usuario_id))
            if cur.fetchone():
                return jsonify({"error": "Ya existe otro usuario con ese username"}), 400

        if email and email != actual["email"]:
            cur.execute("SELECT id FROM usuarios WHERE email=%s AND id<>%s", (email, usuario_id))
            if cur.fetchone():
                return jsonify({"error": "Ya existe otro usuario con ese email"}), 400

        if rol and rol not in ROLES_VALIDOS:
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
            sets.append("especialidad=%s")
            params.append(_normalizar_especialidad(rol, especialidad))

        # Solo se tocan los campos profesionales que el cliente mando. Asi se
        # puede limpiar uno enviandolo vacio, sin pisar los que no vinieron.
        for campo, valor in profesionales.items():
            if campo in data:
                sets.append(f"{campo}=%s")
                params.append(valor)

        if password:
            if not password_valida(password):
                return jsonify({"error": "La contraseña debe tener mínimo 8 caracteres..."}), 400
            sets.append("password_hash=%s")
            params.append(generate_password_hash(password, method="scrypt"))

        if not sets:
            return jsonify({"message": "Sin cambios"}), 200

        params.append(usuario_id)
        cur.execute(f"UPDATE usuarios SET {', '.join(sets)} WHERE id=%s", tuple(params))
        conn.commit()

    return jsonify({"message": "Usuario actualizado ✅"})


# ============================================================
#  ELIMINAR / ACTIVAR
# ============================================================
@bp_usuarios.route('/api/usuarios/<int:usuario_id>', methods=['DELETE'])
@login_required
@requiere_rol('director')
def api_usuarios_eliminar(usuario_id):
    with db_cursor() as (conn, cur):
        cur.execute("SELECT id, activo FROM usuarios WHERE id=%s", (usuario_id,))
        usuario = cur.fetchone()
        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 404
        if usuario["activo"] == 0:
            return jsonify({"message": "Usuario ya estaba inactivo"}), 200

        cur.execute("UPDATE usuarios SET activo=0 WHERE id=%s", (usuario_id,))
        conn.commit()

    return jsonify({"message": "Usuario marcado como inactivo ✅"})


@bp_usuarios.route('/api/usuarios/<int:usuario_id>/activar', methods=['PUT'])
@login_required
@requiere_rol('director')
def api_usuarios_activar(usuario_id):
    with db_cursor() as (conn, cur):
        cur.execute("SELECT id, activo FROM usuarios WHERE id=%s", (usuario_id,))
        if not cur.fetchone():
            return jsonify({"error": "Usuario no encontrado"}), 404

        cur.execute("UPDATE usuarios SET activo=1 WHERE id=%s", (usuario_id,))
        conn.commit()

    return jsonify({"message": "Usuario reactivado ✅"})


# ============================================================
#  LISTAR PROFESIONALES (CORREGIDO)
# ============================================================
@bp_usuarios.route('/api/profesionales', methods=['GET'])
@login_required
def api_listar_profesionales():
    especialidad = request.args.get('especialidad')

    # ✅ INCLUIMOS 'area' EN LA CONSULTA
    base_query = """
        SELECT id, nombre, username, especialidad, duracion_turno, rol
        FROM usuarios
        WHERE rol IN ('profesional', 'director', 'area')
        AND activo = 1
    """

    with db_cursor() as (_conn, cursor):
        if especialidad:
            cursor.execute(base_query + " AND UPPER(especialidad) = UPPER(%s) ORDER BY nombre", (especialidad,))
        else:
            cursor.execute(base_query + " ORDER BY nombre")

        profesionales = cursor.fetchall()

    # ✅ FORMATEO UNIFICADO (Sin duplicados)
    for p in profesionales:
        if p['rol'] == 'director':
            p['especialidad'] = 'Dirección'
        elif p['rol'] == 'area':
            p['especialidad'] = 'Área / Módulo'  # Etiqueta para diferenciar
        elif p['especialidad'] is None:
            p['especialidad'] = 'General'

    return jsonify(profesionales)


@bp_usuarios.route("/api/usuarios/<int:usuario_id>/duracion", methods=["PATCH"])
@login_required
def actualizar_duracion_turno(usuario_id):
    data = request.get_json()
    nueva_duracion = data.get("duracion_turno")
    if not nueva_duracion: return jsonify({"error": "Duración no especificada"}), 400
    try:
        nueva_duracion = int(nueva_duracion)
        if nueva_duracion <= 0: return jsonify({"error": "La duración debe ser positiva"}), 400
    except:
        return jsonify({"error": "Duración inválida"}), 400
    if current_user.rol == "profesional" and current_user.id != usuario_id:
        return jsonify({"error": "No autorizado"}), 403
    with db_cursor(dictionary=False) as (conn, cursor):
        cursor.execute("UPDATE usuarios SET duracion_turno = %s WHERE id = %s", (nueva_duracion, usuario_id))
        conn.commit()

    # El directorio publico guarda su propia copia de la duracion, y hasta ahora
    # solo se rehacia al guardar la pantalla de Turnos online. Cambiar la
    # duracion aca dejaba al paciente viendo la vieja en el buscador, sin nada
    # que lo delatara: los dos numeros son plausibles.
    #
    # No propaga errores: la duracion ya quedo guardada, y que el directorio
    # tarde un rato en ponerse al dia no puede hacer fallar la operacion.
    try:
        from app import reservas
        from app.tenancy import cliente_actual

        cliente = cliente_actual()
        if cliente is not None:
            reservas.sincronizar_directorio(cliente)
    except Exception:
        app.logger.exception(
            "No se pudo actualizar el directorio publico tras cambiar la duracion"
        )

    return jsonify({"message": "Duración actualizada correctamente"})


# ============================================================
#  RUTAS DE PERFIL Y FOTOS
# ============================================================

# 1. RUTA NUEVA PARA OBTENER MIS DATOS + FOTO
@bp_usuarios.route('/api/usuarios/me', methods=['GET'])
@login_required
def api_get_me():
    return jsonify(_current_user_payload())

# 2. RUTA PARA OBTENER DATOS SIMPLES (usada por perfil)
@bp_usuarios.route('/api/usuario/perfil', methods=['GET'])
@login_required
def obtener_perfil():
    # Mismo payload que /api/usuarios/me: Mi Perfil necesita los campos
    # profesionales para poder mostrarlos y editarlos.
    return jsonify(_current_user_payload())

# 3. ACTUALIZAR PERFIL
@bp_usuarios.route('/api/usuario/perfil', methods=['POST'])
@login_required
def actualizar_perfil():
    nuevo_nombre = request.form.get('nombre')
    nuevo_email = request.form.get('email')

    # Se resuelve desde el root_path de Flask en vez de "/app/static/...": la
    # ruta absoluta solo existe dentro del contenedor, asi que correr el backend
    # fuera de Docker rompia la subida de fotos.
    carpeta_fotos = os.path.join(app.root_path, 'static', 'fotos_usuarios')
    os.makedirs(carpeta_fotos, exist_ok=True)

    foto_anterior = current_user.foto
    nueva_foto = foto_anterior

    if "foto" in request.files:
        archivo = request.files["foto"]
        if archivo.filename:
            # Borrar anterior
            if foto_anterior:
                path_anterior = os.path.join(carpeta_fotos, foto_anterior)
                if os.path.exists(path_anterior):
                    os.remove(path_anterior)

            # Guardar nueva
            extension = archivo.filename.rsplit(".", 1)[-1].lower()
            filename = f"user_{current_user.id}.{extension}"
            nueva_foto = filename
            path_nuevo = os.path.join(carpeta_fotos, filename)

            try:
                image = Image.open(archivo)
                if image.mode in ("RGBA", "P", "LA"):
                    image = image.convert("RGB")
                image.save(path_nuevo, optimize=True, quality=85)
            except Exception as e:
                app.logger.warning("No se pudo procesar la imagen, se guarda cruda: %s", e)
                # Image.open() ya consumio el stream: sin volver al inicio, el
                # archivo guardado quedaba en 0 bytes y la foto salia rota.
                archivo.seek(0)
                archivo.save(path_nuevo)

    # request.form y no JSON: la pantalla manda multipart por la foto.
    # _professional_values() funciona igual sobre un form.
    profesionales = _professional_values(request.form)

    sets = ["nombre=%s", "email=%s", "foto=%s"]
    params = [nuevo_nombre, nuevo_email, nueva_foto]

    # Solo lo que el formulario envio, para no pisar lo que no vino.
    for campo, valor in profesionales.items():
        if campo in request.form:
            sets.append(f"{campo}=%s")
            params.append(valor)

    params.append(current_user.id)

    with db_cursor(dictionary=False) as (conn, cursor):
        cursor.execute(f"UPDATE usuarios SET {', '.join(sets)} WHERE id=%s", tuple(params))
        conn.commit()

    return jsonify({"message": "Perfil actualizado correctamente.", "foto": nueva_foto})


@bp_usuarios.route('/api/usuario/cambiar-password', methods=['POST'])
@login_required
def cambiar_password():
    data = request.json
    actual = data.get("actual")
    nueva = data.get("nueva")
    confirmar = data.get("confirmar")

    if not actual or not nueva or not confirmar:
        return jsonify({"error": "Todos los campos son obligatorios"}), 400
    if not check_password_hash(current_user.password_hash, actual):
        return jsonify({"error": "Contraseña incorrecta"}), 400
    if not password_valida(nueva):
        return jsonify({"error": "La contraseña no es segura"}), 400
    if actual == nueva:
        return jsonify({"error": "La nueva contraseña debe ser diferente"}), 400
    if nueva != confirmar:
        return jsonify({"error": "Las contraseñas no coinciden"}), 400

    nuevo_hash = generate_password_hash(nueva, method="scrypt")
    with db_cursor(dictionary=False) as (conn, cursor):
        cursor.execute("UPDATE usuarios SET password_hash=%s WHERE id=%s", (nuevo_hash, current_user.id))
        conn.commit()

    return jsonify({"message": "Contraseña actualizada correctamente"})


@bp_usuarios.route('/api/usuario/foto', methods=['DELETE'])
@login_required
def borrar_foto():
    user_id = current_user.id

    with db_cursor() as (conn, cursor):
        cursor.execute("SELECT foto FROM usuarios WHERE id=%s", (user_id,))
        data = cursor.fetchone()

        if not data or not data.get("foto"):
            # El return temprano dejaba la conexion abierta.
            return jsonify({"message": "No hay foto", "foto": None}), 200

        # Misma ruta dinamica que al subir: la absoluta solo existe en Docker.
        ruta_foto = os.path.join(app.root_path, 'static', 'fotos_usuarios', data["foto"])
        if os.path.exists(ruta_foto):
            os.remove(ruta_foto)

        cursor.execute("UPDATE usuarios SET foto=NULL WHERE id=%s", (user_id,))
        conn.commit()

    return jsonify({"message": "Foto eliminada", "foto": None}), 200