from app.rate_limit import InMemoryRateLimiter


def test_blocks_requests_over_the_limit() -> None:
    limiter = InMemoryRateLimiter(
        limit=2,
        window_seconds=60,
    )

    assert limiter.consume("client-1", now=0) is None
    assert limiter.consume("client-1", now=1) is None
    assert limiter.consume("client-1", now=2) == 58


def test_allows_requests_after_window_expires() -> None:
    limiter = InMemoryRateLimiter(
        limit=2,
        window_seconds=60,
    )

    limiter.consume("client-1", now=0)
    limiter.consume("client-1", now=1)

    assert limiter.consume("client-1", now=61) is None


def test_tracks_clients_independently() -> None:
    limiter = InMemoryRateLimiter(
        limit=1,
        window_seconds=60,
    )

    assert limiter.consume("client-1", now=0) is None
    assert limiter.consume("client-2", now=0) is None
    assert limiter.consume("client-1", now=1) == 59