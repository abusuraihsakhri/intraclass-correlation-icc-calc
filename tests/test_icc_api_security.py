import pytest
from fastapi import HTTPException

from agents.api import ICCRequest, api_icc
from agents.base import AuditTrail


def test_api_icc_values():
    response = api_icc(ICCRequest(ratings=[[1, 2], [2, 3], [3, 4], [4, 5]]))
    assert response["icc_3_1"] == pytest.approx(1)
    assert response["icc_2_1"] == pytest.approx(10 / 13)


def test_api_rejects_unbalanced_matrix():
    with pytest.raises(HTTPException) as err:
        api_icc(ICCRequest(ratings=[[1, 2], [2]]))
    assert err.value.status_code == 422


def test_audit_detects_modified_signed_field():
    trail = AuditTrail("test-key")
    trail.log("system", "test", "event", {"status": "ok"})
    assert trail.verify_integrity()
    # Copies returned from get_trail are safe to modify.
    external = trail.get_trail()
    external[0]["actor"] = "edited"
    assert trail.verify_integrity()
    # Tampering with the internal log is detected cryptographically.
    trail.logs[0]["actor"] = "edited"
    assert trail.verify_integrity() is False


def test_audit_detects_signature_tampering():
    trail = AuditTrail("test-key")
    trail.log("system", "test", "event", {"status": "ok"})
    trail.logs[0]["current_hash"] = "0" * 64
    assert not trail.verify_integrity()



def test_audit_rejects_separator_reallocation_attack():
    trail = AuditTrail("test-key")
    trail.log("alpha|beta", "tier", "event", {"status": "ok"})
    assert trail.verify_integrity()
    trail.logs[0]["actor"] = "alpha"
    trail.logs[0]["actor_tier"] = "beta|tier"
    assert not trail.verify_integrity()
