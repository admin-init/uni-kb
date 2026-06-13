from __future__ import annotations

from uni_kb.parsers.base import ParseResult, ParsedEntity, ParserPlugin


class JavaEntityParser(ParserPlugin):
    def language(self) -> str:
        return "java"

    def detect(self, file_path: str, source: str | None = None) -> bool:
        if not file_path.endswith(".java"):
            return False
        if source is None:
            with open(file_path) as f:
                source = f.read()
        return "@Entity" in source or "@Table" in source or "@Document" in source

    def parse(self, file_path: str, source: str) -> ParseResult:
        import re

        result = ParseResult()
        package_name = self._extract_package(source)
        annotation_pattern = re.compile(r"@(\w+)(?:\([^)]*\))?\s*")
        annotations = [m.group(1) for m in annotation_pattern.finditer(source)]

        class_pattern = re.compile(
            r"public\s+class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w\s,]+))?\s*\{",
            re.DOTALL,
        )
        class_match = class_pattern.search(source)
        if class_match is None:
            return result

        class_name = class_match.group(1)

        table_name = self._extract_table_name(source, class_name)

        fields = self._extract_fields(source)
        primary_keys = [f["name"] for f in fields if f.get("is_primary")]

        indexes: list[dict] = []
        table_match = re.search(r"@Table\s*\(([^)]*)\)", source, re.DOTALL)
        if table_match:
            indexes = self._extract_table_indexes(table_match.group(1))

        entity = ParsedEntity(
            name=class_name,
            table_name=table_name,
            fields=fields,
            annotations=annotations,
            package=package_name,
            file_path=file_path,
            primary_keys=primary_keys,
            indexes=indexes,
        )
        result.entities.append(entity)
        return result

    def _extract_package(self, source: str) -> str:
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("package "):
                return stripped.removeprefix("package ").rstrip(";").strip()
        return ""

    def _extract_table_name(self, source: str, class_name: str) -> str:
        import re

        table_match = re.search(r'@Table\s*\(\s*(?:name\s*=\s*)?\s*"([^"]*)"', source)
        if table_match:
            return table_match.group(1)

        entity_table = re.search(r'@Entity\s*\(\s*name\s*=\s*"([^"]*)"', source)
        if entity_table:
            return entity_table.group(1)

        return self._camel_to_snake(class_name)

    def _camel_to_snake(self, name: str) -> str:
        import re

        s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
        s2 = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s1)
        return s2.lower()

    def _extract_fields(self, source: str) -> list[dict]:
        import re

        fields: list[dict] = []

        field_pattern = re.compile(
            r"@(?:Id|Column|GeneratedValue|JoinColumn|ManyToOne|OneToMany|ManyToMany|OneToOne"
            r"|Lob|Enumerated|Transient|Version|CreatedDate|LastModifiedDate|NotNull"
            r"|Size|Min|Max|Pattern|Email|JsonIgnore|JsonProperty|Field)\s*(?:\([^)]*\)\s*)*\n?"
            r"((?:(?!class|interface|enum)[@\w\s<>(?:\[\])]+?)\s+(\w+)\s*[=;])",
            re.MULTILINE,
        )

        for match in field_pattern.finditer(source):
            block = match.group(1)
            field_name = match.group(2)

            prev_delim = source.rfind(";", 0, match.start())
            if prev_delim == -1:
                prev_delim = source.find("{", 0, match.start())
            annotations_block = source[max(0, prev_delim) : match.end()]
            field_annotations = self._extract_field_annotations(annotations_block, "")

            is_primary = "Id" in field_annotations.get("annotations", [])
            is_transient = "Transient" in field_annotations.get("annotations", [])

            if is_transient:
                continue

            column_name = field_annotations.get("column_name", field_name)
            column_name = self._camel_to_snake(column_name)

            nullable = field_annotations.get("nullable", True)
            col_type = self._extract_type_info(block, field_name)

            field_data: dict = {
                "name": field_name,
                "type": col_type.get("type", "String"),
                "column_name": column_name,
                "nullable": nullable,
                "is_primary": is_primary,
                "annotations": field_annotations.get("annotations", []),
                "length": field_annotations.get("length"),
                "unique": field_annotations.get("unique", False),
                "default_value": field_annotations.get("default_value"),
                "relationship": field_annotations.get("relationship"),
            }
            fields.append(field_data)

        return fields

    def _extract_field_annotations(self, preceding: str, field_line: str) -> dict:
        import re

        result: dict = {"annotations": []}

        for ann_match in re.finditer(
            r"@(Id|GeneratedValue|Column|JoinColumn|ManyToOne|OneToMany|ManyToMany|OneToOne"
            r"|Enumerated|NotNull|Size|Min|Max|Pattern|Email|Lob|Transient"
            r"|JsonIgnore|JsonProperty|Version|CreatedDate|LastModifiedDate)"
            r"\s*(?:\(([^)]*)\))?",
            preceding + field_line,
        ):
            name = ann_match.group(1)
            args = ann_match.group(2) or ""
            result["annotations"].append(name)

            if name in ("ManyToOne", "OneToMany", "ManyToMany", "OneToOne"):
                result["relationship"] = name

            if name == "Column":
                col_name = re.search(r'name\s*=\s*"([^"]*)"', args)
                if col_name:
                    result["column_name"] = col_name.group(1)

                nullable_match = re.search(r"nullable\s*=\s*(true|false)", args)
                if nullable_match:
                    result["nullable"] = nullable_match.group(1) == "true"

                length_match = re.search(r"length\s*=\s*(\d+)", args)
                if length_match:
                    result["length"] = int(length_match.group(1))

                unique_match = re.search(r"unique\s*=\s*(true|false)", args)
                if unique_match:
                    result["unique"] = unique_match.group(1) == "true"

            if name == "JoinColumn":
                col_name = re.search(r'name\s*=\s*"([^"]*)"', args)
                if col_name:
                    result["column_name"] = col_name.group(1)

                nullable_match = re.search(r"nullable\s*=\s*(true|false)", args)
                if nullable_match:
                    result["nullable"] = nullable_match.group(1) == "true"

            if name == "NotNull":
                result["nullable"] = False

            if name == "Size":
                max_match = re.search(r"max\s*=\s*(\d+)", args)
                if max_match:
                    result["length"] = int(max_match.group(1))

        return result

    def _extract_type_info(self, field_line: str, field_name: str) -> dict:

        parts = field_line.split(field_name)[0].split()
        type_str = parts[0] if parts else "String"
        return {"type": type_str}

    def _extract_table_indexes(self, table_args: str) -> list[dict]:
        import re

        indexes: list[dict] = []
        for idx_match in re.finditer(
            r"@Index\s*\(\s*name\s*=\s*\"([^\"]+)\"\s*,\s*columnList\s*=\s*\"([^\"]+)\"(?:\s*,\s*unique\s*=\s*(true|false))?",
            table_args,
        ):
            indexes.append(
                {
                    "name": idx_match.group(1),
                    "columns": idx_match.group(2).split(","),
                    "unique": idx_match.group(3) == "true" if idx_match.group(3) else False,
                }
            )
        for unique_match in re.finditer(
            r"@UniqueConstraint\s*\(\s*name\s*=\s*\"([^\"]+)\"\s*,\s*columnNames\s*=\s*\{([^}]+)\}",
            table_args,
        ):
            cols = [c.strip().strip('"') for c in unique_match.group(2).split(",")]
            indexes.append({"name": unique_match.group(1), "columns": cols, "unique": True})
        return indexes
