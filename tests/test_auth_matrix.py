from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from uni_kb.store.sqlite_store import SQLiteStore
from uni_kb.parsers.base import ParseResult, ParsedEndpoint
from uni_kb.generators.auth_matrix import generate_auth_matrix


@pytest.fixture
def store_with_auth() -> SQLiteStore:
    td = tempfile.mkdtemp()
    s = SQLiteStore(Path(td) / "test.db")
    s.create_tables()

    result = ParseResult(
        endpoints=[
            ParsedEndpoint(http_method="GET", path="/api/users/{id}", method_name="getUser", class_name="UserController", auth_required=True, auth_permissions=["hasRole('ADMIN')"]),
            ParsedEndpoint(http_method="POST", path="/api/users", method_name="createUser", class_name="UserController", auth_required=False),
        ],
    )
    s.ingest_parse_result(result)
    return s


class TestAuthMatrix:
    def test_generates_yaml(self, store_with_auth):
        result = generate_auth_matrix(store_with_auth)
        assert "auth_matrix:" in result
        assert "endpoints:" in result

    def test_includes_auth_info(self, store_with_auth):
        result = generate_auth_matrix(store_with_auth)
        assert "auth_required" in result
        assert "true" in result

    def test_includes_permissions(self, store_with_auth):
        result = generate_auth_matrix(store_with_auth)
        assert "hasRole" in result

    def test_empty_store(self):
        td = tempfile.mkdtemp()
        s = SQLiteStore(Path(td) / "test.db")
        s.create_tables()
        result = generate_auth_matrix(s)
        assert "auth_matrix:" in result
