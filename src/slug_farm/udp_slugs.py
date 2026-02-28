import json
import socket
import copy
from time import sleep
from uuid import uuid4
from typing import Any, Optional, List, Callable
from src.slug_farm.base import Slug, SlugResult, CommandSegment


def upd_kwarg_formatter(kwargs: dict[str, Any]) -> dict[str, Any]:
    return kwargs



def udp_payload_formatter(kwargs: dict[str, Any]) -> dict[str, Any]:
    """
    For UDP, the formatter just ensures we have a clean dict.
    We can also use this to enforce specific types or hidden fields.
    """
    return copy.deepcopy(kwargs)

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
            kwarg_formatter=udp_payload_formatter,
            command_formatter=lambda x: x 
        )

        self.url = url
        self.port = port
        self.burst_size = burst_size
        self.burst_delay = burst_delay_ms / 1000.0
        self.encoding = encoding
        self.sock_family = sock_family
        self.sock_type = sock_type

    def _test_print(self, tokens: list[tuple[Any, dict]]):
        """Override to show the final JSON payload and destination."""
        final_payload = self._merge_payload(tokens)
        print(f"Target  : {self.url}:{self.port}")
        print(f"Burst   : {self.burst_size} pkts ({self.burst_delay}ms delay)")
        print(f"Payload : {json.dumps(final_payload, indent=2)}")

    def _merge_payload(self, tokens: list[tuple[Any, dict]]) -> dict:
        """Merges all segments into a single JSON dictionary."""
        merged = {}
        for cmd, kwargs in tokens:
            merged.update(kwargs)
            if cmd and cmd != "None":
                merged["command"] = cmd
        
        merged["udp_id"] = str(uuid4())
        return merged

    def execute(self, tokens: list[tuple[Any, dict]]) -> SlugResult:
        payload_dict = self._merge_payload(tokens)
        message = json.dumps(payload_dict).encode(self.encoding)

        critical_i = self.burst_size - 1
        try:
            with socket.socket(self.sock_family, self.sock_type) as sock:
                for i in range(self.burst_size):
                    sock.sendto(message, (self.url, self.port))
                    if i < critical_i:
                        sleep(self.burst_delay)
            
            return SlugResult(
                ok=True,
                status=200,
                output=payload_dict,
                tokens=tokens
            )
        except Exception as e:
            return SlugResult(
                ok=False,
                status=500,
                output=payload_dict,
                error=str(e),
                tokens=tokens
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
