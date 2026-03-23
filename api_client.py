import requests

def post_metrics(actor, start_year, end_year, trade_year, policy_name=None, shock=None, intensity=None, base_url="http://127.0.0.1:8000"):
    """POST to FastAPI /v2/metrics.

    Never throws in Streamlit runtime: returns {ok: False, error: ...} on failure.
    """
    payload = {
        "actor": actor,
        "start_year": int(start_year),
        "end_year": int(end_year),
        "trade_year": int(trade_year),
        "policy_name": policy_name,
        "shock": shock,
        "intensity": intensity,
    }
    try:
        r = requests.post(f"{base_url}/v2/metrics", json=payload, timeout=25)
    except Exception as e:
        return {"ok": False, "error": f"backend unreachable: {e}", "request": payload}

    if not r.ok:
        # Best-effort parse JSON error; otherwise include snippet
        try:
            j = r.json()
        except Exception:
            j = None
        snippet = (r.text or "")[:600].replace("\n", " ")
        return {
            "ok": False,
            "status_code": r.status_code,
            "error": j if j is not None else snippet,
            "request": payload,
        }

    try:
        return r.json()
    except Exception as e:
        snippet = (r.text or "")[:600].replace("\n", " ")
        return {"ok": False, "error": f"non-json backend response: {e}", "raw": snippet, "request": payload}
