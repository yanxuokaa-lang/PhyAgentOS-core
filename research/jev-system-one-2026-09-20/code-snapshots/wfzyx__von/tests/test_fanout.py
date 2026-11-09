import pytest
import von
from von.types import noul, choice, score


def test_speculative_fanout():
    state = {
        "event": "database_disk_full",
        "disk_free_percent": 0.01,
        "logs": "No space left on device while writing wal segment",
    }

    questions = {
        "category": choice("What kind of system event is `event`?", {
            "storage": "Disk space, storage volume, filesystem issues",
            "network": "DNS, latency, firewall, timeouts",
            "auth": "Login failure, expired token, permission denied",
        }),
        "is_blocking": noul("Is this event blocking the database from writing data?"),
        "severity": score("Rate the severity of `logs`:", [
            "Informational log",
            "Warning condition with available capacity",
            "Critical storage failure preventing writes",
        ]),
    }

    resp = von.system_one(state=state, questions=questions)
    assert resp.model == "von-1.0.0"
    assert len(resp.answers) == 3

    assert resp.answers["category"].choice == "storage"
    assert resp.answers["is_blocking"].noul > 0.5
    assert resp.answers["severity"].score > 1.0
