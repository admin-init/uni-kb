from __future__ import annotations

from uni_kb.parsers.base import (
    ParsedClass,
    ParsedEndpoint,
    ParsedEntity,
    ParsedMethod,
    ParsedModule,
    ParseResult,
    ParserPlugin,
)


class StubParser(ParserPlugin):
    """Minimal parser for testing ParserPlugin interface."""

    def language(self) -> str:
        return "test"

    def detect(self, file_path: str, source: str | None = None) -> bool:
        return file_path.endswith(".test")

    def parse(self, file_path: str, source: str) -> ParseResult:
        result = ParseResult()
        result.modules.append(
            ParsedModule(name="test_module", path=file_path, language="test")
        )
        return result


class TestParsedClass:
    def test_defaults(self):
        cls = ParsedClass(name="Foo", type="controller")
        assert cls.name == "Foo"
        assert cls.type == "controller"
        assert cls.annotations == []
        assert cls.file_path == ""
        assert cls.package == ""
        assert cls.modifiers == []
        assert cls.extends is None
        assert cls.implements == []

    def test_extends(self):
        cls = ParsedClass(name="Bar", type="service", extends="BaseService")
        assert cls.extends == "BaseService"

    def test_implements(self):
        cls = ParsedClass(name="Foo", type="repository", implements=["FooRepo", "JpaRepository"])
        assert cls.implements == ["FooRepo", "JpaRepository"]


class TestParsedMethod:
    def test_defaults(self):
        method = ParsedMethod(name="doStuff", class_name="MyClass")
        assert method.name == "doStuff"
        assert method.class_name == "MyClass"
        assert method.return_type == "void"
        assert method.params == []
        assert method.annotations == []
        assert method.modifiers == []
        assert method.throws == []
        assert method.body_hash == ""

    def test_with_params(self):
        method = ParsedMethod(
            name="process",
            class_name="Worker",
            params=[{"name": "id", "type": "Long"}, {"name": "data", "type": "String"}],
            return_type="Result",
        )
        assert len(method.params) == 2
        assert method.params[0]["name"] == "id"
        assert method.return_type == "Result"


class TestParsedEndpoint:
    def test_defaults(self):
        ep = ParsedEndpoint(
            http_method="GET",
            path="/api/users",
            method_name="getUser",
            class_name="UserController",
        )
        assert ep.http_method == "GET"
        assert ep.path == "/api/users"
        assert ep.auth_required is False
        assert ep.auth_permissions == []
        assert ep.request_schema is None
        assert ep.response_schema is None

    def test_with_auth(self):
        ep = ParsedEndpoint(
            http_method="POST",
            path="/api/admin",
            method_name="createAdmin",
            class_name="AdminController",
            auth_required=True,
            auth_permissions=["hasRole('ADMIN')"],
        )
        assert ep.auth_required is True
        assert "hasRole('ADMIN')" in ep.auth_permissions


class TestParsedEntity:
    def test_defaults(self):
        entity = ParsedEntity(name="User", table_name="users")
        assert entity.name == "User"
        assert entity.table_name == "users"
        assert entity.fields == []
        assert entity.annotations == []
        assert entity.package == ""
        assert entity.file_path == ""
        assert entity.primary_keys == []
        assert entity.indexes == []

    def test_with_fields(self):
        entity = ParsedEntity(
            name="Product",
            table_name="products",
            fields=[
                {"name": "id", "type": "Long", "is_primary": True},
                {"name": "price", "type": "BigDecimal", "nullable": False},
            ],
            primary_keys=["id"],
        )
        assert len(entity.fields) == 2
        assert entity.primary_keys == ["id"]
        assert entity.fields[0]["is_primary"] is True


class TestParseResult:
    def test_empty(self):
        result = ParseResult()
        assert result.modules == []
        assert result.classes == []
        assert result.methods == []
        assert result.endpoints == []
        assert result.entities == []
        assert result.imports == []
        assert result.errors == []
        assert result.warnings == []

    def test_merge(self):
        a = ParseResult(
            classes=[ParsedClass(name="Foo", type="service")],
            methods=[ParsedMethod(name="run", class_name="Foo")],
        )
        b = ParseResult(
            classes=[ParsedClass(name="Bar", type="controller")],
            endpoints=[
                ParsedEndpoint(
                    http_method="GET",
                    path="/bar",
                    method_name="getBar",
                    class_name="BarController",
                )
            ],
            errors=["Something went wrong"],
        )
        a.merge(b)
        assert len(a.classes) == 2
        assert len(a.methods) == 1
        assert len(a.endpoints) == 1
        assert len(a.errors) == 1
        assert len(a.entities) == 0
        assert a.errors[0] == "Something went wrong"

    def test_merge_returns_self(self):
        a = ParseResult()
        result = a.merge(ParseResult())
        assert result is a


class TestParserPlugin:
    def test_interface(self):
        plugin = StubParser()
        assert plugin.language() == "test"

    def test_detect(self):
        plugin = StubParser()
        assert plugin.detect("file.test") is True
        assert plugin.detect("file.java") is False

    def test_parse(self):
        plugin = StubParser()
        result = plugin.parse("/path/to/Module.test", "source content")
        assert isinstance(result, ParseResult)
        assert len(result.modules) == 1
        assert result.modules[0].name == "test_module"
