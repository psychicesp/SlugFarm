from slug_farm import Slug
from typing import Dict, Any


class SlugRegistry:
    def __init__(self):
        self._slugs: Dict[str, Slug] = {}

    def register(self, slug: Slug):
        """Adds a slug to the registry. Raises ValueError if ID exists."""
        slug_name = slug.name
        if slug_name in self._slugs:
            existing = self._slugs[slug_name]
            raise ValueError(
                f"Redundant Assignment: Name {slug_name} is already taken which is"
                f"({type(existing).__name__})"
            )
        self._slugs[slug_name] = slug

    def get(self, slug_name: str) -> Any:
        """Retrieves a slug by ID. Raises KeyError if missing."""
        if slug_name not in self._slugs:
            raise KeyError(f"No slug registered with name {slug_name}")
        return self._slugs[slug_name]

    def __getitem__(self, slug_name: str) -> Any:
        return self.get(slug_name)

    def __iter__(self):
        return iter(self._slugs.items())
