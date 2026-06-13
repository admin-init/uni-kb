from __future__ import annotations

import hashlib
import re
from pathlib import Path

from uni_kb.parsers.base import ParseResult, ParsedClass, ParsedMethod, ParserPlugin


class NodejsServiceParser(ParserPlugin):
    def language(self) -> str:
        return "nodejs"

    def detect(self, file_path: str, source: str | None = None) -> bool:
        if not file_path.endswith((".js", ".ts")):
            return False
        if source is None:
            source = Path(file_path).read_text(encoding="utf-8")
        has_class = bool(re.search(r"class\s+\w+", source))
        has_injectable = bool(re.search(r"@Injectable\s*\(", source))
        has_export = bool(re.search(r"module\.exports|export\s+(?:default\s+)?(?:class|function)", source))
        return (has_class or has_export) and has_injectable

    def parse(self, file_path: str, source: str) -> ParseResult:
        if not source.strip():
            return ParseResult()

        class_name = _extract_class_name(source, file_path)
        class_type = "service"
        annotations: list[str] = []
        if re.search(r"@Injectable", source):
            annotations.append("Injectable")
        if re.search(r"@Module", source):
            class_type = "configuration"
            annotations.append("Module")

        methods = self._extract_methods(source, class_name)
        imports = self._extract_imports(source)

        return ParseResult(
            classes=[ParsedClass(
                name=class_name, type=class_type,
                annotations=annotations, file_path=file_path,
            )],
            methods=methods,
            imports=imports,
        )

    def _extract_methods(self, source: str, class_name: str) -> list[ParsedMethod]:
        methods: list[ParsedMethod] = []
        pattern = re.compile(
            r"(?:@\w+\s*\([^)]*\)\s*)*"
            r"(?:async\s+)?(\w+)\s*\(([^)]*)\)\s*(?::\s*[\w<>\[\],\s]+)?\s*\{",
            re.MULTILINE,
        )
        for match in pattern.finditer(source):
            name = match.group(1)
            if name in ("constructor", "if", "for", "while", "switch", "catch"):
                continue
            params = self._parse_params(match.group(2))
            body_hash = hashlib.sha256(source[match.start():match.end()].encode()).hexdigest()[:12]
            methods.append(ParsedMethod(
                name=name, class_name=class_name,
                params=params, body_hash=body_hash,
            ))
        return methods

    def _parse_params(self, raw: str) -> list[dict[str, str]]:
        if not raw.strip():
            return []
        params: list[dict[str, str]] = []
        for param in _split_top_level(raw, ","):
            param = param.strip()
            type_name = "any"
            if ":" in param:
                parts = param.split(":", 1)
                param_name = parts[0].strip()
                type_str = parts[1].strip()
                type_m = re.match(r"\s*(\w+)", type_str)
                if type_m:
                    type_name = type_m.group(1)
            else:
                param_name = param.strip()
            if param_name:
                params.append({"name": param_name, "type": type_name})
        return params

    def _extract_imports(self, source: str) -> list[dict[str, str]]:
        imports: list[dict[str, str]] = []
        for m in re.finditer(
            r"""(?:import\s+(?:\{[^}]*\}|\w+)\s+from\s+['"]([^'"]+)['"])|"""
            r"""(?:require\s*\(\s*['"]([^'"]+)['"]\s*\))""",
            source,
        ):
            module_path = m.group(1) or m.group(2)
            imports.append({"qualified_name": module_path})
        return imports


def _extract_class_name(source: str, file_path: str) -> str:
    m = re.search(r"(?:export\s+)?class\s+(\w+)", source)
    if m:
        return m.group(1)
    return Path(file_path).stem


def _split_top_level(text: str, delimiter: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in text:
        if ch in "([{<":
            depth += 1
        elif ch in ")]}>":
            depth -= 1
        if ch == delimiter and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())
    return parts
