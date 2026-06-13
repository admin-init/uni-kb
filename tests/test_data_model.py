from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from uni_kb.store.sqlite_store import SQLiteStore
from uni_kb.parsers.base import ParseResult, ParsedEntity
from uni_kb.generators.data_model import generate_data_model


@pytest.fixture
def store_with_entities() -> SQLiteStore:
    td = tempfile.mkdtemp()
    s = SQLiteStore(Path(td) / "test.db")
    s.create_tables()

    result = ParseResult(
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


class TestDataModel:
    def test_generates_yaml(self, store_with_entities):
        result = generate_data_model(store_with_entities)
        assert "data_model:" in result
        assert "entities:" in result

    def test_includes_table_name(self, store_with_entities):
        result = generate_data_model(store_with_entities)
        assert "users" in result

    def test_includes_fields(self, store_with_entities):
        result = generate_data_model(store_with_entities)
        assert "username" in result
        assert "id" in result

    def test_includes_primary_key(self, store_with_entities):
        result = generate_data_model(store_with_entities)
        assert "primary_key" in result

    def test_empty_store(self):
        td = tempfile.mkdtemp()
        s = SQLiteStore(Path(td) / "test.db")
        s.create_tables()
        result = generate_data_model(s)
        assert "data_model:" in result
