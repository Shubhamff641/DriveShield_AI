import mysql.connector
from mysql.connector import Error

from config import Config


def get_db_connection():
    try:
        return mysql.connector.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB,
            charset="utf8mb4",
            use_unicode=True,
            connection_timeout=10
        )
    except Error as error:
        raise RuntimeError(
            f"Unable to connect to the MySQL database: {error}"
        ) from error


def close_database_resources(cursor=None, connection=None):
    if cursor is not None:
        try:
            cursor.close()
        except Error:
            pass

    if connection is not None and connection.is_connected():
        try:
            connection.close()
        except Error:
            pass