# database.py

import os
import time
import mysql.connector
from mysql.connector import Error

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
