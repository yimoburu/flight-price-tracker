import functools

from amadeus import Client

from app.config import get_settings


@functools.lru_cache(maxsize=1)
def get_amadeus_client() -> Client:
    """Return a cached singleton Amadeus Client instance.

    Called at first use (lazy init). Raises RuntimeError if credentials
    are not configured.
    """
    settings = get_settings()
    if not settings.amadeus_client_id or not settings.amadeus_client_secret:
        raise RuntimeError("Amadeus credentials not configured")
    return Client(
        client_id=settings.amadeus_client_id,
        client_secret=settings.amadeus_client_secret,
        hostname=settings.amadeus_hostname,
    )
