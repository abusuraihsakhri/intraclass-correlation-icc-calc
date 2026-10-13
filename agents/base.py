"""Best-effort identifier guard and in-memory HMAC-SHA256 audit chain."""
import os
import re
import json
import time
import hmac
import hashlib
import secrets
from copy import deepcopy
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

PHI_PATTERNS = [
    re.compile(r"\bMRN[:#\s-]*\d{4,10}\b", re.IGNORECASE),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b(?:DOB|Date of Birth)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", re.IGNORECASE),
    re.compile(r"\b(?:Patient\s+Name|Patient)[:\s]+[A-Z][a-z]+\s+[A-Z][a-z]+\b", re.IGNORECASE),
    re.compile(r"\b(?:John\s+Doe|Jane\s+Smith|Alice\s+Johnson)\b", re.IGNORECASE),
]


class SecurityException(Exception):
    """A recognizable sensitive identifier was detected."""


class ResourceLimitExceededException(Exception):
    """Raised when computation exceeds configured limits."""


def assert_no_phi(text: str) -> None:
    """Reject recognizable identifiers; this is NOT complete PHI deidentification."""
    if not text:
        return
    for pattern in PHI_PATTERNS:
        if pattern.search(str(text)):
            raise SecurityException("Sensitive identifier detected; do not submit patient data")


class PHIGuard:
    @staticmethod
    def assert_no_phi(text: str) -> None:
        assert_no_phi(text)

    @staticmethod
    def redact_phi(text: str) -> str:
        res = str(text)
        for pattern in PHI_PATTERNS:
            res = pattern.sub("[REDACTED_IDENTIFIER]", res)
        return res


class AuditTrail:
    """In-memory tamper-evident chain; restarting loses the log and random key."""
    GENESIS = "GENESIS_BLOCK_0000000000000000"

    def __init__(self, secret_key: Optional[str] = None):
        resolved_key = secret_key or os.getenv("AUDIT_SECRET_KEY")
        if not resolved_key:
            resolved_key = secrets.token_hex(32)
        self.secret_key = resolved_key.encode("utf-8")
        self.logs: List[Dict[str, Any]] = []

    def _signature(self, entry):
        fields = ("audit_id", "timestamp", "actor", "actor_tier",
                  "event_type", "payload_hash", "prev_hash")
        sign_string = json.dumps([entry[name] for name in fields], separators=(",", ":"), ensure_ascii=False)
        return hmac.new(self.secret_key, sign_string.encode("utf-8"), hashlib.sha256).hexdigest()

    def log(self, actor: str, actor_tier: str, event_type: str,
            details: Dict[str, Any]) -> Dict[str, Any]:
        for field in (actor, actor_tier, event_type):
            assert_no_phi(field)
        payload_str = json.dumps(details, sort_keys=True, allow_nan=False)
        assert_no_phi(payload_str)
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        audit_id = f"AUDIT-{int(time.time()*1000)}-{len(self.logs)+1}"
        prev_hash = self.logs[-1]["current_hash"] if self.logs else self.GENESIS
        entry = {
            "audit_id": audit_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "actor_tier": actor_tier,
            "event_type": event_type,
            "payload_hash": payload_hash,
            "prev_hash": prev_hash,
        }
        entry["current_hash"] = self._signature(entry)
        self.logs.append(entry)
        return deepcopy(entry)

    def verify_integrity(self) -> bool:
        prev = self.GENESIS
        try:
            for entry in self.logs:
                if entry["prev_hash"] != prev:
                    return False
                if not hmac.compare_digest(entry["current_hash"], self._signature(entry)):
                    return False
                prev = entry["current_hash"]
            return True
        except (KeyError, TypeError, ValueError):
            return False

    def get_trail(self) -> List[Dict[str, Any]]:
        return deepcopy(self.logs)


GLOBAL_AUDIT = AuditTrail()


class AuditLogger:
    @staticmethod
    def log(actor: str, actor_tier: str, event_type: str, details: Dict[str, Any]) -> Dict[str, Any]:
        return GLOBAL_AUDIT.log(actor, actor_tier, event_type, details)

    @staticmethod
    def get_trail() -> List[Dict[str, Any]]:
        return GLOBAL_AUDIT.get_trail()

    @staticmethod
    def verify_integrity() -> bool:
        return GLOBAL_AUDIT.verify_integrity()


class ActionExecutor:
    @staticmethod
    def execute_with_audit(actor, actor_tier, action_type, fn, *args, **kwargs):
        res = fn(*args, **kwargs)
        AuditLogger.log(actor, actor_tier, action_type, {"status": "SUCCESS"})
        return res
