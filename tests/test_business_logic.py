from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from uni_kb.store.sqlite_store import SQLiteStore
from uni_kb.parsers.base import ParseResult, ParsedClass, ParsedMethod
from uni_kb.generators.business_logic import generate_business_logic_doc


@pytest.fixture
def store_with_methods() -> SQLiteStore:
    td = tempfile.mkdtemp()
    s = SQLiteStore(Path(td) / "test.db")
    s.create_tables()

    result = ParseResult(
        classes=[ParsedClass(name="UserService", type="service", package="com.example.service", file_path="/src/UserService.java", annotations=["Service", "Transactional"])],
        methods=[
            ParsedMethod(name="findUser", class_name="UserService", params=[{"name": "id", "type": "Long"}], return_type="User", body_hash="abc123"),
            ParsedMethod(name="createUser", class_name="UserService", params=[{"name": "user", "type": "User"}], return_type="User", body_hash="def456"),
        ],
    )
    s.ingest_parse_result(result)
    return s


class TestBusinessLogic:
    def test_generates_markdown(self, store_with_methods):
        result = generate_business_logic_doc(store_with_methods)
        assert "# Business Logic Documentation" in result
        assert "## UserService" in result

    def test_includes_method_names(self, store_with_methods):
        result = generate_business_logic_doc(store_with_methods)
        assert "findUser" in result
        assert "createUser" in result

    def test_includes_body_hashes(self, store_with_methods):
        result = generate_business_logic_doc(store_with_methods)
        assert "abc123" in result
        assert "def456" in result

    def test_includes_return_types(self, store_with_methods):
        result = generate_business_logic_doc(store_with_methods)
        assert "User" in result

    def test_empty_store(self):
        td = tempfile.mkdtemp()
        s = SQLiteStore(Path(td) / "test.db")
        s.create_tables()
        result = generate_business_logic_doc(s)
        assert "# Business Logic Documentation" in result
