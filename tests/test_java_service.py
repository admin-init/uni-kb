from __future__ import annotations

from uni_kb.parsers.java.service import JavaServiceParser


class TestJavaServiceParser:
    def test_language(self):
        parser = JavaServiceParser()
        assert parser.language() == "java"

    def test_detect_service(self, service_source):
        parser = JavaServiceParser()
        assert parser.detect("UserService.java", service_source) is True

    def test_detect_non_service(self):
        parser = JavaServiceParser()
        source = "public class PlainPojo { }"
        assert parser.detect("PlainPojo.java", source) is False

    def test_detect_non_java(self):
        parser = JavaServiceParser()
        assert parser.detect("service.ts", "") is False

    def test_parse_extracts_class(self, service_source):
        parser = JavaServiceParser()
        result = parser.parse("UserService.java", service_source)
        assert len(result.classes) == 1
        cls = result.classes[0]
        assert cls.name == "UserService"
        assert cls.type == "service"
        assert cls.package == "com.example.service"
        assert "Service" in cls.annotations

    def test_parse_extracts_methods(self, service_source):
        parser = JavaServiceParser()
        result = parser.parse("UserService.java", service_source)
        assert len(result.methods) >= 3
        method_names = [m.name for m in result.methods]
        assert "findById" in method_names
        assert "create" in method_names
        assert "delete" in method_names

    def test_parse_method_params_and_return(self, service_source):
        parser = JavaServiceParser()
        result = parser.parse("UserService.java", service_source)
        find_method = next(m for m in result.methods if m.name == "findById")
        assert len(find_method.params) == 1
        assert find_method.params[0]["name"] == "id"
        assert find_method.return_type != "void"

    def test_parse_method_has_body_hash(self, service_source):
        parser = JavaServiceParser()
        result = parser.parse("UserService.java", service_source)
        method = next(m for m in result.methods if m.name == "create")
        assert len(method.body_hash) == 12

    def test_parse_extracts_imports(self, service_source):
        parser = JavaServiceParser()
        result = parser.parse("UserService.java", service_source)
        qualified_names = [imp["qualified_name"] for imp in result.imports]
        assert any("UserRepository" in qn for qn in qualified_names)
        assert any("Service" in qn for qn in qualified_names)

    def test_parse_empty_source(self):
        parser = JavaServiceParser()
        result = parser.parse("Empty.java", "")
        assert result.classes == []
        assert result.methods == []
