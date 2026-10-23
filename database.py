import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# Configure these using your MySQL credentials.
# Set MEDINSIGHT_DB_PASSWORD in CMD before starting the app.

password = os.getenv("MEDINSIGHT_DB_PASSWORD")

if not password:
    raise RuntimeError(
        "Set the MEDINSIGHT_DB_PASSWORD environment variable first."
    )

database_url = URL.create(
    drivername="mysql+pymysql",
    username=os.getenv("MEDINSIGHT_DB_USER", "root"),
    password=password,
    host=os.getenv("MEDINSIGHT_DB_HOST", "localhost"),
    port=int(os.getenv("MEDINSIGHT_DB_PORT", "3306")),
    database="medinsight_db",
)

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
)

def test_connection():
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT DATABASE(), VERSION()")
        )
        return result.fetchone()

if __name__ == "__main__":
    try:
        database, version = test_connection()
        print("MySQL connection successful!")
        print("Database:", database)
        print("MySQL version:", version)
    except Exception as error:
        print("MySQL connection failed.")
        print("Error:", error)