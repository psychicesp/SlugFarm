import copy
import json
import socket
from time import sleep
from typing import Any
from uuid import uuid4

from src.slug_farm.base import Slug, SlugResult


def upd_kwarg_formatter(kwargs: dict[str, Any]) -> dict[str, Any]:
    return kwargs


class UDP_Slug(Slug):
    def __init__(
        self,
        name: str,
        url: str,
        port: int,
        base_kwargs: dict = {},
        burst_size=1,
        burst_delay=20,
        encoding="utf-8",
        sock_family=socket.AF_INET,
        sock_type=socket.SOCK_DGRAM,
    ):
        super().__init__(
            name,
            kwarg_formatter=upd_kwarg_formatter,
        )

        self.url = url
        self.port = port
        self.burst_size = burst_size
        self.burst_delay = burst_delay / 1000
        self.encoding = encoding
        self.sock_family = sock_family
        self.sock_type = sock_type
        self.base_kwargs = base_kwargs

    def execute(self, command="", task_kwargs: dict = {}) -> SlugResult:
        udp_id = str(uuid4())

        base_kwargs = copy.deepcopy(self.base_kwargs)

        base_kwargs.update(task_kwargs)

        base_kwargs.update(
            {
                "command": command,
                "id": udp_id,
            }
        )

        message = json.dumps(base_kwargs).encode(self.encoding)

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
                    output=base_kwargs,
                    tokens=[],
                )
        except Exception as e:
            return SlugResult(
                ok=False,
                status=500,
                output=base_kwargs,
                error=str(e),
                tokens=[],
            )
