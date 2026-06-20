"""I6: Verify SQLiteStore -> generators produce valid structured output.

Tests each of the 6 generators produces parseable YAML or Markdown output.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from uni_kb.generators.api_contract import generate_api_contract
from uni_kb.generators.auth_matrix import generate_auth_matrix
from uni_kb.generators.business_logic import generate_business_logic_doc
from uni_kb.generators.config_catalog import generate_config_catalog
from uni_kb.generators.data_model import generate_data_model
from uni_kb.generators.migration_checklist import generate_migration_checklist
from uni_kb.parsers.base import (
    ParsedClass,
    ParsedEndpoint,
    ParsedEntity,
    ParseResult,
)
from uni_kb.store.sqlite_store import SQLiteStore


@pytest.fixture
def populated_store():
    """SQLiteStore with synthetic test data."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    s = SQLiteStore(db_path)
    s.create_tables()

    result = ParseResult(
        classes=[
            ParsedClass(name="PetService", file_path="PetService.java", package="com.example", type="service"),
        ],
        endpoints=[
            ParsedEndpoint(
                path="/api/pets",
                http_method="GET",
                class_name="PetController",
                method_name="listPets",
            ),
            ParsedEndpoint(
                path="/api/pets",
                http_method="POST",
                class_name="PetController",
                method_name="createPet",
            ),
        ],
        entities=[
            ParsedEntity(
                name="Pet",
                table_name="pets",
                fields=[
                    {"name": "id", "type": "Long", "nullable": False, "primary_key": True},
                    {"name": "name", "type": "String", "nullable": False},
                    {"name": "owner_id", "type": "Long", "nullable": True},
                ],
            ),
        ],
    )
    s.ingest_parse_result(result, "test")
    yield s
    try:
        Path(db_path).unlink(missing_ok=True)
    except Exception:
        pass


class TestGenerateApiContract:
    """Verify OpenAPI 3.0 YAML generation."""

    def test_generates_valid_yaml(self, populated_store):
        output = generate_api_contract(populated_store)
        parsed = yaml.safe_load(output)
        assert isinstance(parsed, dict)
        assert parsed.get("openapi") is not None

    def test_contains_paths(self, populated_store):
        output = generate_api_contract(populated_store)
        parsed = yaml.safe_load(output)
        assert "paths" in parsed
        assert "/api/pets" in parsed["paths"]

    def test_contains_operations(self, populated_store):
        output = generate_api_contract(populated_store)
        parsed = yaml.safe_load(output)
        paths = parsed["paths"]["/api/pets"]
        assert "get" in paths or "GET" in paths
        assert "post" in paths or "POST" in paths

    def test_contains_security(self, populated_store):
        output = generate_api_contract(populated_store)
        parsed = yaml.safe_load(output)
        assert "components" in parsed or "security" in parsed


class TestGenerateBusinessLogic:
    """Verify business logic Markdown generation."""

    def test_generates_markdown(self, populated_store):
        output = generate_business_logic_doc(populated_store)
        assert output, "Expected non-empty output"
        assert isinstance(output, str)


class TestGenerateDataModel:
    """Verify data model YAML generation."""

    def test_generates_valid_yaml(self, populated_store):
        output = generate_data_model(populated_store)
        parsed = yaml.safe_load(output)
        assert isinstance(parsed, dict)


class TestGenerateAuthMatrix:
    """Verify auth matrix YAML generation."""

    def test_generates_yaml(self, populated_store):
        output = generate_auth_matrix(populated_store)
        parsed = yaml.safe_load(output)
        assert isinstance(parsed, (dict, list))


class TestGenerateConfigCatalog:
    """Verify config catalog generation."""

    def test_generates_output(self, populated_store):
        output = generate_config_catalog(str(Path(__file__).parent))
        assert isinstance(output, str)


class TestGenerateMigrationChecklist:
    """Verify migration checklist generation with CodeGraph."""

    def test_generates_markdown_with_code_graph(self, populated_store):
        from uni_kb.store.code_graph import CodeGraph
        from uni_kb.parsers.java.controller import JavaControllerParser

        graph = CodeGraph()
        controller_code = """\
package com.example;
import org.springframework.web.bind.annotation.*;
@RestController
@RequestMapping("/api/pets")
public class PetController {
    @GetMapping
    public List<Pet> list() { return null; }
    @PostMapping
    public Pet create(@RequestBody Pet pet) { return null; }
}"""
        parser = JavaControllerParser()
        result = parser.parse("PetController.java", controller_code)
        graph.build_from_parse_results([result])

        output = generate_migration_checklist(graph)
        assert isinstance(output, str)
        assert "Migration Plan" in output
