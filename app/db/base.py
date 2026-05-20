from sqlalchemy.orm import DeclarativeBase

#SQLAlchemy needs a common “base class” to track all your models so it can create tables and so Alembic can discover them.
class Base(DeclarativeBase):
    pass
