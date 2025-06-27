from typing import Any

class Entity:
    def __init__(self, name: str):
        self.name = name
        self._components = {}
    def add_component(self, c: Any): self._components[type(c)] = c; return c
    def get_component(self, ct: type): return self._components.get(ct)
    def has_component(self, ct: type): return ct in self._components