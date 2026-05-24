import os
from collections.abc import AsyncIterator, Iterator

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg2://rlapi:rlapi_password@localhost:55432/rlapi_test",
)
os.environ.setdefault("JWT_SECRET", "test-secret-value-that-is-at-least-32-chars")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "56379")
os.environ.setdefault("RATE_LIMIT", "20")
os.environ.setdefault("RATE_LIMIT_WINDOW_SECONDS", "60")

from app.core.rate_limit import redis_client  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def database_url() -> str:
    return os.environ["DATABASE_URL"]


@pytest.fixture(scope="session")
def db_engine(database_url: str) -> Iterator[Engine]:
    engine = create_engine(database_url, pool_pre_ping=True)
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    yield engine

    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def migrated_database(database_url: str, db_engine: Engine) -> Iterator[None]:
    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", database_url)

    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")

    yield

    command.downgrade(alembic_config, "base")


@pytest.fixture(autouse=True)
def clean_state(db_engine: Engine) -> Iterator[None]:
    with db_engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE notes, users RESTART IDENTITY CASCADE"))
    redis_client.flushdb()

    yield

    redis_client.flushdb()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client


@pytest.fixture
def register_and_login(client: httpx.AsyncClient):
    async def _register_and_login(
        email: str = "user@example.com",
        password: str = "correct-password",
    ) -> str:
        register_response = await client.post(
            "/auth/register",
            json={"email": email, "password": password},
        )
        assert register_response.status_code == 201

        login_response = await client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        assert login_response.status_code == 200

        return login_response.json()["access_token"]

    return _register_and_login
