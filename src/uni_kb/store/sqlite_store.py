from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from sqlite_utils import Database

from uni_kb.parsers.base import ParseResult, ParsedClass, ParsedEndpoint, ParsedEntity, ParsedMethod

logger = logging.getLogger(__name__)


class SQLiteStore:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = Database(str(self._db_path))
        self.db.enable_wal()

    def create_tables(self) -> None:
        self.db["modules"].create(
            {
                "id": int,
                "name": str,
                "path": str,
                "language": str,
                "type": str,
            },
            pk="id",
            not_null={"name", "path", "language"},
        )
        self.db["modules"].create_index(["name"], unique=True)

        self.db["classes"].create(
            {
                "id": int,
                "name": str,
                "module_id": int,
                "type": str,
                "annotations": str,
                "file_path": str,
                "package": str,
                "extends": str,
                "implements": str,
            },
            pk="id",
            foreign_keys=[("module_id", "modules", "id")],
            not_null={"name", "type"},
        )
        self.db["classes"].create_index(["name", "module_id"], unique=True)

        self.db["methods"].create(
            {
                "id": int,
                "name": str,
                "class_id": int,
                "params": str,
                "return_type": str,
                "annotations": str,
                "body_hash": str,
            },
            pk="id",
            foreign_keys=[("class_id", "classes", "id")],
            not_null={"name", "class_id"},
        )
        self.db["methods"].create_index(["name", "class_id"], unique=True)

        self.db["api_endpoints"].create(
            {
                "id": int,
                "method_id": int,
                "class_id": int,
                "http_method": str,
                "path": str,
                "method_name": str,
                "request_schema": str,
                "response_schema": str,
                "auth_required": int,
                "consumes": str,
                "produces": str,
                "description": str,
            },
            pk="id",
            foreign_keys=[
                ("method_id", "methods", "id"),
                ("class_id", "classes", "id"),
            ],
            not_null={"http_method", "path"},
        )
        self.db["api_endpoints"].create_index(["method_id"], unique=True)

        self.db["db_tables"].create(
            {
                "id": int,
                "name": str,
                "entity_name": str,
                "schema": str,
                "package": str,
                "file_path": str,
            },
            pk="id",
            not_null={"name"},
        )
        self.db["db_tables"].create_index(["name"], unique=True)

        self.db["db_columns"].create(
            {
                "id": int,
                "table_id": int,
                "name": str,
                "type": str,
                "nullable": int,
                "default_value": str,
                "unique": int,
                "length": int,
                "fk_ref": str,
                "is_primary_key": int,
                "relationship_type": str,
            },
            pk="id",
            foreign_keys=[("table_id", "db_tables", "id")],
            not_null={"name", "table_id"},
        )

        self.db["auth_permissions"].create(
            {
                "id": int,
                "endpoint_id": int,
                "permission": str,
                "role": str,
            },
            pk="id",
            foreign_keys=[("endpoint_id", "api_endpoints", "id")],
            not_null={"endpoint_id"},
        )

    def ingest_parse_result(self, result: ParseResult, module_name: str = "") -> None:
        module_id = self._upsert_module(module_name, result)
        class_ids: dict[str, int] = {}
        method_ids: dict[str, int] = {}

        for cls in result.classes:
            class_id = self._ingest_class(cls, module_id)
            class_ids[cls.name] = class_id

        for method in result.methods:
            method_id = self._ingest_method(method, class_ids)
            method_ids[f"{method.class_name}.{method.name}"] = method_id

        for endpoint in result.endpoints:
            endpoint_id = self._ingest_endpoint(endpoint, method_ids, class_ids)
            self._ingest_auth_permissions(endpoint, endpoint_id)

        for entity in result.entities:
            self._ingest_entity(entity)

    def _upsert_module(self, module_name: str, result: ParseResult) -> int:
        name = module_name or "unknown"
        row = _first(self.db["modules"].rows_where("name = ?", [name]))
        if row:
            return row["id"]
        return self.db["modules"].insert(
            {"name": name, "path": name, "language": "java", "type": "module"}
        ).last_pk

    def _ingest_class(self, cls: ParsedClass, module_id: int) -> int:
        row = _first(
            self.db["classes"].rows_where(
                "name = ? AND module_id = ?", [cls.name, module_id]
            )
        )
        data = {
            "name": cls.name,
            "module_id": module_id,
            "type": cls.type,
            "annotations": json.dumps(cls.annotations),
            "file_path": cls.file_path,
            "package": cls.package,
            "extends": cls.extends or "",
            "implements": json.dumps(cls.implements),
        }
        if row:
            self.db["classes"].update(row["id"], data)
            return row["id"]
        return self.db["classes"].insert(data).last_pk

    def _ingest_method(self, method: ParsedMethod, class_ids: dict[str, int]) -> int:
        class_id = class_ids.get(method.class_name, 0)
        row = _first(
            self.db["methods"].rows_where(
                "name = ? AND class_id = ?", [method.name, class_id]
            )
        )
        data = {
            "name": method.name,
            "class_id": class_id,
            "params": json.dumps(method.params),
            "return_type": method.return_type,
            "annotations": json.dumps(method.annotations),
            "body_hash": method.body_hash,
        }
        if row:
            self.db["methods"].update(row["id"], data)
            return row["id"]
        return self.db["methods"].insert(data).last_pk

    def _ingest_endpoint(
        self,
        endpoint: ParsedEndpoint,
        method_ids: dict[str, int],
        class_ids: dict[str, int],
    ) -> int:
        method_key = f"{endpoint.class_name}.{endpoint.method_name}"
        method_id = method_ids.get(method_key)
        class_id = class_ids.get(endpoint.class_name)

        data = {
            "method_id": method_id,
            "class_id": class_id,
            "http_method": endpoint.http_method,
            "path": endpoint.path,
            "method_name": endpoint.method_name,
            "request_schema": endpoint.request_schema or "",
            "response_schema": endpoint.response_schema or "",
            "auth_required": 1 if endpoint.auth_required else 0,
            "consumes": endpoint.consumes or "",
            "produces": endpoint.produces or "",
            "description": endpoint.description or "",
        }
        return self.db["api_endpoints"].insert(data).last_pk

    def _ingest_auth_permissions(self, endpoint: ParsedEndpoint, endpoint_id: int) -> None:
        for perm in endpoint.auth_permissions:
            existing = _first(
                self.db["auth_permissions"].rows_where(
                    "endpoint_id = ? AND permission = ?", [endpoint_id, perm]
                )
            )
            if not existing:
                self.db["auth_permissions"].insert(
                    {"endpoint_id": endpoint_id, "permission": perm, "role": perm}
                )

    def _ingest_entity(self, entity: ParsedEntity) -> int:
        row = _first(self.db["db_tables"].rows_where("name = ?", [entity.table_name]))
        table_data = {
            "name": entity.table_name,
            "entity_name": entity.name,
            "schema": "public",
            "package": entity.package,
            "file_path": entity.file_path,
        }
        if row:
            table_id = row["id"]
            self.db["db_tables"].update(table_id, table_data)
        else:
            table_id = self.db["db_tables"].insert(table_data).last_pk

        for field in entity.fields:
            col_name = field.get("column_name", field.get("name", ""))
            col_row = _first(
                self.db["db_columns"].rows_where(
                    "name = ? AND table_id = ?", [col_name, table_id]
                )
            )
            col_data = {
                "name": col_name,
                "table_id": table_id,
                "type": _json_str(field.get("type", field.get("field_type", ""))),
                "nullable": 0 if field.get("nullable") is False else 1,
                "default_value": _json_str(field.get("default_value", "")),
                "unique": 1 if field.get("unique") else 0,
                "length": field.get("length") or 0,
                "fk_ref": _json_str(field.get("fk_ref", "")),
                "is_primary_key": 1 if col_name in entity.primary_keys else 0,
                "relationship_type": _json_str(field.get("relationship_type", "")),
            }
            if col_row:
                self.db["db_columns"].update(col_row["id"], col_data)
            else:
                self.db["db_columns"].insert(col_data)

        return table_id

    def get_class(self, class_id: int) -> dict | None:
        return _first(self.db["classes"].rows_where("id = ?", [class_id]))

    def get_method(self, method_id: int) -> dict | None:
        return _first(self.db["methods"].rows_where("id = ?", [method_id]))

    def get_endpoint(self, endpoint_id: int) -> dict | None:
        return _first(self.db["api_endpoints"].rows_where("id = ?", [endpoint_id]))

    def list_classes(self) -> list[dict]:
        return list(self.db["classes"].rows)

    def list_methods(self) -> list[dict]:
        return list(self.db["methods"].rows)

    def list_endpoints(self) -> list[dict]:
        return list(self.db["api_endpoints"].rows)

    def list_entities(self) -> list[dict]:
        return list(self.db["db_tables"].rows)

    def list_columns(self, table_id: int | None = None) -> list[dict]:
        if table_id is not None:
            return list(self.db["db_columns"].rows_where("table_id = ?", [table_id]))
        return list(self.db["db_columns"].rows)

    def get_db_schema(self) -> str:
        lines: list[str] = []
        for table_row in self.db["db_tables"].rows:
            table_name = table_row["name"]
            lines.append(f"CREATE TABLE {table_name} (")
            cols = list(self.db["db_columns"].rows_where("table_id = ?", [table_row["id"]]))
            for i, col in enumerate(cols):
                suffix = "," if i < len(cols) - 1 else ""
                pk = " PRIMARY KEY" if col["is_primary_key"] else ""
                nl = " NOT NULL" if not col["nullable"] else ""
                fk = f" REFERENCES {col['fk_ref']}" if col["fk_ref"] else ""
                lines.append(f"  {col['name']} {col['type']}{pk}{nl}{fk}{suffix}")
            lines.append(");")
        return "\n".join(lines)


def _first(iterable: Any) -> Any | None:
    return next(iter(iterable), None)


def _json_str(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return json.dumps(value)
