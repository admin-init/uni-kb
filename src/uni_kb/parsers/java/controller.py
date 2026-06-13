from __future__ import annotations

from uni_kb.parsers.base import ParseResult, ParsedClass, ParsedEndpoint, ParserPlugin


class JavaControllerParser(ParserPlugin):
    HTTP_ANNOTATIONS = {
        "GetMapping": "GET",
        "PostMapping": "POST",
        "PutMapping": "PUT",
        "DeleteMapping": "DELETE",
        "PatchMapping": "PATCH",
        "RequestMapping": None,
    }

    AUTH_ANNOTATIONS = {
        "PreAuthorize",
        "PostAuthorize",
        "Secured",
        "RolesAllowed",
        "RequirePermission",
        "SaCheckPermission",
        "SaCheckRole",
    }

    def language(self) -> str:
        return "java"

    def detect(self, file_path: str, source: str | None = None) -> bool:
        if not file_path.endswith(".java"):
            return False
        if source is None:
            with open(file_path) as f:
                source = f.read()
        return any(
            keyword in source
            for keyword in (
                "@RestController",
                "@Controller",
                "@RequestMapping",
            )
        )

    def parse(self, file_path: str, source: str) -> ParseResult:
        result = ParseResult()
        package_name = self._extract_package(source)
        class_name, annotations, class_data = self._extract_class(source, file_path, package_name)

        if class_name is None:
            return result

        cls = ParsedClass(
            name=class_name,
            type="controller",
            annotations=annotations,
            file_path=file_path,
            package=package_name,
            **(class_data or {}),
        )
        result.classes.append(cls)

        endpoints = self._extract_endpoints(source, class_name)
        result.endpoints.extend(endpoints)

        return result

    def _extract_package(self, source: str) -> str:
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("package "):
                return stripped.removeprefix("package ").rstrip(";").strip()
        return ""

    def _extract_class(self, source: str, file_path: str, package: str) -> tuple[str | None, list[str], dict | None]:
        import re

        annotation_pattern = re.compile(r"@(\w+)(?:\([^)]*\))?\s*")
        class_pattern = re.compile(
            r"public\s+(abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w\s,]+))?\s*\{"
        )

        annotations: list[str] = []
        for match in annotation_pattern.finditer(source):
            annotations.append(match.group(1))

        class_match = class_pattern.search(source)
        if class_match:
            class_name = class_match.group(2)
            extends = class_match.group(3)
            implements = [i.strip() for i in class_match.group(4).split(",")] if class_match.group(4) else []
            return class_name, annotations, {"extends": extends, "implements": implements}

        return None, annotations, None

    def _extract_endpoints(self, source: str, class_name: str) -> list[ParsedEndpoint]:
        import re

        endpoints: list[ParsedEndpoint] = []
        class_annotation_pattern = re.compile(r"@RequestMapping\s*\((.*?)\)", re.DOTALL)
        method_pattern = re.compile(
            r"@(?:GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)\s*\([^)]*\)"
            r"(?:(?!\bclass\b|interface\b|enum\b).)*?"
            r"public\s+(?!class\b)(?:static\s+)?(?:\w+(?:<[^>]+>)?\s+)(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w\s,]+)?\s*\{",
            re.DOTALL,
        )

        class_prefix = ""
        class_match = class_annotation_pattern.search(source)
        if class_match:
            class_prefix = self._extract_annotation_value(class_match.group(1), "value", "path", allow_positional=True)

        for method_match in method_pattern.finditer(source):
            block_text = method_match.group(0)
            method_name = method_match.group(1)

            annotation_match = re.match(r"@(\w+)\s*\(([^)]*)\)", block_text)
            if annotation_match is None:
                continue

            annotation_name = annotation_match.group(1)
            annotation_args = annotation_match.group(2)

            http_method = self.HTTP_ANNOTATIONS.get(annotation_name)
            if http_method is None and annotation_name == "RequestMapping":
                http_method = self._extract_annotation_value(annotation_args, "method") or "GET"
            elif http_method is None:
                continue

            path = self._extract_annotation_value(annotation_args, "value", "path", allow_positional=True)
            full_path = self._join_paths(class_prefix, path)

            auth_required = self._has_auth_annotation(block_text)
            auth_permissions = self._extract_auth_values(block_text)

            produces = self._extract_annotation_value(annotation_args, "produces")
            consumes = self._extract_annotation_value(annotation_args, "consumes")

            endpoints.append(
                ParsedEndpoint(
                    http_method=http_method,
                    path=full_path,
                    method_name=method_name,
                    class_name=class_name,
                    auth_required=auth_required,
                    auth_permissions=auth_permissions,
                    produces=produces,
                    consumes=consumes,
                )
            )

        return endpoints

    def _extract_annotation_value(self, args: str, *keys: str, allow_positional: bool = False) -> str | None:
        import re

        for key in keys:
            pattern = rf'\b{key}\s*=\s*"([^"]*)"'
            match = re.search(pattern, args)
            if match:
                return match.group(1)

        if allow_positional and "=" not in args:
            match = re.search(r'"([^"]*)"', args)
            if match:
                return match.group(1)

        return None

    def _join_paths(self, prefix: str, path: str | None) -> str:
        if path is None:
            return prefix or "/"
        if prefix:
            return prefix.rstrip("/") + "/" + path.lstrip("/")
        return "/" + path.lstrip("/")

    def _has_auth_annotation(self, block: str) -> bool:
        import re

        for annotation in self.AUTH_ANNOTATIONS:
            if re.search(rf"@{annotation}\b", block):
                return True
        return False

    def _extract_auth_values(self, block: str) -> list[str]:
        import re

        permissions: list[str] = []
        patterns = [
            r'@PreAuthorize\s*\(\s*"([^"]*)"',
            r'@Secured\s*\(\s*\{?([^)}]+)\}?',
            r'@RolesAllowed\s*\(\s*\{?([^)}]+)\}?',
            r'@SaCheckPermission\s*\(\s*"([^"]*)"',
            r'@SaCheckRole\s*\(\s*"([^"]*)"',
            r'@RequirePermission\s*\(\s*"([^"]*)"',
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, block):
                permissions.extend(p.strip().strip('"') for p in match.group(1).split(","))
        return permissions
