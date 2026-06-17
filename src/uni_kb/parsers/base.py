from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedClass:
    name: str
    type: str  # controller, service, entity, repository, component, configuration
    annotations: list[str] = field(default_factory=list)
    file_path: str = ""
    package: str = ""
    module: str = ""
    modifiers: list[str] = field(default_factory=list)
    extends: str | None = None
    implements: list[str] = field(default_factory=list)


@dataclass
class ParsedMethod:
    name: str
    class_name: str
    params: list[dict[str, str]] = field(default_factory=list)
    return_type: str = "void"
    annotations: list[str] = field(default_factory=list)
    modifiers: list[str] = field(default_factory=list)
    throws: list[str] = field(default_factory=list)
    body_hash: str = ""


@dataclass
class ParsedEndpoint:
    http_method: str  # GET, POST, PUT, PATCH, DELETE
    path: str
    method_name: str
    class_name: str
    request_schema: str | None = None
    response_schema: str | None = None
    auth_required: bool = False
    auth_permissions: list[str] = field(default_factory=list)
    consumes: str | None = None
    produces: str | None = None
    description: str = ""


@dataclass
class ParsedEntity:
    name: str
    table_name: str
    fields: list[dict[str, Any]] = field(default_factory=list)
    annotations: list[str] = field(default_factory=list)
    package: str = ""
    file_path: str = ""
    primary_keys: list[str] = field(default_factory=list)
    indexes: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ParseResult:
    classes: list[ParsedClass] = field(default_factory=list)
    methods: list[ParsedMethod] = field(default_factory=list)
    endpoints: list[ParsedEndpoint] = field(default_factory=list)
    entities: list[ParsedEntity] = field(default_factory=list)
    imports: list[dict[str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def merge(self, other: ParseResult) -> ParseResult:
        self.classes.extend(other.classes)
        self.methods.extend(other.methods)
        self.endpoints.extend(other.endpoints)
        self.entities.extend(other.entities)
        self.imports.extend(other.imports)
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        return self


class ParserPlugin(ABC):
    @abstractmethod
    def language(self) -> str:
        ...

    @abstractmethod
    def detect(self, file_path: str, source: str | None = None) -> bool:
        ...

    @abstractmethod
    def parse(self, file_path: str, source: str) -> ParseResult:
        ...
