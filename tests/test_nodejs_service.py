from __future__ import annotations

from uni_kb.parsers.nodejs.service import NodejsServiceParser


class TestNodejsServiceParser:
    def test_language(self):
        assert NodejsServiceParser().language() == "nodejs"

    def test_detect_nestjs_service(self, nestjs_service_source):
        parser = NodejsServiceParser()
        assert parser.detect("user.service.ts", nestjs_service_source) is True

    def test_detect_non_service(self):
        parser = NodejsServiceParser()
        assert parser.detect("utils.js", "const x = 1;") is False

    def test_detect_non_js(self):
        parser = NodejsServiceParser()
        assert parser.detect("service.java", "") is False

    def test_parse_extracts_class(self, nestjs_service_source):
        parser = NodejsServiceParser()
        result = parser.parse("user.service.ts", nestjs_service_source)
        assert len(result.classes) == 1
        assert result.classes[0].name == "UserService"
        assert result.classes[0].type == "service"

    def test_parse_extracts_methods(self, nestjs_service_source):
        parser = NodejsServiceParser()
        result = parser.parse("user.service.ts", nestjs_service_source)
        assert len(result.methods) >= 3
        method_names = [m.name for m in result.methods]
        assert "findById" in method_names
        assert "create" in method_names
        assert "delete" in method_names

    def test_parse_method_has_body_hash(self, nestjs_service_source):
        parser = NodejsServiceParser()
        result = parser.parse("user.service.ts", nestjs_service_source)
        for m in result.methods:
            assert len(m.body_hash) == 12

    def test_parse_extracts_imports(self, nestjs_service_source):
        parser = NodejsServiceParser()
        result = parser.parse("user.service.ts", nestjs_service_source)
        assert len(result.imports) > 0

    def test_parse_empty_source(self):
        parser = NodejsServiceParser()
        result = parser.parse("empty.js", "")
        assert result.methods == []
        assert result.classes == []
