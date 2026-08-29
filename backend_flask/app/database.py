# database.py

import os
import time
import mysql.connector
from mysql.connector import Error
from contextlib import contextmanager

DB_CONFIG = {
    'host': os.getenv("DB_HOST", "db"),
    'port': int(os.getenv("DB_PORT", "3306")),
    'user': os.getenv("DB_USER", "root"),
    'password': os.getenv("DB_PASSWORD", "root"),
    'database': os.getenv("DB_NAME", "hc_bfa")
}


def config_actual():
    """A que base hay que conectarse para atender lo que se esta haciendo.

    Este es el unico punto del sistema donde se decide eso, y por eso la
    multi-tenencia se resuelve aca en vez de reescribir las 184 consultas: cada
    una pide una conexion y no sabe —ni tiene por que saber— de quien es la base
    que recibe.

    Con un consultorio resuelto en el pedido, se usa el suyo. Sin el —una
    instalacion de un solo centro, una migracion, un comando de consola, el hilo
    que manda un correo— se cae a las variables de entorno, que es como funciono
    siempre.
    """
    try:
        from flask import g, has_request_context

        if has_request_context():
            cliente = getattr(g, "cliente", None)
            if cliente is not None:
                return cliente.config_db()
    except Exception:
        # Fuera de Flask (migrate.py corre como script suelto) o con el plano de
        # control caido, se sigue con la configuracion del entorno en lugar de
        # dejar la aplicacion sin base.
        pass

    return DB_CONFIG


def get_connection(retries=5, delay=3):
    config = config_actual()
    for attempt in range(retries):
        try:
            conn = mysql.connector.connect(**config)
            if conn.is_connected():
                return conn
        except Error as e:
            print(f"⚠️ Intento {attempt+1}/{retries} - No se pudo conectar a MySQL ({e})")
            time.sleep(delay)
    raise Exception("❌ No se pudo conectar a MySQL después de varios intentos.")


@contextmanager
def db_cursor(dictionary=True, commit=False):
    """Abre conexion y cursor, y los cierra pase lo que pase.

    El patron `conn = get_connection()` ... `conn.close()` al final del handler
    filtra la conexion ante cualquier excepcion intermedia: la conexion queda
    ocupada en MySQL hasta que vence wait_timeout, y con suficientes errores se
    agota el pool y la app deja de responder.

    Uso:
        with db_cursor() as (conn, cursor):
            cursor.execute(...)

    Con commit=True hace commit al salir sin excepcion, y rollback si hubo una.

    OJO con los `return` tempranos: salir del bloque con un return **tambien
    hace commit**, porque para el context manager es una salida sin excepcion.
    Comprobado. En la practica eso significa que un handler que escriba algo y
    despues devuelva un error con `return` va a confirmar esa escritura a medias.
    Si hace falta abortar, hay que lanzar una excepcion, no retornar.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield conn, cursor
        if commit:
            conn.commit()
    except Exception:
        if commit:
            try:
                conn.rollback()
            except Error:
                pass
        raise
    finally:
        try:
            cursor.close()
        except Error:
            pass
        conn.close()
