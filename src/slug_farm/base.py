import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class SlugResult:
    ok: bool
    status: int
    output: Any
    error: str = ""
    tokens: list[Any] = field(default_factory=list)


@dataclass(slots=True)
class CommandSegment:
    command: Optional[str] = None
    kwargs: dict = field(default_factory=dict)


def default_command_formatter(command: Optional[str] = None):
    """Does Nothing"""
    return command


def default_kwarg_formatter(kwargs: Optional[dict[str, Any]] = None):
    """Does Nothing"""
    return kwargs


class Slug:
    def __init__(
        self,
        name,
        command: Optional[str] = None,
        slug_kwargs: Optional[dict[str, Any]] = None,
        base_command_segments: Optional[List[CommandSegment]] = None,
    ):
        self.name = name
        self.command_segments = base_command_segments or []

        self.command_segments = self.add_command(
            command=command, slug_kwargs=slug_kwargs
        )

    def branch(
        self,
        branch_name: str,
        command: Optional[str] = None,
        slug_kwargs: Optional[dict[str, Any]] = None,
        replace_kwargs=False,
        **kwargs,
    ) -> "Slug":
        """Creates a new instance with an additional command-flag segment."""
        new_name = f"{self.name}.{branch_name}"
        if replace_kwargs:
            return self.__class__(
                name=new_name,
                command=command,
                slug_kwargs=slug_kwargs,
            )
        return self.__class__(
            name=new_name,
            command=command,
            slug_kwargs=slug_kwargs,
            base_command_segments=copy.deepcopy(self.command_segments),
        )

    def format_commands(self, command: Optional[str] = None) -> Any:
        """Placeholder default formatter. Does Nothing"""
        return command

    def format_kwargs(self, kwargs: Optional[dict[str, Any]] = None) -> Any:
        """Placeholder default formatter. Does Nothing"""
        return kwargs

    def add_command(
        self,
        command: Optional[str] = None,
        slug_kwargs: Optional[dict] = None,
    ) -> list[CommandSegment]:
        new_command_segments = (
            copy.deepcopy(self.command_segments) if self.command_segments else []
        )

        if not command and not slug_kwargs:
            return new_command_segments

        if slug_kwargs and not command:
            if new_command_segments:
                # Case A: Append to existing context
                print("Appending kwargs to last command segment")
                new_command_segments[-1].kwargs.update(slug_kwargs)
            else:
                # Case B: No history yet, create a "Commandless" segment for these flags
                print("Creating a commandless segment for orphaned kwargs")
                new_command_segments.append(
                    CommandSegment(command=None, kwargs=slug_kwargs)
                )
            return new_command_segments

        if not slug_kwargs:
            slug_kwargs = {}

        new_command_segments.append(CommandSegment(command=command, kwargs=slug_kwargs))
        return new_command_segments

    def test_print(
        self,
        tokens: list[Any],
        processed_tokens: Optional[Any] = None,
    ) -> Any:
        if processed_tokens:
            try:
                print(processed_tokens)
                return None
            except Exception:
                pass
        for token in tokens:
            print(str(token))
        return tokens

    def assemble_tokens(
        self,
        command: Optional[str] = None,
        task_kwargs: Optional[dict[str, Any]] = None,
    ):
        task_commands = self.add_command(command=command, slug_kwargs=task_kwargs)
        if isinstance(self.command_segments, list):
            tokens = [
                (self.format_commands(str(x.command)), self.format_kwargs(x.kwargs))
                for x in task_commands
            ]
        else:
            print("Nothing to assemble!")
            tokens = []
        return tokens

    def process_tokens(self, tokens) -> Any:
        """Placeholder with default placement in pipeline to more unusual expressions of tokens"""
        return tokens

    def handle_response(
        self,
        response,
        tokens: list[Any],
        processed_tokens: Optional[Any] = None,
    ) -> SlugResult:
        output_str = str(response)
        if response and processed_tokens:
            output_str = f"{processed_tokens}: {output_str}"
        return SlugResult(
            ok=False,
            status=0,
            output=str(f"{str(processed_tokens)}: {str(response)}") or "Default Result",
            tokens=tokens,
        )

    def execute(
        self,
        tokens: list[Any],
        processed_tokens: Optional[Any | None] = None,
    ) -> Any:
        print(
            "You didn't instantiate this with a usable command.  Its just a sad useless Slug"
        )
        if not processed_tokens:
            processed_tokens = tokens
        return SlugResult(
            ok=True,
            status=200,
            output="You didn't instantiate this with a usable command.  Its just a sad useless Slug",
            tokens=tokens,
        )

    def __call__(
        self,
        command: Optional[str] = None,
        task_kwargs: Optional[dict[str, Any]] = None,
        test=False,
    ) -> SlugResult:
        tokens = self.assemble_tokens(command=command, task_kwargs=task_kwargs)
        processed_tokens = self.process_tokens(tokens)
        if test:
            print(f"\n--- DRY RUN: {self.name} ---")
            print_output = self.test_print(tokens, processed_tokens)
            return SlugResult(
                ok=True,
                status=200,
                output=print_output,
                error="Dont Think So",
                tokens=tokens,
            )
        response = self.execute(
            tokens=tokens,
            processed_tokens=processed_tokens,
        )
        if isinstance(response, SlugResult):
            return response
        return self.handle_response(response, tokens)
