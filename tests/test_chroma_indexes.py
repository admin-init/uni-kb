from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from uni_kb.store.chroma_indexes import ChromaIndexes, COLLECTION_NAMES
from uni_kb.parsers.base import ParseResult, ParsedClass, ParsedEndpoint, ParsedEntity


@pytest.fixture
def chroma() -> ChromaIndexes:
    with tempfile.TemporaryDirectory() as td:
        c = ChromaIndexes(Path(td) / "chroma")
        yield c


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
        endpoints=[
            ParsedEndpoint(
                http_method="GET",
                path="/api/users/{id}",
                method_name="getUser",
                class_name="UserController",
                auth_required=True,
                auth_permissions=["hasRole('ADMIN')"],
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
                    {"name": "id", "column_name": "id", "type": "Long"},
                    {"name": "username", "column_name": "username", "type": "String"},
                ],
            ),
        ],
    )


class TestChromaIndexes:
    def test_ensure_all_creates_collections(self, chroma: ChromaIndexes):
        chroma.ensure_all()
        colls = chroma.get_all_collections()
        assert len(colls) == len(COLLECTION_NAMES)

    def test_search_empty_collection(self, chroma: ChromaIndexes):
        chroma.ensure_all()
        results = chroma.search("code_java_controller", "test")
        assert results == []

    def test_count_empty_collection(self, chroma: ChromaIndexes):
        chroma.ensure_all()
        assert chroma.count("code_java_controller") == 0

    def test_index_code_controller(self, chroma: ChromaIndexes):
        result = _sample_result()
        chroma.index_code(result, "source")
        assert chroma.count("code_java_controller") > 0

    def test_index_code_service(self, chroma: ChromaIndexes):
        result = _sample_result()
        chroma.index_code(result, "source")
        assert chroma.count("code_java_service") > 0

    def test_index_code_entity(self, chroma: ChromaIndexes):
        result = _sample_result()
        chroma.index_code(result, "source")
        assert chroma.count("code_java_entity") > 0

    def test_search_returns_results(self, chroma: ChromaIndexes):
        result = _sample_result()
        chroma.index_code(result, "source")
        docs = chroma.search("code_java_controller", "UserController")
        assert len(docs) > 0

    def test_index_db_schema(self, chroma: ChromaIndexes):
        chroma.ensure_all()
        chroma.index_db_schema("CREATE TABLE users (id INT PRIMARY KEY);")
        assert chroma.count("db_schema") > 0

    def test_index_empty_schema(self, chroma: ChromaIndexes):
        chroma.ensure_all()
        chroma.index_db_schema("")
        assert chroma.count("db_schema") == 0

    def test_index_code_empty_result(self, chroma: ChromaIndexes):
        chroma.index_code(ParseResult(), "")
        assert chroma.count("code_java_controller") == 0
        assert chroma.count("code_java_entity") == 0
