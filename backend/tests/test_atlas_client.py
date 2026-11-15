from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.services.atlas.client import AtlasClient, AtlasError, AtlasForbidden, fmt_since

KEY = "atlas_supersecret123"


def make(handler, sleeps=None):
    sleeps = sleeps if sleeps is not None else []
    return AtlasClient(
        "https://atlas.test",
        KEY,
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
    )


def test_fmt_since_utc_z():
    assert fmt_since(datetime(2026, 11, 14, 10, 0, 0, tzinfo=timezone.utc)) == "2026-11-14T10:00:00Z"
    tz = timezone(timedelta(hours=-6))
    assert fmt_since(datetime(2026, 11, 14, 4, 0, 0, tzinfo=tz)) == "2026-11-14T10:00:00Z"
    assert fmt_since(datetime(2026, 11, 14, 10, 0, 0)) == "2026-11-14T10:00:00Z"


def test_iter_pages_follows_cursor_and_keeps_first_server_time():
    seen = []

    def handler(request):
        seen.append(request)
        if "cursor" not in request.url.params:
            return httpx.Response(200, json={"items": [{"id": 1}], "next_cursor": "c2", "server_time": "T1"})
        if request.url.params["cursor"] == "c2":
            return httpx.Response(200, json={"items": [{"id": 2}], "next_cursor": "c3", "server_time": "T2"})
        return httpx.Response(200, json={"items": [{"id": 3}], "next_cursor": None, "server_time": "T3"})

    since = datetime(2026, 11, 14, 10, 0, 0, tzinfo=timezone.utc)
    pages = list(make(handler).iter_pages("/api/channel/products", since))
    assert pages == [([{"id": 1}], "T1"), ([{"id": 2}], "T1"), ([{"id": 3}], "T1")]
    assert seen[0].headers["Authorization"] == f"Bearer {KEY}"
    assert seen[0].url.params["updated_since"] == "2026-11-14T10:00:00Z"
    assert seen[0].url.params["limit"] == "200"
    assert seen[0].url.path == "/api/channel/products"


def test_iter_pages_without_since_omits_param():
    def handler(request):
        assert "updated_since" not in request.url.params
        return httpx.Response(200, json={"items": [], "next_cursor": None, "server_time": "T"})

    assert list(make(handler).iter_pages("/x", None)) == [([], "T")]


def test_retries_5xx_then_succeeds_with_retry_after():
    calls = []
    sleeps = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "7"})
        if len(calls) == 2:
            return httpx.Response(503)
        return httpx.Response(200, json={"items": [], "next_cursor": None, "server_time": "T"})

    assert list(make(handler, sleeps).iter_pages("/x", None)) == [([], "T")]
    assert len(calls) == 3
    assert sleeps[0] == 7
    assert len(sleeps) == 2


def test_gives_up_after_three_retries():
    calls = []
    sleeps = []

    def handler(request):
        calls.append(1)
        return httpx.Response(500)

    with pytest.raises(AtlasError):
        list(make(handler, sleeps).iter_pages("/x", None))
    assert len(calls) == 4
    assert len(sleeps) == 3


def test_401_raises_without_key_in_message():
    def handler(request):
        return httpx.Response(401, json={"detail": "bad"})

    with pytest.raises(AtlasError) as exc:
        list(make(handler).iter_pages("/x", None))
    assert KEY not in str(exc.value)
    assert KEY not in repr(exc.value)
    assert "401" in str(exc.value)


def test_client_repr_hides_key():
    assert KEY not in repr(make(lambda r: httpx.Response(200)))


def test_network_error_does_not_leak_key():
    def handler(request):
        raise httpx.ConnectError("boom", request=request)

    with pytest.raises(AtlasError) as exc:
        list(make(handler, []).iter_pages("/x", None))
    assert KEY not in str(exc.value)


def test_post_lead_sends_idempotency_key_and_returns_status():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(202, json={})

    status = make(handler).post_lead({"name": "a"}, "idem-1")
    assert status == 202
    assert seen[0].method == "POST"
    assert seen[0].url.path.endswith("/leads")
    assert seen[0].headers["Idempotency-Key"] == "idem-1"
    assert seen[0].headers["Authorization"] == f"Bearer {KEY}"


def test_post_lead_403_is_forbidden():
    with pytest.raises(AtlasForbidden) as exc:
        make(lambda r: httpx.Response(403)).post_lead({}, "k")
    assert isinstance(exc.value, AtlasError)
    assert KEY not in str(exc.value)
