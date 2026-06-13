from __future__ import annotations

from uni_kb.parsers.base import ParserPlugin
from uni_kb.parsers.nodejs.route import NodejsRouteParser
from uni_kb.parsers.nodejs.service import NodejsServiceParser
from uni_kb.parsers.nodejs.model import NodejsModelParser
from uni_kb.parsers.nodejs.middleware import NodejsMiddlewareParser


def register() -> list[ParserPlugin]:
    return [
        NodejsRouteParser(),
        NodejsServiceParser(),
        NodejsModelParser(),
        NodejsMiddlewareParser(),
    ]
