import mysql.connector
from config import Config


def get_emergency_contact(user_id):

    db = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT contact_name, contact_phone, relationship
        FROM emergency_contacts
        WHERE user_id=%s
        LIMIT 1
    """, (user_id,))

    contact = cursor.fetchone()

    cursor.close()
    db.close()

    return contact