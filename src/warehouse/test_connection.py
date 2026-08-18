from sqlalchemy import text

from sql_server_connection import get_sql_server_engine


def test_connection():

    engine = get_sql_server_engine()

    with engine.connect() as connection:

        result = connection.execute(
            text("SELECT @@VERSION")
        )

        print(result.fetchone()[0])

        print("\nSQL Server connection successful!")


if __name__ == "__main__":
    test_connection()