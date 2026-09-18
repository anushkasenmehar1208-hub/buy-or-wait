"""Application settings — all secrets from environment (.env via pydantic-settings)."""
from functools import lru_cache
from urllib.parse import parse_qs, quote, urlencode, urlparse, urlunparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOCAL_PG_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def with_direct_tls_negotiation(url: str) -> str:
    """Add ``sslnegotiation=direct`` to remote postgres URLs that require SSL.

    Why: some networks (corporate firewalls, campus/ISP DPI filters) silently
    drop libpq's *plaintext* SSLRequest packet on port 5432. The TCP handshake
    then succeeds but the connection hangs forever — psycopg2 reports
    "could not receive data from server: Operation timed out" even though the
    port is reachable. libpq's TLS-first handshake (``sslnegotiation=direct``,
    libpq >= 17) opens with a normal TLS ClientHello carrying SNI, which such
    filters pass through and the real server answers.

    Applied only when all of these hold, so local development and tests are
    unaffected and explicit URLs always win:
      * postgres scheme (plain or +psycopg2)
      * non-local host, port 5432 (explicit or default)
      * ``sslmode=require`` is already set
      * ``sslnegotiation`` is not already specified in the URL
    """
    try:
        parsed = urlparse(url)
        port = parsed.port  # may raise ValueError for malformed ports
    except ValueError:
        return url
    if parsed.scheme not in ("postgresql", "postgres", "postgresql+psycopg2", "postgres+psycopg2"):
        return url
    host = (parsed.hostname or "").lower()
    if not host or host in _LOCAL_PG_HOSTS:
        return url
    if port not in (None, 5432):
        return url
    query = parse_qs(parsed.query, keep_blank_values=True)
    if "sslnegotiation" in query:
        return url
    if query.get("sslmode", [None])[0] != "require":
        return url
    query["sslnegotiation"] = ["direct"]
    # quote_via=quote: keep libpq-compatible percent-encoding ('%20', not '+')
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True, quote_via=quote)))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://localhost/buyorwait"
    secret_key: str
    access_token_expire_seconds: int = 60 * 60 * 24 * 7  # 7 days
    cors_origins: str = "http://localhost:5173"

    @field_validator("database_url", mode="after")
    @classmethod
    def _apply_direct_tls(cls, value: str) -> str:
        return with_direct_tls_negotiation(value)

    @property
    def cors_origin_list(self) -> list:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
