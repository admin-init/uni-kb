from __future__ import annotations

from uni_kb.parsers.java.mapper import JavaMapperParser


class TestJavaMapperParser:
    def test_language(self):
        parser = JavaMapperParser()
        assert parser.language() == "java"

    def test_detect_mybatis_xml(self, mapper_xml_source):
        parser = JavaMapperParser()
        assert parser.detect("UserMapper.xml", mapper_xml_source) is True

    def test_detect_non_mybatis_xml(self):
        parser = JavaMapperParser()
        source = """<?xml version="1.0"?><root></root>"""
        assert parser.detect("config.xml", source) is False

    def test_detect_mapper_java(self, mapper_java_source):
        parser = JavaMapperParser()
        assert parser.detect("UserMapper.java", mapper_java_source) is True

    def test_detect_non_mapper_java(self):
        parser = JavaMapperParser()
        source = "public class PlainClass { }"
        assert parser.detect("Plain.java", source) is False

    def test_detect_non_java_non_xml(self):
        parser = JavaMapperParser()
        assert parser.detect("file.txt", "") is False


class TestJavaMapperParserXML:
    def test_parse_xml_select(self, mapper_xml_source):
        parser = JavaMapperParser()
        result = parser.parse("UserMapper.xml", mapper_xml_source)
        select_ep = next(ep for ep in result.endpoints if ep.method_name == "findById")
        assert select_ep.http_method == "GET"
        assert select_ep.class_name == "com.example.mapper.UserMapper"
        assert select_ep.response_schema == "com.example.entity.User"

    def test_parse_xml_insert(self, mapper_xml_source):
        parser = JavaMapperParser()
        result = parser.parse("UserMapper.xml", mapper_xml_source)
        insert_ep = next(ep for ep in result.endpoints if ep.method_name == "insert")
        assert insert_ep.http_method == "POST"
        assert insert_ep.request_schema == "com.example.entity.User"

    def test_parse_xml_update(self, mapper_xml_source):
        parser = JavaMapperParser()
        result = parser.parse("UserMapper.xml", mapper_xml_source)
        update_ep = next(ep for ep in result.endpoints if ep.method_name == "update")
        assert update_ep.http_method == "PUT"
        assert update_ep.request_schema == "com.example.entity.User"

    def test_parse_xml_delete(self, mapper_xml_source):
        parser = JavaMapperParser()
        result = parser.parse("UserMapper.xml", mapper_xml_source)
        delete_ep = next(ep for ep in result.endpoints if ep.method_name == "deleteById")
        assert delete_ep.http_method == "DELETE"

    def test_parse_xml_extracts_all_endpoints(self, mapper_xml_source):
        parser = JavaMapperParser()
        result = parser.parse("UserMapper.xml", mapper_xml_source)
        assert len(result.endpoints) == 4

    def test_parse_xml_endpoint_path(self, mapper_xml_source):
        parser = JavaMapperParser()
        result = parser.parse("UserMapper.xml", mapper_xml_source)
        paths = [ep.path for ep in result.endpoints]
        assert "/api/findById" in paths or any("findById" in p for p in paths)


class TestJavaMapperParserJavaInterface:
    def test_parse_java_interface(self, mapper_java_source):
        parser = JavaMapperParser()
        result = parser.parse("UserMapper.java", mapper_java_source)
        assert len(result.endpoints) == 4

    def test_parse_java_select(self, mapper_java_source):
        parser = JavaMapperParser()
        result = parser.parse("UserMapper.java", mapper_java_source)
        select_ep = next(ep for ep in result.endpoints if ep.method_name == "findById")
        assert select_ep.http_method == "GET"
        assert select_ep.response_schema is not None

    def test_parse_java_insert(self, mapper_java_source):
        parser = JavaMapperParser()
        result = parser.parse("UserMapper.java", mapper_java_source)
        insert_ep = next(ep for ep in result.endpoints if ep.method_name == "insert")
        assert insert_ep.http_method == "POST"

    def test_parse_java_update(self, mapper_java_source):
        parser = JavaMapperParser()
        result = parser.parse("UserMapper.java", mapper_java_source)
        update_ep = next(ep for ep in result.endpoints if ep.method_name == "update")
        assert update_ep.http_method == "PUT"

    def test_parse_java_delete(self, mapper_java_source):
        parser = JavaMapperParser()
        result = parser.parse("UserMapper.java", mapper_java_source)
        delete_ep = next(ep for ep in result.endpoints if ep.method_name == "deleteById")
        assert delete_ep.http_method == "DELETE"

    def test_parse_empty_source(self):
        parser = JavaMapperParser()
        result = parser.parse("empty.xml", "<root></root>")
        assert result.endpoints == []
