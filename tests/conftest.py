import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tfl_task_scheduler.db import Base, get_session
from tfl_task_scheduler import db as db_module
from tfl_task_scheduler.main import app
from tfl_task_scheduler import scheduler


@pytest.fixture(scope="session")
def db_engine():
    # One shared in-memory SQLite across all connections/threads
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    # Make the app/worker use this same engine
    db_module.SessionLocal = sessionmaker(
        bind=engine, autocommit=False, autoflush=False
    )
    return engine


@pytest.fixture(scope="function")
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        try:
            scheduler.clear_all()
        except Exception:
            pass


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
