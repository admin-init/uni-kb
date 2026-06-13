from __future__ import annotations

import logging

import networkx as nx

from uni_kb.parsers.base import ParseResult, ParsedClass, ParsedEndpoint, ParsedEntity, ParsedMethod

logger = logging.getLogger(__name__)

HAS_METHOD = "HAS_METHOD"
ROUTES_TO = "ROUTES_TO"
CALLS = "CALLS"
INJECTS = "INJECTS"
IMPLEMENTS = "IMPLEMENTS"
EXTENDS = "EXTENDS"
MAPS_TO = "MAPS_TO"
FK_TO = "FK_TO"
API_CALLER = "API_CALLER"
PERMITS = "PERMITS"
IMPORTS = "IMPORTS"
MIGRATES_TO = "MIGRATES_TO"
BLOCKED_BY = "BLOCKED_BY"
VERIFIED_AGAINST = "VERIFIED_AGAINST"

EDGE_TYPES = [
    HAS_METHOD,
    ROUTES_TO,
    CALLS,
    INJECTS,
    IMPLEMENTS,
    EXTENDS,
    MAPS_TO,
    FK_TO,
    API_CALLER,
    PERMITS,
    IMPORTS,
    MIGRATES_TO,
    BLOCKED_BY,
    VERIFIED_AGAINST,
]


class CodeGraph:
    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def build_from_parse_results(self, results: list[ParseResult]) -> None:
        for result in results:
            self._add_nodes_from_result(result)
        for result in results:
            self._add_edges_from_result(result)

    def _add_nodes_from_result(self, result: ParseResult) -> None:
        for cls in result.classes:
            self._add_class_node(cls)
        for method in result.methods:
            self._add_method_node(method)
        for endpoint in result.endpoints:
            self._add_endpoint_node(endpoint)
        for entity in result.entities:
            self._add_entity_node(entity)

    def _add_class_node(self, cls: ParsedClass) -> None:
        node_id = f"Class:{cls.name}"
        self.graph.add_node(
            node_id,
            type="Class",
            name=cls.name,
            class_type=cls.type,
            package=cls.package,
            file_path=cls.file_path,
        )

    def _add_method_node(self, method: ParsedMethod) -> None:
        node_id = f"Method:{method.class_name}.{method.name}"
        self.graph.add_node(
            node_id,
            type="Method",
            name=method.name,
            class_name=method.class_name,
            return_type=method.return_type,
            body_hash=method.body_hash,
        )

    def _add_endpoint_node(self, endpoint: ParsedEndpoint) -> None:
        node_id = f"APIEndpoint:{endpoint.class_name}.{endpoint.method_name}"
        self.graph.add_node(
            node_id,
            type="APIEndpoint",
            http_method=endpoint.http_method,
            path=endpoint.path,
            auth_required=endpoint.auth_required,
        )

    def _add_entity_node(self, entity: ParsedEntity) -> None:
        node_id = f"DBTable:{entity.table_name}"
        self.graph.add_node(
            node_id,
            type="DBTable",
            name=entity.table_name,
            entity_name=entity.name,
            package=entity.package,
        )
        for field in entity.fields:
            col_name = field.get("column_name", field.get("name", ""))
            col_node = f"DBColumn:{entity.table_name}.{col_name}"
            self.graph.add_node(
                col_node,
                type="DBColumn",
                name=col_name,
                table_name=entity.table_name,
                col_type=field.get("type", field.get("field_type", "")),
                is_pk=col_name in entity.primary_keys,
            )
            self.graph.add_edge(col_node, node_id, type=FK_TO)
            fk_ref = field.get("fk_ref", "")
            if fk_ref:
                self.graph.add_edge(col_node, f"DBTable:{fk_ref}", type=FK_TO)

    def _add_edges_from_result(self, result: ParseResult) -> None:
        for cls in result.classes:
            class_node = f"Class:{cls.name}"
            if cls.extends:
                self.graph.add_edge(class_node, f"Class:{cls.extends}", type=EXTENDS)
            for impl in cls.implements:
                self.graph.add_edge(class_node, f"Class:{impl}", type=IMPLEMENTS)

        for method in result.methods:
            method_node = f"Method:{method.class_name}.{method.name}"
            class_node = f"Class:{method.class_name}"
            if class_node in self.graph:
                self.graph.add_edge(class_node, method_node, type=HAS_METHOD)

        for endpoint in result.endpoints:
            ep_node = f"APIEndpoint:{endpoint.class_name}.{endpoint.method_name}"
            class_node = f"Class:{endpoint.class_name}"
            if class_node in self.graph:
                self.graph.add_edge(class_node, ep_node, type=ROUTES_TO)

        for entity in result.entities:
            table_node = f"DBTable:{entity.table_name}"
            for endpoint in result.endpoints:
                ep_node = f"APIEndpoint:{endpoint.class_name}.{endpoint.method_name}"
                if ep_node in self.graph:
                    self.graph.add_edge(ep_node, table_node, type=MAPS_TO)

    def get_dependencies(self, node_id: str) -> list[str]:
        return list(self.graph.predecessors(node_id))

    def get_dependents(self, node_id: str) -> list[str]:
        return list(self.graph.successors(node_id))

    def topological_sort(self) -> list[str]:
        return list(nx.topological_sort(self.graph))

    def save(self, path: str) -> None:
        nx.write_gml(self.graph, path)

    def load(self, path: str) -> None:
        self.graph = nx.read_gml(path)

    def node_count(self) -> int:
        return self.graph.number_of_nodes()

    def edge_count(self) -> int:
        return self.graph.number_of_edges()
