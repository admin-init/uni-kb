from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from uni_kb.parsers.base import ParseResult, ParsedClass, ParsedEndpoint, ParsedEntity, ParsedMethod
from uni_kb.store.code_graph import CodeGraph


def _sample_result() -> ParseResult:
    return ParseResult(
        classes=[
            ParsedClass(
                name="UserController",
                type="controller",
                annotations=["RestController"],
                file_path="/src/UserController.java",
                package="com.example.controller",
                extends="BaseController",
                implements=["InitializingBean"],
            ),
            ParsedClass(
                name="UserService",
                type="service",
                annotations=["Service"],
                file_path="/src/UserService.java",
                package="com.example.service",
            ),
        ],
        methods=[
            ParsedMethod(
                name="getUser",
                class_name="UserController",
                params=[{"name": "id", "type": "Long"}],
                return_type="User",
                body_hash="abc123",
            ),
            ParsedMethod(
                name="findUser",
                class_name="UserService",
                params=[{"name": "id", "type": "Long"}],
                return_type="User",
                body_hash="def456",
            ),
        ],
        endpoints=[
            ParsedEndpoint(
                http_method="GET",
                path="/api/users/{id}",
                method_name="getUser",
                class_name="UserController",
                auth_required=True,
            ),
            ParsedEndpoint(
                http_method="POST",
                path="/api/users",
                method_name="createUser",
                class_name="UserController",
            ),
        ],
        entities=[
            ParsedEntity(
                name="User",
                table_name="users",
                package="com.example.entity",
                file_path="/src/User.java",
                primary_keys=["id"],
                fields=[
                    {"name": "id", "column_name": "id", "type": "Long"},
                    {"name": "username", "column_name": "username", "type": "String"},
                    {"name": "department_id", "column_name": "department_id", "type": "Long", "fk_ref": "departments"},
                ],
            ),
        ],
    )


@pytest.fixture
def empty_graph() -> CodeGraph:
    return CodeGraph()


@pytest.fixture
def populated_graph() -> CodeGraph:
    g = CodeGraph()
    g.build_from_parse_results([_sample_result()])
    return g


class TestCodeGraph:
    def test_empty_graph(self, empty_graph: CodeGraph):
        assert empty_graph.node_count() == 0
        assert empty_graph.edge_count() == 0

    def test_build_adds_class_nodes(self, populated_graph: CodeGraph):
        assert "Class:UserController" in populated_graph.graph
        assert "Class:UserService" in populated_graph.graph

    def test_build_adds_method_nodes(self, populated_graph: CodeGraph):
        assert "Method:UserController.getUser" in populated_graph.graph
        assert "Method:UserService.findUser" in populated_graph.graph

    def test_build_adds_endpoint_nodes(self, populated_graph: CodeGraph):
        assert "APIEndpoint:UserController.getUser" in populated_graph.graph
        assert "APIEndpoint:UserController.createUser" in populated_graph.graph

    def test_build_adds_entity_nodes(self, populated_graph: CodeGraph):
        assert "DBTable:users" in populated_graph.graph
        assert "DBColumn:users.id" in populated_graph.graph
        assert "DBColumn:users.username" in populated_graph.graph

    def test_build_adds_has_method_edges(self, populated_graph: CodeGraph):
        assert populated_graph.graph.has_edge("Class:UserController", "Method:UserController.getUser")

    def test_build_adds_routes_to_edges(self, populated_graph: CodeGraph):
        assert populated_graph.graph.has_edge("Class:UserController", "APIEndpoint:UserController.getUser")

    def test_build_adds_extends_edges(self, populated_graph: CodeGraph):
        assert populated_graph.graph.has_edge("Class:UserController", "Class:BaseController")

    def test_build_adds_implements_edges(self, populated_graph: CodeGraph):
        assert populated_graph.graph.has_edge("Class:UserController", "Class:InitializingBean")

    def test_build_adds_fk_to_edges(self, populated_graph: CodeGraph):
        assert populated_graph.graph.has_edge("DBColumn:users.department_id", "DBTable:users")
        assert populated_graph.graph.has_edge("DBColumn:users.department_id", "DBTable:departments")

    def test_get_dependencies(self, populated_graph: CodeGraph):
        deps = populated_graph.get_dependencies("Method:UserController.getUser")
        assert "Class:UserController" in deps

    def test_get_dependents(self, populated_graph: CodeGraph):
        deps = populated_graph.get_dependents("Class:UserController")
        assert "Method:UserController.getUser" in deps
        assert "APIEndpoint:UserController.getUser" in deps

    def test_topological_sort(self, populated_graph: CodeGraph):
        order = populated_graph.topological_sort()
        assert len(order) == populated_graph.node_count()

    def test_save_load_roundtrip(self, populated_graph: CodeGraph):
        with tempfile.NamedTemporaryFile(suffix=".gml", delete=False) as tf:
            path = tf.name
        try:
            populated_graph.save(path)
            loaded = CodeGraph()
            loaded.load(path)
            assert loaded.node_count() == populated_graph.node_count()
            assert loaded.edge_count() == populated_graph.edge_count()
        finally:
            Path(path).unlink(missing_ok=True)

    def test_build_from_empty_results(self, empty_graph: CodeGraph):
        empty_graph.build_from_parse_results([])
        assert empty_graph.node_count() == 0

    def test_build_from_multiple_results(self, empty_graph: CodeGraph):
        r1 = ParseResult(classes=[ParsedClass(name="A", type="controller", file_path="/a.java")])
        r2 = ParseResult(classes=[ParsedClass(name="B", type="service", file_path="/b.java")])
        empty_graph.build_from_parse_results([r1, r2])
        assert empty_graph.node_count() == 2
        assert "Class:A" in empty_graph.graph
        assert "Class:B" in empty_graph.graph
