from os import getenv

from psycopg2 import connect, sql


def create_django_schema():
    schema = getenv("POSTGRES_SCHEMA")
    if schema is None:
        raise ValueError("No schema defined")
    with connect(
        host=getenv("POSTGRES_HOST"),
        dbname=getenv("POSTGRES_DB"),
        user=getenv("POSTGRES_USER"),
        password=getenv("POSTGRES_PASSWORD"),
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE SCHEMA {schema}")
            print(f"Created the Schema '{schema}'")
        with connection.cursor() as cursor2:
            cursor2.execute(
                f'GRANT ALL ON SCHEMA {schema} TO {getenv("POSTGRES_USER")}'
            )
            print(f"Granted rights on schema {schema} to {getenv('POSTGRES_USER')}")


if __name__ == "__main__":
    create_django_schema()
