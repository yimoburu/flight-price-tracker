"""Tests for m02 Settings fields and SQLAlchemy DB layer."""

from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Settings tests
# ---------------------------------------------------------------------------


def test_settings_database_url_default():
    from app.config import Settings

    s = Settings()
    assert s.database_url == "sqlite:///./flight_tracker.db"


def test_settings_scheduler_interval_minutes_default():
    from app.config import Settings

    s = Settings()
    assert s.scheduler_interval_minutes == 60


def test_settings_smtp_host_default():
    from app.config import Settings

    s = Settings()
    assert s.smtp_host == "localhost"


def test_settings_smtp_port_default():
    from app.config import Settings

    s = Settings()
    assert s.smtp_port == 25


def test_settings_smtp_username_default():
    from app.config import Settings

    s = Settings()
    assert s.smtp_username is None


def test_settings_smtp_password_default():
    from app.config import Settings

    s = Settings()
    assert s.smtp_password is None


def test_settings_smtp_from_address_default():
    from app.config import Settings

    s = Settings()
    assert s.smtp_from_address == "alerts@flighttracker.local"


def test_settings_smtp_use_tls_default():
    from app.config import Settings

    s = Settings()
    assert s.smtp_use_tls is False


# ---------------------------------------------------------------------------
# DB import tests
# ---------------------------------------------------------------------------


def test_base_importable():
    from app.db import Base  # noqa: F401

    assert Base is not None


def test_engine_importable():
    from app.db import engine  # noqa: F401

    assert engine is not None


def test_session_local_importable():
    from app.db import SessionLocal  # noqa: F401

    assert SessionLocal is not None


def test_get_db_importable():
    from app.db import get_db  # noqa: F401

    assert callable(get_db)


# ---------------------------------------------------------------------------
# get_db behaviour
# ---------------------------------------------------------------------------


def test_get_db_yields_session_and_closes():
    """get_db should yield a Session object and close it on exit."""
    from app.db import get_db

    gen = get_db()
    db = next(gen)
    assert isinstance(db, Session)

    # Track that close() is called when generator is exhausted
    original_close = db.close
    close_called = []
    db.close = lambda: (close_called.append(True), original_close())  # type: ignore[method-assign]

    try:
        next(gen)
    except StopIteration:
        pass

    assert close_called, "Session.close() was not called after generator exhausted"


# ---------------------------------------------------------------------------
# engine uses in-memory SQLite when database_url is overridden
# ---------------------------------------------------------------------------


def test_engine_uses_overridden_database_url(monkeypatch):
    """When get_settings returns an in-memory URL, _make_engine builds the right engine."""
    import importlib

    from app import config, db

    # Clear the lru_cache so our patched Settings is picked up
    config.get_settings.cache_clear()

    # Monkeypatch Settings to return in-memory URL
    original_settings = config.Settings

    class InMemorySettings(original_settings):
        database_url: str = "sqlite:///:memory:"

    monkeypatch.setattr(config, "Settings", InMemorySettings)

    try:
        new_engine = db._make_engine()
        assert "/:memory:" in str(new_engine.url)
    finally:
        # Restore
        config.get_settings.cache_clear()
        monkeypatch.setattr(config, "Settings", original_settings)
        importlib.reload(db)
        config.get_settings.cache_clear()
