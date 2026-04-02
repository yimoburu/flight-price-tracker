from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models.tracked_search import PriceSnapshot, TrackedSearch
from app.services.scheduler import (
    check_all_tracked_searches,
    check_single_tracked_search,
    create_scheduler,
)

TEST_DB_URL = "sqlite:///file:test_scheduler?mode=memory&cache=shared&uri=true"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=test_engine)

SEARCH_FLIGHTS = "app.services.scheduler.search_flights"
GET_AMADEUS_CLIENT = "app.services.scheduler.get_amadeus_client"
SEND_PRICE_ALERT = "app.services.scheduler.send_price_alert"


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    Base.metadata.create_all(bind=test_engine)
    # Override SessionLocal to use test DB
    monkeypatch.setattr("app.services.scheduler.SessionLocal", TestingSession)
    yield
    Base.metadata.drop_all(bind=test_engine)


def make_tracked_search(**kwargs) -> TrackedSearch:
    defaults = dict(
        id="ts-001",
        client_id="client-001",
        origin="JFK",
        destination="LAX",
        trip_type="one_way",
        departure_date_from=date(2026, 5, 1),
        departure_date_to=date(2026, 5, 7),
        return_date_from=None,
        return_date_to=None,
        adults=1,
        max_stops=None,
        threshold_price=Decimal("300.00"),
        alert_email="user@example.com",
        created_at=datetime(2026, 3, 28),
        is_active=True,
    )
    defaults.update(kwargs)
    return TrackedSearch(**defaults)


def make_flight_result(price: str = "250.00", currency: str = "USD"):
    result = MagicMock()
    result.price = price
    result.currency = currency
    return result


# Test 1: writes a PriceSnapshot row when search returns results
def test_check_single_writes_snapshot_when_results():
    ts = make_tracked_search()
    db = TestingSession()
    db.add(ts)
    db.commit()
    db.close()

    results = [make_flight_result("250.00")]
    with patch(SEARCH_FLIGHTS, return_value=results):
        with patch(GET_AMADEUS_CLIENT, return_value=MagicMock()):
            with patch(SEND_PRICE_ALERT):
                check_single_tracked_search(ts)

    db = TestingSession()
    snapshots = db.query(PriceSnapshot).filter(PriceSnapshot.tracked_search_id == "ts-001").all()
    db.close()
    assert len(snapshots) == 1
    assert snapshots[0].best_price == Decimal("250.00")
    assert snapshots[0].currency == "USD"


# Test 2: writes NO snapshot when results is empty
def test_check_single_no_snapshot_when_no_results():
    ts = make_tracked_search()
    db = TestingSession()
    db.add(ts)
    db.commit()
    db.close()

    with patch(SEARCH_FLIGHTS, return_value=[]):
        with patch(GET_AMADEUS_CLIENT, return_value=MagicMock()):
            with patch(SEND_PRICE_ALERT) as mock_alert:
                check_single_tracked_search(ts)

    db = TestingSession()
    snapshots = db.query(PriceSnapshot).filter(PriceSnapshot.tracked_search_id == "ts-001").all()
    db.close()
    assert len(snapshots) == 0
    mock_alert.assert_not_called()


# Test 3: calls send_price_alert when price <= threshold and no prior snapshot
def test_check_single_sends_alert_when_below_threshold_no_prior():
    ts = make_tracked_search(threshold_price=Decimal("300.00"))
    db = TestingSession()
    db.add(ts)
    db.commit()
    db.close()

    results = [make_flight_result("250.00")]
    with patch(SEARCH_FLIGHTS, return_value=results):
        with patch(GET_AMADEUS_CLIENT, return_value=MagicMock()):
            with patch(SEND_PRICE_ALERT) as mock_alert:
                check_single_tracked_search(ts)

    mock_alert.assert_called_once()
    call_kwargs = mock_alert.call_args.kwargs
    assert call_kwargs["best_price"] == Decimal("250.00")
    assert call_kwargs["previous_best_price"] is None


# Test 4: calls send_price_alert when price < previous_best AND price <= threshold
def test_check_single_sends_alert_when_price_drops():
    ts = make_tracked_search(threshold_price=Decimal("300.00"))
    db = TestingSession()
    db.add(ts)
    # Add a prior snapshot at 270.00
    prior = PriceSnapshot(
        tracked_search_id="ts-001",
        checked_at=datetime(2026, 3, 27, 12, 0, 0),
        best_price=Decimal("270.00"),
        currency="USD",
    )
    db.add(prior)
    db.commit()
    db.close()

    results = [make_flight_result("250.00")]
    with patch(SEARCH_FLIGHTS, return_value=results):
        with patch(GET_AMADEUS_CLIENT, return_value=MagicMock()):
            with patch(SEND_PRICE_ALERT) as mock_alert:
                check_single_tracked_search(ts)

    mock_alert.assert_called_once()
    call_kwargs = mock_alert.call_args.kwargs
    assert call_kwargs["best_price"] == Decimal("250.00")
    assert call_kwargs["previous_best_price"] == Decimal("270.00")


# Test 5: does NOT call send_price_alert when price > threshold
def test_check_single_no_alert_when_above_threshold():
    ts = make_tracked_search(threshold_price=Decimal("200.00"))
    db = TestingSession()
    db.add(ts)
    db.commit()
    db.close()

    results = [make_flight_result("250.00")]
    with patch(SEARCH_FLIGHTS, return_value=results):
        with patch(GET_AMADEUS_CLIENT, return_value=MagicMock()):
            with patch(SEND_PRICE_ALERT) as mock_alert:
                check_single_tracked_search(ts)

    mock_alert.assert_not_called()


# Test 6: does NOT call send_price_alert when price == previous_best (not strictly less)
def test_check_single_no_alert_when_price_same_as_previous():
    ts = make_tracked_search(threshold_price=Decimal("300.00"))
    db = TestingSession()
    db.add(ts)
    prior = PriceSnapshot(
        tracked_search_id="ts-001",
        checked_at=datetime(2026, 3, 27, 12, 0, 0),
        best_price=Decimal("250.00"),
        currency="USD",
    )
    db.add(prior)
    db.commit()
    db.close()

    results = [make_flight_result("250.00")]
    with patch(SEARCH_FLIGHTS, return_value=results):
        with patch(GET_AMADEUS_CLIENT, return_value=MagicMock()):
            with patch(SEND_PRICE_ALERT) as mock_alert:
                check_single_tracked_search(ts)

    mock_alert.assert_not_called()


# Test 7: catches exceptions from search_flights and does not raise
def test_check_single_catches_exception_from_search_flights():
    ts = make_tracked_search()
    db = TestingSession()
    db.add(ts)
    db.commit()
    db.close()

    with patch(SEARCH_FLIGHTS, side_effect=RuntimeError("API down")):
        with patch(GET_AMADEUS_CLIENT, return_value=MagicMock()):
            # Should not raise
            check_single_tracked_search(ts)


# Test 8: catches exceptions from send_price_alert and does not raise
def test_check_single_catches_exception_from_send_price_alert():
    ts = make_tracked_search(threshold_price=Decimal("300.00"))
    db = TestingSession()
    db.add(ts)
    db.commit()
    db.close()

    results = [make_flight_result("250.00")]
    with patch(SEARCH_FLIGHTS, return_value=results):
        with patch(GET_AMADEUS_CLIENT, return_value=MagicMock()):
            with patch(SEND_PRICE_ALERT, side_effect=Exception("SMTP error")):
                # Should not raise
                check_single_tracked_search(ts)


# Test 9: check_all_tracked_searches only processes is_active=True searches
def test_check_all_only_processes_active():
    db = TestingSession()
    active_ts = make_tracked_search(id="ts-active", is_active=True)
    inactive_ts = make_tracked_search(id="ts-inactive", is_active=False)
    db.add(active_ts)
    db.add(inactive_ts)
    db.commit()
    db.close()

    processed_ids = []

    def fake_check_single(ts):
        processed_ids.append(ts.id)

    with patch("app.services.scheduler.check_single_tracked_search", side_effect=fake_check_single):
        check_all_tracked_searches()

    assert "ts-active" in processed_ids
    assert "ts-inactive" not in processed_ids


# Test 10: create_scheduler returns BackgroundScheduler with job registered
def test_create_scheduler_has_job_registered():
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = create_scheduler()
    assert isinstance(scheduler, BackgroundScheduler)
    job_ids = [job.id for job in scheduler.get_jobs()]
    assert "check_all_tracked_searches" in job_ids
