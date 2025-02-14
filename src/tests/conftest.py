import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert

from config import get_settings, get_s3_storage_client
from database import (
    reset_database,
    get_db_contextmanager,
)
from database.models.accounts import (
    UserGroupEnum,
    UserGroupModel
)
from main import app
from security.token_manager import JWTAuthManager
from storages import S3StorageClient



def pytest_configure(config):
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests"
    )
    config.addinivalue_line(
        "markers", "order: Specify the order of test execution"
    )
    config.addinivalue_line(
        "markers", "unit: Unit tests"
    )


@pytest.fixture(scope="function", autouse=True)
def reset_db(request):
    if request.node.get_closest_marker("e2e"):
        return None
    reset_database()


@pytest.fixture(scope="session")
def reset_db_once_for_e2e(request):
    reset_database()


@pytest.fixture(scope="session")
def settings():
    return get_settings()



@pytest.fixture(scope="session")
def s3_client(settings):
    return S3StorageClient(
        endpoint_url=settings.S3_STORAGE_ENDPOINT,
        access_key=settings.S3_STORAGE_ACCESS_KEY,
        secret_key=settings.S3_STORAGE_SECRET_KEY,
        bucket_name=settings.S3_BUCKET_NAME
    )


@pytest.fixture(scope="function")
def client():
    with TestClient(app) as test_client:
        yield test_client



@pytest.fixture(scope="session")
def e2e_client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def db_session():
    with get_db_contextmanager() as session:
        yield session


@pytest.fixture(scope="function")
def jwt_manager(settings):
    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM
    )


@pytest.fixture(scope="function")
def seed_user_groups(db_session):
    groups = [{"name": group.value} for group in UserGroupEnum]
    db_session.execute(insert(UserGroupModel).values(groups))
    db_session.commit()
    yield db_session


