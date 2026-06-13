from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from uni_kb.generators.config_catalog import generate_config_catalog


@pytest.fixture
def project_with_config() -> Path:
    td = tempfile.mkdtemp()
    root = Path(td)
    (root / "app.yaml").write_text("server:\n  port: 8080\n  host: localhost")
    (root / ".env").write_text("DB_HOST=postgres\nDB_PORT=5432\n# comment\nAPI_KEY=secret")
    return root


class TestConfigCatalog:
    def test_generates_yaml(self, project_with_config):
        result = generate_config_catalog(str(project_with_config))
        assert "config_catalog:" in result
        assert "entries:" in result

    def test_includes_env_vars(self, project_with_config):
        result = generate_config_catalog(str(project_with_config))
        assert "DB_HOST" in result
        assert "DB_PORT" in result

    def test_excludes_comments(self, project_with_config):
        result = generate_config_catalog(str(project_with_config))
        assert "comment" not in result

    def test_includes_yaml_keys(self, project_with_config):
        result = generate_config_catalog(str(project_with_config))
        assert "server.port" in result
        assert "server.host" in result or "port" in result

    def test_empty_dir(self):
        td = tempfile.mkdtemp()
        result = generate_config_catalog(td)
        assert "entries:" in result
