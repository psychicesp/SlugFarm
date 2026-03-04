import copy
import shlex
import subprocess
from typing import Any, List, Optional

from src.slug_farm.base import CommandSegment, Slug, SlugResult


class BashSlug(Slug):
    def __init__(
        self,
        name: str,
        command: Optional[str] = None,
        slug_kwargs: Optional[dict[str, Any]] = None,
        base_command_segments: Optional[List[CommandSegment]] = None,
    ):
        super().__init__(
            name=name,
            command=command,
            slug_kwargs=slug_kwargs,
            base_command_segments=base_command_segments,
        )

    def branch(
        self,
        branch_name: str,
        command: Optional[str] = None,
        slug_kwargs: Optional[dict[str, Any]] = None,
    ) -> "BashSlug":
        """
        Create a child BashSlug.

        Tip: BashSlug will auto-prefix kwargs adding
            --  in front of words
            - in front of letters.  Some bash commands expect otherwise.
        In `slug_kwargs`, keys starting with '-' (e.g. {"-name": "*.csv"}) to bypass auto-prefixing.
        """

        return self.__class__(
            f"{self.name}.{branch_name}",
            command,
            slug_kwargs,
            base_command_segments=self.command_segments,
        )

    def format_kwargs(self, kwargs: dict[str, Any] | None = None) -> list[str]:
        formatted = []
        if kwargs:
            for k, v in sorted(kwargs.items(), key=lambda x: (len(x[0]), x[0])):
                if k.startswith("-"):
                    flag = k
                else:
                    prefix = "-" if len(k) == 1 else "--"
                    flag = f"{prefix}{k}"

                if v is True:
                    formatted.append(flag)
                elif v is not False and v is not None:
                    formatted.extend([flag, str(v)])
        return formatted

    def test_print(
        self,
        tokens: list[tuple[Optional[str], list[str]]],
        processed_tokens: Optional[Any] = None,
    ):
        flat = []
        for cmd, flags in tokens:
            if cmd and cmd != "None":
                flat.extend(shlex.split(cmd))
            if flags:
                flat.extend(flags)
        command_string = shlex.join(flat)
        print(f"Command: {command_string}")
        return command_string

    def execute(
        self,
        tokens: list[tuple[Optional[str], list[str]]],
        processed_tokens: Optional[Any] = None,
    ):
        """
        Flattens the tuples into a single list of strings for subprocess.
        tokens looks like: [('git', []), ('commit', ['-m', 'msg']), (None, ['--force'])]
        """
        final_flag_list: list[str] = []

        for cmd, flags in tokens:
            if cmd:
                final_flag_list.extend(shlex.split(cmd))

            if flags:
                final_flag_list.extend(flags)

        try:
            cp = subprocess.run(
                final_flag_list, capture_output=True, text=True, check=True
            )
            return SlugResult(
                ok=True,
                status=cp.returncode,
                output=cp.stdout,
                error=cp.stderr,
                tokens=final_flag_list,
            )
        except subprocess.CalledProcessError as e:
            return SlugResult(
                ok=False,
                status=e.returncode,
                output=e.stdout,
                error=e.stderr,
                tokens=final_flag_list,
            )
        except Exception as e:
            return SlugResult(
                ok=False, status=1, output="", error=str(e), tokens=final_flag_list
            )
