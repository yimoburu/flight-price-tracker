"""Tests for TrackedSearch and PriceSnapshot ORM models."""

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models.tracked_search import PriceSnapshot, TrackedSearch

TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=test_engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def _make_tracked_search(**overrides):
    """Helper to create a TrackedSearch with valid required fields."""
    defaults = dict(
        client_id="client-uuid-1234",
        origin="JFK",
        destination="LAX",
        trip_type="one_way",
        departure_date_from=date(2026, 6, 1),
        departure_date_to=date(2026, 6, 30),
        threshold_price=Decimal("299.99"),
        alert_email="test@example.com",
    )
    defaults.update(overrides)
    return TrackedSearch(**defaults)


# ---------------------------------------------------------------------------
# TrackedSearch basic creation
# ---------------------------------------------------------------------------


def test_tracked_search_can_be_created_and_saved():
    """TrackedSearch can be created with required fields and saved to DB."""
    db = TestingSession()
    try:
        ts = _make_tracked_search()
        db.add(ts)
        db.commit()
        db.refresh(ts)
        found = db.query(TrackedSearch).filter_by(origin="JFK").first()
        assert found is not None
        assert found.origin == "JFK"
        assert found.destination == "LAX"
        assert found.trip_type == "one_way"
        assert found.threshold_price == Decimal("299.99")
        assert found.alert_email == "test@example.com"
    finally:
        db.close()


def test_tracked_search_id_auto_generated_uuid():
    """TrackedSearch.id is auto-generated UUID string if not provided."""
    db = TestingSession()
    try:
        ts = _make_tracked_search()
        db.add(ts)
        db.commit()
        db.refresh(ts)
        assert ts.id is not None
        assert isinstance(ts.id, str)
        assert len(ts.id) == 36  # UUID format: 8-4-4-4-12
        assert ts.id.count("-") == 4
    finally:
        db.close()


def test_tracked_search_is_active_defaults_true():
    """TrackedSearch.is_active defaults to True."""
    db = TestingSession()
    try:
        ts = _make_tracked_search()
        db.add(ts)
        db.commit()
        db.refresh(ts)
        assert ts.is_active is True
    finally:
        db.close()


def test_tracked_search_adults_defaults_to_1():
    """TrackedSearch.adults defaults to 1."""
    db = TestingSession()
    try:
        ts = _make_tracked_search()
        db.add(ts)
        db.commit()
        db.refresh(ts)
        assert ts.adults == 1
    finally:
        db.close()


def test_tracked_search_created_at_set_automatically():
    """TrackedSearch.created_at is set automatically."""
    db = TestingSession()
    try:
        ts = _make_tracked_search()
        db.add(ts)
        db.commit()
        db.refresh(ts)
        assert ts.created_at is not None
        assert isinstance(ts.created_at, datetime)
    finally:
        db.close()


def test_tracked_search_return_dates_can_be_none():
    """TrackedSearch.return_date_from and return_date_to can be None."""
    db = TestingSession()
    try:
        ts = _make_tracked_search(return_date_from=None, return_date_to=None)
        db.add(ts)
        db.commit()
        db.refresh(ts)
        assert ts.return_date_from is None
        assert ts.return_date_to is None
    finally:
        db.close()


def test_tracked_search_max_stops_can_be_none():
    """TrackedSearch.max_stops can be None."""
    db = TestingSession()
    try:
        ts = _make_tracked_search(max_stops=None)
        db.add(ts)
        db.commit()
        db.refresh(ts)
        assert ts.max_stops is None
    finally:
        db.close()


# ---------------------------------------------------------------------------
# PriceSnapshot
# ---------------------------------------------------------------------------


def test_price_snapshot_can_be_created_and_linked():
    """PriceSnapshot can be created and linked to a TrackedSearch."""
    db = TestingSession()
    try:
        ts = _make_tracked_search()
        db.add(ts)
        db.flush()

        snap = PriceSnapshot(
            tracked_search_id=ts.id,
            checked_at=datetime(2026, 6, 5, 12, 0, 0),
            best_price=Decimal("199.50"),
            currency="USD",
        )
        db.add(snap)
        db.commit()
        db.refresh(snap)

        found = db.query(PriceSnapshot).first()
        assert found is not None
        assert found.best_price == Decimal("199.50")
        assert found.currency == "USD"
        assert found.tracked_search_id == ts.id
    finally:
        db.close()


def test_price_snapshot_id_auto_incremented_integer():
    """PriceSnapshot.id is auto-generated integer."""
    db = TestingSession()
    try:
        ts = _make_tracked_search()
        db.add(ts)
        db.flush()

        snap1 = PriceSnapshot(
            tracked_search_id=ts.id,
            checked_at=datetime(2026, 6, 5, 12, 0, 0),
            best_price=Decimal("100.00"),
            currency="USD",
        )
        snap2 = PriceSnapshot(
            tracked_search_id=ts.id,
            checked_at=datetime(2026, 6, 6, 12, 0, 0),
            best_price=Decimal("110.00"),
            currency="USD",
        )
        db.add_all([snap1, snap2])
        db.commit()
        db.refresh(snap1)
        db.refresh(snap2)

        assert snap1.id is not None
        assert isinstance(snap1.id, int)
        assert snap2.id is not None
        assert isinstance(snap2.id, int)
        assert snap1.id != snap2.id
    finally:
        db.close()


def test_deleting_tracked_search_cascades_to_snapshots():
    """Deleting TrackedSearch cascades to delete its PriceSnapshots."""
    db = TestingSession()
    try:
        ts = _make_tracked_search()
        db.add(ts)
        db.flush()

        snap = PriceSnapshot(
            tracked_search_id=ts.id,
            checked_at=datetime(2026, 6, 5, 12, 0, 0),
            best_price=Decimal("150.00"),
            currency="USD",
        )
        db.add(snap)
        db.commit()

        snap_id = snap.id
        assert db.query(PriceSnapshot).filter_by(id=snap_id).first() is not None

        db.delete(ts)
        db.commit()

        assert db.query(PriceSnapshot).filter_by(id=snap_id).first() is None
    finally:
        db.close()


def test_tracked_search_snapshots_relationship():
    """TrackedSearch.snapshots relationship returns list of PriceSnapshot."""
    db = TestingSession()
    try:
        ts = _make_tracked_search()
        db.add(ts)
        db.flush()

        snap1 = PriceSnapshot(
            tracked_search_id=ts.id,
            checked_at=datetime(2026, 6, 5, 12, 0, 0),
            best_price=Decimal("100.00"),
            currency="USD",
        )
        snap2 = PriceSnapshot(
            tracked_search_id=ts.id,
            checked_at=datetime(2026, 6, 6, 12, 0, 0),
            best_price=Decimal("90.00"),
            currency="USD",
        )
        db.add_all([snap1, snap2])
        db.commit()
        db.refresh(ts)

        assert len(ts.snapshots) == 2
        assert all(isinstance(s, PriceSnapshot) for s in ts.snapshots)
    finally:
        db.close()


def test_price_snapshot_back_reference_to_tracked_search():
    """PriceSnapshot.tracked_search back-reference returns the parent TrackedSearch."""
    db = TestingSession()
    try:
        ts = _make_tracked_search()
        db.add(ts)
        db.flush()

        snap = PriceSnapshot(
            tracked_search_id=ts.id,
            checked_at=datetime(2026, 6, 5, 12, 0, 0),
            best_price=Decimal("200.00"),
            currency="USD",
        )
        db.add(snap)
        db.commit()
        db.refresh(snap)

        assert snap.tracked_search is not None
        assert isinstance(snap.tracked_search, TrackedSearch)
        assert snap.tracked_search.id == ts.id
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Query tests
# ---------------------------------------------------------------------------


def test_query_by_client_id():
    """TrackedSearch with client_id can be queried by client_id."""
    db = TestingSession()
    try:
        ts1 = _make_tracked_search(client_id="client-aaa")
        ts2 = _make_tracked_search(client_id="client-bbb", origin="ORD")
        db.add_all([ts1, ts2])
        db.commit()

        results = db.query(TrackedSearch).filter_by(client_id="client-aaa").all()
        assert len(results) == 1
        assert results[0].client_id == "client-aaa"
    finally:
        db.close()


def test_query_multiple_by_is_active():
    """Multiple TrackedSearches can be queried by is_active=True."""
    db = TestingSession()
    try:
        ts1 = _make_tracked_search(client_id="c1")
        ts2 = _make_tracked_search(client_id="c2", origin="ORD")
        ts3 = _make_tracked_search(client_id="c3", origin="SFO", is_active=False)
        db.add_all([ts1, ts2, ts3])
        db.commit()

        active = db.query(TrackedSearch).filter_by(is_active=True).all()
        assert len(active) == 2
        inactive = db.query(TrackedSearch).filter_by(is_active=False).all()
        assert len(inactive) == 1
        assert inactive[0].client_id == "c3"
    finally:
        db.close()
