import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()


def get_sql_server_engine():

    server = os.getenv("SQL_SERVER_HOST", "localhost")
    port = os.getenv("SQL_SERVER_PORT", "1434")
    database = os.getenv("SQL_SERVER_DATABASE", "AirbnbDWH")
    username = os.getenv("SQL_SERVER_USERNAME", "sa")
    password = os.getenv("MSSQL_SA_PASSWORD")

    driver = os.getenv(
        "SQL_SERVER_DRIVER",
        "ODBC Driver 18 for SQL Server"
    )

    if not password:
        raise ValueError(
            "MSSQL_SA_PASSWORD is not set in environment variables."
        )

    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server},{port};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        f"TrustServerCertificate=yes;"
    )

    connection_url = (
        "mssql+pyodbc:///?odbc_connect="
        + quote_plus(connection_string)
    )

    return create_engine(
        connection_url,
        fast_executemany=True
    )