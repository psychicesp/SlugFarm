from copy import deepcopy
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
        base_command_segments: Optional[list[CommandSegment]] = None,
    ):
        super().__init__(
            name=name,
            command=str(base_url),
            slug_kwargs=payload_data,
            base_command_segments=base_command_segments,
        )

        self.method = method.upper()
        self.headers = headers or {}
        self.params = params or {}
        self.payload_data = payload_data or {}
        self.timeout = timeout
        self.include_params = set(include_params) if include_params else None
        self.exclude_params = set(exclude_params) if exclude_params else None
        self.command_segments = base_command_segments

    def branch(
        self,
        branch_name: str,
        url_segment: str = "",
        sub_payload: Optional[dict] = None,
        sub_params: Optional[dict] = None,
        method: Optional[str] = None,
        sub_headers: Optional[dict] = None,
        timeout: Optional[int] = None,
    ) -> "RequestsSlug":
        """Creates a sub-route or specialized version of the current request."""

        new_params = {**self.params, **(sub_params or {})}
        new_headers = {**self.headers, **(sub_headers or {})}

        new_command_segments = self.add_command(
            command=url_segment, slug_kwargs=sub_payload
        )

        return self.__class__(
            name=f"{branch_name}.{self.name}",
            method=method or self.method,
            headers=new_headers,
            params=new_params,
            payload_data=self.payload_data,
            timeout=timeout or self.timeout,
            include_params=self.include_params,
            exclude_params=self.exclude_params,
            base_command_segments=new_command_segments,
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
        all_segments = self.add_command(command=command, slug_kwargs=task_kwargs)

        url_obj = URL(all_segments[0].command or "")
        accumulated_params = deepcopy(self.params)
        accumulated_payload = deepcopy(self.payload_data)

        for seg in all_segments[1:]:
            if seg.command:
                url_obj = url_obj / seg.command.lstrip("/")

            if seg.kwargs:
                for k, v in seg.kwargs.items():
                    if self.include_params and k in self.include_params:
                        accumulated_params[k] = v
                    elif self.method == "GET":
                        accumulated_params[k] = v
                    else:
                        accumulated_payload[k] = v

        if command and "?" in command:
            call_query = URL(command).query
            accumulated_params.update(call_query)

        final_params = self._filter_params(accumulated_params)

        return [
            RequestPackage(
                method=self.method,
                url=str(url_obj),
                params=final_params,
                json_body=accumulated_payload if self.method != "GET" else {},
                headers=deepcopy(self.headers),
                timeout=self.timeout,
            )
        ]

    def test_print(
        self,
        tokens: list[RequestPackage],
        processed_tokens: Optional[Any] = None,
    ) -> RequestPackage:
        """
        Displays a structured 'Dry Run' of the Request.
        Returns the first RequestPackage for programmatic inspection.
        """
        if not tokens or not isinstance(tokens[0], RequestPackage):
            print("!!! No RequestPackage found to test !!!")
            return None

        pkg = tokens[0]

        print(f"--- DRY RUN: {self.name} ---")
        print(f"METHOD:  {pkg.method}")
        print(f"URL:     {pkg.url}")

        if pkg.params:
            print(f"QUERY:   {pkg.params}")
        else:
            print("QUERY:   (None)")

        if pkg.json_body:
            import json

            try:
                body_str = json.dumps(pkg.json_body, indent=4)
                print(f"BODY:\n{body_str}")
            except:
                print(f"BODY:    {pkg.json_body}")
        else:
            print("BODY:    (None)")

        if pkg.headers:
            masked_headers = {
                k: ("********" if k.lower() in ["authorization", "token", "key"] else v)
                for k, v in pkg.headers.items()
            }
            print(f"HEADERS: {masked_headers}")

        print(f"TIMEOUT: {pkg.timeout}s")
        print("----------------------------\n")

        return pkg

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
