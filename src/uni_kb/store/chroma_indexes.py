from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

from uni_kb.parsers.base import ParseResult, ParsedEndpoint, ParsedEntity

logger = logging.getLogger(__name__)

MAX_BATCH_SIZE = 96

COLLECTION_NAMES = [
    "code_java_controller",
    "code_java_service",
    "code_java_entity",
    "code_java_mapper",
    "code_typescript_admin",
    "code_typescript_game",
    "specs_api",
    "specs_business_logic",
    "specs_data_model",
    "specs_auth",
    "specs_config",
    "db_schema",
    "project_docs",
    "migration_checklists",
]


class ChromaIndexes:
    def __init__(self, persist_dir: str | Path) -> None:
        self._persist_dir = Path(persist_dir)
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self._persist_dir))
        self._ef = embedding_functions.DefaultEmbeddingFunction()
        self._collections: dict[str, chromadb.Collection] = {}

    def _get_collection(self, name: str) -> chromadb.Collection:
        if name not in self._collections:
            self._collections[name] = self._client.get_or_create_collection(
                name=name, embedding_function=self._ef
            )
        return self._collections[name]

    def get_all_collections(self) -> list[str]:
        return [c for c in COLLECTION_NAMES if c in self._collections]

    def ensure_all(self) -> None:
        for name in COLLECTION_NAMES:
            self._get_collection(name)

    def index_code(self, result: ParseResult, source: str, language: str = "java") -> None:
        collections: dict[str, list[str]] = {}
        if language == "java":
            collections["code_java_controller"] = []
            collections["code_java_service"] = []
            collections["code_java_entity"] = []
            collections["code_java_mapper"] = []

        for cls in result.classes:
            doc = _class_to_doc(cls)
            if cls.type == "controller":
                collections.get("code_java_controller", []).append(doc)
            elif cls.type in ("service", "repository", "component"):
                collections.get("code_java_service", []).append(doc)

        for endpoint in result.endpoints:
            doc = _endpoint_to_doc(endpoint)
            trg = "code_java_controller" if _is_rest_endpoint(endpoint) else "code_java_mapper"
            collections[trg].append(doc)

        for entity in result.entities:
            doc = _entity_to_doc(entity)
            collections.get("code_java_entity", []).append(doc)

        for coll_name, docs in collections.items():
            if not docs:
                continue
            coll = self._get_collection(coll_name)
            for i in range(0, len(docs), MAX_BATCH_SIZE):
                batch = docs[i : i + MAX_BATCH_SIZE]
                ids = [f"{coll_name}_{i + j}" for j in range(len(batch))]
                coll.add(documents=batch, ids=ids)

    def index_db_schema(self, schema_text: str) -> None:
        if not schema_text.strip():
            return
        coll = self._get_collection("db_schema")
        coll.add(documents=[schema_text], ids=["db_schema_current"])

    def search(self, collection: str, query: str, k: int = 5) -> list[dict[str, Any]]:
        coll = self._get_collection(collection)
        results = coll.query(query_texts=[query], n_results=k)
        docs: list[dict[str, Any]] = []
        ids_list = results.get("ids", [[]])[0]
        docs_list = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        for i in range(len(ids_list)):
            docs.append({
                "id": ids_list[i],
                "document": docs_list[i] if i < len(docs_list) else "",
                "distance": distances[i] if i < len(distances) else 0.0,
            })
        return docs

    def count(self, collection: str) -> int:
        coll = self._get_collection(collection)
        return coll.count()


def _class_to_doc(cls: Any) -> str:
    return (
        f"Class: {cls.name}\n"
        f"Type: {cls.type}\n"
        f"Package: {cls.package}\n"
        f"File: {cls.file_path}\n"
        f"Annotations: {', '.join(cls.annotations)}"
    )


def _endpoint_to_doc(ep: ParsedEndpoint) -> str:
    return (
        f"Endpoint: {ep.http_method} {ep.path}\n"
        f"Method: {ep.class_name}.{ep.method_name}\n"
        f"Auth: {'required' if ep.auth_required else 'none'}\n"
        f"Request: {ep.request_schema or 'none'}\n"
        f"Response: {ep.response_schema or 'none'}"
    )


def _entity_to_doc(entity: ParsedEntity) -> str:
    fields_str = "\n".join(
        f"  {f.get('name', f.get('column_name', '?'))} : {f.get('type', f.get('field_type', '?'))}"
        for f in entity.fields
    )
    return (
        f"Entity: {entity.name}\n"
        f"Table: {entity.table_name}\n"
        f"Package: {entity.package}\n"
        f"Keys: {', '.join(entity.primary_keys)}\n"
        f"Fields:\n{fields_str}"
    )


def _is_rest_endpoint(ep: ParsedEndpoint) -> bool:
    return "/api" in ep.path or not ep.path.startswith("/api/mapper")
