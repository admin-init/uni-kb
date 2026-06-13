from __future__ import annotations

from uni_kb.parsers.base import ParseResult, ParsedClass, ParsedMethod, ParserPlugin


class JavaServiceParser(ParserPlugin):
    def language(self) -> str:
        return "java"

    def detect(self, file_path: str, source: str | None = None) -> bool:
        if not file_path.endswith(".java"):
            return False
        if source is None:
            with open(file_path) as f:
                source = f.read()
        return "@Service" in source or "@Component" in source or "@Repository" in source

    def parse(self, file_path: str, source: str) -> ParseResult:
        import re

        result = ParseResult()
        package_name = self._extract_package(source)

        annotation_pattern = re.compile(r"@(\w+)(?:\([^)]*\))?\s*")
        annotations = [m.group(1) for m in annotation_pattern.finditer(source)]

        class_type = "service"
        if "@Repository" in annotations:
            class_type = "repository"
        elif "@Component" in annotations:
            class_type = "component"

        class_pattern = re.compile(
            r"public\s+(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w\s,]+))?\s*\{",
            re.DOTALL,
        )
        class_match = class_pattern.search(source)
        if class_match is None:
            return result

        class_name = class_match.group(1)
        extends = class_match.group(2)
        implements = [i.strip() for i in class_match.group(3).split(",")] if class_match.group(3) else []

        cls = ParsedClass(
            name=class_name,
            type=class_type,
            annotations=annotations,
            file_path=file_path,
            package=package_name,
            extends=extends,
            implements=implements,
        )
        result.classes.append(cls)

        methods = self._extract_methods(source, class_name)
        result.methods.extend(methods)

        header = source[:class_match.start()]
        result.imports.extend(self._extract_imports(header))

        return result

    def _extract_package(self, source: str) -> str:
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("package "):
                return stripped.removeprefix("package ").rstrip(";").strip()
        return ""

    def _extract_imports(self, header: str) -> list[dict[str, str]]:
        import re

        imports: list[dict[str, str]] = []
        for match in re.finditer(r"import\s+(static\s+)?([\w.]+)(?:\.\*)?\s*;", header):
            is_static = match.group(1) is not None
            fqdn = match.group(2)
            imports.append({"qualified_name": fqdn, "static": is_static})
        return imports

    def _extract_methods(self, source: str, class_name: str) -> list[ParsedMethod]:
        import hashlib
        import re

        methods: list[ParsedMethod] = []

        method_pattern = re.compile(
            r"(@[\w]+(?:\([^)]*\))?\s*)*"
            r"(public|protected|private|)\s*"
            r"(static\s+)?"
            r"(?:\w+(?:<[^>]+>)?\s+)"
            r"(\w+)\s*"
            r"\((.*?)\)\s*"
            r"(?:throws\s+([\w\s,]+))?\s*"
            r"\{",
            re.DOTALL,
        )

        annotation_pattern = re.compile(r"@(\w+)(?:\(([^)]*)\))?")

        for match in method_pattern.finditer(source):
            full_match = match.group(0)
            method_name = match.group(4)
            raw_params = match.group(5) or ""

            ann_matches = annotation_pattern.findall(full_match)
            annotations_list = [a[0] for a in ann_matches]

            params = self._parse_params(raw_params)

            return_type = ""
            ret_parts = match.group(0).split(method_name)[0].split()
            if len(ret_parts) >= 2:
                return_type = ret_parts[-1]

            body_hash = hashlib.sha256(full_match.encode()).hexdigest()[:12]

            throws: list[str] = []
            if match.group(6):
                throws = [t.strip() for t in match.group(6).split(",")]

            method = ParsedMethod(
                name=method_name,
                class_name=class_name,
                params=params,
                return_type=return_type,
                annotations=annotations_list,
                modifiers=self._parse_modifiers(full_match),
                throws=throws,
                body_hash=body_hash,
            )
            methods.append(method)

        return methods

    def _parse_params(self, raw: str) -> list[dict[str, str]]:
        params: list[dict[str, str]] = []
        if not raw.strip():
            return params

        for param in self._split_params(raw):
            param = param.strip()
            parts = param.rsplit(None, 1)
            if len(parts) == 2:
                params.append({"name": parts[1], "type": parts[0]})
            elif len(parts) == 1:
                params.append({"name": parts[0], "type": "var"})

        return params

    def _split_params(self, raw: str) -> list[str]:
        result: list[str] = []
        depth = 0
        current: list[str] = []
        for ch in raw:
            if ch == "<":
                depth += 1
            elif ch == ">":
                depth -= 1
            elif ch == "," and depth == 0:
                result.append("".join(current))
                current = []
                continue
            current.append(ch)
        if current:
            result.append("".join(current))
        return result

    def _parse_modifiers(self, method_header: str) -> list[str]:
        import re

        modifiers: list[str] = []
        for mod in ("public", "protected", "private", "static", "final", "abstract", "synchronized"):
            if re.search(rf"\b{mod}\b", method_header):
                modifiers.append(mod)
        return modifiers
