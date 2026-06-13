from __future__ import annotations

from uni_kb.parsers.nodejs.route import NodejsRouteParser


class TestNodejsRouteParser:
    def test_language(self):
        assert NodejsRouteParser().language() == "nodejs"

    def test_detect_express(self, express_source):
        parser = NodejsRouteParser()
        assert parser.detect("routes.js", express_source) is True

    def test_detect_nestjs(self, nestjs_source):
        parser = NodejsRouteParser()
        assert parser.detect("controller.ts", nestjs_source) is True

    def test_detect_non_route(self):
        parser = NodejsRouteParser()
        assert parser.detect("utils.js", "const x = 1;") is False

    def test_detect_non_js(self):
        parser = NodejsRouteParser()
        assert parser.detect("routes.java", "") is False

    def test_parse_express_extracts_endpoints(self, express_source):
        parser = NodejsRouteParser()
        result = parser.parse("routes.js", express_source)
        assert len(result.endpoints) == 4

    def test_parse_express_get_endpoint(self, express_source):
        parser = NodejsRouteParser()
        result = parser.parse("routes.js", express_source)
        get_ep = [e for e in result.endpoints if e.http_method == "GET"][0]
        assert "/api/users/:id" in get_ep.path or "/api/users/{id}" in get_ep.path

    def test_parse_express_post_endpoint(self, express_source):
        parser = NodejsRouteParser()
        result = parser.parse("routes.js", express_source)
        post_ep = [e for e in result.endpoints if e.http_method == "POST"][0]
        assert post_ep.path == "/api/users"

    def test_parse_express_class(self, express_source):
        parser = NodejsRouteParser()
        result = parser.parse("routes.js", express_source)
        assert len(result.classes) == 1
        assert result.classes[0].type == "controller"

    def test_parse_nestjs_extracts_endpoints(self, nestjs_source):
        parser = NodejsRouteParser()
        result = parser.parse("controller.ts", nestjs_source)
        assert len(result.endpoints) == 4

    def test_parse_nestjs_prefix(self, nestjs_source):
        parser = NodejsRouteParser()
        result = parser.parse("controller.ts", nestjs_source)
        for ep in result.endpoints:
            assert ep.path.startswith("/users")

    def test_parse_empty_source(self):
        parser = NodejsRouteParser()
        result = parser.parse("empty.js", "")
        assert result.endpoints == []
