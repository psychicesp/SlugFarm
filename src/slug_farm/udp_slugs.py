import copy
import json
import socket
from time import sleep
from typing import Any, List, Optional
from uuid import uuid4

from src.slug_farm.base import CommandSegment, Slug, SlugResult


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
        sock_family=socket.AF_INET,
        sock_type=socket.SOCK_DGRAM,
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

    def branch(self, **kwargs):
        print("UDP_Slug does not yet support branching")
        attr_dict = self.__dict__.copy()
        attr_dict.update(kwargs)
        return UDP_Slug(
            name=f"{attr_dict.pop('name')}.{attr_dict.pop('branch_name')}",
            base_command_segments=attr_dict.pop("command_segments"),
            burst_delay_ms=attr_dict.pop("burst_delay") * 1000,
            **attr_dict,
        )

    def test_print(
        self,
        tokens: list[tuple[Any, dict]],
        processed_tokens: Optional[Any] = None,
    ):
        """Override to show the final JSON payload and destination."""
        print(f"Target  : {self.url}:{self.port}")
        print(f"Burst   : {self.burst_size} pkts ({self.burst_delay * 1000} ms delay)")
        print(f"Payload : {json.dumps(processed_tokens, indent=2)}")

    def format_kwargs(
        self, kwargs: Optional[dict[str, Any] | None] = None
    ) -> dict[str, Any]:
        """
        For UDP, the formatter just ensures we have a clean dict.
        """
        if kwargs:
            return copy.deepcopy(kwargs)
        return {}

    def process_tokens(self, tokens: list[tuple[Any, dict]]) -> dict:
        """Merges all segments into a single JSON dictionary."""
        merged = {}
        for cmd, kwargs in tokens:
            merged.update(kwargs)
            if cmd and cmd != "None":
                merged["command"] = cmd

        merged["udp_id"] = str(uuid4())
        return merged

    def execute(
        self,
        tokens: list[tuple[Any, dict]],
        processed_tokens: Optional[Any] = None,
    ) -> SlugResult:
        message = json.dumps(processed_tokens).encode(self.encoding)

        critical_i = self.burst_size - 1
        try:
            with socket.socket(self.sock_family, self.sock_type) as sock:
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


# class UDP_Slug(Slug):
#     def __init__(
#         self,
#         name: str,
#         url: str,
#         port: int,
#         base_kwargs: dict = {},
#         burst_size=1,
#         burst_delay=20,
#         encoding="utf-8",
#         sock_family=socket.AF_INET,
#         sock_type=socket.SOCK_DGRAM,
#     ):
#         super().__init__(
#             name,
#             kwarg_formatter=upd_kwarg_formatter,
#         )

#         self.url = url
#         self.port = port
#         self.burst_size = burst_size
#         self.burst_delay = burst_delay / 1000
#         self.encoding = encoding
#         self.sock_family = sock_family
#         self.sock_type = sock_type
#         self.base_kwargs = base_kwargs

#     def execute(self, command="", task_kwargs: dict = {}) -> SlugResult:
#         udp_id = str(uuid4())

#         base_kwargs = copy.deepcopy(self.base_kwargs)

#         base_kwargs.update(task_kwargs)

#         base_kwargs.update(
#             {
#                 "command": command,
#                 "id": udp_id,
#             }
#         )

#         message = json.dumps(base_kwargs).encode(self.encoding)

#         critical_i = self.burst_size - 1
#         try:
#             with socket.socket(self.sock_family, self.sock_type) as sock:
#                 for i in range(self.burst_size):
#                     sock.sendto(message, (self.url, self.port))
#                     if i < critical_i:
#                         sleep(self.burst_delay)
#                 return SlugResult(
#                     ok=True,
#                     status=200,
#                     output=base_kwargs,
#                     tokens=[],
#                 )
#         except Exception as e:
#             return SlugResult(
#                 ok=False,
#                 status=500,
#                 output=base_kwargs,
#                 error=str(e),
#                 tokens=[],
#             )
