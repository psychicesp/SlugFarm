import traceback
from typing import Any, Callable, Optional

from src.slug_farm.base import Slug, SlugResult


class PythonSlug(Slug):
    """Completely unnecessary in a vacuum,
    but if you wanted to wrap a python callable in a slug so it is accessible
    in the same structure as your other slugs, you can use this.
    Putting in a command will do nothing and all kwargs will pass to the python func."""

    def __init__(
        self,
        name: str,
        python_func=Callable[..., Any],
    ):
        self.name = name
        self.python_func = staticmethod(python_func)
        self.func_name = getattr(python_func, "__name__", str(python_func))

    def assemble_tokens(
        self,
        command: Optional[str] = None,
        task_kwargs: Optional[dict[str, Any]] = None,
    ):
        return [task_kwargs or {}]

    def test_print(
        self,
        tokens: list[Any],
        processed_tokens: Optional[Any] = None,
    ) -> Any:
        kwargs = tokens[0]
        kwarg_string = ", ".join([f"{x}: {y}" for x, y in kwargs.items()])
        print(f"{self.func_name}({kwarg_string})")
        return kwargs

    def execute(
        self,
        tokens: list[Any],
        processed_tokens: Optional[Any] = None,
    ) -> SlugResult:
        kwargs = tokens[0] if tokens else {}

        try:
            result_data = self.python_func(**kwargs)

            return SlugResult(
                ok=True,
                status=0,
                output=result_data,
                error="",
                tokens=tokens,
            )

        except TypeError as e:
            return SlugResult(
                ok=False,
                status=1,
                output=None,
                error=f"Signature Error in {self.func_name}: {str(e)}",
                tokens=tokens,
            )

        except Exception:
            err_stack = traceback.format_exc()
            return SlugResult(
                ok=False,
                status=1,
                output=None,
                error=err_stack,
                tokens=tokens,
            )
