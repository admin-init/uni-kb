from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from uni_kb.store.sqlite_store import SQLiteStore
from uni_kb.parsers.base import ParseResult, ParsedClass, ParsedEndpoint, ParsedEntity
from uni_kb.generators.api_contract import generate_api_contract


@pytest.fixture
def store_with_data() -> SQLiteStore:
    td = tempfile.mkdtemp()
    s = SQLiteStore(Path(td) / "test.db")
    s.create_tables()

    result = ParseResult(
        classes=[
            ParsedClass(name="UserController", type="controller", package="com.example.controller", file_path="/src/UserController.java", annotations=["RestController"]),
            ParsedClass(name="UserService", type="service", package="com.example.service", file_path="/src/UserService.java", annotations=["Service"]),
        ],
        endpoints=[
            ParsedEndpoint(http_method="GET", path="/api/users/{id}", method_name="getUser", class_name="UserController", response_schema="User", auth_required=True, auth_permissions=["hasRole('ADMIN')"]),
            ParsedEndpoint(http_method="POST", path="/api/users", method_name="createUser", class_name="UserController", request_schema="UserRequest", response_schema="User"),
        ],
        entities=[
            ParsedEntity(
                name="User", table_name="users", package="com.example.entity", file_path="/src/User.java", primary_keys=["id"],
                fields=[
                    {"name": "id", "column_name": "id", "type": "Long", "nullable": False},
                    {"name": "username", "column_name": "username", "type": "String", "nullable": False, "unique": True, "length": 50},
                ],
            ),
        ],
    )
    s.ingest_parse_result(result)
    return s


class TestApiContract:
    def test_generates_yaml(self, store_with_data):
        result = generate_api_contract(store_with_data)
        assert "openapi: 3.0.3" in result
        assert "/api/users/{id}" in result
        assert "/api/users" in result

    def test_includes_security(self, store_with_data):
        result = generate_api_contract(store_with_data)
        assert "bearerAuth" in result

    def test_includes_schemas(self, store_with_data):
        result = generate_api_contract(store_with_data)
        assert "schemas" in result

    def test_includes_path_params(self, store_with_data):
        result = generate_api_contract(store_with_data)
        assert "parameters" in result
        assert "id" in result

    def test_empty_store(self):
        td = tempfile.mkdtemp()
        s = SQLiteStore(Path(td) / "test.db")
        s.create_tables()
        result = generate_api_contract(s)
        assert "openapi: 3.0.3" in result
