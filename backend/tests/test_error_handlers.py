from unittest.mock import MagicMock

import pytest
from amadeus import ResponseError
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.error_handlers import amadeus_exception_handler
from app.services.amadeus_client import get_amadeus_client


def make_exc(status_code: int) -> ResponseError:
    mock_response = MagicMock()
    mock_response.status_code = status_code
    return ResponseError(mock_response)


def make_test_app() -> FastAPI:
    """Create a minimal test app that raises ResponseError on /trigger."""
    _app = FastAPI()
    _app.add_exception_handler(ResponseError, amadeus_exception_handler)

    @_app.get("/trigger/{code}")
    async def trigger(code: int) -> dict:
        raise make_exc(code)

    return _app


client = TestClient(make_test_app())


def test_rate_limit_429() -> None:
    response = client.get("/trigger/429")
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["detail"]


def test_auth_error_401() -> None:
    response = client.get("/trigger/401")
    assert response.status_code == 503
    assert "credentials" in response.json()["detail"]


def test_server_error_500() -> None:
    response = client.get("/trigger/500")
    assert response.status_code == 502
    assert "temporarily unavailable" in response.json()["detail"]


def test_bad_params_400() -> None:
    response = client.get("/trigger/400")
    assert response.status_code == 422


def test_client_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    get_amadeus_client.cache_clear()
    monkeypatch.setenv("AMADEUS_CLIENT_ID", "test_id")
    monkeypatch.setenv("AMADEUS_CLIENT_SECRET", "test_secret")
    monkeypatch.setenv("AMADEUS_HOSTNAME", "test")
    # Clear pydantic-settings cache so it re-reads env
    from app.config import get_settings
    get_settings.cache_clear()
    a = get_amadeus_client()
    b = get_amadeus_client()
    assert a is b
    get_amadeus_client.cache_clear()
    get_settings.cache_clear()


def test_client_hostname(monkeypatch: pytest.MonkeyPatch) -> None:
    get_amadeus_client.cache_clear()
    monkeypatch.setenv("AMADEUS_CLIENT_ID", "test_id")
    monkeypatch.setenv("AMADEUS_CLIENT_SECRET", "test_secret")
    monkeypatch.setenv("AMADEUS_HOSTNAME", "test")
    from app.config import get_settings
    get_settings.cache_clear()
    amadeus = get_amadeus_client()
    assert amadeus.hostname == "test"
    get_amadeus_client.cache_clear()
    get_settings.cache_clear()
