from sqlalchemy.orm import DeclarativeBase


# SQLAlchemy needs a common base class to track models and let Alembic
# discover table metadata.
class Base(DeclarativeBase):
    pass
