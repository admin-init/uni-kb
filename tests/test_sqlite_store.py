from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from uni_kb.parsers.base import ParseResult, ParsedClass, ParsedEndpoint, ParsedEntity, ParsedMethod
from uni_kb.store.sqlite_store import SQLiteStore


@pytest.fixture
def store() -> SQLiteStore:
    with tempfile.TemporaryDirectory() as td:
        s = SQLiteStore(Path(td) / "test.db")
        s.create_tables()
        yield s


@pytest.fixture
def populated_store(store: SQLiteStore) -> SQLiteStore:
    result = _sample_result()
    store.ingest_parse_result(result)
    return store


def _sample_result() -> ParseResult:
    return ParseResult(
        classes=[
            ParsedClass(
                name="UserController",
                type="controller",
                annotations=["RestController", "RequestMapping"],
                file_path="/src/UserController.java",
                package="com.example.controller",
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
                annotations=["GetMapping", "PreAuthorize"],
                body_hash="abc123def456",
            ),
            ParsedMethod(
                name="findUser",
                class_name="UserService",
                params=[{"name": "id", "type": "Long"}],
                return_type="User",
                body_hash="def789abc012",
            ),
        ],
        endpoints=[
            ParsedEndpoint(
                http_method="GET",
                path="/api/users/{id}",
                method_name="getUser",
                class_name="UserController",
                auth_required=True,
                auth_permissions=["hasRole('ADMIN')"],
                consumes="application/json",
                produces="application/json",
            ),
            ParsedEndpoint(
                http_method="POST",
                path="/api/users",
                method_name="createUser",
                class_name="UserController",
                request_schema="User",
                response_schema="User",
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
                    {"name": "id", "column_name": "id", "type": "Long", "nullable": False},
                    {"name": "username", "column_name": "username", "type": "String", "nullable": False, "unique": True, "length": 50},
                    {"name": "email", "column_name": "email", "type": "String", "nullable": False, "unique": True},
                ],
            ),
        ],
    )


class TestSQLiteStore:
    def test_create_tables(self, store: SQLiteStore):
        tables = store.db.table_names()
        assert "modules" in tables
        assert "classes" in tables
        assert "methods" in tables
        assert "api_endpoints" in tables
        assert "db_tables" in tables
        assert "db_columns" in tables
        assert "auth_permissions" in tables

    def test_ingest_parse_result_adds_classes(self, populated_store: SQLiteStore):
        classes = populated_store.list_classes()
        assert len(classes) == 2
        names = [c["name"] for c in classes]
        assert "UserController" in names
        assert "UserService" in names

    def test_ingest_parse_result_adds_methods(self, populated_store: SQLiteStore):
        methods = populated_store.list_methods()
        assert len(methods) == 2
        names = [m["name"] for m in methods]
        assert "getUser" in names
        assert "findUser" in names

    def test_ingest_parse_result_adds_endpoints(self, populated_store: SQLiteStore):
        endpoints = populated_store.list_endpoints()
        assert len(endpoints) == 2

    def test_ingest_parse_result_adds_entities(self, populated_store: SQLiteStore):
        entities = populated_store.list_entities()
        assert len(entities) == 1
        assert entities[0]["name"] == "users"

    def test_ingest_parse_result_adds_columns(self, populated_store: SQLiteStore):
        columns = populated_store.list_columns()
        assert len(columns) == 3
        col_names = {c["name"] for c in columns}
        assert col_names == {"id", "username", "email"}

    def test_ingest_parse_result_adds_auth_permissions(self, populated_store: SQLiteStore):
        perms = list(populated_store.db["auth_permissions"].rows)
        assert len(perms) == 1
        assert perms[0]["permission"] == "hasRole('ADMIN')"

    def test_get_endpoint(self, populated_store: SQLiteStore):
        ep = populated_store.get_endpoint(1)
        assert ep is not None
        assert ep["http_method"] == "GET"
        assert ep["auth_required"] == 1

    def test_get_class(self, populated_store: SQLiteStore):
        cls = populated_store.get_class(1)
        assert cls is not None
        assert cls["type"] == "controller"

    def test_get_db_schema(self, populated_store: SQLiteStore):
        schema = populated_store.get_db_schema()
        assert "CREATE TABLE users" in schema
        assert "id Long" in schema or "id LONG" in schema

    def test_ingest_empty_result(self, store: SQLiteStore):
        store.ingest_parse_result(ParseResult())
        assert store.list_classes() == []

    def test_ingest_idempotent(self, store: SQLiteStore):
        cls = ParsedClass(name="TestClass", type="service", file_path="/src/Test.java", package="com.example")
        result = ParseResult(classes=[cls])
        store.ingest_parse_result(result)
        store.ingest_parse_result(result)
        classes = store.list_classes()
        assert len(classes) == 1

    def test_method_stores_params_as_json(self, populated_store: SQLiteStore):
        method = populated_store.get_method(1)
        assert method is not None
        params = json.loads(method["params"])
        assert len(params) == 1
        assert params[0]["name"] == "id"

    def test_class_stores_annotations_as_json(self, populated_store: SQLiteStore):
        cls = populated_store.get_class(1)
        assert cls is not None
        annotations = json.loads(cls["annotations"])
        assert "RestController" in annotations
