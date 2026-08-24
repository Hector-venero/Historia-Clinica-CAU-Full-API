# database.py

import os
import time
import mysql.connector
from mysql.connector import Error
from contextlib import contextmanager

DB_CONFIG = {
    'host': os.getenv("DB_HOST", "db"),
    'user': os.getenv("DB_USER", "root"),
    'password': os.getenv("DB_PASSWORD", "root"),
    'database': os.getenv("DB_NAME", "hc_bfa")
}

def get_connection(retries=5, delay=3):
    for attempt in range(retries):
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
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
