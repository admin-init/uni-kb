from __future__ import annotations

from uni_kb.parsers.java.entity import JavaEntityParser


class TestJavaEntityParser:
    def test_language(self):
        parser = JavaEntityParser()
        assert parser.language() == "java"

    def test_detect_entity(self, entity_source):
        parser = JavaEntityParser()
        assert parser.detect("User.java", entity_source) is True

    def test_detect_non_entity(self):
        parser = JavaEntityParser()
        source = "public class PlainPojo { }"
        assert parser.detect("PlainPojo.java", source) is False

    def test_detect_non_java(self):
        parser = JavaEntityParser()
        assert parser.detect("model.ts", "") is False

    def test_parse_extracts_table_name(self, entity_source):
        parser = JavaEntityParser()
        result = parser.parse("User.java", entity_source)
        assert len(result.entities) == 1
        entity = result.entities[0]
        assert entity.name == "User"
        assert entity.table_name == "users"

    def test_parse_extracts_package(self, entity_source):
        parser = JavaEntityParser()
        result = parser.parse("User.java", entity_source)
        entity = result.entities[0]
        assert entity.package == "com.example.entity"

    def test_parse_extracts_fields(self, entity_source):
        parser = JavaEntityParser()
        result = parser.parse("User.java", entity_source)
        entity = result.entities[0]
        field_names = [f["name"] for f in entity.fields]
        assert "id" in field_names
        assert "username" in field_names
        assert "email" in field_names
        assert "department" in field_names

    def test_parse_skips_transient_field(self, entity_source):
        parser = JavaEntityParser()
        result = parser.parse("User.java", entity_source)
        entity = result.entities[0]
        field_names = [f["name"] for f in entity.fields]
        assert "tempField" not in field_names

    def test_parse_primary_key(self, entity_source):
        parser = JavaEntityParser()
        result = parser.parse("User.java", entity_source)
        entity = result.entities[0]
        assert "id" in entity.primary_keys
        id_field = next(f for f in entity.fields if f["name"] == "id")
        assert id_field["is_primary"] is True

    def test_parse_column_constraints(self, entity_source):
        parser = JavaEntityParser()
        result = parser.parse("User.java", entity_source)
        entity = result.entities[0]
        username_field = next(f for f in entity.fields if f["name"] == "username")
        assert username_field["nullable"] is False
        assert username_field["unique"] is True
        assert username_field["length"] == 50

    def test_parse_relationship_field(self, entity_source):
        parser = JavaEntityParser()
        result = parser.parse("User.java", entity_source)
        entity = result.entities[0]
        dept_field = next(f for f in entity.fields if f["name"] == "department")
        assert dept_field["relationship"] == "ManyToOne"

    def test_parse_table_indexes(self, entity_source):
        parser = JavaEntityParser()
        result = parser.parse("User.java", entity_source)
        entity = result.entities[0]
        assert len(entity.indexes) >= 1
        idx = entity.indexes[0]
        assert idx["name"] == "idx_email"
        assert idx["unique"] is True
        assert "email" in idx["columns"]

    def test_parse_empty_source(self):
        parser = JavaEntityParser()
        result = parser.parse("Empty.java", "")
        assert result.entities == []

    def test_camel_to_snake(self):
        parser = JavaEntityParser()
        assert parser._camel_to_snake("UserProfile") == "user_profile"
        assert parser._camel_to_snake("ID") == "id"

    def test_table_name_fallback(self):
        source = """\
package com.example;
import javax.persistence.Entity;
@Entity
public class OrderItem {
    private Long id;
}
"""
        parser = JavaEntityParser()
        result = parser.parse("OrderItem.java", source)
        assert result.entities[0].table_name == "order_item"
