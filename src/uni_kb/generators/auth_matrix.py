from __future__ import annotations

import yaml

from uni_kb.store.sqlite_store import SQLiteStore


def generate_auth_matrix(store: SQLiteStore) -> str:
    endpoints = store.list_endpoints()
    perms = list(store.db["auth_permissions"].rows)
    perm_map: dict[int, list[str]] = {}
    for p in perms:
        perm_map.setdefault(p["endpoint_id"], []).append(p["permission"])

    rows: list[dict] = []
    for ep in endpoints:
        ep_perms = perm_map.get(ep["id"], [])
        rows.append({
            "path": ep["path"],
            "method": ep["http_method"],
            "auth_required": bool(ep.get("auth_required")),
            "permissions": ep_perms,
        })

    doc = {
        "auth_matrix": {
            "generated_by": "uni-kb auth_matrix generator",
            "endpoints": rows,
        }
    }
    return yaml.dump(doc, default_flow_style=False, sort_keys=False, allow_unicode=True)
