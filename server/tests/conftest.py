import uuid
import asyncio
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import Uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from httpx import AsyncClient, ASGITransport

from core.database import Base, get_db
from models.db_models import User
from services.authentication.token import create_access_token

# SQLite ne supporte pas UUID nativement.
# On remplace chaque colonne UUID par une instance Uuid(native_uuid=False)
# pour que SQLAlchemy gère la conversion en Python (CHAR(32)) au lieu de compter sur le driver.
for table in Base.metadata.tables.values():
    for column in table.columns:
        if isinstance(column.type, Uuid):
            column.type = Uuid(as_uuid=True, native_uuid=False)


#  Event loop
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


#  Base de données SQLite en mémoire
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


# Utilisateur de test
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
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


#  JWT valide pour le test user 
@pytest.fixture
def auth_headers(test_user: User) -> dict:
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


# Client HTTP async 
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
