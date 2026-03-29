import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def set_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AMADEUS_CLIENT_ID", "test_id")
    monkeypatch.setenv("AMADEUS_CLIENT_SECRET", "test_secret")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
