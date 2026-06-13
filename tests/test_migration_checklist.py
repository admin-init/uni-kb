from __future__ import annotations

import pytest
from uni_kb.parsers.base import ParseResult, ParsedClass, ParsedEndpoint
from uni_kb.store.code_graph import CodeGraph
from uni_kb.generators.migration_checklist import generate_migration_checklist


@pytest.fixture
def populated_graph() -> CodeGraph:
    g = CodeGraph()
    result = ParseResult(
        classes=[
            ParsedClass(name="UserController", type="controller", file_path="/src/UserController.java"),
            ParsedClass(name="UserService", type="service", file_path="/src/UserService.java"),
            ParsedClass(name="BaseController", type="controller", file_path="/src/BaseController.java"),
        ],
        endpoints=[
            ParsedEndpoint(http_method="GET", path="/api/users/{id}", method_name="getUser", class_name="UserController"),
        ],
    )
    g.build_from_parse_results([result])
    return g


class TestMigrationChecklist:
    def test_generates_markdown(self, populated_graph):
        result = generate_migration_checklist(populated_graph)
        assert "# Migration Plan" in result
        assert "## Migration Order" in result

    def test_includes_node_count(self, populated_graph):
        result = generate_migration_checklist(populated_graph)
        assert "Total nodes" in result
        assert "Total edges" in result

    def test_lists_all_nodes(self, populated_graph):
        result = generate_migration_checklist(populated_graph)
        assert "UserController" in result
        assert "UserService" in result

    def test_empty_graph(self):
        g = CodeGraph()
        result = generate_migration_checklist(g)
        assert "# Migration Plan" in result
