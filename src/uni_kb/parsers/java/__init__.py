"""
Java / Spring Boot parser plugin.

Detects Java source files and dispatches to sub-parsers:
- ControllerParser: @RestController, @RequestMapping, @GetMapping, etc.
- ServiceParser: @Service class method extraction
- EntityParser: @Entity, @Column, JPA annotations
- MapperParser: MyBatis XML mapper files
"""

from uni_kb.parsers.base import ParserPlugin
from uni_kb.parsers.java.controller import JavaControllerParser
from uni_kb.parsers.java.service import JavaServiceParser
from uni_kb.parsers.java.entity import JavaEntityParser
from uni_kb.parsers.java.mapper import JavaMapperParser


def register() -> list[ParserPlugin]:
    return [
        JavaControllerParser(),
        JavaServiceParser(),
        JavaEntityParser(),
        JavaMapperParser(),
    ]
