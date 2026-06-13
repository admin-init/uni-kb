# uni-kb — Knowledge Base Library

Reusable data layer for codebase understanding. Parses source code into structured knowledge, indexes it for search, and serves via MCP.

Can be used standalone by human developers or consumed by uni-dev agent system.

## Architecture

```
Source Code
  │
  ▼
┌────────────────────────────────────────────────────┐
│  Regex-based Parsers (plugin system)               │
│  Java/Spring · Node.js/Express/NestJS               │
└───────────────┬────────────────────────────────────┘
                ▼  structured JSON (ParseResult)
┌────────────────────────────────────────────────────┐
│  Storage Layer                                      │
│  ┌──────────┬──────────┬───────────────┐           │
│  │ SQLite   │ ChromaDB │ NetworkX      │           │
│  │ 8 tables │ 14 idx   │ Code Graph    │           │
│  └──────────┴──────────┴───────────────┘           │
└───────────────┬────────────────────────────────────┘
                ▼
┌────────────────────────────────────────────────────┐
│  Spec Generators (6)                                │
│  API Contract · Business Logic · Data Model         │
│  Auth Matrix · Config Catalog · Migration Checklist │
└───────────────┬────────────────────────────────────┘
                ▼
┌────────────────────────────────────────────────────┐
│  MCP Server (21 tools, 5 categories)                │
└────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Install
cd uni-kb
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Initialize knowledge base for a project
uni-kb init --project /path/to/project

# Generate specs (OpenAPI, data model, auth matrix, etc.)
uni-kb generate --project /path/to/project

# Incrementally update KB (re-parses changed files only)
uni-kb update --project /path/to/project

# Watch for changes and auto-update KB in real time
uni-kb watch --project /path/to/project

# Start MCP server (stdio transport)
uni-kb serve --project /path/to/project

# Run tests
pytest
```

## Phase 1: Parser Extension System

**Goal:** Abstract plugin interface + registry + Java + Node.js parsers

### Base Plugin Interface (`parsers/base.py`)

```python
class ParserPlugin(ABC):
    @abstractmethod
    def language(self) -> str: ...
    @abstractmethod
    def detect(self, file_path: str, source: str | None = None) -> bool: ...
    @abstractmethod
    def parse(self, file_path: str, source: str) -> ParseResult: ...
```

Output: `ParseResult` with `classes`, `methods`, `endpoints`, `entities`, `imports`.

### Plugin Registry (`parsers/registry.py`)

Discovers plugins via Python entry points (`pyproject.toml` `[project.entry-points."uni_kb.parsers"]`). Loads on demand.

### Java Parser (`parsers/java/`)

Four regex-based parsers for Spring Boot:

| Parser | Target | Extracts |
|--------|--------|----------|
| `controller.py` | `@RestController`, `@RequestMapping` | Endpoints, HTTP methods, paths, auth |
| `service.py` | `@Service`, method bodies | Business logic structure, dependencies, body hash |
| `entity.py` | `@Entity`, `@Column`, `@Table` | Entities, fields, types, constraints, relationships |
| `mapper.py` | MyBatis XML + annotation interfaces | SQL operations, parameter bindings |

### Node.js Parser (`parsers/nodejs/`)

Four regex-based parsers for Express + NestJS:

| Parser | Target | Extracts |
|--------|--------|----------|
| `route.py` | Express `router.get()` / NestJS `@Get()` | Endpoints, HTTP methods, paths, auth |
| `service.py` | `@Injectable()` service classes | Business logic, methods, imports |
| `model.py` | Sequelize `define()` / TypeORM `@Entity()` | Entities, fields, relationships |
| `middleware.py` | JWT/auth/guard middleware | Auth type detection, permissions |

## Phase 2: Storage Layer

### SQLite Store (`store/sqlite_store.py`)

8 tables initialized on `uni-kb init --project ./`:

| Table | Purpose |
|-------|---------|
| `modules` | Top-level source modules |
| `classes` | Classes / components |
| `methods` | Methods / functions |
| `api_endpoints` | REST endpoints |
| `db_tables` | Database tables |
| `db_columns` | Table columns |
| `frontend_components` | Vue/Cocos components |
| `auth_permissions` | Permission annotations |

Ingests `ParseResult` objects via upsert. Uses `sqlite-utils`.

### ChromaDB Indexes (`store/chroma_indexes.py`)

14 named collections with `DefaultEmbeddingFunction` (all-MiniLM-L6-v2), persisted in `.uni-kb/chroma/`:

| # | Index | Content |
|---|-------|---------|
| 1 | `code_java_controller` | Java controller source |
| 2 | `code_java_service` | Java service source |
| 3 | `code_java_entity` | Java entity source |
| 4 | `code_java_mapper` | Mapper XML source |
| 5 | `code_typescript_admin` | Vue admin source |
| 6 | `code_typescript_game` | Cocos game source |
| 7 | `specs_api` | Generated OpenAPI specs |
| 8 | `specs_business_logic` | Generated method docs |
| 9 | `specs_data_model` | Generated entity specs |
| 10 | `specs_auth` | Permission matrix |
| 11 | `specs_config` | Config catalog |
| 12 | `db_schema` | Table DDL |
| 13 | `project_docs` | Documentation |
| 14 | `migration_checklists` | Per-module checklists |

### Code Graph (`store/code_graph.py`)

NetworkX directed graph.

**Nodes (8 types):** Module, Class, Method, APIEndpoint, DBTable, DBColumn, VueComponent, CocosComponent

**Edges (11 + 3 migration):** HAS_METHOD, CALLS, INJECTS, IMPLEMENTS, EXTENDS, ROUTES_TO, MAPS_TO, FK_TO, API_CALLER, PERMITS, IMPORTS + MIGRATES_TO, BLOCKED_BY, VERIFIED_AGAINST

## Phase 3: Spec Generators + MCP

### Generators (`generators/`)

6 generators, 4 exposed as direct MCP tools:

| Generator | Input | Output | MCP Tool |
|-----------|-------|--------|----------|
| `api_contract.py` | SQLiteStore endpoints | OpenAPI 3.0 YAML | `get_api_contract` |
| `business_logic.py` | SQLiteStore methods | Markdown pseudo-code | `get_business_logic_doc` |
| `data_model.py` | SQLiteStore entities | YAML model spec | → `get_entity_spec` |
| `auth_matrix.py` | SQLiteStore permissions | Permission matrix YAML | `get_permission_matrix` |
| `config_catalog.py` | YAML/.env files | Config catalog YAML | → `get_config_value` |
| `migration_checklist.py` | CodeGraph | Prioritized checklist MD | `get_migration_checklist` |

### MCP Server (`mcp_server.py`)

21 tools in 5 categories, stdio transport:

| Category | Tools |
|----------|-------|
| Code Exploration | `search_code`, `get_method_body`, `get_class_structure`, `find_endpoints`, `find_usages` |
| Spec Retrieval | `get_api_contract`, `get_business_logic_doc`, `verify_contract`, `compare_api_responses` |
| Data Model | `get_entity_spec`, `get_db_schema`, `get_column_info`, `trace_fk_chain` |
| Auth & Config | `get_permission_matrix`, `get_config_value`, `get_config_catalog` |
| Operations | `get_migration_checklist`, `get_dependency_graph`, `get_migration_status`, `run_test_suite`, `update_kb` |

## CLI Commands

```bash
uni-kb init --project /path/to/project     # Initialize KB
uni-kb generate --project /path/to/project # Generate all specs
uni-kb update --project /path/to/project   # Re-parse changed files
uni-kb watch --project /path/to/project    # Auto-update on file changes
uni-kb serve --project /path/to/project    # Start MCP server (stdio)
```

## Dependencies

```
chromadb>=0.5.0
networkx>=3.0
sqlite-utils>=3.35
pyyaml>=6.0
mcp>=1.0.0
click
importlib-metadata>=5.0 (Python < 3.12)
```

## Milestones

| Milestone | Content | Tests |
|-----------|---------|-------|
| M1 — Parser System | Abstract interface + registry + Java parsers + specs | 79 |
| M2 — Storage Layer | SQLite (8 tables) + ChromaDB (14 idx) + NetworkX graph + CLI init | +40 |
| M3 — Node.js Parsers | Express/NestJS route, service, model, middleware parsers | +40 |
| M4 — Generators + MCP | 6 spec generators + 21 MCP tools + update/watch | +28 |
| **Total** | | **187** |
