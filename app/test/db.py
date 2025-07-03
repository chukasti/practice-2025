import psycopg2

conn = psycopg2.connect("dbname=postgres_db user=postgres_user password=postgres_password port=5430")
cur = conn.cursor()

cur.execute("")

