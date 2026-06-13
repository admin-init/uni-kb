from __future__ import annotations

from uni_kb.parsers.nodejs.model import NodejsModelParser


class TestNodejsModelParser:
    def test_language(self):
        assert NodejsModelParser().language() == "nodejs"

    def test_detect_sequelize(self, sequelize_source):
        parser = NodejsModelParser()
        assert parser.detect("user.model.js", sequelize_source) is True

    def test_detect_typeorm(self, typeorm_source):
        parser = NodejsModelParser()
        assert parser.detect("user.entity.ts", typeorm_source) is True

    def test_detect_non_model(self):
        parser = NodejsModelParser()
        assert parser.detect("utils.js", "const x = 1;") is False

    def test_detect_non_js(self):
        parser = NodejsModelParser()
        assert parser.detect("User.java", "") is False

    def test_parse_sequelize_table_name(self, sequelize_source):
        parser = NodejsModelParser()
        result = parser.parse("user.model.js", sequelize_source)
        assert len(result.entities) == 1
        assert result.entities[0].table_name == "users"

    def test_parse_sequelize_fields(self, sequelize_source):
        parser = NodejsModelParser()
        result = parser.parse("user.model.js", sequelize_source)
        entity = result.entities[0]
        assert len(entity.fields) >= 4
        field_names = [f["name"] for f in entity.fields]
        assert "id" in field_names
        assert "username" in field_names
        assert "email" in field_names

    def test_parse_sequelize_primary_key(self, sequelize_source):
        parser = NodejsModelParser()
        result = parser.parse("user.model.js", sequelize_source)
        assert "id" in result.entities[0].primary_keys

    def test_parse_typeorm_table_name(self, typeorm_source):
        parser = NodejsModelParser()
        result = parser.parse("user.entity.ts", typeorm_source)
        assert len(result.entities) == 1
        assert result.entities[0].table_name == "users"

    def test_parse_typeorm_fields(self, typeorm_source):
        parser = NodejsModelParser()
        result = parser.parse("user.entity.ts", typeorm_source)
        entity = result.entities[0]
        assert len(entity.fields) >= 3
        field_names = [f["name"] for f in entity.fields]
        assert "id" in field_names
        assert "username" in field_names
        assert "email" in field_names

    def test_parse_empty_source(self):
        parser = NodejsModelParser()
        result = parser.parse("empty.js", "")
        assert result.entities == []
