from datetime import datetime, timezone
def make_meta(name, source_url, resolution, start, end, n_obs, kind):
    assert kind in ("observed", "modeled", "assumed")
    return dict(name=name, source_url=source_url, resolution=resolution, period_start=start,
                period_end=end, n_obs=n_obs, kind=kind,
                retrieved_at=datetime.now(timezone.utc).isoformat())
def unavailable(name, reason):
    """Never fabricate: the UI shows 'unavailable' + reason."""
    return dict(available=False, name=name, reason=reason)
