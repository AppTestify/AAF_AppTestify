from unittest.mock import MagicMock
from aaf.config import Settings
from app.models.config import TenantConnectorConfig
from app.services.config_resolver import resolve_effective_settings

def test_config_resolver_reads_jira_project_key():
    db = MagicMock()
    tenant = MagicMock()
    tenant.id = 1
    
    row = TenantConnectorConfig(
        tenant_id=1,
        connector_name="jira",
        enabled=True,
        config_json={"project_key": "CAS", "base_url": "https://example.atlassian.net"}
    )
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [row]
    db.execute.return_value = mock_result
    
    base = Settings()
    effective = resolve_effective_settings(db, base, tenant)
    
    assert effective.jira_project == "CAS"
    assert effective.jira_url == "https://example.atlassian.net"
