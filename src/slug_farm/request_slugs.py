from dataclasses import dataclass
from typing import Any, Iterable, Optional

import requests
from yarl import URL

from src.slug_farm.base import CommandSegment, Slug, SlugResult


@dataclass(slots=True)
class RequestPackage:
    """Internal transport for Requests data through the Slug pipeline."""

    method: str
    url: str
    params: dict
    json_body: dict
    headers: dict
    timeout: int


class RequestsSlug(Slug):
    def __init__(
        self,
        name: str,
        segments: list[CommandSegment] = None,
        method: str = "GET",
        headers: Optional[dict] = None,
        payload_data: Optional[dict] = None,
        params: Optional[dict] = None,
        timeout: int = 120,
        kwarg_formatter=lambda x: dict(x),
        include_params: Optional[Iterable[str]] = None,
        exclude_params: Optional[Iterable[str]] = None,
    ):
        super().__init__(name, segments, kwarg_formatter=kwarg_formatter)
        self.method = method.upper()
        self.headers = headers or {}
        self.params = params or {}
        self.payload_data = payload_data or {}
        self.timeout = timeout

        # Initialize as Sets or None
        self.include_params = set(include_params) if include_params else None
        self.exclude_params = set(exclude_params) if exclude_params else None

    def branch(
        self,
        name: str,
        sub_path: str = "",
        sub_params: Optional[dict] = None,
        sub_payload: Optional[dict] = None,
        method: Optional[str] = None,
        headers: Optional[dict] = None,
        include_params: Optional[Iterable[str]] = None,
        exclude_params: Optional[Iterable[str]] = None,
    ) -> "RequestsSlug":
        # Pass sub_params to super().branch to store in segment flags
        child = super().branch(name, sub_path, sub_params)

        child.payload_data = {**self.payload_data, **(sub_payload or {})}
        child.headers = {**self.headers, **(headers or {})}
        child.params = {**self.params, **(sub_params or {})}
        child.method = method.upper() if method else self.method
        child.timeout = self.timeout

        # Handle Filter Inheritance
        child.include_params = (
            set(include_params) if include_params else self.include_params
        )

        if exclude_params:
            parent_exclude = self.exclude_params or set()
            child.exclude_params = parent_exclude.union(set(exclude_params))
        else:
            child.exclude_params = self.exclude_params

        return child

    def _filter_params(self, params: dict) -> dict:
        """Safe membership testing for sets."""
        filtered = {}
        for k, v in params.items():
            if self.include_params is not None:
                if k not in self.include_params:
                    continue

            if self.exclude_params is not None:
                if k in self.exclude_params:
                    continue

            filtered[k] = v
        return filtered

    def _assemble_tokens(
        self, final_word: str = "", final_kwargs: Optional[dict] = None
    ) -> list[Any]:
        base_word = self.segments[0].word if self.segments else ""
        url_obj = URL(base_word)
        for seg in self.segments[1:]:
            if seg.word:
                url_obj = url_obj / seg.word
        if final_word:
            url_obj = url_obj / final_word

        all_params = {**self.params}
        for seg in self.segments:
            all_params.update(seg.flags)

        if url_obj.query:
            all_params.update(dict(url_obj.query))
            url_obj = url_obj.with_query({})

        final_path = url_obj.path
        for key, val in all_params.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in final_path:
                final_path = final_path.replace(placeholder, str(val))

        final_params = self._filter_params(all_params)
        final_url = str(url_obj.with_path(final_path))

        full_payload = {**self.payload_data, **(final_kwargs or {})}

        return [
            RequestPackage(
                method=self.method,
                url=final_url,
                params=final_params,
                json_body=full_payload,
                headers=self.headers,
                timeout=self.timeout,
            )
        ]

    def execute(self, tokens: list[Any]) -> SlugResult:
        if not tokens or not isinstance(tokens[0], RequestPackage):
            return SlugResult(False, 500, "", "Invalid RequestPackage", [])

        pkg: RequestPackage = tokens[0]

        request_config = {
            "method": pkg.method,
            "url": pkg.url,
            "params": pkg.params,
            "headers": pkg.headers,
            "timeout": pkg.timeout,
        }

        if pkg.method in ["POST", "PUT", "PATCH", "DELETE"]:
            request_config["json"] = pkg.json_body
        else:
            request_config["params"].update(pkg.json_body)

        try:
            resp = requests.request(**request_config)
            return self._handle_response(resp)
        except Exception as e:
            return SlugResult(False, 500, "", str(e), [f"{pkg.method} {pkg.url}"])

    def _handle_response(self, resp: requests.Response) -> SlugResult:
        try:
            output = resp.json()
        except Exception:
            output = resp.text
        return SlugResult(
            ok=resp.ok,
            status=resp.status_code,
            output=output,
            error="" if resp.ok else resp.text,
            tokens=[f"{resp.request.method} {resp.url}"],
        )
