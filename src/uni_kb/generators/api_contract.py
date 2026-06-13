from __future__ import annotations

import re
from typing import Any

import yaml

from uni_kb.store.sqlite_store import SQLiteStore


def generate_api_contract(store: SQLiteStore, title: str = "API", version: str = "1.0.0") -> str:
    endpoints = store.list_endpoints()
    classes = {c["id"]: c for c in store.list_classes()}

    paths: dict[str, dict] = {}
    schemas: dict[str, dict[str, Any]] = {}

    for ep in endpoints:
        path = ep["path"]
        method = ep["http_method"].lower()
        path_item = paths.setdefault(path, {})

        params = _build_path_params(path)
        cls_name = ""
        if ep.get("class_id") and ep["class_id"] in classes:
            cls_name = classes[ep["class_id"]]["name"]

        responses = {"200": {"description": "Success"}}
        if ep.get("response_schema"):
            schema_name = ep["response_schema"]
            responses["200"]["content"] = {
                "application/json": {"schema": {"$ref": f"#/components/schemas/{schema_name}"}}
            }

        request_body = None
        if ep.get("request_schema"):
            schema_name = ep["request_schema"]
            request_body = {
                "content": {
                    "application/json": {"schema": {"$ref": f"#/components/schemas/{schema_name}"}}
                }
            }

        security = None
        if ep.get("auth_required"):
            security = [{"bearerAuth": []}]

        operation: dict[str, Any] = {
            "operationId": f"{ep.get('method_name', method)}_{path.lstrip('/').replace('/', '_')}",
            "summary": ep.get("description") or f"{method.upper()} {path}",
            "responses": responses,
            "tags": [cls_name] if cls_name else [],
        }
        if params:
            operation["parameters"] = params
        if request_body:
            operation["requestBody"] = request_body
        if security:
            operation["security"] = security

        path_item[method] = operation

    for cls in store.list_classes():
        schemas[cls["name"]] = {"type": "object", "properties": {}}

    for entity in store.list_entities():
        props: dict = {}
        for col in store.list_columns(entity["id"]):
            col_type = _map_sql_to_openapi_type(col["type"])
            prop = {"type": col_type}
            if col.get("nullable") and not col.get("is_primary_key"):
                prop["nullable"] = True
            props[col["name"]] = prop
        if props:
            schemas.setdefault(entity.get("entity_name", entity["name"]), {"type": "object", "properties": {}})
            schemas[entity["entity_name"]]["properties"] = props

    spec = {
        "openapi": "3.0.3",
        "info": {"title": title, "version": version},
        "paths": paths,
        "components": {
            "schemas": schemas,
            "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}},
        },
    }

    return yaml.dump(spec, default_flow_style=False, sort_keys=False, allow_unicode=True)


def _build_path_params(path: str) -> list[dict[str, Any]]:
    params: list[dict[str, Any]] = []
    seen: set[str] = set()
    for m in re.finditer(r"\{(\w+)\}", path):
        name = m.group(1)
        if name not in seen:
            seen.add(name)
            params.append({
                "name": name,
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
            })
    return params


def _map_sql_to_openapi_type(sql_type: str) -> str:
    mapping = {
        "INTEGER": "integer", "INT": "integer", "BIGINT": "integer",
        "VARCHAR": "string", "TEXT": "string", "STRING": "string",
        "BOOLEAN": "boolean", "FLOAT": "number", "DOUBLE": "number",
        "TIMESTAMP": "string", "DATE": "string", "JSON": "object",
        "UUID": "string",
    }
    return mapping.get(sql_type.upper(), "string")
