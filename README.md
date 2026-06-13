# uni-kb — Knowledge Base Library

Reusable data layer for codebase understanding. Parses source code into structured knowledge, indexes it for search, and serves it via MCP.

Can be used standalone by human developers or consumed by uni-dev agent system.

## Architecture

```
Source Code
  │
  ▼
┌──────────────────────────────────────────┐
│  tree-sitter Parsers (plugin system)     │
│  Java/Spring · Node.js/Express/NestJS     │
└───────────────┬──────────────────────────┘
                ▼  structured JSON
┌──────────────────────────────────────────┐
│  Storage Layer                            │
│  ┌──────────┬──────────┬───────────────┐ │
│  │ SQLite   │ ChromaDB │ NetworkX      │ │
│  │ 8 tables │ 14 idx   │ Code Graph    │ │
│  └──────────┴──────────┴───────────────┘ │
└───────────────┬──────────────────────────┘
                ▼
┌──────────────────────────────────────────┐
│  Spec Generators (6)                      │
│  API Contract · Business Logic · Models   │
│  Auth Matrix · Config · Migration         │
└───────────────┬──────────────────────────┘
                ▼
┌──────────────────────────────────────────┐
│  MCP Server (20 tools, 5 categories)      │
└──────────────────────────────────────────┘
```

## Phase 1: Parser Extension System

**Goal:** Abstract plugin interface + registry + Java parser

### 1.1 Base Plugin Interface (`parsers/base.py`)

```python
class ParserPlugin(ABC):
    @abstractmethod
    def language(self) -> str: ...
    @abstractmethod
    def detect(self, file_path: str) -> bool: ...
    @abstractmethod
    def parse(self, file_path: str, source: str) -> ParseResult: ...
```

### 1.2 Plugin Registry (`parsers/registry.py`)

Discovers plugins via Python entry points (`pyproject.toml` `[project.entry-points."uni_kb.parsers"]`). Loads on demand.

### 1.3 Java Parser (`parsers/java/`)

Four sub-parsers using `tree-sitter-java`:

| Parser | Target | Extracts |
|--------|--------|----------|
| `controller.py` | `@RestController`, `@RequestMapping` | Endpoints, HTTP methods, paths, params, response types |
| `service.py` | `@Service`, method bodies | Business logic structure, dependencies |
| `entity.py` | `@Entity`, `@Column`, `@Table` | Entities, fields, types, constraints, relationships |
| `mapper.py` | MyBatis XML | Custom SQL queries, result maps |

**Output:** `ParseResult` with standardized JSON matching SQLite schema.

## Phase 2: Storage Layer

### 2.1 SQLite Store (`store/sqlite_store.py`)

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

### 2.2 ChromaDB Indexes (`store/chroma_indexes.py`)

14 named collections with embedded mode (persisted in `.uni-kb/chroma/`):

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

### 2.3 Code Graph (`store/code_graph.py`)

NetworkX directed graph.

**Nodes (8 types):** Module, Class, Method, APIEndpoint, DBTable, DBColumn, VueComponent, CocosComponent

**Edges (11 + 3 migration):** HAS_METHOD, CALLS, INJECTS, IMPLEMENTS, EXTENDS, ROUTES_TO, MAPS_TO, FK_TO, API_CALLER, PERMITS, IMPORTS + MIGRATES_TO, BLOCKED_BY, VERIFIED_AGAINST

## Phase 3: Node.js Parser

### 1.4 Node.js Parser (`parsers/nodejs/`)

Four sub-parsers using `tree-sitter-typescript`:

| Parser | Target | Extracts |
|--------|--------|----------|
| `route.py` | Express `router.get()` / NestJS `@Get()` | Endpoints, HTTP methods, paths, middleware chains |
| `service.py` | Service classes | Business logic structure |
| `model.py` | Sequelize / TypeORM models | Entities, fields, types, relationships |
| `middleware.py` | Auth middleware | Permission chains, guards |

## Phase 4: Spec Generators + MCP

### 4.1 Generators (`generators/`)

6 generators, 4 exposed as direct MCP tools:

| Generator | Input | Output | MCP Tool |
|-----------|-------|--------|----------|
| `api_contract.py` | Controller/Route AST | OpenAPI 3.0 YAML | `get_api_contract` |
| `business_logic.py` | Service AST | Markdown pseudo-code | `get_business_logic_doc` |
| `data_model.py` | Entity + DB schema | YAML model spec | → `get_entity_spec` |
| `auth_matrix.py` | Permission annotations | Permission matrix YAML | `get_permission_matrix` |
| `config_catalog.py` | YAML/.env files | Config catalog YAML | → `get_config_value` |
| `migration_checklist.py` | Module + dep graph | Prioritized checklist MD | `get_migration_checklist` |

### 4.2 MCP Server (`mcp_server.py`)

20 tools in 5 categories:

| Category | Tools |
|----------|-------|
| Code Exploration | `search_code`, `get_method_body`, `get_class_structure`, `find_endpoints`, `find_usages` |
| Spec Retrieval | `get_api_contract`, `get_business_logic_doc`, `verify_contract`, `compare_api_responses` |
| Data Model | `get_entity_spec`, `get_db_schema`, `get_column_info`, `trace_fk_chain` |
| Auth & Config | `get_permission_matrix`, `get_config_value`, `get_config_catalog` |
| Operations | `get_migration_checklist`, `get_dependency_graph`, `get_migration_status`, `run_test_suite` |

## Dependencies

```
chromadb
networkx
tree-sitter
tree-sitter-java
tree-sitter-typescript
sqlite-utils
pyyaml
mcp>=1.0.0
```

## CLI Usage

```bash
# Initialize knowledge base for a project
uni-kb init --project /path/to/project

# Parse and index source code
uni-kb index --project /path/to/project

# Start MCP server
uni-kb serve --project /path/to/project --port 9020
```
