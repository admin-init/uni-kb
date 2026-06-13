from __future__ import annotations

from uni_kb.parsers.nodejs.middleware import NodejsMiddlewareParser


class TestNodejsMiddlewareParser:
    def test_language(self):
        assert NodejsMiddlewareParser().language() == "nodejs"

    def test_detect_auth_middleware(self, middleware_source):
        parser = NodejsMiddlewareParser()
        assert parser.detect("auth.js", middleware_source) is True

    def test_detect_non_middleware(self):
        parser = NodejsMiddlewareParser()
        assert parser.detect("utils.js", "const x = 1;") is False

    def test_detect_non_js(self):
        parser = NodejsMiddlewareParser()
        assert parser.detect("auth.java", "") is False

    def test_parse_extracts_class(self, middleware_source):
        parser = NodejsMiddlewareParser()
        result = parser.parse("auth.js", middleware_source)
        assert len(result.classes) == 1
        assert result.classes[0].type == "component"

    def test_parse_extracts_methods(self, middleware_source):
        parser = NodejsMiddlewareParser()
        result = parser.parse("auth.js", middleware_source)
        assert len(result.methods) >= 1

    def test_parse_auth_type(self, middleware_source):
        parser = NodejsMiddlewareParser()
        result = parser.parse("auth.js", middleware_source)
        assert result.classes[0].annotations
        auth_type = result.classes[0].annotations[0]
        assert auth_type in ("JWT", "CustomAuth")

    def test_parse_empty_source(self):
        parser = NodejsMiddlewareParser()
        result = parser.parse("empty.js", "")
        assert result.classes == []
