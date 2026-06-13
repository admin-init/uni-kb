from __future__ import annotations

import os
import re
from pathlib import Path

import yaml


def generate_config_catalog(project_dir: str) -> str:
    dir_path = Path(project_dir)
    entries: list[dict] = []

    for root, _dirs, files in os.walk(str(dir_path)):
        for fname in files:
            fpath = Path(root) / fname
            try:
                rel = fpath.relative_to(dir_path)
            except ValueError:
                rel = fpath

            if fname.endswith((".yaml", ".yml")):
                try:
                    content = yaml.safe_load(fpath.read_text(encoding="utf-8"))
                    for key, value in _flatten_config(content, str(rel)):
                        entries.append({
                            "key": key,
                            "value": _safe_str(value),
                            "file": str(rel),
                            "source": "yaml",
                        })
                except Exception:
                    pass
            elif fname.endswith(".env") or fname == ".env":
                try:
                    for line in fpath.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        m = re.match(r"(\w[\w_]*)\s*=\s*(.*)", line)
                        if m:
                            entries.append({
                                "key": m.group(1),
                                "value": _safe_str(m.group(2)),
                                "file": str(rel),
                                "source": "env",
                            })
                except Exception:
                    pass

    doc = {
        "config_catalog": {
            "generated_by": "uni-kb config_catalog generator",
            "entries": entries,
        }
    }
    return yaml.dump(doc, default_flow_style=False, sort_keys=False, allow_unicode=True)


def _flatten_config(data: object, prefix: str) -> list[tuple[str, object]]:
    if isinstance(data, dict):
        result: list[tuple[str, object]] = []
        for k, v in data.items():
            result.extend(_flatten_config(v, f"{prefix}.{k}" if prefix else k))
        return result
    return [(prefix, data)]


def _safe_str(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return ""
    return str(value)
