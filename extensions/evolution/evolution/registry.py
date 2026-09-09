"""Registry for independently deployable evolution methods."""

from __future__ import annotations

from collections.abc import Iterable

from evolution.api import EvolutionMethod


class EvolutionMethodRegistry:
    def __init__(self, methods: Iterable[EvolutionMethod] = ()) -> None:
        self._methods: dict[str, EvolutionMethod] = {}
        for method in methods:
            self.register(method)

    def register(self, method: EvolutionMethod) -> None:
        if not isinstance(method, EvolutionMethod):
            raise TypeError("evolution method does not implement the PAOS interface")
        if method.method_id in self._methods:
            raise ValueError(f"evolution method already registered: {method.method_id}")
        self._methods[method.method_id] = method

    def get(self, method_id: str) -> EvolutionMethod:
        try:
            return self._methods[method_id]
        except KeyError as exc:
            raise KeyError(f"evolution method is not registered: {method_id}") from exc

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._methods))


__all__ = ["EvolutionMethodRegistry"]
