import asyncio
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Uuid
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.clock import utcnow
from core.database import Base, get_db
from models.db_models import User
from services.authentication.token import create_access_token

for table in Base.metadata.tables.values():
    for column in table.columns:
        if isinstance(column.type, Uuid):
            column.type = Uuid(as_uuid=True, native_uuid=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSession() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        github_id=123456,
        login="testuser",
        username="Test User",
        avatar_url="https://example.com/avatar.png",
        email="test@example.com",
        access_token="fake-encrypted-token",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(test_user.id)}"}


@pytest_asyncio.fixture
async def client(db: AsyncSession, test_user: User):
    from app import app

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
