from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server

from uni_kb.store.sqlite_store import SQLiteStore
from uni_kb.store.chroma_indexes import ChromaIndexes
from uni_kb.store.code_graph import CodeGraph
from uni_kb.generators.api_contract import generate_api_contract
from uni_kb.generators.business_logic import generate_business_logic_doc
from uni_kb.generators.auth_matrix import generate_auth_matrix
from uni_kb.generators.config_catalog import generate_config_catalog
from uni_kb.generators.migration_checklist import generate_migration_checklist

logger = logging.getLogger(__name__)

app = Server("uni-kb-mcp")


def create_mcp_server(kb_dir: str) -> Server:
    db_path = Path(kb_dir) / "store.db"
    chroma_dir = Path(kb_dir) / "chroma"
    graph_path = Path(kb_dir) / "graph.gml"

    store = SQLiteStore(str(db_path))
    chroma = ChromaIndexes(str(chroma_dir))
    chroma.ensure_all()
    graph = CodeGraph()
    if graph_path.exists():
        graph.load(str(graph_path))

    # ── Code Exploration ──

    @app.tool()
    async def search_code(query: str, k: int = 5) -> str:
        results = chroma.search("code_java_controller", query, k)
        if not results:
            results = chroma.search("code_java_service", query, k)
        return json.dumps(results, indent=2)

    @app.tool()
    async def get_method_body(method_name: str) -> str:
        for m in store.list_methods():
            if m["name"] == method_name:
                return json.dumps({"name": m["name"], "body_hash": m["body_hash"], "params": json.loads(m["params"])}, indent=2)
        return json.dumps({"error": f"Method '{method_name}' not found"})

    @app.tool()
    async def get_class_structure(class_name: str) -> str:
        for c in store.list_classes():
            if c["name"] == class_name:
                methods = [m for m in store.list_methods() if m["class_id"] == c["id"]]
                c["methods"] = [m["name"] for m in methods]
                return json.dumps(c, indent=2)
        return json.dumps({"error": f"Class '{class_name}' not found"})

    @app.tool()
    async def find_endpoints(path_filter: str = "") -> str:
        eps = store.list_endpoints()
        if path_filter:
            eps = [e for e in eps if path_filter in e["path"]]
        return json.dumps(eps, indent=2)

    @app.tool()
    async def find_usages(method_name: str) -> str:
        results = chroma.search("code_java_service", method_name, 10)
        return json.dumps([r["document"] for r in results], indent=2)

    # ── Spec Retrieval ──

    @app.tool()
    async def get_api_contract(title: str = "API", version: str = "1.0.0") -> str:
        return generate_api_contract(store, title, version)

    @app.tool()
    async def get_business_logic_doc() -> str:
        return generate_business_logic_doc(store)

    @app.tool()
    async def verify_contract(endpoint_path: str) -> str:
        eps = [e for e in store.list_endpoints() if e["path"] == endpoint_path]
        if eps:
            return json.dumps({"status": "verified", "endpoint": eps[0]})
        spec = generate_api_contract(store)
        if endpoint_path in spec:
            return json.dumps({"status": "exists_in_spec", "path": endpoint_path})
        return json.dumps({"status": "missing", "path": endpoint_path})

    @app.tool()
    async def compare_api_responses(endpoint_path: str) -> str:
        eps = [e for e in store.list_endpoints() if e["path"] == endpoint_path]
        if not eps:
            return json.dumps({"status": "no_endpoint_found"})
        ep = eps[0]
        spec_entry = generate_api_contract(store)
        return json.dumps({
            "endpoint": ep,
            "has_spec": endpoint_path in spec_entry,
        })

    # ── Data Model ──

    @app.tool()
    async def get_entity_spec(entity_name: str) -> str:
        entities = store.list_entities()
        for entity in entities:
            if entity.get("entity_name") == entity_name or entity["name"] == entity_name:
                cols = store.list_columns(entity["id"])
                entity["columns"] = cols
                return json.dumps(entity, indent=2)
        return json.dumps({"error": f"Entity '{entity_name}' not found"})

    @app.tool()
    async def get_db_schema() -> str:
        return store.get_db_schema()

    @app.tool()
    async def get_column_info(table: str, column: str) -> str:
        for entity in store.list_entities():
            if entity["name"] == table:
                for col in store.list_columns(entity["id"]):
                    if col["name"] == column:
                        return json.dumps(col, indent=2)
        return json.dumps({"error": f"Column '{column}' not found in table '{table}'"})

    @app.tool()
    async def trace_fk_chain(table: str, column: str) -> str:
        chain: list[dict[str, Any]] = []
        current_table = table
        max_depth = 5
        for _ in range(max_depth):
            found = False
            for entity in store.list_entities():
                if entity["name"] == current_table:
                    for col in store.list_columns(entity["id"]):
                        if col["name"] == column and col.get("fk_ref"):
                            chain.append({
                                "from_table": current_table,
                                "column": column,
                                "to_table": col["fk_ref"],
                            })
                            current_table = col["fk_ref"]
                            found = True
                            break
                if found:
                    break
            if not found:
                break
        return json.dumps(chain, indent=2)

    # ── Auth & Config ──

    @app.tool()
    async def get_permission_matrix() -> str:
        return generate_auth_matrix(store)

    @app.tool()
    async def get_config_value(key: str) -> str:
        catalog_yaml = generate_config_catalog(str(Path(kb_dir).parent))
        data = __import__("yaml").safe_load(catalog_yaml)
        entries = data.get("config_catalog", {}).get("entries", [])
        for entry in entries:
            if entry["key"] == key:
                return json.dumps(entry)
        return json.dumps({"error": f"Config key '{key}' not found"})

    @app.tool()
    async def get_config_catalog() -> str:
        return generate_config_catalog(str(Path(kb_dir).parent))

    # ── Operations ──

    @app.tool()
    async def get_migration_checklist() -> str:
        return generate_migration_checklist(graph)

    @app.tool()
    async def get_dependency_graph(module_name: str = "") -> str:
        nodes: list[dict[str, Any]] = []
        for node_id in graph.graph.nodes():
            data = dict(graph.graph.nodes[node_id])
            data["id"] = node_id
            data["dependencies"] = graph.get_dependencies(node_id)
            if module_name and module_name not in node_id:
                continue
            nodes.append(data)
        return json.dumps({"nodes": nodes, "total": len(nodes)}, indent=2)

    @app.tool()
    async def get_migration_status() -> str:
        try:
            order = graph.topological_sort()
            total = len(order)
            return json.dumps({"total_items": total, "order": order[:20]})
        except Exception:
            return json.dumps({"total_items": graph.node_count()})

    @app.tool()
    async def run_test_suite(test_dir: str = "tests") -> str:
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_dir, "-q"],
            capture_output=True, text=True, cwd=str(Path(kb_dir).parent),
        )
        return result.stdout or result.stderr

    @app.tool()
    async def update_kb() -> str:
        from uni_kb.cli import _reparse_changed_files
        project_path = Path(kb_dir).parent
        s = SQLiteStore(str(db_path))
        c = ChromaIndexes(str(chroma_dir))
        c.ensure_all()
        count = _reparse_changed_files(project_path, Path(kb_dir), s, c)
        g = CodeGraph()
        g.build_from_parse_results([])
        g.save(str(graph_path))
        return json.dumps({"updated": count, "total_nodes": g.node_count()})

    return app


async def run_mcp_server(kb_dir: str) -> None:
    server = create_mcp_server(kb_dir)
    async with stdio_server() as (reader, writer):
        await server.run(reader, writer, server.create_initialization_options())
