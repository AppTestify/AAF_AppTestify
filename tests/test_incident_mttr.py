"""Tests for DORA MTTR incident correlation pipeline."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.metrics import DeploymentEvent
from app.services.incident_mttr import batch_correlate_incidents, correlate_incident_to_mttr


@pytest.fixture
def mock_session():
    """Mock SQLAlchemy session."""
    return MagicMock(spec=Session)


@pytest.fixture
def sample_deployment():
    """Sample deployment event."""
    return DeploymentEvent(
        id=1,
        tenant_id=100,
        service_name="payment-service",
        environment="production",
        deployed_at=datetime(2026, 6, 17, 10, 0, 0, tzinfo=timezone.utc),
        lead_time_hours=2.5,
        succeeded=True,
        rollback=False,
        metadata_json={},
    )


@pytest.fixture
def sample_incident():
    """Sample incident data."""
    return {
        "id": "INC001",
        "service_name": "payment-service",
        "started_at": datetime(2026, 6, 17, 10, 30, 0, tzinfo=timezone.utc),
        "resolved_at": datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc),
        "mttr_hours": 1.5,
    }


def test_correlate_incident_to_mttr_success(mock_session, sample_deployment, sample_incident):
    """Successful correlation: incident matched to deployment with MTTR updated."""
    mock_session.execute.return_value.scalars.return_value.all.return_value = [sample_deployment]
    
    result = correlate_incident_to_mttr(
        db=mock_session,
        tenant_id=100,
        incident_id="INC001",
        service_name="payment-service",
        incident_start=sample_incident["started_at"],
        incident_end=sample_incident["resolved_at"],
        mttr_hours=1.5,
    )
    
    assert result is True
    # Verify deployment was updated
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    
    # Check metadata was updated with incident info
    updated_deployment = mock_session.add.call_args[0][0]
    assert "incidents" in updated_deployment.metadata_json
    assert updated_deployment.metadata_json["mttr_hours"] == 1.5


def test_correlate_incident_to_mttr_no_deployment_found(mock_session):
    """No deployment found for service -> returns False."""
    mock_session.execute.return_value.scalars.return_value.all.return_value = []
    
    result = correlate_incident_to_mttr(
        db=mock_session,
        tenant_id=100,
        incident_id="INC001",
        service_name="payment-service",
        incident_start=datetime(2026, 6, 17, 10, 30, 0, tzinfo=timezone.utc),
        incident_end=datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc),
    )
    
    assert result is False
    # No updates should be made
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()


def test_correlate_incident_to_mttr_no_end_time_no_mttr(mock_session):
    """Incident without end_time or mttr_hours -> returns False."""
    result = correlate_incident_to_mttr(
        db=mock_session,
        tenant_id=100,
        incident_id="INC001",
        service_name="payment-service",
        incident_start=datetime(2026, 6, 17, 10, 30, 0, tzinfo=timezone.utc),
        incident_end=None,
        mttr_hours=None,
    )
    
    assert result is False


def test_correlate_incident_to_mttr_calculates_mttr_from_end_time(mock_session, sample_deployment):
    """MTTR calculated from incident_end - incident_start when mttr_hours not provided."""
    mock_session.execute.return_value.scalars.return_value.all.return_value = [sample_deployment]
    
    start = datetime(2026, 6, 17, 10, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 17, 13, 30, 0, tzinfo=timezone.utc)
    
    result = correlate_incident_to_mttr(
        db=mock_session,
        tenant_id=100,
        incident_id="INC002",
        service_name="payment-service",
        incident_start=start,
        incident_end=end,
        mttr_hours=None,  # Will be calculated
    )
    
    assert result is True
    updated_deployment = mock_session.add.call_args[0][0]
    assert updated_deployment.metadata_json["mttr_hours"] == 3.5  # 3.5 hours


def test_correlate_incident_marks_rollback_if_mttr_significant(mock_session, sample_deployment):
    """Incident with MTTR > 1 hour marks deployment as rollback."""
    sample_deployment.succeeded = False
    mock_session.execute.return_value.scalars.return_value.all.return_value = [sample_deployment]
    
    result = correlate_incident_to_mttr(
        db=mock_session,
        tenant_id=100,
        incident_id="INC003",
        service_name="payment-service",
        incident_start=datetime(2026, 6, 17, 10, 0, 0, tzinfo=timezone.utc),
        incident_end=None,
        mttr_hours=2.5,  # Significant MTTR
    )
    
    assert result is True
    updated_deployment = mock_session.add.call_args[0][0]
    assert updated_deployment.rollback is True


def test_correlate_incident_within_24_hour_window(mock_session, sample_deployment):
    """Only deployments within 24 hours before incident start are matched."""
    mock_session.execute.return_value.scalars.return_value.all.return_value = [sample_deployment]
    
    # Incident starts 6 hours after deployment
    incident_start = sample_deployment.deployed_at + timedelta(hours=6)
    
    result = correlate_incident_to_mttr(
        db=mock_session,
        tenant_id=100,
        incident_id="INC004",
        service_name="payment-service",
        incident_start=incident_start,
        incident_end=incident_start + timedelta(hours=1),
    )
    
    assert result is True


def test_batch_correlate_incidents_multiple(mock_session, sample_deployment):
    """Batch correlation processes multiple incidents."""
    mock_session.execute.return_value.scalars.return_value.all.return_value = [sample_deployment]
    
    incidents = [
        {
            "id": "INC001",
            "service_name": "payment-service",
            "started_at": datetime(2026, 6, 17, 10, 30, 0, tzinfo=timezone.utc),
            "resolved_at": datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc),
            "mttr_hours": 1.5,
        },
        {
            "id": "INC002",
            "service_name": "payment-service",
            "started_at": datetime(2026, 6, 17, 14, 0, 0, tzinfo=timezone.utc),
            "resolved_at": None,
            "mttr_hours": None,  # Will fail correlation
        },
    ]
    
    results = batch_correlate_incidents(mock_session, 100, incidents)
    
    assert "INC001" in results
    assert results["INC001"] is True
    assert "INC002" in results
    assert results["INC002"] is False


def test_batch_correlate_incidents_empty():
    """Batch correlation with empty list returns empty dict."""
    mock_session = MagicMock(spec=Session)
    results = batch_correlate_incidents(mock_session, 100, [])
    assert results == {}


def test_incident_metadata_structure(mock_session, sample_deployment):
    """Incident correlation creates proper metadata structure."""
    mock_session.execute.return_value.scalars.return_value.all.return_value = [sample_deployment]
    
    start = datetime(2026, 6, 17, 10, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 17, 11, 15, 0, tzinfo=timezone.utc)
    
    correlate_incident_to_mttr(
        db=mock_session,
        tenant_id=100,
        incident_id="INC-TEST-001",
        service_name="payment-service",
        incident_start=start,
        incident_end=end,
    )
    
    updated_deployment = mock_session.add.call_args[0][0]
    meta = updated_deployment.metadata_json
    
    assert "incidents" in meta
    assert len(meta["incidents"]) == 1
    
    incident_record = meta["incidents"][0]
    assert incident_record["id"] == "INC-TEST-001"
    assert incident_record["started_at"] == start.isoformat()
    assert incident_record["ended_at"] == end.isoformat()
    assert incident_record["mttr_hours"] == 1.25
