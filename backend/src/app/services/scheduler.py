from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings
from app.db import SessionLocal
from app.models.tracked_search import PriceSnapshot, TrackedSearch
from app.schemas.search import SearchRequest
from app.services.amadeus_client import get_amadeus_client
from app.services.email_service import send_price_alert
from app.services.flight_service import search_flights

logger = logging.getLogger(__name__)


def create_scheduler() -> BackgroundScheduler:
    """Create APScheduler with a single recurring job. Does NOT start it."""
    settings = get_settings()
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        check_all_tracked_searches,
        trigger=IntervalTrigger(minutes=settings.scheduler_interval_minutes),
        id="check_all_tracked_searches",
        replace_existing=True,
    )
    return scheduler


def check_all_tracked_searches() -> None:
    """Open a DB session, load all active tracked searches, check each one."""
    db = SessionLocal()
    try:
        searches = (
            db.query(TrackedSearch)
            .filter(TrackedSearch.is_active == True)  # noqa: E712
            .all()
        )
        db.expunge_all()
    finally:
        db.close()
    for ts in searches:
        check_single_tracked_search(ts)


def check_single_tracked_search(ts: TrackedSearch) -> None:
    """
    Check one tracked search: run Amadeus search, write snapshot, send alert if needed.
    All exceptions are caught and logged — this function never raises.
    """
    db = SessionLocal()
    try:
        # Re-fetch in new session to avoid DetachedInstanceError
        ts = db.merge(ts)
        request = SearchRequest(
            origin=ts.origin,
            destination=ts.destination,
            trip_type=ts.trip_type,
            departure_date_from=ts.departure_date_from,
            departure_date_to=ts.departure_date_to,
            return_date_from=ts.return_date_from,
            return_date_to=ts.return_date_to,
            adults=ts.adults,
            max_stops=ts.max_stops,
        )
        client = get_amadeus_client()
        results = search_flights(request, client)

        if not results:
            logger.warning("No results for tracked_search %s", ts.id)
            return

        best_offer = min(results, key=lambda o: float(o.price))
        best_price = Decimal(best_offer.price)
        currency = best_offer.currency

        prev_snapshot = (
            db.query(PriceSnapshot)
            .filter(PriceSnapshot.tracked_search_id == ts.id)
            .order_by(PriceSnapshot.checked_at.desc())
            .first()
        )
        previous_best_price = Decimal(str(prev_snapshot.best_price)) if prev_snapshot else None

        snapshot = PriceSnapshot(
            tracked_search_id=ts.id,
            checked_at=datetime.now(timezone.utc).replace(tzinfo=None),
            best_price=best_price,
            currency=currency,
        )
        db.add(snapshot)
        db.commit()

        threshold = Decimal(str(ts.threshold_price))
        if best_price <= threshold and (
            previous_best_price is None or best_price < previous_best_price
        ):
            send_price_alert(
                to_address=ts.alert_email,
                origin=ts.origin,
                destination=ts.destination,
                departure_date_from=ts.departure_date_from,
                departure_date_to=ts.departure_date_to,
                return_date_from=ts.return_date_from,
                return_date_to=ts.return_date_to,
                best_price=best_price,
                currency=currency,
                threshold_price=threshold,
                previous_best_price=previous_best_price,
            )
    except Exception:
        logger.error("check_single_tracked_search failed for %s", ts.id, exc_info=True)
    finally:
        db.close()
