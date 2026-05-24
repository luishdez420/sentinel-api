from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect


def test_database_migrations_reach_head(db_engine):
    inspector = inspect(db_engine)
    tables = set(inspector.get_table_names())

    assert {"alembic_version", "users", "notes"}.issubset(tables)

    with db_engine.connect() as connection:
        current_revision = connection.exec_driver_sql(
            "SELECT version_num FROM alembic_version"
        ).scalar_one()

    script = ScriptDirectory.from_config(Config("alembic.ini"))
    heads = set(script.get_heads())

    assert current_revision in heads
