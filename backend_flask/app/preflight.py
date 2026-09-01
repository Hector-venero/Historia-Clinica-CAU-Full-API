"""Lo que tiene que ser cierto antes de servir en produccion.

CLAUDE.md tiene una decena de avisos con la forma "si te olvidas de esto en
produccion, pasa algo malo en silencio". Un aviso en un archivo de texto no
detiene un despliegue; esto si.

**Dos niveles, y la diferencia importa.**

  * `FATAL` impide arrancar. Solo entra aca lo que, dejado pasar, significa que
    el sistema esta sirviendo de forma insegura o incorrecta **y nadie se va a
    enterar**. Servir con una clave de sesion publica no es "una advertencia":
    es que cualquiera puede fabricarse una sesion de director.
  * `AVISO` se imprime y sigue. Es lo que conviene revisar pero puede ser una
    decision deliberada.

Fallar al arrancar es la misma politica que ya aplica el resto del sistema: las
migraciones que fallan tumban el contenedor, y sin PLATAFORMA_SECRET_KEY no se
levanta. Es preferible un despliegue que no sube a uno que sube mal.

⚠️ **Solo se exige en produccion** (`FLASK_ENV=production`). En desarrollo todo
esto es normal y bloquearlo haria imposible trabajar.
"""

import os

# El valor que trae config.py cuando nadie definio SECRET_KEY. Vive aca escrito
# a mano y no importado: la gracia es detectar exactamente ese texto, y si
# alguien cambia el default en config.py lo que hay que revisar es esta lista.
CLAVE_DE_EJEMPLO = "CambiaEstoPorUnValorSeguro"

# Contrasena del admin que siembra db/init.sql.
PASSWORD_SEMBRADA = "admin123"

FATAL = "fatal"
AVISO = "aviso"


class ConfiguracionInsegura(RuntimeError):
    """Hay algo que impide servir en produccion."""


def _es_verdadero(valor):
    return str(valor or "").strip().lower() in ("1", "true", "si", "yes")


def revisar(entorno=None):
    """Devuelve la lista de problemas: [(nivel, clave, que pasa)].

    Recibe el entorno como diccionario para poder probarlo sin tocar os.environ
    del proceso. Por defecto, el real.
    """
    env = os.environ if entorno is None else entorno
    problemas = []

    def falta(clave):
        return not (env.get(clave) or "").strip()

    produccion = (env.get("FLASK_ENV") or "development").strip().lower() == "production"
    if not produccion:
        # En desarrollo nada de esto es un problema. Se devuelve vacio en vez de
        # devolver avisos: un chequeo que grita siempre deja de leerse.
        return []

    # --- lo que impide arrancar -------------------------------------------

    clave = (env.get("SECRET_KEY") or "").strip()
    if not clave or clave == CLAVE_DE_EJEMPLO:
        problemas.append((
            FATAL, "SECRET_KEY",
            "Esta sin definir o quedo el valor de ejemplo, que esta publicado en "
            "el repositorio. Con esa clave cualquiera puede firmarse una cookie "
            "de sesion valida y entrar como director de cualquier consultorio. "
            "Generar una con: python -c \"import secrets; print(secrets.token_hex(32))\"",
        ))
    elif len(clave) < 32:
        problemas.append((
            AVISO, "SECRET_KEY",
            f"Tiene {len(clave)} caracteres. Conviene al menos 32.",
        ))

    if _es_verdadero(env.get("FLASK_DEBUG")):
        problemas.append((
            FATAL, "FLASK_DEBUG",
            "Esta encendido. El depurador de Werkzeug expone una consola de "
            "Python en el navegador ante cualquier excepcion: es ejecucion "
            "remota de codigo servida por la propia aplicacion.",
        ))

    multi = _es_verdadero(env.get("MULTI_TENANT"))
    if multi and falta("DOMINIO_BASE"):
        problemas.append((
            FATAL, "DOMINIO_BASE",
            "Con MULTI_TENANT=true es obligatoria. Sin ella, CUALQUIER host que "
            "apunte al servidor se interpreta como el slug de un consultorio.",
        ))

    if multi and falta("PLATAFORMA_SECRET_KEY"):
        problemas.append((
            FATAL, "PLATAFORMA_SECRET_KEY",
            "Con ella se cifran las credenciales de las bases de cada "
            "consultorio. Sin ella no se puede leer ninguna.",
        ))

    if env.get("SESSION_COOKIE_DOMAIN"):
        problemas.append((
            FATAL, "SESSION_COOKIE_DOMAIN",
            "No debe definirse nunca. Con un dominio comodin la cookie de "
            "sesion de un consultorio viaja a todos los demas.",
        ))

    url = (env.get("FRONTEND_URL") or "").strip()
    if not url.startswith("https://"):
        problemas.append((
            FATAL, "FRONTEND_URL",
            f"Tiene que ser https en produccion (hoy: {url or 'sin definir'}). "
            "Sobre http la cookie de sesion viaja en claro.",
        ))

    # Sin definir esta bien: config.py la deriva del entorno y en produccion da
    # True. Lo que se busca es que alguien la haya apagado a mano.
    cookie_segura = env.get("SESSION_COOKIE_SECURE")
    if cookie_segura is not None and not _es_verdadero(cookie_segura):
        problemas.append((
            FATAL, "SESSION_COOKIE_SECURE",
            "Esta apagada explicitamente. La cookie de sesion se manda tambien "
            "sobre http, donde se puede leer en el camino.",
        ))

    # --- lo que conviene revisar ------------------------------------------

    if _es_verdadero(env.get("ENABLE_BLOCKCHAIN_TEST_ENDPOINTS")):
        problemas.append((
            AVISO, "ENABLE_BLOCKCHAIN_TEST_ENDPOINTS",
            "Los endpoints de prueba de blockchain quedaron encendidos.",
        ))

    if falta("MAIL_DEFAULT_SENDER"):
        problemas.append((
            AVISO, "MAIL_DEFAULT_SENDER",
            "Sin remitente, los comunicados importantes no se mandan y las "
            "confirmaciones de turno pueden rebotar.",
        ))

    if falta("QBI_BASE_URL"):
        problemas.append((
            AVISO, "QBI_BASE_URL",
            "El modulo de recetas va a responder 503. Es lo correcto si todavia "
            "no se contrato el proveedor.",
        ))

    if (env.get("DB_PASSWORD") or "") in ("", "hc_password"):
        problemas.append((
            AVISO, "DB_PASSWORD",
            "Quedo la contrasena de ejemplo de la base.",
        ))

    if falta("CORS_ORIGINS") and not url:
        problemas.append((
            AVISO, "CORS_ORIGINS",
            "Sin CORS_ORIGINS ni FRONTEND_URL no hay allowlist que derivar.",
        ))

    return problemas


def exigir(entorno=None):
    """Levanta si hay algo FATAL. Es lo que corre al arrancar.

    Los avisos no se levantan pero se devuelven, para que quien llama los
    imprima: un aviso que nadie ve es lo mismo que no tenerlo.
    """
    problemas = revisar(entorno)
    fatales = [p for p in problemas if p[0] == FATAL]
    if fatales:
        detalle = "\n".join(f"  - {clave}: {texto}" for _n, clave, texto in fatales)
        raise ConfiguracionInsegura(
            "La configuracion de produccion no es segura y la aplicacion no va a "
            f"arrancar:\n\n{detalle}\n\n"
            "Se revisa con: FLASK_APP=app.main flask verificar-produccion"
        )
    return [p for p in problemas if p[0] == AVISO]
