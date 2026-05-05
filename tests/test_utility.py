from aaf.config import Settings
from aaf.schema import EvidenceRecord
from orchestrator.utility import score_actions


def test_utility_prefers_mitigate_when_workflow_fails():
    ev = [
        EvidenceRecord(
            source="github",
            kind="workflow_run",
            summary="ci: failure",
            severity=0.9,
        )
    ]
    s = Settings()
    u = score_actions(ev, s)
    assert u.recommended_action.value in (
        "mitigate_monitor",
        "rollback",
        "patch_block_release",
    )
