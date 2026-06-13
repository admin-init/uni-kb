from __future__ import annotations

import re
from pathlib import Path

from uni_kb.parsers.base import ParseResult, ParsedClass, ParsedMethod, ParserPlugin


class NodejsMiddlewareParser(ParserPlugin):
    def language(self) -> str:
        return "nodejs"

    def detect(self, file_path: str, source: str | None = None) -> bool:
        if not file_path.endswith((".js", ".ts")):
            return False
        if source is None:
            source = Path(file_path).read_text(encoding="utf-8")
        has_middleware = bool(re.search(
            r"(?:function\s+\w*(?:auth|guard|middleware|jwt|role|permission))|"
            r"(?:@UseGuards)|"
            r"(?:@Injectable\s*\(\s*\)\s*(?:export\s+)?class\s+\w*(?:Guard|Auth|Jwt))\s*",
            source,
            re.IGNORECASE,
        ))
        return has_middleware

    def parse(self, file_path: str, source: str) -> ParseResult:
        if not source.strip():
            return ParseResult()

        class_name = _extract_middleware_name(source, file_path)
        methods = self._extract_methods(source, class_name)
        self._extract_permissions(source)
        auth_type = self._detect_auth_type(source)

        return ParseResult(
            classes=[ParsedClass(
                name=class_name,
                type="component",
                annotations=[auth_type],
                file_path=file_path,
            )],
            methods=methods,
            endpoints=[],  # middleware doesn't produce endpoints directly
        )

    def _extract_methods(self, source: str, class_name: str) -> list[ParsedMethod]:
        methods: list[ParsedMethod] = []
        for m in re.finditer(
            r"(?:async\s+)?(?:canActivate|use|validate|handle|verifyToken|authorize)\s*\([^)]*\)",
            source,
        ):
            methods.append(ParsedMethod(
                name=m.group(0).split("(")[0].strip(),
                class_name=class_name,
                return_type="boolean",
            ))
        return methods

    def _extract_permissions(self, source: str) -> list[str]:
        perms: list[str] = []
        for m in re.finditer(r"""(?:role|permission|scope)\s*(?:===?|!==?|includes|indexOf)\s*.*?['\"]([^'\"]+)['\"]""", source):
            perms.append(m.group(1))
        for m in re.finditer(r"""SetMetadata\s*\(\s*['\"](?:roles|permissions)['\"]\s*,\s*\[([^\]]+)\]""", source):
            for pm in re.finditer(r"""['\"]([^'\"]+)['\"]""", m.group(1)):
                perms.append(pm.group(1))
        return perms

    def _detect_auth_type(self, source: str) -> str:
        if re.search(r"@UseGuards|@Injectable|canActivate", source):
            return "NestGuard"
        if re.search(r"passport|jwt\.verify|jsonwebtoken", source):
            return "JWT"
        if re.search(r"session|cookie", source):
            return "Session"
        return "CustomAuth"


def _extract_middleware_name(source: str, file_path: str) -> str:
    m = re.search(r"(?:export\s+)?class\s+(\w+)", source)
    if m:
        return m.group(1)
    m = re.search(r"function\s+(\w+)", source)
    if m:
        return m.group(1)
    m = re.search(r"module\.exports\s*=\s*(\w+)", source)
    if m:
        return m.group(1)
    return Path(file_path).stem
