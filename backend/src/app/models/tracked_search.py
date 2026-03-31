import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.db import Base


class TrackedSearch(Base):
    __tablename__ = "tracked_searches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String(36), nullable=False, index=True)
    origin = Column(String(3), nullable=False)
    destination = Column(String(3), nullable=False)
    trip_type = Column(String(10), nullable=False)  # 'one_way' or 'round_trip'
    departure_date_from = Column(Date, nullable=False)
    departure_date_to = Column(Date, nullable=False)
    return_date_from = Column(Date, nullable=True)
    return_date_to = Column(Date, nullable=True)
    adults = Column(Integer, nullable=False, default=1)
    max_stops = Column(Integer, nullable=True)
    threshold_price = Column(Numeric(10, 2), nullable=False)
    alert_email = Column(String(254), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True)

    snapshots = relationship(
        "PriceSnapshot",
        back_populates="tracked_search",
        cascade="all, delete-orphan",
    )


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tracked_search_id = Column(
        String(36), ForeignKey("tracked_searches.id"), nullable=False, index=True
    )
    checked_at = Column(DateTime, nullable=False)
    best_price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False)

    tracked_search = relationship("TrackedSearch", back_populates="snapshots")
