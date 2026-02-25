import shlex
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


def bash_kwarg_tokens(kwargs: dict[str, Any]) -> list[str]:
    tokens: list[str] = []

    for k, v in sorted(kwargs.items(), key=lambda kv: (len(kv[0]), kv[0])):
        prefix = "-" if len(k) == 1 else "--"
        flag = f"{prefix}{k}"
        if v is False:
            continue

        if v is None or v is True:
            tokens.append(flag)

        else:
            tokens.extend([flag, str(v)])

    return tokens


@dataclass(slots=True)
class SlugResult:
    ok: bool
    status: int
    output: Any
    error: str = ""
    tokens: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CommandSegment:
    word: str
    flags: dict[str, Any]


class Slug:
    def __init__(
        self,
        name: str,
        segments: list[CommandSegment] = None,
        kwarg_formatter: Optional[Callable[[dict], list[str]]] = None,
    ):
        self.name = name
        self.segments = segments or []
        self.format_kwargs = kwarg_formatter or bash_kwarg_tokens

    def branch(
        self,
        name: str,
        sub_word: str = "",
        sub_kwargs: Optional[dict] = None,
        kwarg_formatter: Optional[Callable[[dict], list[str]]] = None,
    ) -> "Slug":
        """Creates a new instance with an additional command-flag segment."""
        new_segment = CommandSegment(word=sub_word, flags=sub_kwargs or {})
        return self.__class__(
            name=name,
            segments=self.segments + [new_segment],
            kwarg_formatter=kwarg_formatter or self.format_kwargs,
        )

    def _assemble_tokens(
        self, final_word: str = "", final_kwargs: Optional[dict] = None
    ) -> list[str]:
        tokens: list[str] = []
        for seg in self.segments:
            if seg.word:
                tokens.extend(shlex.split(seg.word))
            if seg.flags:
                tokens.extend(self.format_kwargs(seg.flags))

        # Add the leaf command and flags
        if final_word:
            tokens.extend(shlex.split(final_word))
        if final_kwargs:
            tokens.extend(self.format_kwargs(final_kwargs))

        return tokens

    def __call__(
        self,
        command: str = "",
        task_kwargs: Optional[dict] = None,
        test: bool = False,
    ) -> SlugResult:
        tokens = self._assemble_tokens(command, task_kwargs)

        if test:
            print(f"\n--- DRY RUN: {self.name} ---")

            if tokens and not isinstance(tokens[0], str):
                pkg = tokens[0]
                attrs = {k: v for k, v in vars(pkg).items() if not k.startswith("_")}
                for key, val in attrs.items():
                    print(f"{key.replace('_', ' ').title():<10}: {val}")
                display_tokens = [f"OBJECT: {type(pkg).__name__}"]
            else:
                print(f"Command   : {' '.join(map(str, tokens))}")
                display_tokens = tokens

            print("-" * (len(self.name) + 15) + "\n")
            return SlugResult(
                ok=True, status=0, output="Test Mode", tokens=display_tokens
            )

        return self.execute(tokens)

    def execute(self, tokens: list[str]) -> SlugResult:
        try:
            cp = subprocess.run(tokens, capture_output=True, text=True, check=True)
            return SlugResult(
                cp.returncode == 0, cp.returncode, cp.stdout, cp.stderr, tokens
            )
        except Exception as e:
            return SlugResult(False, 1, "", str(e), tokens)


class SlugRegistry:
    def __init__(self, engine, table, schema):
        self._slugs: Dict[int, "Slug"] = {}
        self.engine = engine
        self.table = table
        self.schema = schema

    def register(self, id: int, slug: "Slug"):
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
