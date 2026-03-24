from amadeus import Client

from app.config import get_settings


def get_amadeus_client() -> Client:
    settings = get_settings()
    return Client(
        client_id=settings.amadeus_client_id,
        client_secret=settings.amadeus_client_secret,
        hostname=settings.amadeus_hostname,
    )
