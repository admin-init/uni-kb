from __future__ import annotations

import re
from pathlib import Path

from uni_kb.parsers.base import ParseResult, ParsedEntity, ParserPlugin


class NodejsModelParser(ParserPlugin):
    def language(self) -> str:
        return "nodejs"

    def detect(self, file_path: str, source: str | None = None) -> bool:
        if not file_path.endswith((".js", ".ts")):
            return False
        if source is None:
            source = Path(file_path).read_text(encoding="utf-8")
        has_sequelize = bool(re.search(r"sequelize\s*\.\s*define|Model\s*\.\s*init\s*\(", source))
        has_typeorm = bool(re.search(r"@Entity\s*\(", source))
        return has_sequelize or has_typeorm

    def parse(self, file_path: str, source: str) -> ParseResult:
        if not source.strip():
            return ParseResult()
        if re.search(r"@Entity", source):
            return self._parse_typeorm(file_path, source)
        return self._parse_sequelize(file_path, source)

    def _parse_sequelize(self, file_path: str, source: str) -> ParseResult:
        table_name = _extract_table_name(source, file_path) or _model_to_table(file_path)
        entity_name = _extract_entity_name(source, file_path)
        fields, primary_keys = self._extract_sequelize_fields(source)

        return ParseResult(
            entities=[ParsedEntity(
                name=entity_name,
                table_name=table_name,
                fields=fields,
                file_path=file_path,
                primary_keys=primary_keys,
            )],
        )

    def _parse_typeorm(self, file_path: str, source: str) -> ParseResult:
        entity_name = _extract_entity_name(source, file_path)
        table_name = _extract_table_name(source, file_path) or entity_name.lower()
        fields, primary_keys = self._extract_typeorm_fields(source)

        return ParseResult(
            entities=[ParsedEntity(
                name=entity_name,
                table_name=table_name,
                fields=fields,
                file_path=file_path,
                primary_keys=primary_keys,
            )],
        )

    def _extract_sequelize_fields(self, source: str) -> tuple[list[dict[str, object]], list[str]]:
        fields: list[dict[str, object]] = []
        primary_keys: list[str] = []

        definition_pattern = re.compile(
            r"(\w+)\s*:\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}",
            re.DOTALL,
        )

        for match in definition_pattern.finditer(source):
            name = match.group(1)
            body = match.group(2)

            col_name = name
            col_name_m = re.search(r"field\s*:\s*['\"]([^'\"]+)['\"]", body)
            if col_name_m:
                col_name = col_name_m.group(1)

            col_type = _extract_field_prop(body, "type", "STRING")
            nullable = not _has_field_prop(body, "allowNull", negate=True)
            unique = _has_field_prop(body, "unique")
            pk = _has_field_prop(body, "primaryKey")
            default_val = _extract_field_prop(body, "defaultValue", "")

            field_info: dict[str, object] = {
                "name": name,
                "column_name": col_name,
                "type": _map_sequelize_type(col_type),
                "nullable": nullable,
                "unique": unique,
                "default_value": default_val,
            }
            fields.append(field_info)

            ref_m = re.search(r"references\s*:\s*\{[^}]*model\s*:\s*['\"]([^'\"]+)['\"]", body, re.DOTALL)
            if ref_m:
                field_info["fk_ref"] = ref_m.group(1)

            if pk:
                primary_keys.append(col_name)

        return fields, primary_keys

    def _extract_typeorm_fields(self, source: str) -> tuple[list[dict[str, object]], list[str]]:
        fields: list[dict[str, object]] = []
        primary_keys: list[str] = []

        field_pattern = re.compile(
            r"(@(?:\w+)\s*\([^)]*\)\s*)*"
            r"(\w+)\s*:\s*(\w+(?:\[\])?)\s*;"
            r"((?:\s*@\w+\s*\([^)]*\))*)",
            re.DOTALL,
        )

        for match in field_pattern.finditer(source):
            annotations_block = source[match.start():match.end()]
            name = match.group(2)
            col_type = match.group(3)

            col_name = name
            col_name_m = re.search(r"@Column\s*\(\s*\{[^}]*name\s*:\s*['\"]([^'\"]+)['\"]", annotations_block)
            if col_name_m:
                col_name = col_name_m.group(1)

            nullable = not re.search(r"nullable\s*:\s*false", annotations_block)

            pk = bool(re.search(r"@PrimaryGeneratedColumn|@PrimaryColumn", source[match.start():match.end() + 50]))

            field_info: dict[str, object] = {
                "name": name,
                "column_name": col_name,
                "type": _map_typeorm_type(col_type),
                "nullable": nullable,
                "unique": bool(re.search(r"unique\s*:\s*true", annotations_block)),
            }
            fields.append(field_info)

            if pk:
                primary_keys.append(col_name)
            elif re.search(r"@ManyToOne|@OneToOne", annotations_block):
                field_info["relationship_type"] = "ManyToOne"
                join_m = re.search(r"@JoinColumn\s*\(\s*\{[^}]*name\s*:\s*['\"]([^'\"]+)['\"]", annotations_block)
                if join_m:
                    field_info["column_name"] = join_m.group(1)

        return fields, primary_keys


def _extract_entity_name(source: str, file_path: str) -> str:
    m = re.search(r"(?:export\s+)?(?:class|interface)\s+(\w+)", source)
    if m:
        return m.group(1)
    m = re.search(r"(?:module\.exports\s*=\s*(?:\w+\.)?model\s*\(\s*['\"]([^'\"]+)['\"]|"
                   r"sequelize\s*\.\s*define\s*\(\s*['\"]([^'\"]+)['\"])", source)
    if m:
        return m.group(1) or m.group(2)
    return Path(file_path).stem


def _extract_table_name(source: str, file_path: str) -> str:
    m = re.search(r"tableName\s*:\s*['\"]([^'\"]+)['\"]", source)
    if m:
        return m.group(1)
    m = re.search(r"@Entity\s*\(\s*\{[^}]*name\s*:\s*['\"]([^'\"]+)['\"]", source, re.DOTALL)
    if m:
        return m.group(1)
    m = re.search(r"(?:modelName|name)\s*:\s*['\"]([^'\"]+)['\"]", source)
    if m:
        return m.group(1)
    m = re.search(r"(?:sequelize\s*\.\s*define|\.define)\s*\(\s*['\"]([^'\"]+)['\"]", source)
    if m:
        return m.group(1)
    return ""


def _model_to_table(file_path: str) -> str:
    name = Path(file_path).stem
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _has_field_prop(body: str, key: str, negate: bool = False) -> bool:
    m = re.search(rf"{key}\s*:\s*(true|false)", body)
    if not m:
        return False
    val = m.group(1) == "true"
    return not val if negate else val


def _extract_field_prop(body: str, key: str, default: str) -> str:
    m = re.search(rf"{key}\s*:\s*(?:DataTypes\s*\.\s*)?(\w+)", body)
    if m:
        return m.group(1)
    m = re.search(rf"{key}\s*:\s*['\"]([^'\"]+)['\"]", body)
    if m:
        return m.group(1)
    return default


def _map_sequelize_type(t: str) -> str:
    mapping = {
        "STRING": "VARCHAR", "TEXT": "TEXT", "INTEGER": "INTEGER",
        "BIGINT": "BIGINT", "FLOAT": "FLOAT", "DOUBLE": "DOUBLE",
        "BOOLEAN": "BOOLEAN", "DATE": "TIMESTAMP", "DATEONLY": "DATE",
        "JSON": "JSON", "JSONB": "JSONB", "UUID": "UUID",
        "ENUM": "VARCHAR", "ARRAY": "ARRAY",
    }
    return mapping.get(t.upper(), t.upper())


def _map_typeorm_type(t: str) -> str:
    mapping = {
        "string": "VARCHAR", "text": "TEXT", "number": "INTEGER",
        "int": "INTEGER", "bigint": "BIGINT", "float": "FLOAT",
        "boolean": "BOOLEAN", "date": "TIMESTAMP", "json": "JSON",
    }
    return mapping.get(t.lower(), t.upper())
