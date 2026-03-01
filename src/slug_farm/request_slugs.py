from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Optional

import requests
from yarl import URL

from src.slug_farm.base import Slug, SlugResult


@dataclass(slots=True)
class RequestPackage:
    """Internal transport for Requests data through the Slug pipeline."""

    method: str
    url: str
    params: dict
    json_body: dict
    headers: dict
    timeout: int


class RequestSlug(Slug):
    def __init__(
        self,
        name: str,
        base_url: str | URL = URL(),
        method: str = "GET",
        headers: Optional[dict] = None,
        payload_data: Optional[dict] = None,
        params: Optional[dict] = None,
        timeout: int = 120,
        include_params: Optional[Iterable[str]] = None,
        exclude_params: Optional[Iterable[str]] = None,
        base_command_segments: Optional[list] = None,  # Added to support branch
    ):
        # We pass the base_url as the 'command' to the first segment
        super().__init__(
            name=name,
            command=str(base_url) if not base_command_segments else None,
            base_command_segments=base_command_segments,
        )

        self.method = method.upper()
        self.headers = headers or {}
        self.params = params or {}  # Static base params
        self.payload_data = payload_data or {}
        self.timeout = timeout

        self.include_params = set(include_params) if include_params else None
        self.exclude_params = set(exclude_params) if exclude_params else None

    def branch(
        self,
        branch_name: str,
        url_segment: str = "",
        sub_params: Optional[dict] = None,
        sub_payload: Optional[dict] = None,
        method: Optional[str] = None,
        sub_headers: Optional[dict] = None,
        timeout: Optional[int] = None,
    ) -> "RequestsSlug":
        """Creates a sub-route or specialized version of the current request."""

        # 1. Use base class logic to add the new URL segment and params/payload
        # We treat sub_params/sub_payload as the 'kwargs' for this segment
        combined_kwargs = {**(sub_params or {}), **(sub_payload or {})}
        new_segments = self.add_command(
            command=url_segment, slug_kwargs=combined_kwargs
        )

        # 2. Merge headers and state
        new_headers = {**self.headers, **(sub_headers or {})}

        return self.__class__(
            name=f"{branch_name}.{self.name}",
            method=method or self.method,
            headers=new_headers,
            params=self.params,  # Base params stay base
            payload_data=self.payload_data,
            timeout=timeout or self.timeout,
            include_params=self.include_params,
            exclude_params=self.exclude_params,
            base_command_segments=new_segments,
        )

    def _filter_params(self, params: dict) -> dict:
        if self.include_params is None and self.exclude_params is None:
            return params

        filtered = {}
        for k, v in params.items():
            if self.include_params is not None and k not in self.include_params:
                continue
            if self.exclude_params is not None and k in self.exclude_params:
                continue
            filtered[k] = v
        return filtered

    def assemble_tokens(
        self, command: Optional[str] = None, task_kwargs: Optional[dict] = None
    ) -> list[RequestPackage]:
        """Collapses all segments into a single RequestPackage."""

        all_segments = self.add_command(command=command, slug_kwargs=task_kwargs)
        url_obj = URL(all_segments[0].command or "")

        accumulated_url_params = deepcopy(self.params)
        accumulated_payload = deepcopy(self.payload_data)

        for i, seg in enumerate(all_segments):
            # i > 0 because segment 0 is the base URL
            if i > 0 and seg.command:
                url_obj = url_obj / seg.command

            # For REST, we have to decide if kwargs are params or payload.
            # Usually, GET/DELETE = params, POST/PUT/PATCH = JSON.
            if seg.kwargs:
                if self.method in ["POST", "PUT", "PATCH"]:
                    accumulated_payload.update(seg.kwargs)
                else:
                    accumulated_url_params.update(seg.kwargs)

        # Final URL processing (filtering and path interpolation)
        final_params = self._filter_params(accumulated_url_params)

        return [
            RequestPackage(
                method=self.method,
                url=str(url_obj),
                params=final_params,
                json_body=accumulated_payload,
                headers=self.headers,
                timeout=self.timeout,
            )
        ]

    def execute(self, tokens: list[Any], processed_tokens: Any = None) -> Any:
        if not tokens or not isinstance(tokens[0], RequestPackage):
            return SlugResult(False, 500, "Invalid tokens", tokens=tokens)

        pkg: RequestPackage = tokens[0]

        try:
            resp = requests.request(
                method=pkg.method,
                url=pkg.url,
                params=pkg.params,
                json=pkg.json_body if pkg.method in ["POST", "PUT", "PATCH"] else None,
                headers=pkg.headers,
                timeout=pkg.timeout,
            )
            return resp
        except Exception as e:
            return SlugResult(False, 500, str(e), tokens=tokens)

    def handle_response(
        self, response: Any, tokens: list[Any], processed_tokens: Any = None
    ) -> SlugResult:
        if isinstance(response, SlugResult):
            return response

        try:
            data = response.json()
        except:
            data = response.text

        return SlugResult(
            ok=response.ok,
            status=response.status_code,
            output=data,
            error="" if response.ok else response.text,
            tokens=tokens,
        )
