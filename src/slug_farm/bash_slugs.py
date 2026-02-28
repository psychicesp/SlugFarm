import shlex
import subprocess
from typing import Any, Optional, List, Callable
from src.slug_farm.base import Slug, SlugResult, CommandSegment, default_command_formatter


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


class BashSlug(Slug):
    def __init__(
        self,
        name: str,
        command: Optional[str] = None,
        slug_kwargs: Optional[dict[str, Any]] = None,
        base_command_segments: Optional[List[CommandSegment]] = None,
        kwarg_formatter: Callable[[dict], list[str]] = bash_kwarg_tokens,
        command_formatter: Callable[[str], Any] = default_command_formatter,
    ):
        super().__init__(
            name=name,
            command=command,
            slug_kwargs=slug_kwargs,
            base_command_segments=base_command_segments,
            kwarg_formatter=kwarg_formatter,
            command_formatter=command_formatter
        )
        
    def _flatten_tokens(self, tokens: list[tuple[Optional[str], list[str]]]) -> list[str]:
        """Internal helper to turn the (cmd, [flags]) list into a single list of strings."""
        flat = []
        for cmd, flags in tokens:
            if cmd and cmd != "None":
                flat.extend(shlex.split(cmd))
            if flags:
                flat.extend(flags)
        return flat

    def _test_print(self, tokens: list[tuple[Optional[str], list[str]]]):
        """Override to show the actual bash command line."""
        flat = self._flatten_tokens(tokens)
        print(f"Command: {' '.join(flat)}")

    def execute(self, tokens: list[tuple[Optional[str], list[str]]]) -> SlugResult:
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
                final_flag_list, 
                capture_output=True, 
                text=True,
                check=True
            )
            return SlugResult(
                ok=True, 
                status=cp.returncode, 
                output=cp.stdout, 
                error=cp.stderr, 
                tokens=final_flag_list
            )
        except subprocess.CalledProcessError as e:
            return SlugResult(
                ok=False, 
                status=e.returncode, 
                output=e.stdout, 
                error=e.stderr, 
                tokens=final_flag_list
            )
        except Exception as e:
            return SlugResult(
                ok=False, 
                status=1, 
                output="", 
                error=str(e), 
                tokens=final_flag_list
            )