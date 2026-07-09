from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.dependencies import verify_token
from api.main import app
from database.db import Base, engine
from database.models import Conversation, User


@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test and drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_list_conversations_unauthorized() -> None:
    client = TestClient(app)
    response = client.get("/conversations")
    assert response.status_code == 401


def test_list_conversations_success() -> None:
    # 1. Registrar dependência temporária de banco e token
    user_a = User(id=1, username="alice", hashed_password="x", created_at=datetime.now(UTC))
    user_b = User(id=2, username="bob", hashed_password="x", created_at=datetime.now(UTC))

    app.dependency_overrides[verify_token] = lambda: User(
        id=1, username="alice", hashed_password="x", created_at=datetime.now(UTC)
    )

    # Criar sessão de teste física para inserir dados
    from database.db import SessionLocal
    db = SessionLocal()
    try:
        db.add(user_a)
        db.add(user_b)
        db.commit()

        from datetime import timedelta
        now_time = datetime.now(UTC)
        # Criar conversas para alice
        conv1 = Conversation(user_id=user_a.id, title="Alice Conv 1", created_at=now_time - timedelta(minutes=10))
        conv2 = Conversation(user_id=user_a.id, title="Alice Conv 2", created_at=now_time)
        # Criar conversa para bob
        conv3 = Conversation(user_id=user_b.id, title="Bob Conv 1", created_at=now_time)

        db.add(conv1)
        db.add(conv2)
        db.add(conv3)
        db.commit()
    finally:
        db.close()

    try:
        client = TestClient(app)
        response = client.get("/conversations")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # As conversas vêm ordenadas de forma decrescente por data
        assert data[0]["title"] == "Alice Conv 2"
        assert data[1]["title"] == "Alice Conv 1"
        assert all(c["user_id"] == 1 for c in data)
    finally:
        app.dependency_overrides.clear()
