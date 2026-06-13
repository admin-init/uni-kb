from __future__ import annotations

import json

from uni_kb.store.sqlite_store import SQLiteStore


def generate_business_logic_doc(store: SQLiteStore) -> str:
    lines: list[str] = ["# Business Logic Documentation", ""]
    classes = store.list_classes()
    class_methods: dict[int, list[dict]] = {}

    for method in store.list_methods():
        cid = method["class_id"]
        class_methods.setdefault(cid, []).append(method)

    for cls in classes:
        cid = cls["id"]
        methods = class_methods.get(cid, [])
        if cls["type"] in ("controller",):
            continue

        lines.append(f"## {cls['name']}")
        lines.append(f"**Type:** {cls['type']}")
        if cls.get("package"):
            lines.append(f"**Package:** {cls['package']}")
        annotations = _parse_json_list(cls.get("annotations", "[]"))
        if annotations:
            lines.append(f"**Annotations:** {', '.join(annotations)}")
        lines.append("")

        for method in methods:
            params = _parse_json_list(method.get("params", "[]"))
            param_str = ", ".join(
                f"{p.get('type', 'any')} {p.get('name', '?')}" for p in params
            ) if isinstance(params, list) else ""
            lines.append(f"### {method['name']}({param_str})")
            if method.get("return_type") and method["return_type"] != "void":
                lines.append(f"**Returns:** `{method['return_type']}`")
            if method.get("body_hash"):
                lines.append(f"**Body Hash:** `{method['body_hash']}`")
            annotations = _parse_json_list(method.get("annotations", "[]"))
            if annotations:
                lines.append(f"**Annotations:** {', '.join(annotations)}")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def _parse_json_list(raw: str | list) -> list:
    if isinstance(raw, list):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
