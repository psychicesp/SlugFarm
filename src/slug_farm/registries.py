


class SlugRegistry:
    def __init__(self):
        self._slugs: Dict[str, "Slug"] = {}

    def register(self, slug: "Slug"):
        """Adds a slug to the registry. Raises ValueError if ID exists."""
        if id in self._slugs:
            existing = self._slugs[id]
            raise ValueError(
                f"Redundant Assignment: ID {id} is already taken by '{existing.name}' "
                f"({type(existing).__name__})"
            )
        self._slugs[id] = slug

    def get(self, id: int) -> Any:
        """Retrieves a slug by ID. Raises KeyError if missing."""
        if id not in self._slugs:
            raise KeyError(f"No slug registered with ID {id}")
        return self._slugs[id]

    def __getitem__(self, id: int) -> Any:
        return self.get(id)

    def __iter__(self):
        return iter(self._slugs.items())
