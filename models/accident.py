from database.db import get_db_connection


class Accident:

    @staticmethod
    def create_accident(user_id, latitude, longitude,
                        severity, hospital_id,
                        email_sent, status,
                        description):

        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
        INSERT INTO accidents
        (
            user_id,
            latitude,
            longitude,
            severity,
            hospital_id,
            email_sent,
            status,
            description
        )
        VALUES
        (%s,%s,%s,%s,%s,%s,%s,%s)
        """

        values = (
            user_id,
            latitude,
            longitude,
            severity,
            hospital_id,
            email_sent,
            status,
            description
        )

        cursor.execute(query, values)
        conn.commit()

        cursor.close()
        conn.close()


    @staticmethod
    def get_accidents(user_id):

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM accidents
            WHERE user_id=%s
            ORDER BY accident_time DESC
            """,
            (user_id,)
        )

        accidents = cursor.fetchall()

        cursor.close()
        conn.close()

        return accidents


    @staticmethod
    def get_accident(accident_id):

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM accidents
            WHERE accident_id=%s
            """,
            (accident_id,)
        )

        accident = cursor.fetchone()

        cursor.close()
        conn.close()

        return accident


    @staticmethod
    def delete_accident(accident_id):

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM accidents
            WHERE accident_id=%s
            """,
            (accident_id,)
        )

        conn.commit()

        cursor.close()
        conn.close()