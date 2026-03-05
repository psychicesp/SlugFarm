import copy
import json
from dataclasses import dataclass
from socket import AF_INET, SOCK_DGRAM, AddressFamily, SocketKind, socket
from time import sleep
from typing import Any, List, Optional
from uuid import uuid4

from yarl import URL

from slug_farm.base import CommandSegment, Slug, SlugResult


@dataclass(slots=True)
class UDP_Package:
    """Internal transport for UDP data through the Slug pipeline."""

    target: str
    body: dict


class UDP_Slug(Slug):
    def __init__(
        self,
        name: str,
        url: str,
        port: int,
        command: Optional[str] = None,
        slug_kwargs: Optional[dict[str, Any]] = None,
        base_command_segments: Optional[List[CommandSegment]] = None,
        burst_size: int = 1,
        burst_delay_ms: int = 20,
        encoding: str = "utf-8",
        sock_family: AddressFamily = AF_INET,
        sock_type: SocketKind = SOCK_DGRAM,
    ):
        super().__init__(
            name=name,
            command=command,
            slug_kwargs=slug_kwargs,
            base_command_segments=base_command_segments,
        )

        self.url = url
        self.port = port
        self.burst_size = burst_size
        self.burst_delay = burst_delay_ms / 1000.0
        self.encoding = encoding
        self.sock_family = sock_family
        self.sock_type = sock_type

    def branch(
        self,
        branch_name: str,
        url_extension: str | None = None,
        new_port: int | None = None,
        command: Optional[str] = None,
        slug_kwargs: Optional[dict[str, Any]] = None,
        burst_size: int | None = None,
        burst_delay_ms: int | None = None,
        encoding: str | None = None,
        sock_family: AddressFamily | None = None,
        sock_type: SocketKind | None = None,
    ):
        new_segments = self.add_command(command, slug_kwargs)

        if url_extension:
            new_url_obj = URL(self.url) / url_extension.lstrip("/")
            new_url = new_url_obj.path
        else:
            new_url = self.url

        return self.__class__(
            name=f"{self.name}.{branch_name}",
            url=new_url,
            port=new_port or self.port,
            command=None,
            slug_kwargs=None,
            base_command_segments=new_segments,
            burst_size=burst_size or self.burst_size,
            burst_delay_ms=burst_delay_ms or int(self.burst_delay * 1000),
            encoding=encoding or self.encoding,
            sock_family=sock_family or self.sock_family,
            sock_type=sock_type or self.sock_type,
        )

    def test_print(
        self,
        tokens: list[tuple[Any, dict]],
        processed_tokens: UDP_Package,
    ) -> UDP_Package:
        """Override to show the final JSON payload and destination."""
        print(f"Target  : {self.url}:{self.port}")
        print(f"Burst   : {self.burst_size} pkts ({self.burst_delay * 1000} ms delay)")
        print(f"Payload : {json.dumps(processed_tokens.body, indent=2)}")
        return processed_tokens

    def format_kwargs(
        self, kwargs: Optional[dict[str, Any] | None] = None
    ) -> dict[str, Any]:
        """
        For UDP, the formatter just ensures we have a clean dict.
        """
        if kwargs:
            return copy.deepcopy(kwargs)
        return {}

    def process_tokens(self, tokens: list[tuple[Any, dict]]) -> UDP_Package:
        """Merges all segments into a single JSON dictionary."""
        merged = {}
        for cmd, kwargs in tokens:
            merged.update(kwargs)
            if cmd and cmd != "None":
                merged["command"] = cmd

        merged["udp_id"] = str(uuid4())
        return UDP_Package(target=f"{self.url}:{self.port}", body=merged)

    def execute(
        self,
        tokens: list[tuple[Any, dict]],
        processed_tokens: UDP_Package,
    ) -> SlugResult:
        message = json.dumps(processed_tokens.body).encode(self.encoding)

        critical_i = self.burst_size - 1
        try:
            with socket(self.sock_family, self.sock_type) as sock:
                for i in range(self.burst_size):
                    sock.sendto(message, (self.url, self.port))
                    if i < critical_i:
                        sleep(self.burst_delay)

            return SlugResult(
                ok=True, status=200, output=processed_tokens, tokens=tokens
            )
        except Exception as e:
            return SlugResult(
                ok=False,
                status=500,
                output=processed_tokens,
                error=str(e),
                tokens=tokens,
            )
