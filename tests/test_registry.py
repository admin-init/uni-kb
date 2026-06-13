from __future__ import annotations

import pytest
from uni_kb.parsers.base import ParseResult, ParserPlugin
from uni_kb.parsers.registry import ParserRegistry


class FakeJavaParser(ParserPlugin):
    def language(self) -> str:
        return "java"

    def detect(self, file_path: str, source: str | None = None) -> bool:
        return file_path.endswith(".java")

    def parse(self, file_path: str, source: str) -> ParseResult:
        return ParseResult()


class FakePythonParser(ParserPlugin):
    def language(self) -> str:
        return "python"

    def detect(self, file_path: str, source: str | None = None) -> bool:
        return file_path.endswith(".py")

    def parse(self, file_path: str, source: str) -> ParseResult:
        return ParseResult()


@pytest.fixture(autouse=True)
def reset_registry():
    ParserRegistry.reset()
    yield
    ParserRegistry.reset()


class TestParserRegistry:
    def test_register_and_get(self):
        plugin = FakeJavaParser()
        ParserRegistry.register(plugin)
        plugins = ParserRegistry.get("java")
        assert len(plugins) == 1
        assert isinstance(plugins[0], FakeJavaParser)

    def test_get_returns_empty_for_unknown_language(self):
        plugins = ParserRegistry.get("nonexistent")
        assert plugins == []

    def test_find_returns_first_match(self):
        ParserRegistry.register(FakeJavaParser())
        ParserRegistry.register(FakePythonParser())
        found = ParserRegistry.find("Test.java")
        assert found is not None
        assert found.language() == "java"

    def test_find_returns_none_when_no_match(self):
        ParserRegistry.register(FakeJavaParser())
        found = ParserRegistry.find("script.rb")
        assert found is None

    def test_all_plugins(self):
        ParserRegistry.register(FakeJavaParser())
        ParserRegistry.register(FakePythonParser())
        all_plugins = ParserRegistry.all_plugins()
        assert len(all_plugins) == 2

    def test_supported_languages(self):
        ParserRegistry.register(FakeJavaParser())
        ParserRegistry.register(FakePythonParser())
        langs = ParserRegistry.supported_languages()
        assert "java" in langs
        assert "python" in langs

    def test_reset_clears_everything(self):
        ParserRegistry.register(FakeJavaParser())
        ParserRegistry.reset()
        assert ParserRegistry.get("java") == []
        assert ParserRegistry.all_plugins() == []

    def test_discover_from_entry_points(self):
        ParserRegistry.discover()
        ParserRegistry.load_all()
        languages = ParserRegistry.supported_languages()
        assert "java" in languages

    def test_discover_is_idempotent(self):
        ParserRegistry.discover()
        ParserRegistry.discover()
        ParserRegistry.load_all()
        langs = ParserRegistry.supported_languages()
        assert "java" in langs

    def test_register_multiple_same_language(self):
        ParserRegistry.register(FakeJavaParser())
        ParserRegistry.register(FakeJavaParser())
        plugins = ParserRegistry.get("java")
        assert len(plugins) == 2
