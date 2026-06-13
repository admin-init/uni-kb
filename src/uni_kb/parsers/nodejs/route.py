from __future__ import annotations

import re
from pathlib import Path

from uni_kb.parsers.base import ParseResult, ParsedClass, ParsedEndpoint, ParserPlugin

HTTP_METHOD_MAP = {
    "get": "GET",
    "post": "POST",
    "put": "PUT",
    "patch": "PATCH",
    "delete": "DELETE",
}


class NodejsRouteParser(ParserPlugin):
    def language(self) -> str:
        return "nodejs"

    def detect(self, file_path: str, source: str | None = None) -> bool:
        if not file_path.endswith((".js", ".ts")):
            return False
        if source is None:
            source = Path(file_path).read_text(encoding="utf-8")
        has_express = bool(re.search(r"(?:router|app)\s*\.\s*(?:get|post|put|patch|delete)\s*\(", source))
        has_nestjs = bool(re.search(r"@(?:Get|Post|Put|Patch|Delete|Controller)\s*\(", source))
        return has_express or has_nestjs

    def parse(self, file_path: str, source: str) -> ParseResult:
        result = ParseResult()
        if re.search(r"@(?:Get|Post|Put|Patch|Delete|Controller)\s*\(", source):
            result.merge(self._parse_nestjs(file_path, source))
        else:
            result.merge(self._parse_express(file_path, source))
        return result

    def _parse_express(self, file_path: str, source: str) -> ParseResult:
        class_name = Path(file_path).stem
        class_name = _pascal_case(class_name)
        prefix = self._extract_express_prefix(source)
        endpoints: list[ParsedEndpoint] = []

        pattern = re.compile(
            r"(?:router|app)\s*\.\s*(get|post|put|patch|delete)\s*\(\s*"
            r"""(?:'([^']*)'|"([^"]*)"|`([^`]*)`)""",
            re.IGNORECASE,
        )
        for match in pattern.finditer(source):
            verb = match.group(1).lower()
            path_str = match.group(2) or match.group(3) or match.group(4) or ""
            full_path = _join_paths(prefix, path_str)
            auth_block = self._slice_method_context(source, match.start())
            auth_required, auth_perms = self._extract_auth(auth_block)

            endpoints.append(ParsedEndpoint(
                http_method=HTTP_METHOD_MAP.get(verb, "GET"),
                path=full_path,
                method_name=_method_name(verb, path_str),
                class_name=class_name,
                auth_required=auth_required,
                auth_permissions=auth_perms,
            ))

        return ParseResult(
            classes=[ParsedClass(
                name=class_name, type="controller",
                file_path=file_path, annotations=["Express"],
            )],
            endpoints=endpoints,
        )

    def _parse_nestjs(self, file_path: str, source: str) -> ParseResult:
        class_name = _extract_nest_class(source)
        prefix = _extract_nest_prefix(source)
        endpoints: list[ParsedEndpoint] = []

        pattern = re.compile(
            r"@(Get|Post|Put|Patch|Delete)\s*\((?:['\"]([^'\"]*)['\"])?\)\s*"
            r"(?:async\s+)?(\w+)\s*\([^)]*\)",
            re.IGNORECASE,
        )
        for match in pattern.finditer(source):
            http_method = HTTP_METHOD_MAP.get(match.group(1).lower(), "GET")
            path_str = match.group(2) or ""
            method_name = match.group(3)
            full_path = _join_paths(prefix, path_str)
            endpoints.append(ParsedEndpoint(
                http_method=http_method, path=full_path,
                method_name=method_name, class_name=class_name,
            ))

        return ParseResult(
            classes=[ParsedClass(
                name=class_name, type="controller",
                file_path=file_path, annotations=["NestJS"],
            )],
            endpoints=endpoints,
        )

    def _extract_express_prefix(self, source: str) -> str:
        m = re.search(r"""(?:router|app)\s*\.\s*use\s*\(\s*(?:['"]([^'"]*)['"])""", source)
        return m.group(1) if m else ""

    def _slice_method_context(self, source: str, start: int) -> str:
        return source[max(0, start - 300):start + 500]

    def _extract_auth(self, block: str) -> tuple[bool, list[str]]:
        auth_required = False
        perms: list[str] = []
        if re.search(r"(?:auth|authenticate|verifyToken|requireAuth|passport)", block, re.IGNORECASE):
            auth_required = True
        for m in re.finditer(r"(?:hasRole|hasPermission|requireRole)\s*\(\s*['\"]([^'\"]+)['\"]", block):
            perms.append(m.group(1))
        return auth_required, perms


def _extract_nest_class(source: str) -> str:
    m = re.search(r"export\s+class\s+(\w+)", source)
    return m.group(1) if m else "UnknownController"


def _extract_nest_prefix(source: str) -> str:
    m = re.search(r"@Controller\s*\(\s*['\"]([^'\"]*)['\"]", source)
    return m.group(1) if m else ""


def _join_paths(prefix: str, path: str) -> str:
    if not path:
        path = ""
    if not prefix:
        return f"/{path.strip('/')}"
    result = f"/{prefix.strip('/')}/{path.strip('/')}"
    return result.rstrip("/") or "/"


def _pascal_case(s: str) -> str:
    parts = re.split(r"[-_.]", s)
    return "".join(p.capitalize() for p in parts)


def _method_name(verb: str, path: str) -> str:
    stem = path.strip("/").replace("/", "_").replace("-", "_").replace("{", "").replace("}", "")
    if stem:
        return f"{verb}_{stem}"
    return verb
