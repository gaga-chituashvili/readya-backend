import psycopg

DB_NAME = "readya_db"
DB_USER = "readya_db_user"
DB_PASSWORD = "U29beW6zkDEyi0H6NfT63KGQFsMLPSUX"
DB_HOST = "dpg-d610nt4hg0os73fb0100-a.oregon-postgres.render.com"
DB_PORT = 5432

try:
    conn = psycopg.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
    cur = conn.cursor()
    cur.execute("SELECT NOW();")
    print("DB works! Current time:", cur.fetchone())
    cur.close()
    conn.close()
except Exception as e:
    print("Error connecting to DB:", e)
