from __future__ import annotations

import sys
from typing import Callable

from uni_kb.parsers.base import ParserPlugin

if sys.version_info >= (3, 12):
    from importlib.metadata import entry_points
else:
    from importlib_metadata import entry_points


ENTRY_POINT_GROUP = "uni_kb.parsers"


class ParserRegistry:
    _plugins: dict[str, list[ParserPlugin]] = {}
    _by_extension: dict[str, list[ParserPlugin]] = {}
    _scanned: bool = False
    _register_funcs: list[Callable[[], list[ParserPlugin]]] = []

    @classmethod
    def discover(cls) -> None:
        if cls._scanned:
            return

        try:
            eps = entry_points(group=ENTRY_POINT_GROUP)
        except TypeError:
            eps = entry_points().get(ENTRY_POINT_GROUP, [])

        for ep in eps:
            try:
                register_fn = ep.load()
                cls._register_funcs.append(register_fn)
            except Exception as e:
                import logging
                logging.warning(f"Failed to load entry point {ep.name}: {e}")

        cls._scanned = True

    @classmethod
    def load_all(cls) -> None:
        cls.discover()
        for register_fn in cls._register_funcs:
            try:
                plugins = register_fn()
                for plugin in plugins:
                    cls.register(plugin)
            except Exception as e:
                import logging
                logging.warning(f"Failed to load parser plugin: {e}")

    @classmethod
    def register(cls, plugin: ParserPlugin) -> None:
        lang = plugin.language()
        cls._plugins.setdefault(lang, []).append(plugin)

    @classmethod
    def get(cls, language: str) -> list[ParserPlugin]:
        return cls._plugins.get(language, [])

    @classmethod
    def find(cls, file_path: str, source: str | None = None) -> ParserPlugin | None:
        cls.load_all()
        for plugins in cls._plugins.values():
            for plugin in plugins:
                try:
                    if plugin.detect(file_path, source):
                        return plugin
                except Exception:
                    continue
        return None

    @classmethod
    def all_plugins(cls) -> list[ParserPlugin]:
        result: list[ParserPlugin] = []
        for plugins in cls._plugins.values():
            result.extend(plugins)
        return result

    @classmethod
    def supported_languages(cls) -> list[str]:
        return list(cls._plugins.keys())

    @classmethod
    def reset(cls) -> None:
        cls._plugins.clear()
        cls._by_extension.clear()
        cls._scanned = False
        cls._register_funcs.clear()
