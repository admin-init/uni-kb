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


if __name__ == "__main__":
    main()
