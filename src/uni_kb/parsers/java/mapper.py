from __future__ import annotations

from uni_kb.parsers.base import ParseResult, ParsedEndpoint, ParserPlugin


class JavaMapperParser(ParserPlugin):
    NAMESPACE_TAG_PREFIX = "{http://mybatis.org/dtd/mapper}"
    MYBATIS_NAMESPACES = (
        "http://mybatis.org/dtd/mapper",
        "http://mybatis.org/schema/mapper",
    )

    SQL_OPERATIONS = {
        "select": "GET",
        "insert": "POST",
        "update": "PUT",
        "delete": "DELETE",
    }

    def language(self) -> str:
        return "java"

    def detect(self, file_path: str, source: str | None = None) -> bool:
        if file_path.endswith(".xml"):
            if source is None:
                with open(file_path) as f:
                    source = f.read()
            return any(ns in source for ns in self.MYBATIS_NAMESPACES)
        if file_path.endswith(".java"):
            if source is None:
                with open(file_path) as f:
                    source = f.read()
            return "@Mapper" in source or "@Repository" in source
        return False

    def parse(self, file_path: str, source: str) -> ParseResult:
        if file_path.endswith(".xml"):
            return self._parse_xml(file_path, source)
        return self._parse_java_interface(file_path, source)

    def _parse_xml(self, file_path: str, source: str) -> ParseResult:
        import re

        result = ParseResult()

        ns_match = re.search(r'namespace\s*=\s*"([^"]*)"', source)
        namespace = ns_match.group(1) if ns_match else ""

        tag_pattern = re.compile(
            r"<(select|insert|update|delete)\s+"
            r'id\s*=\s*"([^"]*)"'
            r'(?:\s+resultType\s*=\s*"([^"]*)")?'
            r'(?:\s+resultMap\s*=\s*"([^"]*)")?'
            r'(?:\s+parameterType\s*=\s*"([^"]*)")?'
            r"(.*?)>",
            re.DOTALL,
        )

        for match in tag_pattern.finditer(source):
            tag_name = match.group(1)
            method_id = match.group(2)
            result_type = match.group(3)
            result_map = match.group(4) or ""
            parameter_type = match.group(5) or ""

            param_blocks = re.findall(r"#\{(\w+)[,\s]*([^}]*)?\}", source[match.start() : match.end()])
            params: list[dict[str, str]] = []
            for param_name, param_extra in param_blocks:
                param_info = {"name": param_name}
                if param_extra:
                    for part in param_extra.split(","):
                        part = part.strip()
                        if "=" in part:
                            k, v = part.split("=", 1)
                            param_info[k.strip()] = v.strip()
                params.append(param_info)

            http_method = self.SQL_OPERATIONS.get(tag_name, "POST")

            endpoint_path = "/api/" + method_id.replace("_", "/")
            auth_annotations = self._find_auth_in_comments(source, match.start(), match.end())

            endpoint = ParsedEndpoint(
                http_method=http_method,
                path=endpoint_path,
                method_name=method_id,
                class_name=namespace,
                request_schema=parameter_type,
                response_schema=result_type or result_map,
                auth_required=len(auth_annotations) > 0,
                auth_permissions=auth_annotations,
            )
            result.endpoints.append(endpoint)

        return result

    def _parse_java_interface(self, file_path: str, source: str) -> ParseResult:
        import re

        result = ParseResult()

        class_match = re.search(r"public\s+interface\s+(\w+)", source)
        if class_match is None:
            return result

        class_name = class_match.group(1)

        method_pattern = re.compile(
            r"(\w+(?:<[^>]+>)?)\s+(\w+)\s*\(([^)]*)\)\s*;",
        )

        annotation_pattern = re.compile(r"@(\w+)")

        interface_match = re.search(r"interface\s+\w+\s*\{", source)
        prev_end = interface_match.end() if interface_match else 0

        for match in method_pattern.finditer(source):
            return_type = match.group(1)
            method_name = match.group(2)

            preceding = source[prev_end : match.start()]
            prev_end = match.end()

            annotations_list: list[str] = []
            for ann_match in annotation_pattern.finditer(preceding):
                annotations_list.append(ann_match.group(1))

            http_method = "GET"
            if "Insert" in annotations_list:
                http_method = "POST"
            elif "Update" in annotations_list:
                http_method = "PUT"
            elif "Delete" in annotations_list:
                http_method = "DELETE"
            elif "Select" in annotations_list:
                http_method = "GET"

            endpoint = ParsedEndpoint(
                http_method=http_method,
                path="/api/" + method_name.replace("_", "/"),
                method_name=method_name,
                class_name=class_name,
                response_schema=return_type,
                auth_required=False,
            )
            result.endpoints.append(endpoint)

        return result

    def _find_auth_in_comments(self, source: str, start: int, end: int) -> list[str]:
        import re

        context = source[max(0, start - 500) : end]
        permissions: list[str] = []
        auth_patterns = [
            r'@PreAuthorize\s*\(\s*"([^"]*)"',
            r'@SaCheckPermission\s*\(\s*"([^"]*)"',
            r'@SaCheckRole\s*\(\s*"([^"]*)"',
        ]
        for pattern in auth_patterns:
            for match in re.finditer(pattern, context):
                permissions.append(match.group(1))
        return permissions
