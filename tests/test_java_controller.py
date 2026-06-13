from __future__ import annotations

from uni_kb.parsers.java.controller import JavaControllerParser


class TestJavaControllerParser:
    def test_language(self):
        parser = JavaControllerParser()
        assert parser.language() == "java"

    def test_detect_controller_file(self, controller_source):
        parser = JavaControllerParser()
        assert parser.detect("UserController.java", controller_source) is True

    def test_detect_non_controller(self):
        parser = JavaControllerParser()
        source = "public class PlainPojo { }"
        assert parser.detect("PlainPojo.java", source) is False

    def test_detect_non_java_file(self):
        parser = JavaControllerParser()
        assert parser.detect("controller.ts", "") is False

    def test_parse_class_name_and_package(self, controller_source):
        parser = JavaControllerParser()
        result = parser.parse("UserController.java", controller_source)
        assert len(result.classes) == 1
        cls = result.classes[0]
        assert cls.name == "UserController"
        assert cls.type == "controller"
        assert cls.package == "com.example.controller"
        assert "RestController" in cls.annotations

    def test_parse_extracts_endpoints(self, controller_source):
        parser = JavaControllerParser()
        result = parser.parse("UserController.java", controller_source)
        endpoints = result.endpoints
        assert len(endpoints) == 4

    def test_parse_get_endpoint(self, controller_source):
        parser = JavaControllerParser()
        result = parser.parse("UserController.java", controller_source)
        get_endpoint = next(ep for ep in result.endpoints if ep.http_method == "GET")
        assert get_endpoint.path == "/api/users/{id}"
        assert get_endpoint.method_name == "getUser"
        assert get_endpoint.auth_required is True
        assert "hasRole('ADMIN')" in get_endpoint.auth_permissions

    def test_parse_post_endpoint(self, controller_source):
        parser = JavaControllerParser()
        result = parser.parse("UserController.java", controller_source)
        post_endpoint = next(ep for ep in result.endpoints if ep.http_method == "POST")
        assert post_endpoint.path == "/api/users"
        assert post_endpoint.method_name == "createUser"
        assert post_endpoint.consumes == "application/json"
        assert post_endpoint.produces == "application/json"

    def test_parse_delete_endpoint_no_auth(self, controller_source):
        parser = JavaControllerParser()
        result = parser.parse("UserController.java", controller_source)
        delete_endpoint = next(ep for ep in result.endpoints if ep.http_method == "DELETE")
        assert delete_endpoint.method_name == "deleteUser"
        assert delete_endpoint.auth_required is False
        assert delete_endpoint.auth_permissions == []

    def test_parse_put_endpoint_multiple_roles(self, controller_source):
        parser = JavaControllerParser()
        result = parser.parse("UserController.java", controller_source)
        put_endpoint = next(ep for ep in result.endpoints if ep.http_method == "PUT")
        assert put_endpoint.auth_required is True
        assert len(put_endpoint.auth_permissions) == 1
        assert "hasRole('ADMIN') or hasRole('MANAGER')" in put_endpoint.auth_permissions

    def test_parse_empty_source(self):
        parser = JavaControllerParser()
        result = parser.parse("Empty.java", "")
        assert result.classes == []
        assert result.endpoints == []
