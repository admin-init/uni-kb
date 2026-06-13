from __future__ import annotations

import yaml

from uni_kb.store.sqlite_store import SQLiteStore


def generate_data_model(store: SQLiteStore) -> str:
    entities = store.list_entities()
    models: dict[str, dict] = {}

    for entity in entities:
        columns = store.list_columns(entity["id"])
        fields: list[dict] = []
        for col in columns:
            field = {
                "name": col["name"],
                "type": col["type"],
                "nullable": bool(col.get("nullable")),
                "unique": bool(col.get("unique")),
            }
            if col.get("is_primary_key"):
                field["primary_key"] = True
            if col.get("length"):
                field["length"] = col["length"]
            if col.get("default_value"):
                field["default"] = col["default_value"]
            if col.get("fk_ref"):
                field["foreign_key"] = col["fk_ref"]
            if col.get("relationship_type"):
                field["relationship"] = col["relationship_type"]
            fields.append(field)

        model = {
            "entity": entity.get("entity_name", entity["name"]),
            "table": entity["name"],
            "package": entity.get("package", ""),
            "file": entity.get("file_path", ""),
            "fields": fields,
        }
        models[model["table"]] = model

    doc = {
        "data_model": {
            "generated_by": "uni-kb data_model generator",
            "entities": list(models.values()),
        }
    }
    return yaml.dump(doc, default_flow_style=False, sort_keys=False, allow_unicode=True)
