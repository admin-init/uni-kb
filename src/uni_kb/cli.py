from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import click

from uni_kb.parsers.base import ParseResult
from uni_kb.parsers.registry import ParserRegistry
from uni_kb.store.chroma_indexes import ChromaIndexes
from uni_kb.store.code_graph import CodeGraph
from uni_kb.store.sqlite_store import SQLiteStore
from uni_kb.generators.api_contract import generate_api_contract
from uni_kb.generators.business_logic import generate_business_logic_doc
from uni_kb.generators.data_model import generate_data_model
from uni_kb.generators.auth_matrix import generate_auth_matrix
from uni_kb.generators.config_catalog import generate_config_catalog
from uni_kb.generators.migration_checklist import generate_migration_checklist

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("uni_kb")


@click.group()
@click.version_option(package_name="uni_kb")
def main() -> None:
    """uni-kb — Knowledge Base library for codebase understanding."""


@main.command()
@click.option("--project", required=True, type=click.Path(exists=True), help="Path to project")
@click.option("--output", "-o", default=None, type=click.Path(), help="Output directory (default: <project>/.uni-kb)")
def init(project: str, output: str | None) -> None:
    """Initialize knowledge base for a project.

    Walks source tree, parses files, and populates SQLite, ChromaDB, and NetworkX stores.
    """
    project_path = Path(project).resolve()
    kb_dir = Path(output).resolve() if output else project_path / ".uni-kb"
    kb_dir.mkdir(parents=True, exist_ok=True)

    db_path = kb_dir / "store.db"
    chroma_dir = kb_dir / "chroma"
    graph_path = kb_dir / "graph.gml"

    store = SQLiteStore(str(db_path))
    store.create_tables()
    logger.info(f"SQLite store created at {db_path}")

    chroma = ChromaIndexes(str(chroma_dir))
    chroma.ensure_all()
    logger.info(f"ChromaDB initialized at {chroma_dir}")

    graph = CodeGraph()
    all_results: list[ParseResult] = []
    total_files = 0

    for java_file in _walk_source_files(project_path, {".java", ".xml"}):
        try:
            source = java_file.read_text(encoding="utf-8")
        except Exception:
            logger.warning(f"Could not read {java_file}")
            continue

        plugin = ParserRegistry.find(str(java_file), source)
        if plugin is None:
            continue

        result = plugin.parse(str(java_file), source)
        module_name = _resolve_module_name(java_file, project_path)

        store.ingest_parse_result(result, module_name=module_name)
        chroma.index_code(result, source, language=plugin.language())
        all_results.append(result)
        total_files += 1

        if result.errors:
            for err in result.errors:
                logger.warning(f"  [{java_file.name}] {err}")

    graph.build_from_parse_results(all_results)
    graph.save(str(graph_path))

    db_schema = store.get_db_schema()
    if db_schema.strip():
        chroma.index_db_schema(db_schema)

    logger.info(f"Indexed {total_files} files")
    logger.info(f"  Classes: {sum(len(r.classes) for r in all_results)}")
    logger.info(f"  Methods: {sum(len(r.methods) for r in all_results)}")
    logger.info(f"  Endpoints: {sum(len(r.endpoints) for r in all_results)}")
    logger.info(f"  Entities: {sum(len(r.entities) for r in all_results)}")
    logger.info(f"  Graph nodes: {graph.node_count()}")
    logger.info(f"  Graph edges: {graph.edge_count()}")


def _walk_source_files(root: Path, extensions: set[str]) -> Any:
    ext = extensions.pop()
    extensions.add(ext)
    for ext in extensions:
        yield from root.rglob(f"*{ext}")


def _resolve_module_name(file_path: Path, project_path: Path) -> str:
    try:
        rel = file_path.relative_to(project_path / "src" / "main" / "java")
        parts = list(rel.parts)
        if parts:
            module = parts[0]
            return module.replace("/", ".")
    except ValueError:
        pass
    try:
        rel = file_path.relative_to(project_path)
        parts = list(rel.parts)
        return ".".join(parts[:-1]).replace("/", ".")
    except ValueError:
        pass
    return file_path.stem


@main.command()
@click.option("--project", required=True, type=click.Path(exists=True), help="Path to project")
@click.option("--output", "-o", default=None, type=click.Path(), help="Output directory for generated specs")
@click.option("--type", "gen_type", default="all", help="Generator type: all, api, logic, model, auth, config, migration")
def generate(project: str, output: str | None, gen_type: str) -> None:
    """Generate specifications from the knowledge base."""
    project_path = Path(project).resolve()
    kb_dir = project_path / ".uni-kb"
    db_path = kb_dir / "store.db"
    graph_path = kb_dir / "graph.gml"

    if not db_path.exists():
        click.echo("Knowledge base not found. Run 'uni-kb init --project <path>' first.", err=True)
        return

    out_dir = Path(output).resolve() if output else project_path

    store = SQLiteStore(str(db_path))
    graph = CodeGraph()
    if graph_path.exists():
        graph.load(str(graph_path))

    def _write(name: str, content: str) -> None:
        path = out_dir / f"{name}.yaml"
        path.write_text(content, encoding="utf-8")
        click.echo(f"  {path}")

    if gen_type in ("all", "api"):
        click.echo("Generating API contract...")
        _write("api-contract", generate_api_contract(store))

    if gen_type in ("all", "logic"):
        click.echo("Generating business logic docs...")
        path = out_dir / "business-logic.md"
        path.write_text(generate_business_logic_doc(store), encoding="utf-8")
        click.echo(f"  {path}")

    if gen_type in ("all", "model"):
        click.echo("Generating data model...")
        _write("data-model", generate_data_model(store))

    if gen_type in ("all", "auth"):
        click.echo("Generating auth matrix...")
        _write("auth-matrix", generate_auth_matrix(store))

    if gen_type in ("all", "config"):
        click.echo("Generating config catalog...")
        _write("config-catalog", generate_config_catalog(str(project_path)))

    if gen_type in ("all", "migration"):
        click.echo("Generating migration checklist...")
        path = out_dir / "migration-checklist.md"
        path.write_text(generate_migration_checklist(graph), encoding="utf-8")
        click.echo(f"  {path}")

    click.echo("Done.")


@main.command()
@click.option("--project", required=True, type=click.Path(exists=True), help="Path to project")
def serve(project: str) -> None:
    """Start MCP server for the project."""
    from uni_kb.mcp_server import run_mcp_server
    import asyncio

    project_path = Path(project).resolve()
    kb_dir = project_path / ".uni-kb"
    if not (kb_dir / "store.db").exists():
        click.echo("Knowledge base not found. Run 'uni-kb init --project <path>' first.", err=True)
        return
    asyncio.run(run_mcp_server(str(kb_dir)))


if __name__ == "__main__":
    main()
